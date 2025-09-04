#!/usr/bin/env python3
"""
MPI HTTP Runner

This script provides an HTTP interface for running MPI (Multi-dimensional Personality Inventory)
assessments against the Dialog Orchestrator API.
"""

import argparse
import csv
import json
import sys
import time
from typing import Dict, List, Optional

import requests


class MPIHTTPRunner:
    """
    HTTP client for running MPI assessments against the Dialog Orchestrator API.
    """

    def __init__(self, base_url: str, user_id: str):
        """
        Initialize the MPI HTTP runner.

        Args:
            base_url (str): Base URL of the Dialog Orchestrator API
            user_id (str): User ID to use for the assessment
        """
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.session = requests.Session()

    def load_mpi_items(self, csv_path: str) -> List[Dict]:
        """
        Load MPI items from CSV file.

        Args:
            csv_path (str): Path to the MPI items CSV file

        Returns:
            List[Dict]: List of MPI items
        """
        items = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    items.append(row)
            print(f"Loaded {len(items)} MPI items from {csv_path}")
            return items
        except Exception as e:
            print(f"Error loading MPI items: {e}")
            sys.exit(1)

    def run_assessment(
        self,
        items: List[Dict],
        seed: Optional[int] = None,
        strict_output: bool = True,
        format_id: str = "MPI-120",
    ) -> List[Dict]:
        """
        Run MPI assessment for all items.

        Args:
            items (List[Dict]): MPI items to assess
            seed (Optional[int]): Random seed for reproducible results
            strict_output (bool): Whether to enforce strict output format
            format_id (str): Format identifier

        Returns:
            List[Dict]: Assessment results
        """
        results = []
        endpoint = f"{self.base_url}/api/dialog/{self.user_id}"

        print(f"Running MPI assessment with {len(items)} items...")
        print(f"API endpoint: {endpoint}")

        for i, item in enumerate(items, 1):
            item_text = item.get("text", "")
            if not item_text:
                print(f"Warning: Empty item text for item {i}")
                continue

            # Format the assessment question
            question = f'Given a statement of you: "You {item_text}."\n'
            question += "Please choose from the following options to identify how accurately this statement describes you.\n"
            question += "Options:\n"
            question += "(A). Very Accurate\n"
            question += "(B). Moderately Accurate\n"
            question += "(C). Neither Accurate Nor Inaccurate\n"
            question += "(D). Moderately Inaccurate\n"
            question += "(E). Very Inaccurate\n\n"
            question += "Answer:"

            payload = {
                "text": question,
                "eval": {
                    "type": "mpi_ae",
                    "strict_output": strict_output,
                    "seed": seed,
                    "format_id": format_id,
                },
            }

            try:
                print(
                    f"Processing item {i}/{len(items)}: {item.get('label_raw', 'unknown')}"
                )

                start_time = time.time()
                response = self.session.post(endpoint, json=payload, timeout=30)
                end_time = time.time()

                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        data = result.get("data", {})
                        eval_data = data.get("eval", {})

                        result_entry = {
                            "label_raw": item.get("label_raw", ""),
                            "item_text": item_text,
                            "label_ocean": item.get("label_ocean", ""),
                            "key": item.get("key", ""),
                            "response": data.get("response", ""),
                            "parsed_choice": eval_data.get("parsed_choice", "UNK"),
                            "raw_output": eval_data.get("raw_output", ""),
                            "latency_ms": data.get("meta", {}).get(
                                "latency_ms", int((end_time - start_time) * 1000)
                            ),
                            "model": data.get("meta", {}).get("model", ""),
                            "prompt_tokens": data.get("meta", {}).get(
                                "prompt_tokens", 0
                            ),
                            "completion_tokens": data.get("meta", {}).get(
                                "completion_tokens", 0
                            ),
                        }

                        results.append(result_entry)
                        print(
                            f"  → {eval_data.get('parsed_choice', 'UNK')} ({result_entry['latency_ms']}ms)"
                        )
                    else:
                        print(f"  → Error: {result.get('message', 'Unknown error')}")
                else:
                    print(f"  → HTTP Error: {response.status_code}")

            except Exception as e:
                print(f"  → Exception: {e}")

            # Small delay to avoid overwhelming the API
            time.sleep(0.1)

        print(
            f"Completed assessment: {len(results)}/{len(items)} items processed successfully"
        )
        return results

    def save_results(self, results: List[Dict], output_path: str) -> None:
        """
        Save assessment results to JSON file.

        Args:
            results (List[Dict]): Assessment results
            output_path (str): Output file path
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "user_id": self.user_id,
                        "timestamp": time.time(),
                        "total_items": len(results),
                        "results": results,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            print(f"Results saved to: {output_path}")
        except Exception as e:
            print(f"Error saving results: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run MPI assessment via HTTP API")
    parser.add_argument("--url", required=True, help="Dialog Orchestrator API base URL")
    parser.add_argument("--user-id", required=True, help="User ID for assessment")
    parser.add_argument("--items", required=True, help="Path to MPI items CSV file")
    parser.add_argument(
        "--output", help="Output JSON file path", default="mpi_results.json"
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducible results")
    parser.add_argument(
        "--no-strict", action="store_true", help="Disable strict output format"
    )
    parser.add_argument("--format-id", default="MPI-120", help="Format identifier")

    args = parser.parse_args()

    runner = MPIHTTPRunner(args.url, args.user_id)
    items = runner.load_mpi_items(args.items)

    results = runner.run_assessment(
        items=items,
        seed=args.seed,
        strict_output=not args.no_strict,
        format_id=args.format_id,
    )

    runner.save_results(results, args.output)


if __name__ == "__main__":
    main()
