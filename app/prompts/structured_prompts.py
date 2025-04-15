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
    
    # Specific prompt templates for different use cases
    
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
You are an expert HR analyst reviewing employee reports. Your task is to analyze the following weekly/monthly report from an employee and extract key information in a structured format.

Please provide a comprehensive analysis with the following elements:

1. ACHIEVEMENTS: Identify key accomplishments mentioned in the report. For each achievement:
   - Provide a detailed description of what was accomplished
   - Rate its impact on a scale from 1-10 (where 10 is highest impact)

2. CHALLENGES: Identify obstacles or issues the employee faced. For each challenge:
   - Provide a detailed description of the challenge
   - Rate its severity as "low", "medium", or "high"

3. SENTIMENT: Determine if the overall tone is "positive", "negative", or "neutral"

4. TOPICS: Extract the main discussion points or project areas (as a list of key phrases)

5. ACTION ITEMS: Recommend specific follow-up actions based on the report content (as a list)

6. RISK ASSESSMENT: Determine if there are any concerns requiring management attention
   - Rate the overall risk as "low", "medium", or "high"
   - Provide detailed reasoning for your risk assessment

Analyze only the content provided and stay objective. Your response should be structured in a format suitable for JSON conversion.

EMPLOYEE REPORT:
---
{report_text}
---"""

        # Add context from similar reports if provided
        if similar_reports and len(similar_reports) > 0:
            similar_context = "\n\n".join([f"Similar Report #{i+1}:\n{report}" for i, report in enumerate(similar_reports)])
            prompt += f"""
SIMILAR PREVIOUS REPORTS FOR CONTEXT:
---
{similar_context}
---

Use these similar reports to identify patterns, but focus your analysis on the current report.
"""

        # Add final instructions for structured output
        prompt += """
Structure your response as follows:
{
  "achievements": [
    {"description": "Detailed achievement description", "impact": "Impact rating (1-10)"},
    {"description": "Another achievement", "impact": "Impact rating (1-10)"}
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
