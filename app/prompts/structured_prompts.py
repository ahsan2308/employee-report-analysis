"""
Prompt templates for structured output generation.

This module contains templates for prompting LLMs to generate
structured outputs in specific JSON formats. Import these when
you need consistent prompt templates for structured data generation.
"""
from app.prompts import monthly, quarterly, weekly
from typing import Dict, Any
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
    
    employee_analysis_prompt = staticmethod(weekly.employee_analysis_prompt)
    
    @staticmethod
    def combine_prompt(task_prompt: str, format_prompt: str) -> str:
        """Combine a task prompt with a format prompt."""
        return f"{task_prompt}\n\n{format_prompt}"
    
    monthly_analysis_prompt = staticmethod(monthly.monthly_analysis_prompt)

    quarterly_analysis_prompt = staticmethod(quarterly.quarterly_analysis_prompt)


