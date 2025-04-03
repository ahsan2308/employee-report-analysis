"""
Comprehensive test script for the LLMService class and its functionality.
"""
import sys
import os
import json
import time
import unittest
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.llm_service import LLMService, get_llm_service
from app.core.logger import logger

# Helper function to print JSON data in a formatted way
def print_json(data: Dict[str, Any]) -> None:
    """Print JSON data in a formatted way."""
    print(json.dumps(data, indent=2))

class TestLLMServiceBasic:
    """Basic tests for LLMService that don't require mocking."""
    
    def test_initialization(self):
        """Test LLMService initialization with different models."""
        print("\n=== Testing LLMService Initialization ===")
        
        # Default initialization
        service1 = get_llm_service()
        print(f"Default model: {service1.model}")
        
        # Specific model initialization
        model_name = "llama3.1:8b"
        service2 = get_llm_service(model=model_name)
        print(f"Specified model: {service2.model}")
        
        # Verify the model info method works
        try:
            model_info = service2.provider.get_model_info()
            print("Model info retrieved successfully:")
            print(model_info)
        except Exception as e:
            print(f"Could not retrieve model info: {e}")
    
    def test_text_generation(self):
        """Test basic text generation functionality."""
        print("\n=== Testing Text Generation ===")
        service = get_llm_service(model="llama3.1:8b")
        
        prompts = [
            "Write a haiku about programming.",
            "Explain quantum computing in one sentence.",
            "List three benefits of exercise."
        ]
        
        for i, prompt in enumerate(prompts):
            print(f"\nPrompt {i+1}: {prompt}")
            
            # Test with different temperatures
            for temp in [0.0, 0.7]:
                print(f"\nTemperature: {temp}")
                result = service.generate_text(prompt, temperature=temp, max_tokens=100)
                print(f"Result: {result[:200]}...")
    
    def test_json_extraction(self):
        """Test JSON extraction from different text formats."""
        print("\n=== Testing JSON Extraction ===")
        service = get_llm_service(model="llama3.1:8b")
        
        test_cases = [
            # Clean JSON
            '{"name": "John", "age": 30}',
            
            # JSON with code block markers
            '```json\n{"name": "Alice", "age": 25}\n```',
            
            # JSON with text before and after
            'Here is the data: {"name": "Bob", "age": 40}. That\'s all folks!',
            
            # JSON with nested structures
            '{"person": {"name": "Eve", "details": {"age": 22, "job": "developer"}}}',
            
            # Malformed JSON to test error handling
            '{"name": "Broken JSON, "age": 50'
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\nTest case {i+1}:")
            print(f"Input: {test_case}")
            result = service.extract_json_from_text(test_case)
            print("Extracted JSON:")
            print_json(result)
    
    def test_structured_response(self):
        """Test structured response generation."""
        print("\n=== Testing Structured Response ===")
        service = get_llm_service(model="llama3.1:8b")
        
        # Simple format test
        simple_format = {
            "name": "example name",
            "age": 30,
            "skills": ["skill1", "skill2"]
        }
        
        prompt = "Generate information about a software developer."
        
        print(f"Prompt: {prompt}")
        print("Using simple format:")
        print_json(simple_format)
        
        result = service.get_structured_response(
            prompt=prompt,
            response_format=simple_format,
            temperature=0
        )
        
        print("\nResult:")
        print_json(result)
        
        # More complex schema
        complex_schema = {
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "number"},
                        "contact": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "phone": {"type": "string"}
                            }
                        }
                    }
                },
                "projects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        prompt = "Generate information about a software developer and their projects."
        
        print(f"\nPrompt: {prompt}")
        print("Using complex schema:")
        
        result = service.get_structured_response(
            prompt=prompt,
            response_format=complex_schema,
            temperature=0
        )
        
        print("\nResult:")
        print_json(result)
    
    def test_employee_analysis(self):
        """Test the employee report analysis functionality."""
        print("\n=== Testing Employee Report Analysis ===")
        service = get_llm_service(model="llama3.1:8b")
        
        sample_report = """
        Monthly Report - May 2023
        Employee: John Doe
        Department: Marketing
        
        Accomplishments:
        - Led successful product launch campaign that reached 2M+ people
        - Improved social media engagement by 34% through new content strategy
        - Organized team-building event that improved department coordination
        
        Challenges:
        - Budget constraints limited some planned promotional activities
        - Deadline pressure caused some quality control issues on minor deliverables
        
        Goals for Next Month:
        - Implement new analytics framework
        - Develop training materials for content creation
        - Establish better workflow with design team
        """
        
        # Test with no similar reports
        print("\nAnalyzing without similar reports:")
        result1 = service.analyze_report(sample_report)
        print_json(result1)
        
        # Test with similar reports
        similar_reports = [
            """
            Monthly Report - April 2023
            Employee: John Doe
            Department: Marketing
            
            Accomplishments:
            - Created new brand guidelines document
            - Conducted competitor analysis
            
            Challenges:
            - Team was understaffed due to spring vacations
            
            Goals for Next Month:
            - Complete product launch campaign
            - Improve social media metrics
            """,
        ]
        
        print("\nAnalyzing with similar reports:")
        result2 = service.analyze_report(sample_report, similar_reports)
        print_json(result2)
        
        return result1, result2


class TestLLMServiceAdvanced(unittest.TestCase):
    """Advanced tests for LLMService that require mocking."""
    
    def setUp(self):
        """Set up test environment."""
        # Don't create a real service in setUp, we'll create it in each test with the proper mock
        pass
    
    @patch('app.services.llm_service.get_llm_provider')  # Patch the import as used in llm_service.py
    def test_retry_mechanism(self, mock_get_provider):
        """Test the retry mechanism when generation fails."""
        print("\n=== Testing Retry Mechanism ===")
        
        # Create a mock provider that fails twice then succeeds
        mock_provider = MagicMock()
        mock_provider.generate_text.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            "Success on third try!"
        ]
        mock_get_provider.return_value = mock_provider
        
        # Create a service with our mocked provider AFTER setting up the mock
        service = LLMService(model="test-model")
        service.retry_delay = 0.01  # Speed up for testing even more
        
        # Call generate_text and verify retries
        start_time = time.time()
        result = service.generate_text("Test prompt", max_tokens=10)
        elapsed_time = time.time() - start_time
        
        self.assertEqual(result, "Success on third try!")
        self.assertEqual(mock_provider.generate_text.call_count, 3)
        print(f"Retries successful. Attempts: {mock_provider.generate_text.call_count}")
        print(f"Final result: {result}")
        print(f"Elapsed time: {elapsed_time:.2f}s")
    
    @patch('app.services.llm_service.get_llm_provider')  # Patch the import as used in llm_service.py
    def test_structured_output_fallback(self, mock_get_provider):
        """Test fallback when native structured output fails."""
        print("\n=== Testing Structured Output Fallback ===")
        
        # Create a mock provider
        mock_provider = MagicMock()
        
        # Set up the mock to have the required methods and behaviors
        mock_provider.generate_structured_output = MagicMock(side_effect=Exception("Not supported"))
        mock_provider.generate_text = MagicMock(return_value='{"name": "John", "occupation": "Developer"}')
        
        mock_get_provider.return_value = mock_provider
        
        # Create service with mock AFTER setting up the mock
        service = LLMService(model="test-model")
        
        # Test with a simple format
        format = {"name": "example", "occupation": "example"}
        result = service.get_structured_response("Describe a person", format)
        
        # Verify the correct methods were called
        mock_provider.generate_structured_output.assert_called_once()
        mock_provider.generate_text.assert_called_once()
        
        # Check the results
        self.assertEqual(result.get("name"), "John")
        self.assertEqual(result.get("occupation"), "Developer")
        
        print("Fallback to text generation successful:")
        print_json(result)
    
    @patch('app.services.llm_service.get_llm_provider')  # Patch the import as used in llm_service.py
    def test_max_retries_failure(self, mock_get_provider):
        """Test behavior when maximum retries are exceeded.
        
        This test verifies that the service properly handles the case
        when all retry attempts fail and returns an appropriate result.
        """
        print("\n=== Testing Max Retries Failure ===")
        
        # Create a mock provider that always fails
        mock_provider = MagicMock()
        mock_provider.generate_text = MagicMock(side_effect=Exception("API always fails"))
        mock_get_provider.return_value = mock_provider
        
        # Create service with limited retries AFTER setting up the mock
        service = LLMService(model="test-model")
        service.retry_delay = 0.01  # Speed up for testing
        service.max_retries = 2
        
        # Call generate_text and verify it handles failure gracefully
        result = service.generate_text("Test prompt", max_tokens=10)
        
        # Verify the expected behavior
        self.assertEqual(result, "")
        self.assertEqual(mock_provider.generate_text.call_count, 2)  # In practice, max_retries=2 means 2 total attempts
        print(f"Max retries exceeded as expected. Attempts: {mock_provider.generate_text.call_count}")
        print(f"Final result: '{result}'")


def run_tests():
    """Run all the tests."""
    try:
        print("Comprehensive LLM Service Tests")
        print("==============================")
        
        # Run basic tests
        basic_tests = TestLLMServiceBasic()
        basic_tests.test_initialization()
        basic_tests.test_text_generation()
        basic_tests.test_json_extraction()
        basic_tests.test_structured_response()
        basic_tests.test_employee_analysis()
        
        # Run advanced tests
        print("\nRunning advanced tests that require mocking...")
        unittest.main(argv=['first-arg-is-ignored'], exit=False)
        
        print("\n==============================")
        print("All tests completed!")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"Error during test: {e}")


if __name__ == "__main__":
    run_tests()
