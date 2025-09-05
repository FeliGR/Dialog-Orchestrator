#!/usr/bin/env python3
"""
Quick Test - Single NEUTRAL condition run to verify system functionality
"""
import os
import sys
import subprocess
import json
from pathlib import Path

# Configuration
ENGINE_URL = os.getenv("ENGINE_URL", "http://localhost:5001")
DIALOG_URL = os.getenv("DIALOG_URL", "http://localhost:5002")
SEED = 111
USER_ID = "NEUTRAL"


def set_persona_neutral():
    """Configure NEUTRAL persona"""
    script_path = Path(__file__).parent.parent / "scripts" / "set_persona.sh"
    cmd = ["bash", str(script_path), USER_ID, "3", "3", "3", "3", "3"]
    subprocess.run(cmd, check=True, env={**os.environ, "ENGINE_URL": ENGINE_URL})
    print(f"Persona {USER_ID} configured successfully")


def run_quick_test():
    """Execute single MPI assessment"""
    print(f"\nRunning quick test: {USER_ID}, seed={SEED}")

    # Prepare directories
    runs_dir = Path(__file__).parent.parent / "runs"
    test_dir = runs_dir / "quick-test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Output file
    output_file = test_dir / f"quick_test_seed_{SEED}.json"

    # Execute MPI runner
    csv_path = Path(__file__).parent.parent / "inventories" / "mpi_120.csv"
    runner_path = Path(__file__).parent.parent / "eval" / "run_mpi_http.py"

    args = [
        "python3",
        str(runner_path),
        "--csv",
        str(csv_path),
        "--url",
        f"{DIALOG_URL}",
        "--user",
        USER_ID,
        "--output",
        str(output_file),
        "--seed",
        str(SEED),
    ]

    print(f"Executing: {' '.join(args)}")
    subprocess.run(args, check=True)

    # Display basic results
    if output_file.exists():
        with open(output_file) as f:
            data = json.load(f)

        # JSON format uses "results" not "responses"
        valid_count = sum(
            1
            for r in data["results"]
            if (r.get("parsed_choice") or r.get("response"))
            in ("A", "B", "C", "D", "E")
        )
        total_count = len(data["results"])

    print(f"Test completed: {valid_count}/{total_count} valid responses")
    print(f"Results saved to: {output_file}")
    print("")  # Add spacing

    # Generate aggregated report
    print("Generating aggregated analysis...")
    generate_quick_report(output_file)

    return output_file


def generate_quick_report(json_file: Path):
    """Generate aggregated report for quick test results"""
    # Import aggregator
    sys.path.append(str(Path(__file__).parent.parent / "eval"))
    from mpi_aggregator import MPIResultsAggregator

    # Create report file
    report_file = json_file.with_suffix(".md")

    # NEUTRAL persona for comparison
    neutral_persona = {
        "openness": 3.0,
        "conscientiousness": 3.0,
        "extraversion": 3.0,
        "agreeableness": 3.0,
        "neuroticism": 3.0,
    }

    try:
        # Load and aggregate results
        agg = MPIResultsAggregator()
        agg.load_results(str(json_file))
        agg.aggregate_traits()

        # Generate markdown report
        agg.generate_report(str(report_file), neutral_persona)

        # Display key metrics
        traits = agg.aggregated["trait_summary"]
        print(f"\nBig Five Results:")
        for trait, values in traits.items():
            mean_val = values["mean"]
            print(f"  {trait}: {mean_val:.3f}")

        # Quality metrics
        quality = agg.aggregated["quality_metrics"]
        completion_rate = agg.aggregated["metadata"]["completion_rate"]
        unk_count = agg.aggregated["choice_counts"].get("UNK", 0)

        print(f"\nQuality Metrics:")
        print(f"  Completion rate: {completion_rate:.3f}")
        print(f"  UNK responses: {unk_count}")
        print(f"  Extreme bias: {quality['extreme_response_bias']:.3f}")

        # Persona comparison
        comparison = agg.compare_with_persona(neutral_persona)
        corr = comparison["overall_metrics"]["correlation"]
        mae = comparison["overall_metrics"]["mean_absolute_error"]

        print(f"\nPersona Comparison:")
        import math

        if math.isnan(corr):
            print(f"  Correlation: N/A (constant reference vector)")
        else:
            print(f"  Correlation: {corr:.3f}")
        print(f"  Mean Absolute Error: {mae:.3f}")

        print(f"\nDetailed report saved to: {report_file}")

    except Exception as e:
        print(f"Warning: Could not generate aggregated report: {e}")
        print("Raw JSON results are still available")


def main():
    print("")
    print("QUICK TEST - Single NEUTRAL condition assessment")
    print("=" * 50)
    print("")

    try:
        # 1. Configure persona
        set_persona_neutral()
        print("")

        # 2. Execute test
        result_file = run_quick_test()

        print("=" * 50)
        print("Quick test completed successfully")
        print(f"Result file: {result_file}")
        print("")

    except Exception as e:
        print(f"ERROR: Quick test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
