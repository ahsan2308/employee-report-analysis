"""
Test script for the vision data filtering and formatting functionality.
This script helps verify that zero-value sub-entities are properly filtered
and the remaining data is correctly formatted for inclusion in prompts.
"""
import sys
import os
import json
from datetime import date, timedelta

# Add the parent directory to path so we can import the app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# format_vision_data_for_prompt was renamed in commit 4213c2f
from app.services.additional_services import filter_vision_data, format_vision_data_for_weekly_analysis_prompt as format_vision_data_for_prompt
from app.core.logger import logger

def create_sample_vision_data():
    """Create sample vision data for testing, including zero and non-zero values."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    
    return {
        "date_context": {
            "report_date": today.isoformat(),
        },
        "current_data": [
            {
                "main_entity": "Persons",
                "sub_entities": {
                    "Persons": 5,
                    "Numbers": 3,
                    "Pictures": 0,  # Should be filtered out
                    "Addresses": 2,
                    "Features": 0,  # Should be filtered out
                    "POIs": 1
                },
                "from_date": yesterday.isoformat(),
                "to_date": today.isoformat()
            },
            {
                "main_entity": "Tasks",
                "sub_entities": {
                    "Tasks": 7,
                    "Task Updates": 4,
                    "Task Attachments": 0,  # Should be filtered out
                    "Assigned/CC": 2
                },
                "from_date": yesterday.isoformat(),
                "to_date": today.isoformat()
            },
            {
                "main_entity": "Events",
                "sub_entities": {
                    "Events": 0,  # All zero, this entire main entity should be filtered out
                    "EOIs": 0,
                    "Information": 0,
                    "Labels": 0
                },
                "from_date": yesterday.isoformat(),
                "to_date": today.isoformat()
            }
        ],
        "previous_data": [
            {
                "main_entity": "Persons",
                "sub_entities": {
                    "Persons": 10,
                    "Numbers": 5,
                    "Pictures": 2,
                    "Addresses": 0,  # Should be filtered out
                    "Features": 1
                },
                "from_date": last_week.isoformat(),
                "to_date": yesterday.isoformat()
            },
            {
                "main_entity": "Organizations",
                "sub_entities": {
                    "Orgs": 3,
                    "OOIs": 0,  # Should be filtered out
                    "Particulars": 1,
                    "Attachments": 0,  # Should be filtered out
                    "OPs": 2
                },
                "from_date": two_weeks_ago.isoformat(),
                "to_date": last_week.isoformat()
            },
            {
                "main_entity": "Links",
                "sub_entities": {
                    "Per-Per": 0,  # All zero, entire main entity should be filtered
                    "Per-Org": 0,
                    "Per-Event": 0
                },
                "from_date": two_weeks_ago.isoformat(),
                "to_date": last_week.isoformat()
            }
        ]
    }

def test_vision_data_filtering():
    """Test the vision data filtering functionality."""
    logger.info("Starting vision data filtering test")
    
    # Create sample data
    sample_data = create_sample_vision_data()
    
    # Print original data structure
    print("\n===== ORIGINAL VISION DATA =====")
    print(f"Current data entries: {len(sample_data['current_data'])}")
    print(f"Previous data entries: {len(sample_data['previous_data'])}")
    
    # Filter the data
    filtered_data = filter_vision_data(sample_data)
    
    # Print filtered data structure
    print("\n===== FILTERED VISION DATA =====")
    print(f"Current data entries: {len(filtered_data['current_data'])}")
    print(f"Previous data entries: {len(filtered_data['previous_data'])}")
    
    # Verify that main entities with all zeros were removed
    current_entities = [item["main_entity"] for item in filtered_data["current_data"]]
    previous_entities = [item["main_entity"] for item in filtered_data["previous_data"]]
    
    print("\nCurrent main entities after filtering:", current_entities)
    print("Previous main entities after filtering:", previous_entities)
    
    # Check if the filtering worked as expected
    assert "Events" not in current_entities, "Main entity with all zeros was not filtered out"
    assert "Links" not in previous_entities, "Main entity with all zeros was not filtered out"
    
    # Verify sub-entities with zero values were removed
    for item in filtered_data["current_data"]:
        if item["main_entity"] == "Persons":
            assert "Pictures" not in item["sub_entities"], "Zero-value sub-entity was not filtered out"
            assert "Features" not in item["sub_entities"], "Zero-value sub-entity was not filtered out"
            assert "Persons" in item["sub_entities"], "Non-zero sub-entity was incorrectly filtered"
            
            # Check that descriptions were added
            assert "value" in item["sub_entities"]["Persons"], "Value field not added to sub-entity"
            assert "description" in item["sub_entities"]["Persons"], "Description field not added to sub-entity"
    
    # Format the filtered data for prompts
    formatted_text = format_vision_data_for_prompt(filtered_data)
    
    # Print the formatted text
    print("\n===== FORMATTED VISION DATA FOR PROMPT =====")
    print(formatted_text)
    
    # Save the formatted text to a file for inspection
    with open("formatted_vision_data.txt", "w") as f:
        f.write(formatted_text)
    
    print("\nTest completed successfully!")
    print(f"Formatted data saved to 'formatted_vision_data.txt' for inspection")

def test_with_unknown_entities():
    """Test how the system handles unknown sub-entities without descriptions."""
    logger.info("Testing with unknown sub-entities")
    
    # Create sample data with unknown sub-entities
    sample_data = create_sample_vision_data()
    
    # Add unknown sub-entities
    sample_data["current_data"][0]["sub_entities"]["UnknownEntity1"] = 5
    sample_data["previous_data"][0]["sub_entities"]["UnknownEntity2"] = 3
    
    # Filter and format
    filtered_data = filter_vision_data(sample_data)
    formatted_text = format_vision_data_for_prompt(filtered_data)
    
    print(sample_data["previous_data"][0]["sub_entities"]["UnknownEntity2"])
    # Print results
    print("\n===== TESTING UNKNOWN ENTITIES =====")
    print("Formatted text includes unknown entities:")
    
    # Find the unknown entities in the formatted text
    if "UnknownEntity1" in formatted_text:
        print("OK: UnknownEntity1 is included with empty description")
    else:
        print("X: UnknownEntity1 is missing from the output")
        
    if "UnknownEntity2" in formatted_text:
        print("OK: UnknownEntity2 is included with empty description")
    else:
        print("X: UnknownEntity2 is missing from the output")
    
    print("\nUnknown entities test completed")

def test_empty_vision_data():
    """Test handling of empty vision data."""
    logger.info("Testing with empty vision data")
    
    # Test with completely empty data
    empty_data = {}
    filtered_empty = filter_vision_data(empty_data)
    formatted_empty = format_vision_data_for_prompt(filtered_empty)
    
    print("\n===== TESTING EMPTY VISION DATA =====")
    print(f"Empty data filtered result: {filtered_empty}")
    print(f"Empty data formatted result: '{formatted_empty}'")
    
    assert filtered_empty == {}, "Empty data should return empty dict"
    assert formatted_empty == "", "Empty data should return empty string when formatted"
    
    # Test with empty sub-sections but valid structure
    empty_structured = {
        "date_context": {},
        "current_data": [],
        "previous_data": []
    }
    filtered_structured = filter_vision_data(empty_structured)
    formatted_structured = format_vision_data_for_prompt(filtered_structured)
    
    print(f"Empty structured data formatted result: '{formatted_structured}'")
    assert formatted_structured == "", "Empty structured data should return empty string when formatted"
    
    print("Empty data tests passed!")

def test_mixed_value_entities():
    """Test handling of entities with mixed zero and non-zero values."""
    logger.info("Testing with mixed value entities")
    
    today = date.today()
    
    # Create a test case with mixed values
    mixed_data = {
        "date_context": {"report_date": today.isoformat()},
        "current_data": [
            {
                "main_entity": "MixedEntity",
                "sub_entities": {
                    "ZeroValue1": 0,  # Should be filtered out
                    "ZeroValue2": 0,  # Should be filtered out
                    "NonZeroValue1": 5,  # Should remain
                    "NonZeroValue2": 3   # Should remain
                },
                "from_date": (today - timedelta(days=1)).isoformat(),
                "to_date": today.isoformat()
            }
        ],
        "previous_data": []
    }
    
    # Filter and format
    filtered_mixed = filter_vision_data(mixed_data)
    formatted_mixed = format_vision_data_for_prompt(filtered_mixed)
    
    print("\n===== TESTING MIXED VALUE ENTITIES =====")
    
    # Check that zero values were removed but non-zero values remain
    if "current_data" in filtered_mixed and filtered_mixed["current_data"]:
        sub_entities = filtered_mixed["current_data"][0]["sub_entities"]
        print(f"Filtered sub-entities: {list(sub_entities.keys())}")
        
        assert "ZeroValue1" not in sub_entities, "Zero value should be filtered out"
        assert "ZeroValue2" not in sub_entities, "Zero value should be filtered out"
        assert "NonZeroValue1" in sub_entities, "Non-zero value should remain"
        assert "NonZeroValue2" in sub_entities, "Non-zero value should remain"
    
    # Check the formatted output
    print("\nFormatted output:")
    print(formatted_mixed)
    
    # More specific checks that look for formatted entries rather than just string presence
    assert "Number of ZeroValue1:" not in formatted_mixed, "Zero value should not appear as a formatted entry"
    assert "Number of ZeroValue2:" not in formatted_mixed, "Zero value should not appear as a formatted entry"
    assert "Number of NonZeroValue1:" in formatted_mixed, "Non-zero value should appear as a formatted entry"
    assert "Number of NonZeroValue2:" in formatted_mixed, "Non-zero value should appear as a formatted entry"
    
    print("Mixed value entity tests passed!")

def test_description_formatting():
    """Test that descriptions are correctly formatted in the output."""
    logger.info("Testing description formatting")
    
    today = date.today()
    
    # Create test data with known descriptions
    test_data = {
        "date_context": {"report_date": today.isoformat()},
        "current_data": [
            {
                "main_entity": "Persons",  # This should have a description
                "sub_entities": {
                    "Persons": 5,  # This should have a description
                    "CustomEntity": 3  # This should not have a description
                },
                "from_date": (today - timedelta(days=1)).isoformat(),
                "to_date": today.isoformat()
            }
        ],
        "previous_data": []
    }
    
    # Filter and format
    filtered_data = filter_vision_data(test_data)
    formatted_text = format_vision_data_for_prompt(filtered_data)
    
    print("\n===== TESTING DESCRIPTION FORMATTING =====")
    print(formatted_text)
    
    # Check that known descriptions are properly included
    assert "Persons: 5 (New Person records created)" in formatted_text, "Known entity description should be included"
    assert "CustomEntity: 3 ()" in formatted_text, "Unknown entity should have empty description parentheses"
    
    print("Description formatting tests passed!")

def test_all_zero_entities():
    """Test that main entities with all zero sub-entities are completely filtered out."""
    logger.info("Testing all-zero entities filtering")
    
    today = date.today()
    
    # Create test data with an all-zero entity
    test_data = {
        "date_context": {"report_date": today.isoformat()},
        "current_data": [
            {
                "main_entity": "AllZeros",
                "sub_entities": {
                    "SubEntity1": 0,
                    "SubEntity2": 0,
                    "SubEntity3": 0
                },
                "from_date": (today - timedelta(days=1)).isoformat(),
                "to_date": today.isoformat()
            },
            {
                "main_entity": "MixedValues",
                "sub_entities": {
                    "SubEntity1": 0,
                    "SubEntity2": 5,
                    "SubEntity3": 0
                },
                "from_date": (today - timedelta(days=1)).isoformat(),
                "to_date": today.isoformat()
            }
        ],
        "previous_data": []
    }
    
    # Filter and format
    filtered_data = filter_vision_data(test_data)
    formatted_text = format_vision_data_for_prompt(filtered_data)
    
    print("\n===== TESTING ALL-ZERO ENTITIES FILTERING =====")
    print(f"Number of current data entries after filtering: {len(filtered_data['current_data'])}")
    print(formatted_text)
    
    # Check that all-zero entity was removed but mixed entity remains
    assert len(filtered_data["current_data"]) == 1, "Only one entity should remain after filtering"
    assert filtered_data["current_data"][0]["main_entity"] == "MixedValues", "Only the mixed values entity should remain"
    assert "AllZeros" not in formatted_text, "All-zero entity should be completely filtered out"
    assert "MixedValues" in formatted_text, "Mixed values entity should remain"
    
    print("All-zero entities filtering tests passed!")

def test_sub_entity_content_limit():
    """Test that the entity limit per sub-entity content is respected and 'and X more...' is shown."""
    logger.info("Testing sub-entity content limit in formatted vision data")
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Create sample vision data with sub_entities_content
    sample_data = {
        "date_context": {"report_date": today.isoformat()},
        "current_data": [
            {
                "main_entity": "Tasks",
                "sub_entities": {
                    "DFA": 5,
                    "Correspondence": 2
                },
                "sub_entities_content": {
                    "DFA": [
                        {"Correspondence_Title": "A", "Correspondence_Report": "Attached", "Correspondence_Date": "2025-06-27"},
                        {"Correspondence_Title": "B", "Correspondence_Report": "Attached", "Correspondence_Date": "2025-06-28"},
                        {"Correspondence_Title": "C", "Correspondence_Report": "Attached", "Correspondence_Date": "2025-06-29"},
                        {"Correspondence_Title": "D", "Correspondence_Report": "Attached", "Correspondence_Date": "2025-06-30"},
                        {"Correspondence_Title": "E", "Correspondence_Report": "Attached", "Correspondence_Date": "2025-07-01"},
                        {"Correspondence_Title": "F", "Correspondence_Report": "Attached", "Correspondence_Date": "2025-07-02"}
                    ],
                    "Correspondence": [
                        {"Correspondence_Title": "G", "Correspondence_Report": "Attached", "Correspondence_Date": "2025-07-03"}
                    ]
                },
                "from_date": yesterday.isoformat(),
                "to_date": today.isoformat()
            }
        ],
        "previous_data": []
    }

    # Pass sample_data through filter_vision_data to match expected structure
    filtered_data = filter_vision_data(sample_data)
    max_items = 3
    formatted_text = format_vision_data_for_prompt(filtered_data, max_content_items_per_entity=max_items)
    print("\n===== TESTING SUB-ENTITY CONTENT LIMIT =====")
    print(formatted_text)

    # Check that only max_items are shown for DFA and the "and X more..." line appears
    assert formatted_text.count("---> Correspondence_Title:") == max_items + 1, "Should show only max_items for DFA plus one for Correspondence"
    assert "and 3 more..." in formatted_text, "'and X more...' message should appear for DFA"
    assert "Correspondence_Title: G" in formatted_text, "Single Correspondence item should be shown"
    print("Sub-entity content limit test passed!")

if __name__ == "__main__":
    # Run all tests
    test_vision_data_filtering()
    test_with_unknown_entities()
    test_empty_vision_data()
    test_mixed_value_entities()
    test_description_formatting()
    test_all_zero_entities()
    test_sub_entity_content_limit()
    
    print("\n===== ALL TESTS COMPLETED SUCCESSFULLY =====")
