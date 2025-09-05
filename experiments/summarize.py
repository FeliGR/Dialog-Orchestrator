#!/usr/bin/env python3
"""
Global summary generator - Scans runs/ directory and creates consolidated summary.csv
Calculates correlation/MAE/RMSE using the aggregator (no MD scraping).
"""
import json
import csv
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import sys

# --- Path to import the aggregator -------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from eval.mpi_aggregator import MPIResultsAggregator  # type: ignore

# Score mapping from A-E to numerical values
SCORES = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


def score_item(result: dict) -> Tuple[str, Optional[float]]:
    """
    Score a single item with proper reverse scoring.

    Returns:
        Tuple of (trait_code, score) where score is None if invalid
    """
    # Prefer parsed_choice, else response (backward compat)
    choice = result.get("parsed_choice") or result.get("response") or "UNK"
    if choice not in SCORES:
        return result.get("label_ocean", ""), None

    score = SCORES[choice]
    key = int(result.get("key", 1))
    if key != 1:
        score = 6 - score
    return result.get("label_ocean", ""), float(score)


# Personas por condición (de experiments/run_all.py)
def persona_for_condition(condition: str) -> Optional[Dict[str, float]]:
    base = {
        "openness": 3.0,
        "conscientiousness": 3.0,
        "extraversion": 3.0,
        "agreeableness": 3.0,
        "neuroticism": 3.0,
    }
    cond = condition.upper()

    if cond == "NEUTRAL":
        return base
    if cond == "E_HIGH":
        p = dict(base)
        p["extraversion"] = 4.5
        return p
    if cond == "C_HIGH":
        p = dict(base)
        p["conscientiousness"] = 4.5
        return p
    if cond == "N_LOW":
        p = dict(base)
        p["neuroticism"] = 2.0
        return p
    if cond == "E_20":
        p = dict(base)
        p["extraversion"] = 2.0
        return p
    if cond == "E_30":
        p = dict(base)
        p["extraversion"] = 3.0
        return p
    if cond == "E_40":
        p = dict(base)
        p["extraversion"] = 4.0
        return p
    if cond == "E_50":
        p = dict(base)
        p["extraversion"] = 5.0
        return p
    if cond == "TEST_USER":
        return {
            "openness": 3.0,
            "conscientiousness": 4.2,
            "extraversion": 4.5,
            "agreeableness": 3.0,
            "neuroticism": 2.1,
        }
    # Para directorios no experimentales (ej. quick-test), no calculamos correlación
    return None


def scan_run_files(runs_dir: Path) -> List[Dict[str, Any]]:
    """Scan all JSON result files in runs directory"""
    results: List[Dict[str, Any]] = []

    for condition_dir in runs_dir.iterdir():
        if not condition_dir.is_dir() or condition_dir.name.startswith("."):
            continue

        condition_name = condition_dir.name

        for json_file in condition_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})

                # Extract seed / order del nombre de archivo
                filename = json_file.stem  # p.ej., "NEUTRAL__seed-111__order-None"
                parts = filename.split("__")
                seed = None
                order = None
                for part in parts[1:]:
                    if part.startswith("seed-"):
                        seed = part.split("-", 1)[1]
                    elif part.startswith("order-"):
                        order_val = part.split("-", 1)[1]
                        order = order_val if order_val != "None" else None

                # Medias por rastrillado con reverse scoring
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

                trait_means = {}
                for trait, scores in trait_totals.items():
                    trait_means[f"{trait}_mean"] = (
                        statistics.mean(scores) if scores else 0.0
                    )

                total_responses = valid_responses + unknown_responses
                unk_rate = (
                    (unknown_responses / total_responses)
                    if total_responses > 0
                    else 0.0
                )

                latencies = [r.get("latency_ms", 0) for r in data.get("results", [])]
                p95_latency = (
                    statistics.quantiles(latencies, n=20)[18]
                    if len(latencies) >= 20
                    else (max(latencies) if latencies else 0)
                )

                # --- NUEVO: calcular corr/MAE/RMSE con el agregador -----------------
                corr = float("nan")
                mae = float("nan")
                rmse = float("nan")
                try:
                    persona = persona_for_condition(condition_name)
                    if persona:
                        agg = MPIResultsAggregator()
                        agg.load_results(str(json_file))
                        agg.aggregate_traits()
                        comp = agg.compare_with_persona(persona)
                        om = comp.get("overall_metrics", {})
                        corr = om.get("correlation", float("nan"))
                        mae = om.get("mean_absolute_error", float("nan"))
                        rmse = om.get("root_mean_square_error", float("nan"))
                except Exception as e:
                    # No abortar el resumen por fallos de un archivo
                    print(
                        f"Warning: correlation metrics failed for {json_file.name}: {e}"
                    )

                # Entrada consolidada
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
                    "correlation": corr,
                    "mae": mae,
                    "rmse": rmse,
                }

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
        sorted_results = sorted(
            results, key=lambda x: (x["condition"], x["seed"], x["order"])
        )
        for row in sorted_results:
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

    by_condition: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        by_condition.setdefault(result["condition"], []).append(result)
    print(f"Conditions found: {', '.join(sorted(by_condition.keys()))}")

    output_file = runs_dir / "summary.csv"
    write_summary_csv(results, output_file)

    print(f"Summary generated: {output_file}")
    print(f"Total experiments: {len(results)}")

    total_tokens = sum(r.get("total_tokens", 0) for r in results)
    avg_unk_rate = statistics.mean([r.get("unk_rate", 0) for r in results])
    print(f"Total tokens consumed: {total_tokens:,}")
    print(f"Average UNK rate: {avg_unk_rate:.3f}")
    print("")


if __name__ == "__main__":
    main()
