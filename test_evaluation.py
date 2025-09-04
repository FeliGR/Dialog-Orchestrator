#!/usr/bin/env python3
"""
Test Evaluation Script

This script demonstrates how to test the evaluation functionality of the Dialog Orchestrator.
It shows examples of both regular dialog and MPI-AE evaluation requests.
"""

import json
from typing import Any, Dict

import requests


def test_regular_dialog(base_url: str, user_id: str) -> None:
    """Test regular dialog functionality."""
    print("=== Testing Regular Dialog ===")

    endpoint = f"{base_url}/api/dialog/{user_id}"
    payload = {"text": "Hello, how are you feeling today?"}

    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")


def test_mpi_evaluation(base_url: str, user_id: str) -> None:
    """Test MPI-AE evaluation functionality."""
    print("\n=== Testing MPI-AE Evaluation ===")

    endpoint = f"{base_url}/api/dialog/{user_id}"

    # Sample MPI-AE question
    question = """Given a statement of you: "You are always prepared."
Please choose from the following options to identify how accurately this statement describes you.
Options:
(A). Very Accurate
(B). Moderately Accurate
(C). Neither Accurate Nor Inaccurate
(D). Moderately Inaccurate
(E). Very Inaccurate

Answer:"""

    payload = {
        "text": question,
        "eval": {
            "type": "mpi_ae",
            "strict_output": True,
            "seed": 42,
            "format_id": "MPI-120",
        },
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")

            # Extract evaluation-specific data
            if result.get("status") == "success":
                data = result.get("data", {})
                eval_data = data.get("eval", {})
                print(f"\nEvaluation Summary:")
                print(f"  Parsed Choice: {eval_data.get('parsed_choice', 'N/A')}")
                print(f"  Raw Output: {eval_data.get('raw_output', 'N/A')}")
                print(f"  Latency: {data.get('meta', {}).get('latency_ms', 'N/A')}ms")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")


def test_health_check(base_url: str) -> None:
    """Test the health check endpoint."""
    print("\n=== Testing Health Check ===")

    endpoint = f"{base_url}/health"

    try:
        response = requests.get(endpoint, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Exception: {e}")


def main():
    # Configuration
    base_url = "http://localhost:5002"  # Change as needed
    user_id = "test_user_123"

    print(f"Testing Dialog Orchestrator at: {base_url}")
    print(f"Using user_id: {user_id}")

    # Run tests
    test_health_check(base_url)
    test_regular_dialog(base_url, user_id)
    test_mpi_evaluation(base_url, user_id)

    print("\n=== Test Summary ===")
    print("If all tests pass, your Dialog Orchestrator supports evaluation!")
    print(
        f"Use the MPI runner: python eval/run_mpi_http.py --url {base_url} --user-id {user_id} --items inventories/mpi_120.csv"
    )


if __name__ == "__main__":
    main()
