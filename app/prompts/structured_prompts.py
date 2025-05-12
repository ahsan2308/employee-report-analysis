"""
Prompt templates for structured output generation.

This module contains templates for prompting LLMs to generate
structured outputs in specific JSON formats. Import these when
you need consistent prompt templates for structured data generation.
"""
from typing import Dict, Any, List
import json

class StructuredPrompts:
    """Collection of prompts for structured output generation."""
    
    @staticmethod
    def general_json_instruction() -> str:
        """General instruction for JSON output."""
        return (
            "IMPORTANT: Your response must be valid JSON data conforming to the schema, "
            "not the schema itself. Do not include any explanatory text or code formatting "
            "markers like ```json or ```."
        )
    
    @staticmethod
    def format_schema_prompt(schema: Dict[str, Any], example_format: Dict[str, Any]) -> str:
        """Format a prompt for JSON schema with example."""
        return (
            f"\n{StructuredPrompts.general_json_instruction()}\n\n"
            f"Here's the schema your response should conform to:\n{json.dumps(schema, indent=2)}\n\n"
            f"Example format of what I'm expecting (with your own values):\n{json.dumps(example_format, indent=2)}\n"
        )
    
    @staticmethod
    def format_simple_prompt(example_format: Dict[str, Any]) -> str:
        """Format a prompt for simple JSON with example."""
        return (
            f"\n{StructuredPrompts.general_json_instruction()}\n\n"
            f"Follow this exact format:\n{json.dumps(example_format, indent=2)}\n"
        )
    
    # Specific prompt template
    
    @staticmethod
    def employee_analysis_prompt(report_text: str, similar_reports: List[str] = None) -> str:
        """
        Generate a prompt for analyzing an employee report.
        
        Args:
            report_text: The report text to analyze
            similar_reports: Optional list of similar previous reports for context
            
        Returns:
            Prompt for employee report analysis
        """
        prompt = f"""
You are an expert HR analyst reviewing employee weekly performance reports. Your task is to analyze the following report and extract key information in a structured format.

The report follows a standard Weekly Performance Reporting format with these specific sections:

1. Tasks completed during the past week
   - This includes both routine and special/extraordinary tasks
   - Officers are instructed to provide as much relevant detail as possible
   - Some reports may indicate "Nothing to Report" with a reason

2. Impact/outcome of the completed tasks
   - This may include the level to which reports were viewed
   - Important decisions taken as a result of the employee's work
   - Quantifiable or qualitative outcomes achieved

3. Challenges/obstacles faced
   - Nature and severity of any issues encountered
   - Whether challenges were internal (organizational) or external
   - Any hindrances affecting task performance

4. Required tools/support/resources
   - Specific resources that would help with efficient task completion
   - Whether these deficiencies were previously reported
   - Any immediate support needs

5. Tasks planned for next week
   - Whether tasks were self-identified or assigned by a superior
   - Specific planned activities and deliverables
   - Continuations of ongoing projects

6. Confidence level regarding tasks for the next week
   - Rated on a scale of 1 to 5 (1 being lowest, 5 being highest)
   - An indicator of anticipated challenges or roadblocks
   - Reflects employee's perception of their ability to complete tasks on time

Please provide a comprehensive analysis with the following elements:

1. ACHIEVEMENTS: Identify key accomplishments from the "Tasks completed" and "Impact/outcome" sections. For each achievement:
   - Provide a detailed description of what was accomplished, especially extraordinary tasks
   - Rate its impact on a scale from 1-10 (where 10 is highest impact)
   - Format the impact field EXACTLY as: "N (reason)" where N is just the integer rating and reason is a brief explanation
   - The description field must contain complete sentences WITHOUT mentioning the impact rating
   - In your impact reason, link the reason with the impact level (individual, team, department, or organization-wide etc) as well if applicable   
   - Note if any important decisions resulted from the employee's work

2. CHALLENGES: Identify obstacles or issues from the "Challenges/obstacles faced" section. For each challenge:
   - Provide a detailed description of the challenge, distinguishing between internal and external factors
   - Rate its severity as "low", "medium", or "high"
   - Consider whether the challenge is one-time or recurring from previous reports
   - Note whether the challenge affects only this employee or has broader impact

3. SENTIMENT: Determine if the overall tone is "positive", "negative", or "neutral", paying special attention to:
   - The confidence level reported (1-5 suggests negative, 6-8 suggests neutral, 9-10 suggests positive)
   - Language used when describing challenges (frustrated, concerned, optimistic about resolution)
   - How the employee describes resource requests (urgent needs vs. helpful additions)
   - Balance between achievements reported and challenges faced
   - The employee's outlook on planned tasks

4. TOPICS: Extract the main discussion points, focus areas, or projects mentioned across all sections:
   - Identify specific projects or initiatives mentioned
   - Note recurring themes across current and previous reports
   - Capture key technical or organizational systems referenced
   - Identify stakeholders or departments mentioned as collaborators

5. ACTION ITEMS: Recommend specific follow-up actions based on:
   - The specific resources/support explicitly requested in section 4
   - Any immediate issues that need addressing from the challenges section
   - Preparation or support needed for tasks planned in the next week
   - Any pattern of decreasing confidence levels that requires intervention
   - Opportunities to build on successful achievements
   - Required follow-up on important decisions that resulted from the employee's work

6. RISK ASSESSMENT: Determine if there are any concerns requiring management attention:
   - Rate the overall risk as "low", "medium", or "high"
   - Pay special attention to: unfulfilled resource requests, declining confidence levels (below 3), external challenges beyond employee control, and negative patterns across reports
   - Consider risks to: project timelines, work quality, employee wellbeing, team dynamics
   - Provide detailed reasoning for your risk assessment, citing specific evidence from the report
   - Note any urgent intervention needed versus monitoring situations

EMPLOYEE REPORT:
---
{report_text}
---"""

        # Context from similar reports if provided
        if similar_reports and len(similar_reports) > 0:
            similar_context = "\n\n".join([f"Similar Report #{i+1}:\n{report}" for i, report in enumerate(similar_reports)])
            prompt += f"""
SIMILAR PREVIOUS REPORTS FOR CONTEXT:
---
{similar_context}
---

Analyze these previous reports to identify:
- Patterns in confidence levels (increasing, decreasing, or fluctuating)
- Recurring resource requests that haven't been addressed
- Previously mentioned challenges that are still present
- Progress on tasks that span multiple weeks
- Changes in tone or sentiment over time
- Do not write anything in the first person or use "I" or "we" in your analysis

Focus your primary analysis on the current report while using these patterns for context.
"""

        # Final instructions for structured output
        prompt += """
Structure your response as follows:
{
  "achievements": [
    {"description": "Detailed achievement description in complete sentences", "impact": "8 (Brief reason for this impact rating)"},
    {"description": "Another detailed achievement in complete sentences", "impact": "6 (Brief reason for this rating)"}
  ],
  "challenges": [
    {"description": "Detailed challenge description", "severity": "low/medium/high"},
    {"description": "Another challenge", "severity": "low/medium/high"}
  ],
  "sentiment": "positive/negative/neutral",
  "topics": ["Topic 1", "Topic 2", "Topic 3"],
  "action_items": ["Specific action recommendation 1", "Specific action recommendation 2"],
  "risk_level": "low/medium/high",
  "risk_explanation": "Detailed explanation of why you assigned this risk level"
}

Ensure your analysis is:
- Detailed and specific with concrete examples from the report
- Objective and fair in assessing achievements and challenges
- Actionable with clear recommendations
- Well-structured following the exact format above
- ALWAYS ensure your response is valid JSON with no extraneous text

Your analysis will help managers understand employee progress and determine where support is needed.
"""
        
        return prompt
    
    @staticmethod
    def fallback_guidance() -> str:
        """Provide guidance for text-based fallback."""
        return (
            "If you encounter any issues processing this, "
            "please ensure your response is valid JSON format. "
            "Remove any markdown, explanatory text, or code block delimiters. "
            "Present only a valid JSON object."
        )

    @staticmethod
    def combine_prompt(task_prompt: str, format_prompt: str) -> str:
        """Combine a task prompt with a format prompt."""
        return f"{task_prompt}\n\n{format_prompt}"


# Add more specialized prompt templates as needed
