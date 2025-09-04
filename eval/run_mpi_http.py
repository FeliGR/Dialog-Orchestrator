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
from typing import Dict, List, Optional, Any

import requests


class MPIHTTPRunner:
    """
    HTTP Runner for MPI assessments using Dialog Orchestrator API.
    """

    def __init__(self, base_url: str, user_id: str):
        """
        Initialize the MPI HTTP Runner.
        
        Args:
            base_url (str): Base URL of the Dialog Orchestrator API
            user_id (str): User ID for assessment requests
        """
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.session = requests.Session()

    def load_mpi_items(self, csv_file: str) -> List[Dict]:
        """
        Load MPI items from CSV file.
        
        Args:
            csv_file (str): Path to MPI CSV file
            
        Returns:
            List[Dict]: List of MPI items with required fields
        """
        items = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Ensure all required fields are present
                item = {
                    'label_raw': row.get('label_raw', ''),
                    'text': row.get('text', ''),
                    'label_ocean': row.get('label_ocean', ''),
                    'key': int(row.get('key', 1))
                }
                items.append(item)
        
        print(f"Loaded {len(items)} MPI items from {csv_file}")
        return items

    def run_assessment(
        self, 
        items: List[Dict], 
        seed: Optional[int] = None,
        strict_output: bool = True,
        format_id: str = "MPI-120",
        item_order_seed: Optional[int] = None,
        retry_unk: bool = True
    ) -> Dict[str, Any]:
        """
        Run MPI assessment for all items with enhanced metadata and validation.
        
        Args:
            items (List[Dict]): MPI items to assess
            seed (Optional[int]): Random seed for reproducible results
            strict_output (bool): Whether to enforce strict output format
            format_id (str): Format identifier
            item_order_seed (Optional[int]): Seed for item order randomization
            retry_unk (bool): Whether to retry unknown responses once
            
        Returns:
            Dict[str, Any]: Assessment results with comprehensive metadata
        """
        import random
        import uuid
        import hashlib
        
        # Generate run metadata
        run_id = str(uuid.uuid4())
        run_timestamp = time.time()
        
        # Randomize item order if seed provided
        items_to_process = items.copy()
        if item_order_seed is not None:
            random.seed(item_order_seed)
            random.shuffle(items_to_process)
        
        results = []
        endpoint = f"{self.base_url}/api/dialog/{self.user_id}"
        
        # Assessment configuration
        config = {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 1,
            "stop": ["\n"]
        }
        
        print(f"Running MPI assessment with {len(items_to_process)} items...")
        print(f"Run ID: {run_id}")
        print(f"API endpoint: {endpoint}")
        print(f"Configuration: {config}")
        
        # Track statistics
        stats = {
            "total_items": len(items_to_process),
            "successful": 0,
            "unknown": 0,
            "retried": 0,
            "errors": 0
        }
        
        for i, item in enumerate(items_to_process, 1):
            item_text = item.get("text", "")
            if not item_text:
                print(f"Warning: Empty item text for item {i}")
                stats["errors"] += 1
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
                    "format_id": format_id
                }
            }
            
            # Try initial request
            success = False
            attempts = 1
            
            for attempt in range(1, 3 if retry_unk else 2):  # Max 2 attempts
                try:
                    print(f"Processing item {i}/{len(items_to_process)}: {item.get('label_raw', 'unknown')} (attempt {attempt})")
                    
                    start_time = time.time()
                    response = self.session.post(endpoint, json=payload, timeout=30)
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success':
                            data = result.get('data', {})
                            eval_data = data.get('eval', {})
                            parsed_choice = eval_data.get('parsed_choice', 'UNK')
                            
                            # Check if we got UNK and should retry
                            if parsed_choice == 'UNK' and retry_unk and attempt == 1:
                                print(f"  → UNK response, retrying...")
                                stats["retried"] += 1
                                attempts += 1
                                continue
                            
                            # Build result entry with enhanced metadata
                            result_entry = {
                                # Item information
                                "item_id": f"{run_id}_{i:03d}",
                                "item_index": i - 1,  # 0-based index in original order
                                "label_raw": item.get("label_raw", ""),
                                "item_text": item_text,
                                "label_ocean": item.get("label_ocean", ""),
                                "key": int(item.get("key", 1)),
                                
                                # Response data
                                "response": data.get("response", ""),
                                "parsed_choice": parsed_choice,
                                "raw_output": eval_data.get("raw_output", ""),
                                
                                # Performance metrics
                                "latency_ms": data.get("meta", {}).get("latency_ms", int((end_time - start_time) * 1000)),
                                "attempts": attempts,
                                
                                # Model information
                                "model": data.get("meta", {}).get("model", ""),
                                "prompt_tokens": int(data.get("meta", {}).get("prompt_tokens", 0)),
                                "completion_tokens": int(data.get("meta", {}).get("completion_tokens", 0)),
                                
                                # Assessment configuration
                                "eval_config": eval_data.copy(),
                                "timestamp": end_time
                            }
                            
                            results.append(result_entry)
                            
                            if parsed_choice == 'UNK':
                                stats["unknown"] += 1
                                print(f"  → UNK ({result_entry['latency_ms']}ms)")
                            else:
                                stats["successful"] += 1
                                print(f"  → {parsed_choice} ({result_entry['latency_ms']}ms)")
                            
                            success = True
                            break
                        else:
                            print(f"  → API Error: {result.get('message', 'Unknown error')}")
                            stats["errors"] += 1
                    else:
                        print(f"  → HTTP Error: {response.status_code}")
                        stats["errors"] += 1
                        
                except Exception as e:
                    print(f"  → Exception: {e}")
                    stats["errors"] += 1
                    
                # Small delay between retries
                if attempt == 1 and not success:
                    time.sleep(0.5)
                    
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
        
        # Calculate final statistics
        completion_time = time.time()
        total_duration = completion_time - run_timestamp
        
        # Generate comprehensive metadata
        metadata = {
            "run_id": run_id,
            "user_id": self.user_id,
            "timestamp": run_timestamp,
            "completion_time": completion_time,
            "duration_seconds": total_duration,
            "format_id": format_id,
            
            # Configuration
            "assessment_config": {
                "seed": seed,
                "strict_output": strict_output,
                "retry_unk": retry_unk,
                "item_order_seed": item_order_seed,
                **config
            },
            
            # Statistics
            "statistics": stats,
            "completion_rate": stats["successful"] / stats["total_items"] if stats["total_items"] > 0 else 0,
            
            # Item metadata
            "total_items_original": len(items),
            "items_processed": len(items_to_process),
            
            # Quality indicators
            "avg_latency_ms": sum(r["latency_ms"] for r in results) / len(results) if results else 0,
            "total_tokens": sum(r["prompt_tokens"] + r["completion_tokens"] for r in results),
        }
        
        print(f"Completed assessment: {stats['successful']}/{stats['total_items']} items successful")
        print(f"Unknown responses: {stats['unknown']}, Retries: {stats['retried']}, Errors: {stats['errors']}")
        print(f"Total duration: {total_duration:.1f}s, Avg latency: {metadata['avg_latency_ms']:.0f}ms")
        
        return {
            "metadata": metadata,
            "results": results
        }

    def save_results(self, results: Dict[str, Any], output_file: str) -> None:
        """
        Save assessment results to JSON file.
        
        Args:
            results (Dict[str, Any]): Assessment results with metadata
            output_file (str): Output file path
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        metadata = results.get("metadata", {})
        total_items = metadata.get("statistics", {}).get("total_items", 0)
        successful = metadata.get("statistics", {}).get("successful", 0)
        
        print(f"Results saved to {output_file}")
        print(f"Summary: {successful}/{total_items} items completed successfully")


def main():
    """Main function to run MPI assessment."""
    parser = argparse.ArgumentParser(description='Run MPI assessment via HTTP API')
    parser.add_argument('--csv', '-c', required=True, help='Path to MPI CSV file')
    parser.add_argument('--url', '-u', default='http://localhost:5000', 
                       help='Base URL of Dialog Orchestrator API (default: http://localhost:5000)')
    parser.add_argument('--user', '-user', default='test_user', 
                       help='User ID for assessment (default: test_user)')
    parser.add_argument('--output', '-o', default='mpi_results.json', 
                       help='Output JSON file (default: mpi_results.json)')
    parser.add_argument('--seed', '-s', type=int, help='Random seed for reproducible results')
    parser.add_argument('--no-strict', action='store_true', 
                       help='Disable strict output format enforcement')
    parser.add_argument('--format-id', default='MPI-120', 
                       help='Format identifier (default: MPI-120)')
    parser.add_argument('--item-order-seed', type=int, 
                       help='Seed for randomizing item order')
    parser.add_argument('--no-retry-unk', action='store_true',
                       help='Disable retrying unknown responses')
    
    args = parser.parse_args()
    
    try:
        # Initialize runner
        runner = MPIHTTPRunner(args.url, args.user)
        
        # Load MPI items
        items = runner.load_mpi_items(args.csv)
        if not items:
            print("Error: No items loaded from CSV file")
            sys.exit(1)
        
        # Run assessment
        results = runner.run_assessment(
            items=items,
            seed=args.seed,
            strict_output=not args.no_strict,
            format_id=args.format_id,
            item_order_seed=args.item_order_seed,
            retry_unk=not args.no_retry_unk
        )
        
        # Save results
        runner.save_results(results, args.output)
        
        print("\nAssessment completed successfully!")
        
    except KeyboardInterrupt:
        print("\nAssessment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
