"""
Test script for verifying the prompt generation with filtered vision data.
This script tests the end-to-end process of filtering vision data and using it in prompt generation.
"""
import sys
import os
from datetime import date, timedelta

# Add the parent directory to path so we can import the app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.prompts.structured_prompts import StructuredPrompts
# format_vision_data_for_prompt was renamed in commit 4213c2f
from app.services.analysis.vision_formatting import (
    filter_vision_data,
    format_vision_data_for_weekly_analysis_prompt as format_vision_data_for_prompt,
)
from app.core.logger import logger

def create_sample_report():
    """Create a sample employee report for testing."""
    return """
Weekly Performance Report - John Doe
Department: Engineering
Week: June 1-5, 2025

1. Tasks completed during the past week:
- Implemented new authentication module for the customer portal
- Fixed 3 critical bugs in the payment processing system
- Conducted code review for team members' pull requests
- Updated documentation for the API endpoints

2. Impact/outcome of the completed tasks:
- Authentication module improves security for customer data
- Bug fixes resolved payment failures that were affecting 5% of transactions
- Code reviews helped maintain code quality standards
- API documentation will help onboard new developers faster

3. Challenges/obstacles faced:
- Limited access to the test environment delayed bug verification
- Had to coordinate with multiple teams for the authentication implementation
- Some documentation was outdated, requiring additional research

4. Required tools/support/resources:
- Need dedicated test environment access to avoid delays
- Request for additional training on the new security framework
- Assistance from UX team for the authentication flow design

5. Tasks planned for next week:
- Begin implementation of the reporting dashboard
- Complete the remaining API documentation updates
- Test and deploy the authentication module to production
- Meet with security team for audit of recent changes

6. Confidence level regarding tasks for the next week:
4 - Confident about completing most tasks, but the security audit might require additional time depending on feedback.
"""

def create_sample_vision_data():
    """Create sample vision data for testing."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    
    return {
        "date_context": {
            "report_date": today.isoformat(),
        },
        "current_data": [
            {
                "main_entity": "Tasks",
                "sub_entities": {
                    "Tasks": 4,
                    "Task Updates": 7,
                    "Task Attachments": 0,  # Should be filtered out
                    "Assigned/CC": 3
                },
                "from_date": yesterday.isoformat(),
                "to_date": today.isoformat()
            },
            {
                "main_entity": "Correspondence",
                "sub_entities": {
                    "DFA": 2,
                    "Correspondence": 5,
                    "Notings": 0  # Should be filtered out
                },
                "from_date": yesterday.isoformat(),
                "to_date": today.isoformat()
            },
            {
                "main_entity": "Events",
                "sub_entities": {
                    "Events": 0,  # All zeros, entire entity should be filtered
                    "EOIs": 0,
                    "Information": 0
                },
                "from_date": yesterday.isoformat(),
                "to_date": today.isoformat()
            }
        ],
        "previous_data": [
            {
                "main_entity": "Tasks",
                "sub_entities": {
                    "Tasks": 6,
                    "Task Updates": 12,
                    "Task Attachments": 3,
                    "Assigned/CC": 0  # Should be filtered out
                },
                "from_date": (last_week - timedelta(days=7)).isoformat(),
                "to_date": last_week.isoformat()
            }
        ]
    }

def create_similar_reports():
    """Create sample similar reports for testing."""
    return [
        """
Weekly Performance Report - John Doe
Department: Engineering
Week: May 25-29, 2025

1. Tasks completed during the past week:
- Completed design for new authentication module
- Created test cases for payment processing fixes
- Participated in sprint planning and backlog refinement

2. Impact/outcome of the completed tasks:
- Design approved by security team
- Test cases ready for implementation
- Sprint backlog properly prioritized

3. Challenges/obstacles faced:
- Security requirements required multiple revisions
- Test environment was down for maintenance

4. Required tools/support/resources:
- Need dedicated test environment access

5. Tasks planned for next week:
- Begin implementation of authentication module
- Fix critical bugs in payment processing
- Update API documentation

6. Confidence level regarding tasks for the next week:
3 - Moderately confident, but concerned about test environment availability.
"""
    ]

def test_prompt_generation():
    """Test the generation of prompts with filtered vision data."""
    logger.info("Starting prompt generation test")
    
    # Create sample data
    report_text = create_sample_report()
    vision_data = create_sample_vision_data()
    similar_reports = create_similar_reports()
    
    # Filter and format vision data
    filtered_vision_data = filter_vision_data(vision_data)
    formatted_vision_data = format_vision_data_for_prompt(filtered_vision_data)
    
    # Print filtered and formatted vision data
    print("\n===== FILTERED AND FORMATTED VISION DATA =====")
    print(formatted_vision_data)
    
    # Generate prompt
    prompt = StructuredPrompts.employee_analysis_prompt(
        report_text=report_text,
        formatted_vision_data=formatted_vision_data,
        similar_reports=similar_reports
    )
    
    # Write prompt to file for inspection
    with open("generated_prompt.txt", "w") as f:
        f.write(prompt)
    
    # Check that prompt contains the vision data with proper headings
    assert "OBJECTIVE TRACKING DATA FROM VISION SYSTEM" in prompt, "Vision data section missing from prompt"
    assert "=== CURRENT REPORT ACTIVITY DATA ===" in prompt, "Current data heading missing from prompt"
    assert "=== HISTORICAL ACTIVITY DATA ===" in prompt, "Historical data heading missing from prompt"
    
    # Check the content and ordering
    assert "- Tasks: 4" in prompt, "Filtered task data missing from prompt"
    
    # Check that sections appear in the correct order
    vision_section_pos = prompt.find("OBJECTIVE TRACKING DATA FROM VISION SYSTEM")
    instructions_pos = prompt.find("USING VISION SYSTEM DATA IN YOUR ANALYSIS")
    similar_reports_pos = prompt.find("SIMILAR PREVIOUS REPORTS FOR CONTEXT")
    
    assert vision_section_pos < instructions_pos, "Vision data should appear before usage instructions"
    assert instructions_pos < similar_reports_pos, "Vision usage instructions should appear before similar reports"
    
    # Check that zero-value entries are filtered out
    assert "Task Attachments" not in formatted_vision_data.split("Historical Activity Data")[0], "Zero-value 'Task Attachments' not filtered out from current data"
    assert "Notings" not in formatted_vision_data, "Zero-value 'Notings' not filtered out"
    assert "Events" not in formatted_vision_data, "All-zero 'Events' entity not filtered out"
    
    # Check that non-zero historical data is preserved
    assert "Task Attachments: 3" in formatted_vision_data, "Non-zero historical 'Task Attachments' should be present"
    
    # Check that the USING VISION SYSTEM DATA section is included
    assert "USING VISION SYSTEM DATA IN YOUR ANALYSIS" in prompt, "Instructions for using vision data missing"
    
    # Check that similar reports are included
    assert "SIMILAR PREVIOUS REPORTS FOR CONTEXT" in prompt, "Similar reports section missing from prompt"
    assert "Week: May 25-29, 2025" in prompt, "Similar report content missing from prompt"
    
    print(f"\nPrompt generation test passed!")
    print(f"Complete prompt saved to 'generated_prompt.txt' for inspection")
    
    # Print some stats about the prompt
    prompt_length = len(prompt)
    print(f"Prompt length: {prompt_length} characters")
    print(f"Approximate token count: {prompt_length / 4} tokens")

if __name__ == "__main__":
    # Run the test
    test_prompt_generation()
