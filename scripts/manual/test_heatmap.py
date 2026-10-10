"""
Test script for heatmap visualization endpoints.
Connects to the API and tests both sentiment and impact heatmap functionality
with various parameters.

Usage:
    python test_heatmap.py

Requirements:
    - requests
    - pandas (optional, for prettier data display)
"""

import requests
import json
from datetime import date, timedelta
import os
import sys
from pprint import pprint

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change to your API server URL if different
SAVE_RESULTS = True
RESULTS_DIR = "heatmap_test_results"

def test_heatmap_endpoint(endpoint, params=None):
    """Call a heatmap endpoint with given parameters and return the results."""
    url = f"{API_BASE_URL}/visualizations/{endpoint}"
    
    print(f"\nCalling {url} with params: {params}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling {endpoint}: {e}")
        return None

def print_heatmap_data(data, title):
    """Print heatmap data in a readable format."""
    print(f"\n=== {title} ===")
    
    if not data or not data.get("cells") or not data.get("x_labels") or not data.get("y_labels"):
        print("No data returned or empty dataset")
        return
    
    # Print metadata
    print(f"Metadata: min={data['metadata']['min']}, max={data['metadata']['max']}, avg={data['metadata']['avg']}")
    
    # Print x and y labels
    print(f"Time periods (x-axis, count={len(data['x_labels'])}): {', '.join(data['x_labels'])}")
    print(f"Dimensions (y-axis, count={len(data['y_labels'])}): {', '.join(data['y_labels'])}")
    
    # Print the cell data in a structured way
    print(f"\nHeatmap cells (total: {len(data['cells'])}, showing first 5):")
    for i, cell in enumerate(data['cells'][:5]):  # Print first 5 cells
        x_label = data['x_labels'][cell['x']]
        y_label = data['y_labels'][cell['y']]
        print(f"  Cell {i+1}: [{x_label}, {y_label}] = {cell['value']}")
    
    if len(data['cells']) > 5:
        print(f"  ... {len(data['cells']) - 5} more cells")
    
    try:
        # Try to use pandas for a nicer display if available
        import pandas as pd
        
        # Create a DataFrame with float dtype to avoid warnings
        df = pd.DataFrame(0.0, index=data['y_labels'], columns=data['x_labels'])
        
        # Fill the DataFrame with cell values
        for cell in data['cells']:
            x_label = data['x_labels'][cell['x']]
            y_label = data['y_labels'][cell['y']]
            df.at[y_label, x_label] = float(cell['value'])
        
        # Print the DataFrame
        print("\nHeatmap data as table:")
        print(df)
    except ImportError:
        # If pandas is not available, just notify the user
        print("\nInstall pandas for prettier table display: pip install pandas")

def save_json_result(data, filename):
    """Save API response as JSON file."""
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    full_path = f"{RESULTS_DIR}/{filename}"
    with open(full_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Data saved to {full_path}")

def run_tests():
    """Run all heatmap tests."""
    print("Starting heatmap functionality tests...")
    
    # Calculate date ranges for tests - use a longer period for daily interval
    today = date.today()
    start_date = (today - timedelta(days=30)).isoformat()  # Last 30 days
    
    # Test 1: Sentiment heatmap by department (daily)
    print("\n\nTEST 1: Sentiment Heatmap by Department (Daily)")
    params = {
        "dimension": "department",
        "interval": "day",
        "start_date": start_date
    }
    results = test_heatmap_endpoint("sentiment-heatmap", params)
    if results:
        print_heatmap_data(results, "Sentiment Heatmap by Department (Daily)")
        if SAVE_RESULTS:
            save_json_result(results, "sentiment_heatmap_by_department_daily.json")
    
    # Test 2: Sentiment heatmap by employee (daily)
    print("\n\nTEST 2: Sentiment Heatmap by Employee (Daily)")
    params = {
        "dimension": "employee",
        "interval": "day",
        "start_date": start_date
    }
    results = test_heatmap_endpoint("sentiment-heatmap", params)
    if results:
        print_heatmap_data(results, "Sentiment Heatmap by Employee (Daily)")
        if SAVE_RESULTS:
            save_json_result(results, "sentiment_heatmap_by_employee_daily.json")
    
    # Test 3: Impact heatmap by department (daily)
    print("\n\nTEST 3: Impact Heatmap by Department (Daily)")
    params = {
        "dimension": "department",
        "interval": "day",
        "start_date": start_date
    }
    results = test_heatmap_endpoint("impact-heatmap", params)
    if results:
        print_heatmap_data(results, "Impact Heatmap by Department (Daily)")
        if SAVE_RESULTS:
            save_json_result(results, "impact_heatmap_by_department_daily.json")
    
    # Test 4: Impact heatmap by employee (daily) 
    print("\n\nTEST 4: Impact Heatmap by Employee (Daily)")
    params = {
        "dimension": "employee",
        "interval": "day",
        "start_date": start_date
    }
    results = test_heatmap_endpoint("impact-heatmap", params)
    if results:
        print_heatmap_data(results, "Impact Heatmap by Employee (Daily)")
        if SAVE_RESULTS:
            save_json_result(results, "impact_heatmap_by_employee_daily.json")

    # Bonus test: Show weekly data as well (more columns than quarterly but fewer than daily)
    print("\n\nTEST 5: Sentiment Heatmap by Department (Weekly)")
    params = {
        "dimension": "department",
        "interval": "week",
        "start_date": (today - timedelta(days=60)).isoformat()  # Last 60 days for multiple weeks
    }
    results = test_heatmap_endpoint("sentiment-heatmap", params)
    if results:
        print_heatmap_data(results, "Sentiment Heatmap by Department (Weekly)")
        if SAVE_RESULTS:
            save_json_result(results, "sentiment_heatmap_by_department_weekly.json")
    
    print("\n\nAll heatmap tests completed!")

if __name__ == "__main__":
    # Check if required libraries are installed
    try:
        import requests
    except ImportError:
        print("Error: This script requires the 'requests' library.")
        print("Please install it with: pip install requests")
        sys.exit(1)
    
    # Run the tests
    run_tests()
