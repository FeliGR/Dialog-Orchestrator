#!/usr/bin/env python3
"""
MPI Assessment Results Aggregator

This module provides functionality to aggregate and analyze MPI assessment results,
including trait scoring, validation, and comparison with personality snapshots.
"""

import json
import statistics
from typing import Dict, List, Any, Optional, Tuple
import math

# Score mapping from A-E to numerical values
SCORES = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}

# Trait mapping
TRAIT_MAPPING = {
    "N": "neuroticism",
    "E": "extraversion", 
    "O": "openness",
    "A": "agreeableness",
    "C": "conscientiousness"
}


class MPIResultsAggregator:
    """
    Aggregator for MPI assessment results with validation and analysis capabilities.
    """
    
    def __init__(self):
        self.results_data = None
        self.aggregated = None
        
    def load_results(self, json_path: str) -> Dict[str, Any]:
        """Load results from JSON file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            self.results_data = json.load(f)
        return self.results_data
    
    def aggregate_traits(self, results_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Aggregate results by trait with comprehensive analysis.
        
        Args:
            results_data: Optional results data, uses loaded data if None
            
        Returns:
            Dict with aggregated trait analysis
        """
        data = results_data or self.results_data
        if not data:
            raise ValueError("No results data available. Load results first.")
            
        # Initialize containers
        traits = {"O": [], "C": [], "E": [], "A": [], "N": []}
        choice_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "UNK": 0}
        item_analysis = []
        unk_items = []
        
        # Process each result
        for i, result in enumerate(data["results"]):
            choice = result["parsed_choice"]
            choice_counts[choice if choice in SCORES else "UNK"] += 1
            
            # Skip unknown responses
            if choice not in SCORES:
                unk_items.append({
                    "index": i,
                    "label_raw": result.get("label_raw", ""),
                    "raw_output": result.get("raw_output", ""),
                    "item_text": result.get("item_text", "")
                })
                continue
                
            # Convert choice to score
            score = SCORES[choice]
            key = int(result.get("key", 1))
            
            # Apply reverse scoring for negative-keyed items
            if key != 1:
                score = 6 - score
                
            # Add to trait
            trait_code = result["label_ocean"]
            if trait_code in traits:
                traits[trait_code].append(score)
                
            # Item-level analysis
            item_analysis.append({
                "index": i,
                "label_raw": result.get("label_raw", ""),
                "trait_code": trait_code,
                "trait_name": TRAIT_MAPPING.get(trait_code, "unknown"),
                "item_text": result.get("item_text", ""),
                "choice": choice,
                "raw_score": SCORES[choice],
                "key": key,
                "final_score": score,
                "latency_ms": result.get("latency_ms", 0)
            })
        
        # Calculate trait statistics
        trait_summary = {}
        for trait_code, scores in traits.items():
            if scores:
                trait_summary[trait_code] = {
                    "trait_name": TRAIT_MAPPING.get(trait_code, "unknown"),
                    "n_items": len(scores),
                    "mean": statistics.mean(scores),
                    "std": statistics.stdev(scores) if len(scores) > 1 else 0.0,
                    "min": min(scores),
                    "max": max(scores),
                    "scores": scores,
                    "median": statistics.median(scores)
                }
            else:
                trait_summary[trait_code] = {
                    "trait_name": TRAIT_MAPPING.get(trait_code, "unknown"),
                    "n_items": 0,
                    "mean": float("nan"),
                    "std": float("nan"),
                    "min": float("nan"), 
                    "max": float("nan"),
                    "scores": [],
                    "median": float("nan")
                }
        
        # Overall statistics
        total_items = len(data["results"])
        valid_items = sum(len(scores) for scores in traits.values())
        
        self.aggregated = {
            "metadata": {
                "user_id": data.get("user_id", ""),
                "timestamp": data.get("timestamp", 0),
                "total_items": total_items,
                "valid_items": valid_items,
                "unk_items": len(unk_items),
                "completion_rate": valid_items / total_items if total_items > 0 else 0
            },
            "choice_counts": choice_counts,
            "trait_summary": trait_summary,
            "item_analysis": item_analysis,
            "unk_items": unk_items,
            "quality_metrics": self._calculate_quality_metrics(choice_counts, trait_summary)
        }
        
        return self.aggregated
    
    def _calculate_quality_metrics(self, choice_counts: Dict[str, int], trait_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality and consistency metrics."""
        total_valid = sum(choice_counts[c] for c in SCORES.keys())
        
        # Response distribution
        choice_dist = {k: v / total_valid for k, v in choice_counts.items() if k in SCORES} if total_valid > 0 else {}
        
        # Extreme response bias (A + E) / total
        extreme_bias = (choice_counts.get("A", 0) + choice_counts.get("E", 0)) / total_valid if total_valid > 0 else 0
        
        # Average standard deviation across traits (consistency)
        trait_stds = [summary["std"] for summary in trait_summary.values() if not math.isnan(summary["std"])]
        avg_within_trait_std = statistics.mean(trait_stds) if trait_stds else float("nan")
        
        return {
            "choice_distribution": choice_dist,
            "extreme_response_bias": extreme_bias,
            "avg_within_trait_consistency": avg_within_trait_std,
            "response_variability": statistics.stdev(choice_counts[c] for c in SCORES.keys()) if total_valid > 0 else 0
        }
    
    def compare_with_persona(self, persona_data: Dict[str, float]) -> Dict[str, Any]:
        """
        Compare aggregated traits with original persona data.
        
        Args:
            persona_data: Dict with trait values (e.g., {"openness": 3.0, ...})
            
        Returns:
            Comparison analysis
        """
        if not self.aggregated:
            raise ValueError("No aggregated data available. Run aggregate_traits first.")
            
        comparisons = {}
        correlations = []
        errors = []
        
        # Map persona data to trait codes
        persona_mapped = {}
        
        # First try direct mapping by trait codes (O, C, E, A, N)
        for code in ["O", "C", "E", "A", "N"]:
            if code in persona_data:
                persona_mapped[code] = persona_data[code]
        
        # If no direct codes, try mapping by full names
        if not persona_mapped:
            for full_name, value in persona_data.items():
                for code, name in TRAIT_MAPPING.items():
                    if name.lower() == full_name.lower():
                        persona_mapped[code] = value
                        break
        
        # Compare each trait
        for trait_code, summary in self.aggregated["trait_summary"].items():
            if trait_code in persona_mapped and not math.isnan(summary["mean"]):
                persona_value = persona_mapped[trait_code]
                measured_value = summary["mean"]
                error = measured_value - persona_value
                abs_error = abs(error)
                
                comparisons[trait_code] = {
                    "trait_name": summary["trait_name"],
                    "persona_value": persona_value,
                    "measured_value": measured_value,
                    "error": error,
                    "abs_error": abs_error,
                    "relative_error": error / persona_value if persona_value != 0 else float("inf"),
                    "n_items": summary["n_items"],
                    "std": summary["std"]
                }
                
                # For overall correlation
                correlations.append((persona_value, measured_value))
                errors.append(abs_error)
        
        # Overall metrics
        if correlations:
            persona_values, measured_values = zip(*correlations)
            correlation = self._pearson_correlation(persona_values, measured_values)
            mae = statistics.mean(errors)
            rmse = math.sqrt(statistics.mean([e**2 for e in [comp["error"] for comp in comparisons.values()]]))
        else:
            correlation = float("nan")
            mae = float("nan") 
            rmse = float("nan")
        
        return {
            "persona_snapshot": persona_mapped,
            "trait_comparisons": comparisons,
            "overall_metrics": {
                "correlation": correlation,
                "mean_absolute_error": mae,
                "root_mean_square_error": rmse,
                "traits_compared": len(comparisons)
            }
        }
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return float("nan")
            
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_x_sq = sum(xi**2 for xi in x)
        sum_y_sq = sum(yi**2 for yi in y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x_sq - sum_x**2) * (n * sum_y_sq - sum_y**2))
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def generate_report(self, output_path: str, persona_data: Optional[Dict[str, float]] = None) -> str:
        """
        Generate a comprehensive analysis report.
        
        Args:
            output_path: Path to save the report
            persona_data: Optional persona data for comparison
            
        Returns:
            Report as string
        """
        if not self.aggregated:
            raise ValueError("No aggregated data available. Run aggregate_traits first.")
            
        lines = []
        lines.append("# MPI Assessment Analysis Report")
        lines.append("=" * 50)
        lines.append("")
        
        # Metadata
        meta = self.aggregated["metadata"]
        lines.append(f"**User ID:** {meta['user_id']}")
        lines.append(f"**Total Items:** {meta['total_items']}")
        lines.append(f"**Valid Items:** {meta['valid_items']}")
        lines.append(f"**Unknown Responses:** {meta['unk_items']}")
        lines.append(f"**Completion Rate:** {meta['completion_rate']:.1%}")
        lines.append("")
        
        # Choice distribution
        lines.append("## Response Distribution")
        lines.append("| Choice | Count | Percentage |")
        lines.append("|--------|-------|------------|")
        for choice in ["A", "B", "C", "D", "E", "UNK"]:
            count = self.aggregated["choice_counts"][choice]
            pct = count / meta['total_items'] * 100
            lines.append(f"| {choice} | {count} | {pct:.1f}% |")
        lines.append("")
        
        # Trait summary
        lines.append("## Trait Summary")
        lines.append("| Trait | Name | Mean | Std | N Items |")
        lines.append("|-------|------|------|-----|---------|")
        for trait_code in ["O", "C", "E", "A", "N"]:
            summary = self.aggregated["trait_summary"][trait_code]
            mean_str = f"{summary['mean']:.2f}" if not math.isnan(summary['mean']) else "N/A"
            std_str = f"{summary['std']:.2f}" if not math.isnan(summary['std']) else "N/A"
            lines.append(f"| {trait_code} | {summary['trait_name']} | {mean_str} | {std_str} | {summary['n_items']} |")
        lines.append("")
        
        # Persona comparison if provided
        if persona_data:
            comparison = self.compare_with_persona(persona_data)
            lines.append("## Persona Comparison")
            lines.append("| Trait | Persona | Measured | Error | Abs Error |")
            lines.append("|-------|---------|----------|-------|-----------|")
            for trait_code in ["O", "C", "E", "A", "N"]:
                if trait_code in comparison["trait_comparisons"]:
                    comp = comparison["trait_comparisons"][trait_code]
                    lines.append(f"| {trait_code} | {comp['persona_value']:.1f} | {comp['measured_value']:.2f} | {comp['error']:+.2f} | {comp['abs_error']:.2f} |")
            lines.append("")
            lines.append(f"**Overall Correlation:** {comparison['overall_metrics']['correlation']:.3f}")
            lines.append(f"**Mean Absolute Error:** {comparison['overall_metrics']['mean_absolute_error']:.3f}")
            lines.append(f"**RMSE:** {comparison['overall_metrics']['root_mean_square_error']:.3f}")
            lines.append("")
        
        # Quality metrics
        quality = self.aggregated["quality_metrics"]
        lines.append("## Quality Metrics")
        lines.append(f"**Extreme Response Bias (A+E):** {quality['extreme_response_bias']:.1%}")
        lines.append(f"**Avg Within-Trait Consistency:** {quality['avg_within_trait_consistency']:.2f}")
        lines.append("")
        
        # UNK items if any
        if self.aggregated["unk_items"]:
            lines.append("## Items with Unknown Responses")
            for item in self.aggregated["unk_items"][:10]:  # Show first 10
                lines.append(f"- **{item['label_raw']}**: \"{item['item_text']}\" → \"{item['raw_output']}\"")
            if len(self.aggregated["unk_items"]) > 10:
                lines.append(f"... and {len(self.aggregated['unk_items']) - 10} more")
            lines.append("")
        
        report = "\n".join(lines)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        return report


def main():
    """Example usage of the aggregator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate MPI assessment results")
    parser.add_argument("--results", required=True, help="Path to results JSON file")
    parser.add_argument("--persona", help="Persona data as JSON string or file path")
    parser.add_argument("--output", default="analysis_report.md", help="Output report file")
    
    args = parser.parse_args()
    
    # Load and aggregate
    aggregator = MPIResultsAggregator()
    aggregator.load_results(args.results)
    aggregator.aggregate_traits()
    
    # Parse persona data if provided
    persona_data = None
    if args.persona:
        try:
            if args.persona.startswith('{'):
                persona_data = json.loads(args.persona)
            else:
                with open(args.persona, 'r') as f:
                    persona_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not parse persona data: {e}")
    
    # Generate report
    report = aggregator.generate_report(args.output, persona_data)
    print(f"Analysis complete! Report saved to: {args.output}")
    print("\nSummary:")
    print(f"Valid responses: {aggregator.aggregated['metadata']['valid_items']}/{aggregator.aggregated['metadata']['total_items']}")
    
    if persona_data:
        comparison = aggregator.compare_with_persona(persona_data)
        print(f"Correlation with persona: {comparison['overall_metrics']['correlation']:.3f}")


if __name__ == "__main__":
    main()
