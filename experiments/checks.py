#!/usr/bin/env python3
"""
Automated validation for experimental results
Validates monotonicity, sensitivity, leakage and other quality metrics
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import statistics

# Quality thresholds
THRESHOLDS = {
    "monotonicity_tolerance": 0.05,  # Allow small deviations
    "sensitivity_r2_min": 0.85,      # R² threshold
    "sensitivity_slope_tolerance": 0.25,  # |slope - 1| < 0.25
    "leakage_slope_max": 0.2,        # Max leakage slope
    "unk_rate_max": 0.02,            # Max 2% UNK rate
}

def load_summary_csv(csv_path: Path) -> List[Dict]:
    """Load summary CSV file"""
    if not csv_path.exists():
        return []
    
    import csv
    data = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in ['O_mean', 'C_mean', 'E_mean', 'A_mean', 'N_mean', 
                       'correlation', 'mae', 'rmse', 'unk_rate']:
                if key in row and row[key]:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        pass
            data.append(row)
    return data

def check_monotonicity(data: List[Dict]) -> Tuple[bool, str]:
    """Check E gradient monotonicity: E_20 < E_30 < E_40 < E_50"""
    e_conditions = {}
    
    # Extract E gradient conditions
    for row in data:
        if row['condition'] in ['E_20', 'E_30', 'E_40', 'E_50']:
            condition = row['condition']
            e_mean = row.get('E_mean')
            if e_mean is not None:
                if condition not in e_conditions:
                    e_conditions[condition] = []
                e_conditions[condition].append(e_mean)
    
    # Calculate means per condition
    e_means = {}
    for condition, values in e_conditions.items():
        if values:
            e_means[condition] = statistics.mean(values)
    
    # Check expected order: E_20 < E_30 < E_40 < E_50
    expected_order = ['E_20', 'E_30', 'E_40', 'E_50']
    available = [c for c in expected_order if c in e_means]
    
    if len(available) < 2:
        return True, "PASS: Monotonicity - Insufficient data for validation"
    
    # Check if values are increasing
    prev_val = None
    violations = []
    
    for condition in available:
        curr_val = e_means[condition]
        if prev_val is not None:
            if curr_val <= prev_val + THRESHOLDS["monotonicity_tolerance"]:
                violations.append(f"{prev_condition}({prev_val:.3f}) >= {condition}({curr_val:.3f})")
        prev_val = curr_val
        prev_condition = condition
    
    if violations:
        return False, f"FAIL: Monotonicity violation - {', '.join(violations)}"
    
    return True, f"PASS: Monotonicity OK - {' < '.join(f'{c}({e_means[c]:.3f})' for c in available)}"

def check_unk_rates(data: List[Dict]) -> Tuple[bool, str]:
    """Check UNK rates across all conditions"""
    high_unk = []
    
    for row in data:
        unk_rate = row.get('unk_rate', 0)
        if unk_rate > THRESHOLDS["unk_rate_max"]:
            high_unk.append(f"{row['condition']} ({unk_rate:.3f})")
    
    if high_unk:
        return False, f"FAIL: High UNK rate - {', '.join(high_unk)} > {THRESHOLDS['unk_rate_max']}"
    
    max_unk = max(row.get('unk_rate', 0) for row in data)
    return True, f"PASS: UNK rates acceptable (max {max_unk:.3f})"

def check_sensitivity_analysis(runs_dir: Path) -> Tuple[bool, str]:
    """Check sensitivity analysis results"""
    sensitivity_file = runs_dir / "sensitivity_E_grad.json"
    
    if not sensitivity_file.exists():
        return False, "FAIL: sensitivity_E_grad.json file not found"
    
    try:
        with open(sensitivity_file) as f:
            sensitivity = json.load(f)
        
        r2 = sensitivity.get("r_squared", 0)
        slope = sensitivity.get("slope", 0)
        
        issues = []
        
        if r2 < THRESHOLDS["sensitivity_r2_min"]:
            issues.append(f"R²={r2:.3f} < {THRESHOLDS['sensitivity_r2_min']}")
        
        slope_deviation = abs(slope - 1.0)
        if slope_deviation > THRESHOLDS["sensitivity_slope_tolerance"]:
            issues.append(f"|slope-1|={slope_deviation:.3f} > {THRESHOLDS['sensitivity_slope_tolerance']}")
        
        if issues:
            return False, f"FAIL: Sensitivity analysis - {', '.join(issues)}"
        
        return True, f"PASS: Sensitivity analysis OK (R²={r2:.3f}, slope={slope:.3f})"
        
    except Exception as e:
        return False, f"FAIL: Error reading sensitivity analysis - {e}"

def main():
    print("")
    print("EXPERIMENTAL RESULTS VALIDATION")
    print("=" * 50)
    
    # Find runs directory
    runs_dir = Path("runs")
    if not runs_dir.exists():
        print("ERROR: runs/ directory not found")
        sys.exit(1)
    
    summary_file = runs_dir / "summary.csv"
    if not summary_file.exists():
        print("ERROR: summary.csv not found")
        sys.exit(1)
    
    # Load data
    print(f"Loading data from {summary_file}...")
    data = load_summary_csv(summary_file)
    
    if not data:
        print("ERROR: No data found in summary.csv")
        sys.exit(1)
    
    print(f"Found {len(data)} experimental runs")
    print("")
    
    # Run validation checks
    checks = [
        ("E Gradient Monotonicity", check_monotonicity),
        ("UNK Rate Validation", check_unk_rates),
        ("Sensitivity Analysis", lambda d: check_sensitivity_analysis(runs_dir)),
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        try:
            if check_name == "Sensitivity Analysis":
                passed, message = check_func(data)
            else:
                passed, message = check_func(data)
            
            print(f"{check_name}:")
            print(f"  {message}")
            print("")
            
            if not passed:
                failed_checks.append(check_name)
                
        except Exception as e:
            print(f"{check_name}:")
            print(f"  FAIL: Error during validation - {e}")
            print("")
            failed_checks.append(check_name)
    
    # Final summary
    print("=" * 50)
    if failed_checks:
        print(f"VALIDATION FAILED: {len(failed_checks)} check(s) failed")
        for check in failed_checks:
            print(f"  - {check}")
        print("")
        sys.exit(1)
    else:
        print("ALL VALIDATION CHECKS PASSED")
        print("Experimental results validated successfully")
        print("")
        sys.exit(0)

if __name__ == "__main__":
    main()
