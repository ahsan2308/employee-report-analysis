"""
Prompt templates for structured output generation.

This module contains templates for prompting LLMs to generate
structured outputs in specific JSON formats. Import these when
you need consistent prompt templates for structured data generation.
"""
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
    
    # Specific prompt templates for different use cases
    
    @staticmethod
    def employee_analysis_prompt(report_text: str, similar_reports: list = None) -> str:
        """Generate prompt for employee report analysis."""
        context = ""
        if similar_reports and len(similar_reports) > 0:
            context = "Previous reports for context:\n\n" + "\n---\n".join(similar_reports) + "\n\n"
        
        # Simplified prompt focused on core fields needed for the simplified model
        return (
            f"{context}Please analyze the following employee report:\n\n{report_text}\n\n"
            "Provide the following analysis focusing on these key required aspects:\n"
            "1. Overall sentiment (must be exactly one of: positive, negative, neutral)\n"
            "2. Risk assessment (must be exactly one of: low, medium, high)\n"
            "3. Detailed explanation for the risk assessment\n"
            "4. Key topics covered in the report (as a list)"
        )
        
        # Original detailed prompt (commented out)
        """
        return (
            f"{context}Please analyze the following employee report:\n\n{report_text}\n\n"
            "Provide the following analysis:\n"
            "1. Key achievements with their measurable impact\n"
            "2. Challenges mentioned and their severity\n"
            "3. Overall sentiment (positive, negative, neutral)\n"
            "4. Key topics covered\n"
            "5. Recommended action items\n"
            "6. Risk assessment (low, medium, high) with explanation"
        )
        """
    
    @staticmethod
    def developer_profile_prompt(developer_info: str = "") -> str:
        """Generate prompt for developer profile information."""
        return (
            f"Generate a detailed developer profile based on the following information:\n\n{developer_info}\n\n"
            "Include personal information, technical skills, projects they've worked on, "
            "years of experience, specialization, programming languages, and frameworks they know."
        )
    
    @staticmethod
    def pet_info_prompt(pet_description: str) -> str:
        """Generate prompt for pet information extraction."""
        return (
            f"Extract pet information from the following description:\n\n{pet_description}\n\n"
            "For each pet mentioned, include their name, animal type, age, "
            "color (if mentioned), and favorite toy (if mentioned)."
        )
    
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
