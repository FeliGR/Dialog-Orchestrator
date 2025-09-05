#!/usr/bin/env python3
"""
Global summary generator - Scans runs/ directory and creates consolidated summary.csv
"""
import json
import csv
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Score mapping from A-E to numerical values
SCORES = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


def score_item(result: dict) -> Tuple[str, Optional[float]]:
    """
    Score a single item with proper reverse scoring.

    Args:
        result: Item result dictionary

    Returns:
        Tuple of (trait_code, score) where score is None if invalid
    """
    # Use parsed_choice if available, otherwise response
    choice = result.get("parsed_choice") or result.get("response") or "UNK"

    if choice not in SCORES:
        return result.get("label_ocean", ""), None

    score = SCORES[choice]
    key = int(result.get("key", 1))

    # Apply reverse scoring if key != 1
    if key != 1:
        score = 6 - score

    return result.get("label_ocean", ""), float(score)


def scan_run_files(runs_dir: Path) -> List[Dict[str, Any]]:
    """Scan all JSON result files in runs directory"""
    results = []

    for condition_dir in runs_dir.iterdir():
        if not condition_dir.is_dir() or condition_dir.name.startswith("."):
            continue

        condition_name = condition_dir.name

        for json_file in condition_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})

                # Extract run parameters from filename or metadata
                filename = json_file.stem  # e.g., "NEUTRAL__seed-111__order-None"
                parts = filename.split("__")

                seed = None
                order = None
                for part in parts[1:]:  # Skip condition name
                    if part.startswith("seed-"):
                        seed = part.split("-", 1)[1]
                    elif part.startswith("order-"):
                        order_val = part.split("-", 1)[1]
                        order = order_val if order_val != "None" else None

                # Calculate trait means from results with proper reverse scoring
                trait_totals = {"O": [], "C": [], "E": [], "A": [], "N": []}
                valid_responses = 0
                unknown_responses = 0

                for result in data.get("results", []):
                    trait, score = score_item(result)
                    if score is None:
                        unknown_responses += 1
                        continue
                    if trait in trait_totals:
                        trait_totals[trait].append(score)
                        valid_responses += 1

                # Calculate means
                trait_means = {}
                for trait, scores in trait_totals.items():
                    trait_means[f"{trait}_mean"] = (
                        statistics.mean(scores) if scores else 0
                    )

                # Calculate quality metrics
                total_responses = valid_responses + unknown_responses
                unk_rate = (
                    unknown_responses / total_responses if total_responses > 0 else 0
                )

                # Get latency percentiles
                latencies = [r.get("latency_ms", 0) for r in data.get("results", [])]
                p95_latency = (
                    statistics.quantiles(latencies, n=20)[18]
                    if len(latencies) >= 20
                    else (max(latencies) if latencies else 0)
                )

                # Compile summary entry
                entry = {
                    "condition": condition_name,
                    "seed": seed or "unknown",
                    "order": order or "None",
                    "valid_responses": valid_responses,
                    "total_responses": total_responses,
                    "unk_rate": unk_rate,
                    "duration_seconds": metadata.get("duration_seconds", 0),
                    "avg_latency_ms": metadata.get("avg_latency_ms", 0),
                    "p95_latency_ms": p95_latency,
                    "total_tokens": metadata.get("total_tokens", 0),
                    **trait_means,
                }

                # Try to load analysis results if available
                md_file = json_file.with_suffix(".md")
                if md_file.exists():
                    try:
                        with open(md_file) as f:
                            content = f.read()
                            # Extract correlation if present
                            for line in content.split("\n"):
                                if "Correlation with persona:" in line:
                                    try:
                                        corr_val = line.split(":")[1].strip()
                                        entry["correlation"] = float(corr_val)
                                    except:
                                        pass
                                elif "MAE:" in line:
                                    try:
                                        mae_val = (
                                            line.split("MAE:")[1].split(",")[0].strip()
                                        )
                                        entry["mae"] = float(mae_val)
                                    except:
                                        pass
                                elif "RMSE:" in line:
                                    try:
                                        rmse_val = line.split("RMSE:")[1].strip()
                                        entry["rmse"] = float(rmse_val)
                                    except:
                                        pass
                    except:
                        pass

                results.append(entry)

            except Exception as e:
                print(f"Warning: Error processing {json_file} - {e}")
                continue

    return results


def write_summary_csv(results: List[Dict[str, Any]], output_file: Path):
    """Write results to CSV file"""
    if not results:
        print("Warning: No results to write")
        return

    # Define column order
    columns = [
        "condition",
        "seed",
        "order",
        "valid_responses",
        "total_responses",
        "unk_rate",
        "O_mean",
        "C_mean",
        "E_mean",
        "A_mean",
        "N_mean",
        "correlation",
        "mae",
        "rmse",
        "duration_seconds",
        "avg_latency_ms",
        "p95_latency_ms",
        "total_tokens",
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()

        # Sort by condition, then seed, then order
        sorted_results = sorted(
            results, key=lambda x: (x["condition"], x["seed"], x["order"])
        )

        for row in sorted_results:
            # Ensure all numeric fields are present
            for col in columns:
                if col not in row:
                    row[col] = (
                        0
                        if col.endswith(
                            (
                                "_mean",
                                "_rate",
                                "_seconds",
                                "_ms",
                                "_tokens",
                                "correlation",
                                "mae",
                                "rmse",
                            )
                        )
                        else ""
                    )
            writer.writerow(row)


def main():
    print("")
    print("GLOBAL SUMMARY GENERATION")
    print("=" * 40)

    runs_dir = Path("runs")
    if not runs_dir.exists():
        print("ERROR: runs/ directory not found")
        return

    print(f"Scanning {runs_dir}...")
    results = scan_run_files(runs_dir)

    if not results:
        print("ERROR: No result files found")
        return

    print(f"Processed {len(results)} experimental runs")

    # Group by condition for summary stats
    by_condition = {}
    for result in results:
        condition = result["condition"]
        if condition not in by_condition:
            by_condition[condition] = []
        by_condition[condition].append(result)

    print(f"Conditions found: {', '.join(sorted(by_condition.keys()))}")

    # Write summary
    output_file = runs_dir / "summary.csv"
    write_summary_csv(results, output_file)

    print(f"Summary generated: {output_file}")
    print(f"Total experiments: {len(results)}")

    # Show quick statistics
    total_tokens = sum(r.get("total_tokens", 0) for r in results)
    avg_unk_rate = statistics.mean([r.get("unk_rate", 0) for r in results])

    print(f"Total tokens consumed: {total_tokens:,}")
    print(f"Average UNK rate: {avg_unk_rate:.3f}")
    print("")


if __name__ == "__main__":
    main()
