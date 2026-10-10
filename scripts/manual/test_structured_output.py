"""
Test script for the new structured output functionality in Ollama.
"""
import sys
import os
import json
from typing import Dict, Any, List, Optional, Literal

# Add the project root to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.llm_service import get_llm_service
from app.core.logger import logger

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    print("Pydantic is not installed. Some tests will be skipped.")

def print_json(data: Dict[str, Any]) -> None:
    """Print JSON data in a formatted way."""
    print(json.dumps(data, indent=2))

def test_schema_dict():
    """Test using a direct JSON schema dictionary."""
    print("\n=== Testing Direct JSON Schema ===")
    llm_service = get_llm_service(model="llama3.1:8b")
    
    # Define a schema as a dictionary
    person_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"},
            "favorite_color": {"type": "string"},
            "hobbies": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["name", "age"]
    }
    
    prompt = "Generate information about a fictional person who enjoys hiking."
    
    print(f"Prompt: {prompt}")
    print("Using direct JSON schema")
    
    result = llm_service.get_structured_response(
        prompt=prompt,
        response_format=person_schema,
        temperature=0  # Use 0 for deterministic output as recommended
    )
    
    print("\nResult:")
    print_json(result)
    
    # Validate the result
    if result:
        print("\nValidation:")
        print(f"- Has name: {'name' in result}")
        print(f"- Has age: {'age' in result}")
        print(f"- Has favorite_color: {'favorite_color' in result}")
        print(f"- Has hobbies: {'hobbies' in result}")
        
        if 'hobbies' in result and isinstance(result['hobbies'], list):
            print(f"- Hobbies: {', '.join(result['hobbies'])}")
    
    return result

def test_pydantic_schema():
    """Test using a Pydantic model schema (if available)."""
    if not HAS_PYDANTIC:
        print("\n=== Skipping Pydantic Schema Test (Pydantic not installed) ===")
        return None
        
    print("\n=== Testing Pydantic Schema ===")
    
    # Define a Pydantic model
    class Pet(BaseModel):
        name: str
        animal: str
        age: int
        color: Optional[str] = None
        favorite_toy: Optional[str] = None

    class PetList(BaseModel):
        pets: List[Pet]
    
    llm_service = get_llm_service(model='llama3.1:8b')
    prompt = """
        I have two pets.
        A cat named Luna who is 5 years old and loves playing with yarn. She has grey fur.
        I also have a 2 year old black cat named Loki who loves tennis balls.
    """
    
    print(f"Prompt: {prompt}")
    print("Using Pydantic schema model")
    
    # Get the provider to use the direct Pydantic model if supported
    if hasattr(llm_service.provider, 'generate_structured_output'):
        try:
            # Try direct Pydantic model usage
            result = llm_service.provider.generate_structured_output(
                prompt=prompt,
                json_schema=PetList,
                temperature=0
            )
            
            if result:
                print("\nResult from direct Pydantic model:")
                print_json(result)
                
                # Create Pydantic model instance from result
                if HAS_PYDANTIC:
                    pet_list = PetList.model_validate(result)
                    print("\nValidated Pydantic model:")
                    for i, pet in enumerate(pet_list.pets):
                        print(f"Pet {i+1}: {pet.name} - {pet.animal}, {pet.age} years old, {pet.color}")
                
                return result
        except Exception as e:
            print(f"Error with direct Pydantic schema: {e}")
    
    # Fallback to using the schema dictionary
    result = llm_service.get_structured_response(
        prompt=prompt,
        response_format=PetList.model_json_schema(),
        temperature=0
    )
    
    print("\nResult from JSON schema:")
    print_json(result)
    
    return result

def test_employee_analysis():
    """Test employee report analysis with the enhanced structured output."""
    print("\n=== Testing Enhanced Employee Analysis ===")
    llm_service = get_llm_service(model='llama3.1:8b')
    
    sample_report = """
    Quarterly Report - Q2 2023
    Employee: Jane Smith
    Department: Software Engineering
    
    Accomplishments:
    - Led the migration of our authentication system to OAuth 2.0, reducing login issues by 45%
    - Mentored two junior developers who are now contributing independently to the codebase
    - Completed all assigned tasks on time despite project scope changes
    
    Challenges:
    - The timeline for the mobile app release was tight and required some weekend work
    - Communication with the design team was sometimes difficult due to conflicting priorities
    
    Goals for Next Quarter:
    - Complete advanced cloud certification
    - Improve test coverage across the platform to 85%
    - Take lead on implementing the new recommendation engine
    """
    
    # Create a schema for employee analysis
    if HAS_PYDANTIC:
        class Achievement(BaseModel):
            description: str
            impact: str = Field(description="The impact or result of this achievement")

        class Challenge(BaseModel):
            description: str
            severity: Literal["low", "medium", "high"] = Field(default="medium")

        class EmployeeAnalysis(BaseModel):
            achievements: List[Achievement]
            challenges: List[Challenge]  
            sentiment: Literal["positive", "negative", "neutral"]
            topics: List[str]
            action_items: List[str]
            risk_level: Literal["low", "medium", "high"]
            risk_explanation: str
        
        schema = EmployeeAnalysis.model_json_schema()
    else:
        # Fallback schema for non-Pydantic environments
        schema = {
            "type": "object",
            "properties": {
                "achievements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "impact": {"type": "string"}
                        },
                        "required": ["description", "impact"]
                    }
                },
                "challenges": {
                    "type": "array", 
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]}
                        },
                        "required": ["description", "severity"]
                    }
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"]
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "action_items": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"]
                },
                "risk_explanation": {"type": "string"}
            },
            "required": ["achievements", "challenges", "sentiment", "topics", "action_items", "risk_level", "risk_explanation"]
        }
    
    print("Analyzing sample employee report...")
    
    prompt = f"""Please analyze the following employee report and extract key information:

{sample_report}

Provide a detailed analysis including achievements with their impact, challenges and their severity,
overall sentiment, key topics, recommended action items, and risk assessment.
"""
    
    result = llm_service.get_structured_response(
        prompt=prompt,
        response_format=schema,
        temperature=0
    )
    
    print("\nAnalysis Result:")
    print_json(result)
    
    return result

if __name__ == "__main__":
    try:
        print("Testing Enhanced Ollama Structured Output")
        print("========================================")
        
        dict_result = test_schema_dict()
        pydantic_result = test_pydantic_schema()
        analysis_result = test_employee_analysis()
        
        print("\n========================================")
        print("All tests completed!")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"Error during test: {e}")
