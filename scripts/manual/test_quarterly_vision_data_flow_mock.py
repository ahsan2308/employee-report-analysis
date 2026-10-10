"""
Comprehensive test script for quarterly vision data processing pipeline.
This script:
1. Creates detailed mock vision data with controlled test cases
2. Tests the filter_vision_data function
3. Tests the format_vision_data_for_quarterly_analysis_prompt function
4. Examines each part of the output and verifies all components
5. Validates truncation behavior and "more..." notifications
"""
import sys
import os
import json
from datetime import date, datetime, timedelta
from pprint import pprint
import random
import re

# Add the parent directory to the Python path so we can import the app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.additional_services import filter_vision_data, format_vision_data_for_quarterly_analysis_prompt

def json_serializer(obj):
    """Helper function to serialize date/datetime objects in JSON"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def create_test_employee_vision_data_for_quarter() -> dict:
    """
    Create detailed test vision data with controlled test cases.
    
    This function creates vision data with specific patterns to test:
    1. Zero-value filtering
    2. Content truncation
    3. Multiple content items
    4. Various entity types
    5. Nested structure handling
    
    Returns:
        Dictionary with test vision data
    """
    # Define test data parameters
    year = 2023
    quarter = 1
    
    # Calculate quarter dates
    quarter_start = date(year, (quarter - 1) * 3 + 1, 1)
    quarter_end = date(year, quarter * 3, 31)
    
    # Create test data structure
    vision_data = {
        "date_context": {
            "quarter": quarter,
            "year": year,
            "period_start": quarter_start.isoformat(),
            "period_end": quarter_end.isoformat(),
        },
        "months_data": []
    }
    
    # Month names for the quarter
    month_names = ["January", "February", "March"]
    
    # Entity types to include - testing different categories
    main_entities = ["Persons", "Organizations", "Events", "Tasks", "Correspondence"]
    
    # Create test sub-entities with varying amounts of content
    sub_entity_templates = {
        "Persons": {
            "POIs": {
                "count": 15,  # Intentionally high to test truncation
                "content": [
                    {"name": f"Test Person {i}", "region": f"Region {i % 5}", "significance": "High" if i % 3 == 0 else "Medium"}
                    for i in range(15)
                ]
            },
            "Skills": {
                "count": 8,
                "content": [
                    {"skill": f"Skill {i}", "level": "Expert" if i % 2 == 0 else "Intermediate"}
                    for i in range(8)
                ]
            },
            "Empty1": {
                "count": 0,  # Test zero-value filtering
                "content": []
            }
        },
        "Organizations": {
            "OOIs": {
                "count": 5,
                "content": [
                    {"org_name": f"Organization {i}", "sector": f"Sector {i}", "size": "Large" if i % 2 == 0 else "Medium"}
                    for i in range(5)
                ]
            },
            "Empty2": {
                "count": 0,  # Test zero-value filtering
                "content": []
            }
        },
        "Events": {
            "EOIs": {
                "count": 12,  # Test truncation
                "content": [
                    {"event_name": f"Event {i}", "impact": "High" if i % 3 == 0 else "Medium", "date": (quarter_start + timedelta(days=i*3)).isoformat()}
                    for i in range(12)
                ]
            }
        },
        "Tasks": {
            "Task Updates": {
                "count": 7,
                "content": [
                    {"status": "Completed" if i % 2 == 0 else "In Progress", "completion": f"{i*10}%", "notes": f"Task note {i}"}
                    for i in range(7)
                ]
            },
            "Task Attachments": {
                "count": 4,
                "content": [
                    {"filename": f"attachment_{i}.pdf", "size": f"{i+1} MB"}
                    for i in range(4)
                ]
            }
        },
        "Correspondence": {
            "DFA": {
                "count": 3,
                "content": [
                    {"subject": f"Draft {i}", "recipient": f"Recipient {i}"}
                    for i in range(3)
                ]
            },
            "Empty3": {
                "count": 0,  # Test zero-value filtering
                "content": []
            }
        }
    }
    
    # Generate month data
    for month_idx, month_name in enumerate(month_names):
        month_num = month_idx + 1
        month_start = date(year, month_idx + 1, 1)
        
        # Get last day of month
        if month_num in [1, 3, 5, 7, 8, 10, 12]:
            month_end = date(year, month_num, 31)
        elif month_num in [4, 6, 9, 11]:
            month_end = date(year, month_num, 30)
        else:  # February
            month_end = date(year, month_num, 28)  # Simplified - not handling leap years
        
        month_data = {
            "month_name": month_name,
            "date_context": {
                "month": month_num,
                "year": year,
                "period_start": month_start.isoformat(),
                "period_end": month_end.isoformat(),
            },
            "weeks_data": []
        }
        
        # Generate 4 weeks per month
        for week_num in range(1, 5):
            week_start = month_start + timedelta(days=(week_num-1)*7)
            week_end = min(week_start + timedelta(days=6), month_end)
            
            # Create activities for this week - use different entities each week
            # to test various combinations
            activities = []
            
            # Select 2-3 random entities for this week
            num_entities = random.randint(2, 3)
            week_entities = random.sample(main_entities, num_entities)
            
            for entity_name in week_entities:
                sub_entities = {}
                sub_entities_content = {}
                
                # Add all sub-entities for this entity
                for sub_entity, data in sub_entity_templates.get(entity_name, {}).items():
                    sub_entities[sub_entity] = data["count"]
                    if data["count"] > 0:
                        sub_entities_content[sub_entity] = data["content"]
                
                # Create activity
                activity = {
                    "main_entity": entity_name,
                    "from_date": week_start.isoformat(),
                    "to_date": week_end.isoformat(),
                    "sub_entities": sub_entities,
                    "sub_entities_content": sub_entities_content
                }
                activities.append(activity)
            
            # Create week data
            week_data = {
                "week_number": week_num,
                "iso_week": week_num + (month_idx * 4),
                "activities": activities
            }
            month_data["weeks_data"].append(week_data)
        
        # Add month to quarter data
        vision_data["months_data"].append(month_data)
    
    return vision_data

def extract_and_count_truncation_messages(formatted_text):
    """
    Extract and count all truncation messages in the formatted text.
    
    Args:
        formatted_text: The formatted vision data text
        
    Returns:
        Dictionary with counts of different types of truncation messages
    """
    results = {
        "content_truncation": 0,   # "and X more..." for content items
        "subentity_truncation": 0, # "and X more sub-entities"
        "content_groups_truncation": 0  # "content for X more sub-entities"
    }
    
    # Find all content truncation messages
    content_matches = re.findall(r'---> and (\d+) more\.\.\.', formatted_text)
    results["content_truncation"] = len(content_matches)
    
    # Find all sub-entity truncation messages
    subentity_matches = re.findall(r'- \.\.\. and (\d+) more sub-entities', formatted_text)
    results["subentity_truncation"] = len(subentity_matches)
    
    # Find all content groups truncation messages
    content_group_matches = re.findall(r'\.\.\. and content for (\d+) more sub-entities', formatted_text)
    results["content_groups_truncation"] = len(content_group_matches)
    
    # Calculate total truncated items
    total_content_truncated = sum(int(count) for count in content_matches) if content_matches else 0
    total_subentities_truncated = sum(int(count) for count in subentity_matches) if subentity_matches else 0
    total_content_groups_truncated = sum(int(count) for count in content_group_matches) if content_group_matches else 0
    
    results["total_content_truncated"] = total_content_truncated
    results["total_subentities_truncated"] = total_subentities_truncated
    results["total_content_groups_truncated"] = total_content_groups_truncated
    
    return results

def test_quarterly_vision_data_processing(max_content_items=5, show_full_output=False):
    """
    Comprehensive test of the quarterly vision data processing pipeline.
    
    Args:
        max_content_items: Maximum content items to include per entity (to test truncation)
        show_full_output: Whether to print the full formatted output
    """
    print(f"Testing quarterly vision data processing with max_content_items={max_content_items}")
    
    # Step 1: Create detailed test vision data
    print("\n==== STEP 1: Creating Test Vision Data ====")
    test_data = create_test_employee_vision_data_for_quarter()
    
    # Count total items in test data for verification
    zero_values = 0
    non_zero_values = 0
    content_items = 0
    
    # Count elements in test data
    for month in test_data.get("months_data", []):
        for week in month.get("weeks_data", []):
            for activity in week.get("activities", []):
                for sub_entity, value in activity.get("sub_entities", {}).items():
                    if value == 0:
                        zero_values += 1
                    else:
                        non_zero_values += 1
                        # Count content items
                        sub_content = activity.get("sub_entities_content", {}).get(sub_entity, [])
                        content_items += len(sub_content)
    
    print(f"Created test data with:")
    print(f"- {len(test_data.get('months_data', []))} months")
    print(f"- {sum(len(month.get('weeks_data', [])) for month in test_data.get('months_data', []))} weeks")
    print(f"- {sum(sum(len(week.get('activities', [])) for week in month.get('weeks_data', [])) for month in test_data.get('months_data', []))} activities")
    print(f"- {non_zero_values} non-zero sub-entities")
    print(f"- {zero_values} zero-value sub-entities (should be filtered out)")
    print(f"- {content_items} individual content items")
    
    # Save raw test data for reference
    with open("test_raw_quarterly_vision_data.json", "w") as f:
        json.dump(test_data, f, indent=2, default=json_serializer)
    print("\nRaw test data saved to test_raw_quarterly_vision_data.json")
    
    # Step 2: Filter the vision data
    print("\n==== STEP 2: Filtering Vision Data ====")
    filtered_data = filter_vision_data(test_data)
    
    # Count filtered items
    filtered_non_zero_values = 0
    filtered_content_items = 0
    
    for month in filtered_data.get("months_data", []):
        for week in month.get("weeks_data", []):
            for activity in week.get("activities", []):
                filtered_non_zero_values += len(activity.get("sub_entities", {}))
                # Count content items in filtered data
                for sub_entity, data in activity.get("sub_entities", {}).items():
                    sub_content = activity.get("sub_entities_content", {}).get(sub_entity, [])
                    filtered_content_items += len(sub_content)
    
    print(f"Filtering results:")
    print(f"- Original non-zero sub-entities: {non_zero_values}")
    print(f"- Filtered non-zero sub-entities: {filtered_non_zero_values}")
    print(f"- Original zero-value sub-entities: {zero_values}")
    print(f"- Removed zero-value sub-entities: {zero_values if filtered_non_zero_values == non_zero_values else 'ERROR - filtering not working correctly'}")
    print(f"- Original content items: {content_items}")
    print(f"- Filtered content items: {filtered_content_items}")
    
    if filtered_non_zero_values == non_zero_values and zero_values > 0:
        print("[OK] Zero-value filtering is working correctly")
    else:
        print("[WARNING] Zero-value filtering may not be working correctly")
    
    # Save filtered data for reference
    with open("test_filtered_quarterly_vision_data.json", "w") as f:
        json.dump(filtered_data, f, indent=2, default=json_serializer)
    print("\nFiltered test data saved to test_filtered_quarterly_vision_data.json")
    
    # Step 3: Format the filtered data
    print("\n==== STEP 3: Formatting Vision Data ====")
    formatted_text = format_vision_data_for_quarterly_analysis_prompt(
        filtered_data, 
        max_content_items_per_entity=max_content_items
    )
    
    # Save complete formatted text
    with open("test_formatted_quarterly_vision_data.txt", "w") as f:
        f.write(formatted_text)
    print("\nFormatted text saved to test_formatted_quarterly_vision_data.txt")
    
    # Analyze the formatted output
    print("\n==== STEP 4: Analyzing Formatted Output ====")
    
    # Check for presence of key sections
    has_quarter_header = "QUARTERLY VISION DATA" in formatted_text
    has_quarter_summary = "Quarter Summary" in formatted_text
    month_sections = re.findall(r"## ([A-Z]+) ACTIVITY DATA", formatted_text)
    week_sections = re.findall(r"Week (\d+) Activity Data", formatted_text)
    activity_sections = re.findall(r"Main Activity: ([A-Za-z]+)", formatted_text)
    
    print(f"Formatted output structure:")
    print(f"- Has quarter header: {has_quarter_header}")
    print(f"- Has quarter summary: {has_quarter_summary}")
    print(f"- Month sections: {len(month_sections)} ({', '.join(month_sections)})")
    print(f"- Week sections: {len(week_sections)}")
    print(f"- Activity sections: {len(activity_sections)}")
    
    # Check for consistency with input data
    months_match = len(month_sections) == len(test_data.get("months_data", []))
    print(f"- Months match input data: {months_match}")
    
    # Analyze truncation messages
    truncation_stats = extract_and_count_truncation_messages(formatted_text)
    
    print("\nTruncation analysis:")
    print(f"- Content truncation messages: {truncation_stats['content_truncation']}")
    print(f"- Sub-entity truncation messages: {truncation_stats['subentity_truncation']}")
    print(f"- Content group truncation messages: {truncation_stats['content_groups_truncation']}")
    print(f"- Total content items truncated: {truncation_stats['total_content_truncated']}")
    
    # Check if truncation is working as expected
    should_truncate = content_items > max_content_items and max_content_items > 0
    if should_truncate and truncation_stats['content_truncation'] > 0:
        print("[OK] Content truncation is working correctly")
    elif not should_truncate and truncation_stats['content_truncation'] == 0:
        print("[OK] No truncation needed and none applied")
    else:
        print("[WARNING] Truncation behavior may not be working correctly")
    
    # Display text structure stats
    lines = formatted_text.split("\n")
    markdown_headers = [line for line in lines if line.startswith("#")]
    detail_lines = [line for line in lines if "-->" in line]
    truncation_lines = [line for line in lines if "more..." in line]
    
    print(f"\nFormatted text statistics:")
    print(f"- Total length: {len(formatted_text)} characters")
    print(f"- Number of lines: {len(lines)}")
    print(f"- Number of markdown headers: {len(markdown_headers)}")
    print(f"- Number of detail lines: {len(detail_lines)}")
    print(f"- Number of truncation notifications: {len(truncation_lines)}")
    
    # Display some examples of the output
    print("\n==== STEP 5: Output Samples ====")
    
    # Display the quarter header and summary
    quarter_header_match = re.search(r"# QUARTERLY VISION DATA.*?(?=\n\n##|\Z)", formatted_text, re.DOTALL)
    if quarter_header_match:
        print("\nQuarter Header and Summary:")
        print(quarter_header_match.group(0))
    
    # Display a sample month
    month_match = re.search(r"## [A-Z]+ ACTIVITY DATA.*?(?=\n\n##|\Z)", formatted_text, re.DOTALL)
    if month_match and not show_full_output:
        print("\nSample Month Section (truncated):")
        month_text = month_match.group(0)
        # Show just the first 500 chars
        print(month_text[:500] + "..." if len(month_text) > 500 else month_text)
    
    # Display a sample week
    week_match = re.search(r"Week \d+ Activity Data.*?(?=\nWeek|\n\n##|\Z)", formatted_text, re.DOTALL)
    if week_match and not show_full_output:
        print("\nSample Week Section:")
        week_text = week_match.group(0)
        # Show just the first 300 chars
        print(week_text[:300] + "..." if len(week_text) > 300 else week_text)
    
    # Find and display truncation examples
    truncation_example = re.search(r".*---> and \d+ more\.\.\.", formatted_text)
    if truncation_example:
        context_start = max(0, truncation_example.start() - 200)
        context_end = min(len(formatted_text), truncation_example.end() + 100)
        print("\nExample of content truncation with context:")
        print("..." + formatted_text[context_start:context_end] + "...")
    
    # Show full output if requested
    if show_full_output:
        print("\n==== FULL FORMATTED OUTPUT ====")
        print(formatted_text)
    
    print("\n==== Test Complete ====")
    print("Output files generated:")
    print("  - test_raw_quarterly_vision_data.json")
    print("  - test_filtered_quarterly_vision_data.json")
    print("  - test_formatted_quarterly_vision_data.txt")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive test for quarterly vision data processing')
    parser.add_argument('--max-content-items', type=int, default=5, 
                       help='Maximum content items per entity for testing truncation (default: 5)')
    parser.add_argument('--show-full-output', action='store_true',
                       help='Display the full formatted output')
    
    args = parser.parse_args()
    
    # Run the comprehensive test
    test_quarterly_vision_data_processing(
        max_content_items=args.max_content_items,
        show_full_output=args.show_full_output
    )
