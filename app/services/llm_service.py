"""
High-level LLM service for text generation and inference operations.
"""
from typing import Dict, List, Any, Optional, Type
import time
import json
import re

from app.integrations.providers import get_llm_provider
from app.core.logger import logger
from app.models.structured_models_llm import EmployeeAnalysis, MonthlyAnalysis, QuarterlyAnalysis
from app.prompts.structured_prompts import StructuredPrompts

# Prioritize environment variables based on selected provider
from app.core.settings import LLM_PROVIDER, LLM_DEFAULT_MODEL as DEFAULT_MODEL  # noqa: F401  (module attributes kept for compatibility)

class LLMService:
    """Service for interacting with LLM models for text generation and inference."""
    
    def __init__(self, model: str = None):
        """
        Initialize LLM service with specified model.
        
        Args:
            model: Model name to use (overrides config default)
        """
        self.model = model or DEFAULT_MODEL
        logger.debug(f"Initializing LLMService with model: {self.model}")
        self.provider = get_llm_provider(model=self.model)
        self.retry_delay = 1.0
        self.max_retries = 3

    def generate_text(self, prompt: str, max_tokens: int = 2000,
                    temperature: float = 0.7, retries: int = None,
                    num_ctx: int = 8192) -> str:
        """
        Generate text response for the given prompt.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            retries: Number of retries on failure (default from config)
            
        Returns:
            Generated text response

        Raises:
            Exception: the provider's last error, once every attempt has failed
        """
        attempts = 0
        max_attempts = retries or self.max_retries
        current_delay = self.retry_delay  # Create local copy of delay
        
        while attempts < max_attempts:
            try:
                response = self.provider.generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    num_ctx = num_ctx 
                )
                return response
            except Exception as e:
                attempts += 1
                logger.warning(f"LLM generation attempt {attempts} failed: {e}")
                
                if attempts >= max_attempts:
                    logger.error(f"LLM generation failed after {max_attempts} attempts")
                    raise
                
                logger.debug(f"Waiting {current_delay}s before retry")
                time.sleep(current_delay)
                current_delay *= 2  

    def extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract valid JSON from text that may contain additional content.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Parsed JSON as dictionary or empty dict if parsing fails
        """
        # Try to find JSON between triple backticks with optional "json" language identifier
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from matched code block: {json_str[:100]}...")
        
        # Try to find content between curly braces with proper JSON formatting
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from curly braces match: {json_str[:100]}...")
        
        # As a last resort, try parsing the entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error(f"Failed to parse any JSON from response: {text[:100]}...")
            return {}

    def get_structured_response(
        self, 
        prompt: str, 
        response_format: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2, 
        max_tokens: int = 10000,
        pydantic_model: Optional[Type] = None,
        num_ctx: int = 8192
    ) -> Dict[str, Any]:
        """
        Generate structured response in specific JSON format.
        
        Args:
            prompt: The input prompt
            response_format: Optional dictionary describing expected response structure.
                Can be a simple template or a JSON schema with 'type', 'properties', etc.
                Will be ignored if pydantic_model is provided.
            temperature: Sampling temperature (lower for more deterministic outputs)
            max_tokens: Maximum tokens to generate
            pydantic_model: Optional Pydantic model class to use (prioritized over response_format)
            
        Returns:
            Structured response as dictionary
            
        Raises:
            ValueError: If neither response_format nor pydantic_model is provided,
                or the model's answer contains no usable JSON
            Exception: the provider's last error, once text generation has used every retry
        """
        # If Pydantic model is provided, derive schema from it
        if pydantic_model is not None:
            try:
                if hasattr(pydantic_model, 'model_json_schema'):
                    response_format = pydantic_model.model_json_schema()
                else:
                    # Fallback for older Pydantic versions
                    response_format = pydantic_model.schema()
                    
                logger.debug(f"Using schema from Pydantic model: {pydantic_model.__name__}")
            except Exception as e:
                logger.error(f"Failed to derive schema from Pydantic model: {e}")
                if response_format is None:
                    raise ValueError(f"Could not derive schema from provided Pydantic model: {e}")
                logger.warning(f"Falling back to provided response_format due to Pydantic schema error")
        
        # If we still don't have a response format, raise an error
        if response_format is None:
            raise ValueError("Either response_format or pydantic_model must be provided")
            
        # Check if response_format is already a proper JSON schema
        is_schema = isinstance(response_format, dict) and any(key in response_format for key in ["type", "properties"])
        
        # Convert simple format template to JSON schema if necessary
        if not is_schema:
            json_schema = {
                "type": "object",
                "properties": {}
            }
            
            for key, value in response_format.items():
                if isinstance(value, list):
                    json_schema["properties"][key] = {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                elif isinstance(value, str):
                    json_schema["properties"][key] = {"type": "string"}
                elif isinstance(value, (int, float)):
                    json_schema["properties"][key] = {"type": "number"}
                elif isinstance(value, bool):
                    json_schema["properties"][key] = {"type": "boolean"}
                else:
                    json_schema["properties"][key] = {"type": "object"}
                    
            example_format = response_format
        else:
            json_schema = response_format
            
            example_format = {}
            if "properties" in json_schema:
                for prop, details in json_schema["properties"].items():
                    if details.get("type") == "array":
                        example_format[prop] = ["example item"]
                    elif details.get("type") == "number":
                        example_format[prop] = 30
                    elif details.get("type") == "boolean":
                        example_format[prop] = True
                    elif details.get("type") == "object" and "properties" in details:
                        example_format[prop] = {k: "example" for k in details["properties"].keys()}
                    else:
                        example_format[prop] = "example value"
        
        # Use a lower temperature for structured outputs
        structured_temp = min(temperature, 0.2)  # Cap at 0.2 for structured outputs
        
        # Try using native structured output if available
        if hasattr(self.provider, "generate_structured_output"):
            try:
                logger.info(f"Attempting to use native structured output with model {self.model}")
                # Always use pydantic_model directly if it's provided
                schema_arg = pydantic_model if pydantic_model else json_schema
                result = self.provider.generate_structured_output(
                    prompt=prompt,
                    json_schema=schema_arg,
                    temperature=structured_temp,
                    max_tokens=max_tokens,
                    num_ctx=num_ctx
                )
                if result is not None:
                    logger.info(f"Received native structured output: {result}")
                    return result
                logger.info("Native structured output returned None, falling back to text generation")
            except Exception as e:
                logger.warning(f"Native structured output generation failed: {e}. Falling back to text generation.")
        
        # Fall back to the text-based approach
        format_instructions = ""
        if is_schema:
            format_instructions = StructuredPrompts.format_schema_prompt(json_schema, example_format)
        else:
            format_instructions = StructuredPrompts.format_simple_prompt(example_format)
            
        full_prompt = StructuredPrompts.combine_prompt(prompt, format_instructions)
        
        logger.debug("Generating structured response using text approach")
        response = self.generate_text(full_prompt, temperature=temperature, max_tokens=max_tokens, num_ctx=num_ctx) or ""
        logger.debug(f"Raw response from LLM: {response[:200]}...")

        result = self.extract_json_from_text(response)
        logger.debug(f"Extracted JSON: {result}")

        if not result:
            raise ValueError("The LLM returned no usable JSON")
        return result

    def analyze_report(
        self, 
        report_text: str,
        formatted_vision_data: str = None, 
        recent_reports: List[Dict[str, Any]] = None,
        similar_reports: List[str] = None,
        formatted_jd_data: str = None,
        employee_info: Dict[str, Any] = None,
        use_custom_format: bool = False,
        custom_format: Optional[Dict[str, Any]] = None,
        num_ctx: int = 8192
    ) -> Dict[str, Any]:
        """
        Analyze an employee report.
        
        Args:
            report_text: The report text to analyze
            formatted_vision_data: Pre-formatted vision data string
            recent_reports: List of recent reports with date information
            similar_reports: List of semantically similar historical reports
            formatted_jd_data: Formatted job description data
            employee_info: Dictionary containing employee details (name, position, wing)
            use_custom_format: If True, use custom_format instead of the Pydantic model
            custom_format: Optional custom response format to use instead of Pydantic model
            
        Returns:
            Analysis results
        """
        # Generate the task-specific prompt using the prompt template
        prompt = StructuredPrompts.employee_analysis_prompt(
            report_text, 
            formatted_vision_data, 
            recent_reports,
            similar_reports,
            formatted_jd_data,
            employee_info
        )
        logger.info(f"Generated prompt: {len(prompt)} characters")

        try:
            # Decide whether to use the custom format or the Pydantic model
            if use_custom_format:
                if custom_format is None:
                    # Provide a default format that aligns with our enhanced EmployeeAnalysis model
                    custom_format = {
                        "achievements": [
                            {
                                "description": "Detailed description of the achievement",
                                "impact": "The measurable impact or result (1-10 scale)"
                            }
                        ],
                        "challenges": [
                            {
                                "description": "Detailed description of the challenge faced",
                                "severity": "low/medium/high"
                            }
                        ],
                        "sentiment": "positive/negative/neutral",
                        "topics": ["topic1", "topic2"],
                        "action_items": ["Recommended action item 1", "Recommended action item 2"],
                        "risk_level": "low/medium/high",
                        "risk_explanation": "Detailed explanation of risk assessment"
                    }
                
                return self.get_structured_response(
                    prompt=prompt,
                    response_format=custom_format,
                    temperature=0,
                    num_ctx = num_ctx
                )
            else:
                # Default behavior: use the enhanced EmployeeAnalysis Pydantic model
                return self.get_structured_response(
                    prompt=prompt,
                    pydantic_model=EmployeeAnalysis,
                    temperature=0,
                    num_ctx = num_ctx
                )
        except Exception as e:
            logger.error(f"Error analyzing report: {e}")
            return {"error": str(e), "status": "failed"}

    def analyze_monthly_reports(
        self,
        monthly_data: Dict[str, Any],
        use_custom_format: bool = False,
        custom_format: Optional[Dict[str, Any]] = None,
        num_ctx: int = 40000 
    ) -> Dict[str, Any]:
        """
        Analyze an employee's performance over a month based on weekly reports and analyses.
        
        Args:
            monthly_data: Dictionary containing all data needed for monthly analysis, including:
                - employee_info: Basic information about the employee
                - reports: List of raw reports for the month
                - analyses: List of weekly analyses for the month
                - metrics: Pre-calculated metrics for the month
                - period_start: Start date of the analysis period
                - period_end: End date of the analysis period
            use_custom_format: If True, use custom_format instead of the Pydantic model
            custom_format: Optional custom response format to use instead of Pydantic model
            num_ctx: Maximum context length for the model
            
        Returns:
            Analysis results as a dictionary
        """
        # Generate the prompt using the monthly analysis prompt template
        prompt = StructuredPrompts.monthly_analysis_prompt(monthly_data)
        logger.info(f"Generating monthly analysis for employee {monthly_data.get('employee_id')}")
        logger.info(f"Generated prompt: {len(prompt)} characters")
        
        try:
            # Decide whether to use the custom format or the Pydantic model
            if use_custom_format:
                if custom_format is None:
                    # Provide a default format that matches our expected monthly analysis structure
                    custom_format = {
                        "progress_trends": {
                            "performance_trend": "improving/declining/stable",
                            "sentiment_trend": "positive/negative/stable",
                            "risk_level_pattern": "increasing/decreasing/stable",
                            "challenge_resolution_progress": "improved/declined/unchanged"
                        },
                        "monthly_achievements": [
                            {"description": "Achievement description", "impact": "Impact rating and reason"}
                        ],
                        "recurring_challenges": [
                            {"description": "Challenge description", "severity": "low/medium/high", "status": "addressed/ongoing"}
                        ],
                        "consistency_assessment": {
                            "task_completion_reliability": "high/medium/low",
                            "work_quality_consistency": "high/medium/low",
                            "performance_stability": "high/medium/low",
                            "notable_strengths": ["Strength 1", "Strength 2"],
                            "notable_weaknesses": ["Weakness 1", "Weakness 2"]
                        },
                        "growth_indicators": {
                            "complexity_of_tasks": "increased/decreased/unchanged",
                            "skill_development_evidence": "high/medium/low",
                            "confidence_level_change": "increased/decreased/unchanged",
                            "approach_to_challenges": "more proactive/more reactive/unchanged"
                        },
                        "focus_areas": [
                            {"project": "Project name", "time_investment": "high/medium/low", "priority_level": "high/medium/low"}
                        ],
                        "monthly_risk_assessment": {
                            "overall_risk_level": "low/medium/high",
                            "significant_risks": ["Risk 1", "Risk 2"],
                            "escalating_risks": ["Escalating risk 1"],
                            "risk_mitigation_recommendations": ["Recommendation 1", "Recommendation 2"]
                        },
                        "strategic_recommendations": [
                            {"action": "Recommended action", "priority": "high/medium/low"}
                        ],
                        "monthly_summary": "A concise but comprehensive narrative overview of the employee's performance during the month, highlighting key achievements, challenges, performance trajectory, and overall assessment."
                    }
                
                return self.get_structured_response(
                    prompt=prompt,
                    response_format=custom_format,
                    temperature=0,
                    num_ctx=num_ctx
                )
            else:
                # Use the MonthlyAnalysis Pydantic model
                return self.get_structured_response(
                    prompt=prompt,
                    pydantic_model=MonthlyAnalysis,
                    temperature=0,
                    num_ctx=num_ctx
                )
        except Exception as e:
            logger.error(f"Error analyzing monthly reports: {e}")
            return {"error": str(e), "status": "failed"}

    def analyze_quarterly_reports(
        self,
        quarterly_data: Dict[str, Any],
        use_custom_format: bool = False,
        custom_format: Optional[Dict[str, Any]] = None,
        num_ctx: int = 40000 
    ) -> Dict[str, Any]:
        """
        Analyze an employee's performance over a quarter based on monthly analyses and weekly reports.
        
        Args:
            quarterly_data: Dictionary containing all data needed for quarterly analysis, including:
                - employee_info: Basic information about the employee
                - monthly_analyses: List of monthly analyses for the quarter
                - metrics: Pre-calculated metrics for the quarter
                - period_start: Start date of the analysis period
                - period_end: End date of the analysis period
                - quarter: Quarter number (1-4)
                - year: Year of the analysis
            use_custom_format: If True, use custom_format instead of the Pydantic model
            custom_format: Optional custom response format to use instead of Pydantic model
            num_ctx: Maximum context length for the model
            
        Returns:
            Analysis results as a dictionary
        """
        # Generate the prompt using the quarterly analysis prompt template
        prompt = StructuredPrompts.quarterly_analysis_prompt(quarterly_data)
        logger.info(f"Generating quarterly analysis for employee {quarterly_data.get('employee_info', {}).get('name')}")
        
                # Save the generated prompt to a text file for auditing/debugging
        # try:
        #     prompts_dir = os.path.join(os.getcwd(), "generated_prompts")
        #     os.makedirs(prompts_dir, exist_ok=True)

        #     emp = quarterly_data.get('employee_info', {}).get('name') or quarterly_data.get('employee_info', {}).get('employee_id') or "unknown"
        #     quarter = quarterly_data.get('quarter', "Q")
        #     year = quarterly_data.get('year', "")
        #     timestamp = int(time.time())

        #     # sanitize filename components
        #     safe_emp = re.sub(r'[^A-Za-z0-9_.-]', '_', str(emp))
        #     safe_year = re.sub(r'[^A-Za-z0-9_.-]', '_', str(year))
        #     safe_quarter = re.sub(r'[^A-Za-z0-9_.-]', '_', str(quarter))

        #     filename = f"quarterly_prompt_{safe_emp}_Q{safe_quarter}_{safe_year}_{timestamp}.txt"
        #     filepath = os.path.join(prompts_dir, filename)

        #     with open(filepath, "w", encoding="utf-8") as f:
        #         f.write(prompt)

        #     logger.info(f"Saved quarterly prompt to {filepath}")
        # except Exception as e:
        #     logger.warning(f"Could not save quarterly prompt to file: {e}")
        
    
        # Estimate tokens from prompt length (heuristic: ~4 characters per token)
        est_tokens = max(1, (len(prompt) + 3) // 4)
        pct_of_context = (est_tokens / num_ctx) * 100 if num_ctx else 0
        logger.info(f"Estimated prompt tokens: {est_tokens} (~{pct_of_context:.2f}% of {num_ctx} context)")
        
        try:
            # Decide whether to use the custom format or the Pydantic model
            if use_custom_format:
                if custom_format is None:
                    # Provide a default format that matches our expected quarterly analysis structure
                    custom_format = {
                        "strategic_alignment": {
                            "organizational_impact": "individual/team/department/organization",
                            "key_initiatives": [
                                {
                                    "initiative": "Initiative name",
                                    "alignment": "high/medium/low",
                                    "outcomes": "Concrete business outcomes achieved"
                                }
                            ]
                        },
                        "achievement_themes": [
                            {
                                "theme": "Theme name",
                                "related_achievements": ["Achievement 1", "Achievement 2"],
                                "impact": "8 (Reason for high impact)",
                                "business_outcome": "Specific measurable results",
                                "vision_verified": True
                            }
                        ],
                        "performance_trajectory": {
                            "trend": "improving/stable/declining/mixed",
                            "consistency": {
                                "task_completion_reliability": "high/medium/low",
                                "work_quality_consistency": "high/medium/low",
                                "performance_stability": "high/medium/low"
                            },
                            "notable_shifts": [
                                {"month": "Month name", "description": "What changed", "factors": "Why it changed"}
                            ]
                        },
                        "challenge_patterns": {
                            "recurring_challenges": [
                                {
                                    "description": "Challenge description",
                                    "type": "internal/external",
                                    "frequency": "constant/intermittent/decreasing/increasing",
                                    "resolution_status": "resolved/ongoing",
                                    "systemic": True
                                }
                            ],
                            "adaptation_effectiveness": "high/medium/low"
                        },
                        "cross_functional_impact": {
                            "collaboration_effectiveness": "high/medium/low",
                            "stakeholder_impacts": [
                                {"stakeholder": "Team/department", "impact": "Impact description", "evidence": "Concrete example"}
                            ]
                        },
                        "risk_assessment": {
                            "overall_risk_level": "low/medium/high",
                            "risk_trend": "increasing/stable/decreasing",
                            "key_risk_factors": ["Risk factor 1", "Risk factor 2"],
                            "mitigation_strategies": ["Mitigation 1", "Mitigation 2"]
                        },
                        "skill_development": {
                            "key_capabilities": [
                                {"skill": "Skill name", "proficiency": "developing/proficient/advanced", "growth": "improved/stable/declined"}
                            ],
                            "learning_agility": "high/medium/low",
                            "autonomy_level": "high/medium/low",
                            "development_focus": "Next capability to develop"
                        },
                        "behavioral_assessment": {
                            "ownership": {
                                "rating": "below/meets/exceeds",
                                "evidence": "Observable behavior example"
                            },
                            "collaboration": {
                                "rating": "below/meets/exceeds",
                                "evidence": "Observable behavior example"
                            },
                            "communication": {
                                "rating": "below/meets/exceeds",
                                "evidence": "Observable behavior example"
                            },
                            "problem_solving": {
                                "rating": "below/meets/exceeds",
                                "evidence": "Observable behavior example"
                            },
                            "quality_standards": {
                                "rating": "below/meets/exceeds",
                                "evidence": "Observable behavior example"
                            }
                        },
                        "credibility_assessment": {
                            "rating": "high/medium/low",
                            "explanation": "Assessment rationale",
                            "vision_data_alignment": "high/medium/low",
                            "impact_on_evaluation": "Description of how credibility affected overall assessment"
                        },
                        "forward_planning": {
                            "keep_doing": ["Activity to continue"],
                            "improve": ["Area to improve"],
                            "start": ["New initiative to begin"],
                            "stop": ["Activity to discontinue"],
                            "support_needed": ["Resource/support required"]
                        },
                        "quarterly_summary": "Executive summary of quarterly performance"
                    }
                
                return self.get_structured_response(
                    prompt=prompt,
                    response_format=custom_format,
                    temperature=0,
                    num_ctx=num_ctx
                )
            else:
                # Use the QuarterlyAnalysis Pydantic model
                return self.get_structured_response(
                    prompt=prompt,
                    pydantic_model=QuarterlyAnalysis,
                    temperature=0,
                    num_ctx=num_ctx
                )
        except Exception as e:
            logger.error(f"Error analyzing quarterly reports: {e}")
            return {"error": str(e), "status": "failed"}


# Convenience function for quick access
def get_llm_service(model: str = None) -> LLMService:
    """Get an instance of the LLM service with the specified model."""
    return LLMService(model)