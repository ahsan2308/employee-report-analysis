"""
Test script for verifying the quarterly analysis functionality with real data.
This script tests the get_quarterly_data_for_analysis function on actual database data.

Usage:
    python scripts/test_quarterly_analysis.py <employee_id>
"""
import sys
import os
import json
from datetime import date
from pprint import pprint

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from app.services.analysis.quarterly_context import get_quarterly_data_for_analysis
from app.repositories.employees import get_employee_info
from app.core.logger import logger

def test_quarterly_analysis(employee_id: int, year: int = 2025, quarter: int = 2):
    """
    Test the quarterly analysis functionality for a specific employee.
    
    Args:
        employee_id: The employee ID to test
        year: The year to analyze (default: 2025)
        quarter: The quarter to analyze (default: 2)
    """
    print(f"\n===== TESTING QUARTERLY ANALYSIS FOR EMPLOYEE {employee_id}, {year}-Q{quarter} =====\n")
    
    # Verify employee exists
    employee_info = get_employee_info(employee_id)
    if not employee_info:
        print(f"ERROR: Employee with ID {employee_id} not found!")
        return
    
    print(f"Employee: {employee_info['name']} ({employee_info['position']} in {employee_info['wing']})")
    
    # Call the quarterly analysis function
    print(f"\nGathering quarterly data...")
    result = get_quarterly_data_for_analysis(employee_id, year, quarter)
    
    # Verify basic structure
    if not result:
        print("ERROR: No result returned from get_quarterly_data_for_analysis!")
        return
    
    print("\n===== BASIC INFORMATION =====")
    print(f"Year: {result['year']}")
    print(f"Quarter: {result['quarter']}")
    print(f"Period: {result['period_start']} to {result['period_end']}")
    
    # Verify employee info in result matches our query
    if result['employee_info'] != employee_info:
        print("WARNING: Employee info in result doesn't match queried employee info!")
        print(f"Expected: {employee_info}")
        print(f"Got: {result['employee_info']}")
    
    # Check monthly analyses
    monthly_analyses = result["monthly_analyses"]
    print(f"\n===== MONTHLY ANALYSES ({len(monthly_analyses)}) =====")
    if not monthly_analyses:
        print("WARNING: No monthly analyses found for this quarter!")
    else:
        for i, analysis in enumerate(monthly_analyses):
            month_name = analysis.get("month_name", f"Month {analysis.get('month', 'unknown')}")
            print(f"{i+1}. {month_name} - {len(analysis.get('monthly_achievements', []))} achievements, " +
                  f"{len(analysis.get('recurring_challenges', []))} challenges")
    
    # Check weekly analyses
    weekly_analyses = result["weekly_analyses"]
    print(f"\n===== WEEKLY ANALYSES ({len(weekly_analyses)}) =====")
    if not weekly_analyses:
        print("WARNING: No weekly analyses found for this quarter!")
    else:
        # Group by month for better visualization
        weeks_by_month = {}
        for analysis in weekly_analyses:
            week_date = analysis.get("date")
            if week_date:
                month = week_date.month if hasattr(week_date, "month") else None
                if month:
                    if month not in weeks_by_month:
                        weeks_by_month[month] = []
                    weeks_by_month[month].append(analysis)
        
        for month, weeks in sorted(weeks_by_month.items()):
            month_names = ["January", "February", "March", "April", "May", "June", 
                           "July", "August", "September", "October", "November", "December"]
            month_name = month_names[month-1] if 1 <= month <= 12 else f"Month {month}"
            print(f"\n{month_name} ({len(weeks)} weeks):")
            for analysis in sorted(weeks, key=lambda x: x.get("date")):
                date_str = analysis.get("date").isoformat() if hasattr(analysis.get("date"), "isoformat") else analysis.get("date")
                print(f"  - {date_str}: {analysis.get('performance_rating', 'unknown')} performance, " +
                      f"{analysis.get('credibility_rating', 'unknown')} credibility")
    
    # Check metrics
    metrics = result["metrics"]
    print("\n===== METRICS =====")
    
    # General metrics
    print("\nGeneral Metrics:")
    print(f"Average Sentiment: {metrics['avg_sentiment']}")
    print(f"Sentiment Trend: {metrics['sentiment_trend']}")
    print(f"Weekly Report Count: {metrics['weekly_report_count']}")
    print(f"Achievement Count: {metrics['achievement_count']}")
    print(f"Challenge Count: {metrics['challenge_count']}")
    print(f"Achievement Impact Average: {metrics['achievement_impact_avg']}")
    
    # Trend metrics
    print("\nTrend Metrics:")
    print(f"Performance Stability: {metrics['performance_stability']}")
    print(f"Task Reliability Trend: {metrics['task_reliability_trend']}")
    print(f"Quality Consistency Trend: {metrics['quality_consistency_trend']}")
    print(f"Risk Trend: {metrics['risk_trend']}")
    print(f"Performance Trend: {metrics.get('performance_trend', 'Not calculated')}")
    print(f"Challenge Resolution Trend: {metrics['challenge_resolution_trend']}")
    
    # Risk levels
    print("\nRisk Levels:")
    for level, count in metrics.get("risk_levels", {}).items():
        print(f"  {level}: {count}")
    
    # Verify performance rating aggregation - critical for ensuring high/medium/low ratings are properly tracked
    perf_aggregation = metrics["performance_rating_aggregation"]
    print("\nPerformance Rating Aggregation:")
    print(f"Most Common Rating: {perf_aggregation['most_common_rating']}")
    print(f"Rating Distribution:")
    for rating, percentage in perf_aggregation.get("rating_distribution", {}).items():
        print(f"  {rating}: {percentage:.1%}")
    print(f"Rating Trend: {perf_aggregation['rating_trend']}")
    
    # Check monthly progress trends
    monthly_progress_trends = metrics["monthly_progress_trends"]
    print(f"\nMonthly Progress Trends ({len(monthly_progress_trends)}):")
    for trend in sorted(monthly_progress_trends, key=lambda x: x.get("month", 0)):
        month = trend.get("month", "Unknown")
        print(f"  Month {month}:")
        print(f"    Performance: {trend.get('performance_trend', 'unknown')}")
        print(f"    Sentiment: {trend.get('sentiment_trend', 'unknown')}")
        print(f"    Risk Level: {trend.get('risk_level_pattern', 'unknown')}")
        print(f"    Challenge Resolution: {trend.get('challenge_resolution_progress', 'unknown')}")
    
    # Check weekly credibility data
    credibility_data = metrics["weekly_credibility_data"]
    print("\nWeekly Credibility Data:")
    print(f"Average Credibility Rating: {credibility_data['avg_credibility_rating']}")
    print(f"Credibility Trend: {credibility_data['credibility_trend']}")
    print(f"Exaggeration Frequency: {credibility_data['exaggeration_frequency']}")
    
    # Check recurring topics
    recurring_topics = metrics["recurring_topics"]
    print(f"\nRecurring Topics ({len(recurring_topics)}):")
    for topic in recurring_topics:
        print(f"  - {topic}")
    
    # Check detailed topics
    detailed_topics = metrics["detailed_topics"]
    print(f"\nDetailed Topics ({len(detailed_topics)}):")
    for topic_data in detailed_topics[:5]:  # Show top 5
        print(f"  - {topic_data['topic']}: {topic_data['frequency']} occurrences")
    if len(detailed_topics) > 5:
        print(f"  ... and {len(detailed_topics) - 5} more")
    
    # Monthly summaries
    monthly_summaries = metrics["monthly_summaries"]
    print(f"\nMonthly Summaries ({len(monthly_summaries)}):")
    for summary in monthly_summaries:
        month = summary.get("month", "Unknown")
        summary_text = summary.get("summary", "")
        print(f"  {month}: {summary_text[:100]}...")  # Show first 100 chars
    
    # Check for any discrepancies or issues
    print("\n===== VALIDATION CHECKS =====")
    
    # Check that all monthly analyses have the required fields
    for i, analysis in enumerate(monthly_analyses):
        month = analysis.get("month", "unknown")
        missing_fields = []
        required_fields = ["month", "month_name", "progress_trends", "monthly_achievements", 
                          "recurring_challenges", "consistency_assessment", "monthly_risk_assessment"]
        for field in required_fields:
            if field not in analysis or analysis[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"WARNING: Monthly analysis for month {month} is missing required fields: {', '.join(missing_fields)}")
    
    # Check that all weekly analyses have the required fields
    for i, analysis in enumerate(weekly_analyses):
        date_str = analysis.get("date")
        if date_str:
            date_str = date_str.isoformat() if hasattr(date_str, "isoformat") else str(date_str)
        
        missing_fields = []
        required_fields = ["date", "performance_rating", "credibility_rating", "risk_level"]
        for field in required_fields:
            if field not in analysis or analysis[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"WARNING: Weekly analysis for {date_str} is missing required fields: {', '.join(missing_fields)}")
    
    # Verify performance rating values
    invalid_ratings = []
    for analysis in weekly_analyses:
        rating = analysis.get("performance_rating")
        if rating and rating not in ["high", "medium", "low"]:
            date_str = analysis.get("date")
            if date_str:
                date_str = date_str.isoformat() if hasattr(date_str, "isoformat") else str(date_str)
            invalid_ratings.append((date_str, rating))
    
    if invalid_ratings:
        print("WARNING: Found invalid performance ratings:")
        for date_str, rating in invalid_ratings:
            print(f"  {date_str}: '{rating}' (should be 'high', 'medium', or 'low')")
    
    # Check that risk trend uses correct values (increasing/decreasing/stable)
    if metrics["risk_trend"] not in ["increasing", "decreasing", "stable"]:
        print(f"WARNING: Invalid risk trend value: '{metrics['risk_trend']}' (should be 'increasing', 'decreasing', or 'stable')")
    
    # Check that performance trend uses correct values (improving/declining/stable)
    perf_trend = metrics.get("performance_trend", "stable")
    if perf_trend not in ["improving", "declining", "stable"]:
        print(f"WARNING: Invalid performance trend value: '{perf_trend}' (should be 'improving', 'declining', or 'stable')")
    
    print("\n===== TEST COMPLETED =====")
    
    return result

def main():
    """Main function to run the test."""
    if len(sys.argv) < 2:
        print("Please provide an employee ID as a command-line argument.")
        print("Usage: python scripts/test_quarterly_analysis.py <employee_id> [year] [quarter]")
        return
    
    try:
        employee_id = int(sys.argv[1])
        
        # Optional year and quarter arguments
        year = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
        quarter = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        
        # Run the test
        test_quarterly_analysis(employee_id, year, quarter)
        
    except ValueError:
        print("Error: Employee ID, year, and quarter must be integers.")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
