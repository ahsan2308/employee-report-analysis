"""
Test vision data content item truncation to prevent context overflow.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.analysis.vision_formatting import (
    _truncate_content_value,
    format_vision_data_for_weekly_analysis_prompt,
    format_vision_data_for_monthly_analysis_prompt,
    format_vision_data_for_quarterly_analysis_prompt,
)


def test_truncate_content_value_short_text():
    """Test that short text is not truncated."""
    text = "This is a short description"
    result = _truncate_content_value(text, max_length=100)
    assert result == text
    assert "..." not in result


def test_truncate_content_value_long_text():
    """Test that long text is truncated with ellipsis."""
    text = "A" * 500  # 500 character string
    result = _truncate_content_value(text, max_length=100)
    assert len(result) == 103  # 100 chars + "..."
    assert result.endswith("...")
    assert result.startswith("A" * 100)


def test_truncate_content_value_none():
    """Test that None returns empty string."""
    result = _truncate_content_value(None)
    assert result == ""


def test_truncate_content_value_non_string():
    """Test that non-string values are converted to string."""
    result = _truncate_content_value(12345, max_length=3)
    assert result == "123..."


def test_vision_data_formatting_with_long_content():
    """Test that vision data formatting truncates long content items."""
    # Create mock vision data with very long content
    long_description = "X" * 1000  # 1000 character description
    
    vision_data = {
        "current_data": [{
            "from_date": "2025-01-01",
            "to_date": "2025-01-07",
            "main_entity": "Tasks",
            "sub_entities": {
                "Task Updates": {
                    "value": 5,
                    "description": "Updates added with Tasks"
                }
            },
            "sub_entities_content": {
                "Task Updates": [
                    {"Description": long_description, "Status": "Completed"},
                    {"Description": "Short desc", "Status": "In Progress"}
                ]
            }
        }]
    }
    
    # Format with max_content_item_length=100
    result = format_vision_data_for_weekly_analysis_prompt(
        vision_data,
        max_content_items_per_entity=5,
        max_content_item_length=100
    )
    
    # Check that the long description was truncated
    assert "..." in result
    # The truncated description should be 100 chars + "..."
    assert long_description not in result  # Full 1000 char string should not appear
    assert "Short desc" in result  # Short descriptions should remain intact


def test_monthly_vision_data_formatting_truncation():
    """Test that monthly vision data formatting applies truncation."""
    long_case_details = "Z" * 800  # 800 character case details
    
    vision_data = {
        "weeks_data": [{
            "week_number": 1,
            "activities": [{
                "from_date": "2025-01-01",
                "to_date": "2025-01-07",
                "main_entity": "Cases",
                "sub_entities": {
                    "Cases": {
                        "value": 2,
                        "description": "FIR details"
                    }
                },
                "sub_entities_content": {
                    "Cases": [
                        {"FIR_Number": "123/2025", "Details": long_case_details}
                    ]
                }
            }]
        }]
    }
    
    result = format_vision_data_for_monthly_analysis_prompt(
        vision_data,
        max_content_items_per_entity=5,
        max_content_item_length=150
    )
    
    # Long case details should be truncated to 150 chars + "..."
    assert "..." in result
    assert len([line for line in result.split('\n') if long_case_details in line]) == 0


def test_quarterly_vision_data_formatting_truncation():
    """Test that quarterly vision data formatting applies truncation."""
    long_report_text = "Q" * 600  # 600 character report
    
    vision_data = {
        "date_context": {
            "year": 2025,
            "quarter": 1,
            "period_start": "2025-01-01",
            "period_end": "2025-03-31"
        },
        "months_data": [{
            "month_name": "January",
            "weeks_data": [{
                "week_number": 1,
                "activities": [{
                    "from_date": "2025-01-01",
                    "to_date": "2025-01-07",
                    "main_entity": "News/Media Reports",
                    "sub_entities": {
                        "News/Media Reports": {
                            "value": 1,
                            "description": "News reports created"
                        }
                    },
                    "sub_entities_content": {
                        "News/Media Reports": [
                            {"Title": "Test Report", "Content": long_report_text}
                        ]
                    }
                }]
            }]
        }]
    }
    
    result = format_vision_data_for_quarterly_analysis_prompt(
        vision_data,
        max_content_items_per_entity=5,
        max_content_item_length=200
    )
    
    # Long report text should be truncated to 200 chars + "..."
    assert "..." in result
    assert len([line for line in result.split('\n') if long_report_text in line]) == 0
    assert "QUARTERLY VISION DATA" in result


def test_different_truncation_lengths():
    """Test that different truncation lengths work correctly."""
    text = "B" * 500
    
    # 100 char limit
    result_100 = _truncate_content_value(text, max_length=100)
    assert len(result_100) == 103  # 100 + "..."
    
    # 200 char limit
    result_200 = _truncate_content_value(text, max_length=200)
    assert len(result_200) == 203  # 200 + "..."
    
    # 300 char limit
    result_300 = _truncate_content_value(text, max_length=300)
    assert len(result_300) == 303  # 300 + "..."
    
    # Verify they're different
    assert result_100 != result_200 != result_300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
