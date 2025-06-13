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
    def employee_analysis_prompt(report_text: str, formatted_vision_data: str = None, 
                           recent_reports: List[Dict[str, Any]] = None, 
                           similar_reports: List[Dict[str, Any]] = None) -> str:
        """
        Generate a prompt for analyzing an employee report.
        
        Args:
            report_text: The report text to analyze
            formatted_vision_data: Optional pre-formatted string of vision system tracking data
            recent_reports: List of recent report dictionaries, each containing text and date
            similar_reports: List of similar historical report dictionaries with text and date
            
        Returns:
            Prompt for employee report analysis
        """
        prompt = f"""
You are an expert HR analyst reviewing employee weekly performance reports. Your task is to analyze the following report and extract key information in a structured format.

IMPORTANT: While assessing credibility is one aspect of your analysis, your primary goal is to provide a balanced and fair assessment of the employee's report. Do not be overly skeptical of reasonable positive statements or measured claims.

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

PRE-ANALYSIS CREDIBILITY ASSESSMENT:
Begin by evaluating the overall credibility of the report by looking for:
- Exaggerated or unrealistic claims about accomplishments or impact
- Vague statements that lack specific, measurable details
- Inflated metrics or outcomes that seem disproportionate to the effort
- Perfect outcomes with minimal or no challenges reported
- Inconsistencies between different sections of the report
- Language patterns suggesting exaggeration (excessive superlatives, absolutes)
- Claims that contradict information in other sections

CREDIBILITY ASSESSMENT GUIDELINES:
- Evaluate with a "presumption of honesty" - most employees report honestly
- Look primarily for extreme cases of exaggeration such as:
  * Claims of unrealistic outcomes (e.g., "increased sales by 500% in one week")
  * Taking sole credit for major team accomplishments
  * Perfect outcomes with zero challenges reported for complex work
- DO NOT flag as exaggeration:
  * Measured positive statements (e.g., "modest improvements", "slight uptick")
  * Normal positive outcomes with appropriate qualifiers
  * Claims that lack extensive metrics but are otherwise reasonable
  * High confidence levels when accompanied by reasonable planned tasks



This initial credibility assessment MUST influence all subsequent sections of your analysis. Lower credibility should result in:
- More cautious wording in achievements
- Lower impact ratings
- More skeptical presentation of claimed outcomes
- Additional action items for verification
- Higher risk assessment

Please provide a comprehensive analysis with the following elements:

1. ACHIEVEMENTS: Identify key accomplishments from the "Tasks completed" and "Impact/outcome" sections. For each achievement:
   - If credibility is high: Present achievements straightforwardly
   - If credibility is medium: Use qualifying language like "The employee reports that..." and adjust impact ratings accordingly
   - If credibility is low: Use clear qualifying language such as "The employee claims to have..." and significantly reduce impact ratings
   - Present achievements straightforwardly unless there is clear evidence of significant exaggeration
   - Provide a detailed description of what was accomplished, especially extraordinary tasks
   - Rate its impact on a scale from 1-10 (where 10 is highest impact)
   - Format the impact field EXACTLY as: "N (reason)" where N is just the integer rating and reason is a brief explanation
   - The description field must contain complete sentences WITHOUT mentioning the impact rating
   - In your impact reason, link the reason with the impact level (individual, team, department, or organization-wide etc) as well if applicable
   - Note if any important decisions resulted from the employee's work
   - For any achievement that appears exaggerated, adjust the impact rating downward proportionally to the degree of suspected exaggeration

2. CHALLENGES: Identify obstacles or issues from the "Challenges/obstacles faced" section. For each challenge:
   - Consider whether the challenges reported seem proportionate to the claimed achievements
   - If few challenges are reported alongside major achievements, note this as a potential credibility concern
   - Provide a detailed description of the challenge, distinguishing between internal and external factors
   - Rate its severity as "low", "medium", or "high"
   - Consider whether the challenge is one-time or recurring from previous reports
   - Note whether the challenge affects only this employee or has broader impact

3. SENTIMENT: Determine if the overall tone is "positive", "negative", or "neutral", paying special attention to:
   - Whether the sentiment seems realistic given the actual content (not just claimed achievements)
   - The confidence level reported (1 being lowest, 5 being highest)
   - Language used when describing challenges (frustrated, concerned, optimistic about resolution)
   - How the employee describes resource requests (urgent needs vs. helpful additions)
   - Balance between achievements reported and challenges faced
   - The employee's outlook on planned tasks

4. TOPICS: Extract the main discussion points, focus areas, or projects mentioned across all sections:
   - Identify specific projects or initiatives mentioned
   - Note recurring themes across current and previous reports
   - Capture key technical or organizational systems referenced
   - Identify stakeholders or departments mentioned as collaborators
   - Cross-reference topics across different sections to check for consistency

5. ACTION ITEMS: Recommend specific follow-up actions based primarily on:
   - The specific resources/support explicitly requested in section 4
   - Any immediate issues that need addressing from the challenges section
   - Preparation or support needed for tasks planned in the next week
   - Any pattern of decreasing confidence levels that requires intervention
   - Opportunities to build on successful achievements
   - Required follow-up on important decisions that resulted from the employee's work
   - Verification actions should be included when there is evidence of significant exaggeration, and should never constitute more than 50% of total recommended actions

6. RISK ASSESSMENT: Determine if there are any concerns requiring management attention:
   - Rate the overall risk as "low", "medium", or "high"
   - IMPORTANT: Low credibility MUST increase the risk level, as exaggeration represents a significant organizational risk
   - Pay special attention to: unfulfilled resource requests, declining confidence levels (below 3), external challenges beyond employee control, and negative patterns across reports
   - Consider risks to: project timelines, work quality, employee wellbeing, team dynamics, and organizational culture (including reporting integrity)
   - Provide detailed reasoning for your risk assessment, citing specific evidence from the report
   - Note any urgent intervention needed versus monitoring situations
   - Explicitly state when exaggerated reporting is contributing to the risk level assessment

7. CREDIBILITY ASSESSMENT: Evaluate the credibility and accuracy of the report:
   - Rate the overall credibility as "high", "medium", or "low"
   - Look specifically for exaggerated claims by identifying:
     * Vague statements without specific, measurable outcomes
     * Inflated impact claims that don't match the scope of the task
     * Overuse of superlatives without supporting evidence
     * Claims that contradict information in other sections
     * Outcomes that seem disproportionate to the effort or time invested
   - Assess the consistency between different sections of the report
   - Cite specific examples of potential exaggeration if found
   - Compare with previous reports (if available) to identify patterns of exaggeration
    In your credibility assessment:
   - "high" credibility applies to most normal reports, even those with positive outcomes and normal levels of detail
   - "medium" credibility should only be used when there are specific examples of claims that seem unrealistic
   - "low" credibility should be reserved for reports with multiple clear examples of significant exaggeration
   - The consistency_score evaluates how well the various sections of the report align with each other
   
GUIDELINES FOR CREDIBILITY RATING:
   - "high": Normal reports with realistic claims, even if positive. Default to this unless evidence suggests otherwise.
   - "medium": Reports with 1-2 specific instances of claims that seem unrealistically positive or vague on important metrics.
   - "low": Reports with multiple clear examples of significant exaggeration or claims that contradict other sections.

EMPLOYEE REPORT:
---
{report_text}
---"""

        # Split vision data into current and historical parts if available
        current_data = ""
        historical_data = ""
        
        if formatted_vision_data:
            parts = formatted_vision_data.split("Historical Activity Data:")
            if len(parts) > 1:
                current_data = parts[0].strip()
                historical_data = parts[1].strip()  # Remove the "Historical Activity Data:" prefix
            else:
                current_data = formatted_vision_data.strip()
                
        # Add both current and historical vision data together if available, with clear headings
        if formatted_vision_data:
            prompt += f"""
OBJECTIVE TRACKING DATA FROM VISION SYSTEM:

=== CURRENT PERIOD ACTIVITY DATA ===
{current_data}

=== HISTORICAL ACTIVITY DATA ===
{historical_data}
"""

        # Add instructions for using vision data immediately after
        prompt += """
USING VISION SYSTEM DATA IN YOUR ANALYSIS:
When analyzing the report, use the vision system data to:
- Cross-validate claims made in the report with the tracked activities
- Identify any discrepancies between what the employee reports and what the vision system tracked
- Assess credibility by comparing self-reported activities with objective tracking data
- Note if major accomplishments mentioned in the report align with the main entities tracked
- Identify shifts in the employee's focus areas over time
- Consider vision data as an objective source when evaluating the credibility of claims
- Compare current period data with historical data to identify trends or changes in work patterns

This objective tracking data should factor into your credibility assessment and overall analysis.
"""

        # Add recent reports with dates if provided
        if recent_reports and len(recent_reports) > 0:
            recent_context = "\n\n".join([
                f"Recent Report from {report['date'].isoformat()}:\n{report['text']}" 
                for report in recent_reports
            ])
            
            prompt += f"""
RECENT REPORTS (FROM THE PAST FEW WEEKS):
---
{recent_context}
---

These recent reports show the employee's work and progress over the past few weeks.
Pay special attention to:
- Tasks promised in previous weeks and whether they were completed in subsequent weeks
- Recent challenges and whether they persist in the current report
- Continuity in the employee's work across reports
- Changes in confidence levels or sentiment over time
- Recurring resource requests that haven't been addressed
"""

        # Add semantically similar reports with dates if provided
        if similar_reports and len(similar_reports) > 0:
            similar_context = "\n\n".join([
                f"Similar Historical Report from {report['date'].isoformat()}:\n{report['text']}" 
                for report in similar_reports
            ])
            
            prompt += f"""
SEMANTICALLY SIMILAR HISTORICAL REPORTS:
---
{similar_context}
---

These historical reports are semantically similar to the current report.
Analyze these reports to identify:
- Patterns in how the employee handles similar tasks or situations
- Common challenges the employee faces in similar contexts
- Typical outcomes when working on similar projects
- Consistent patterns in their reporting style and detail level
- Patterns of exaggeration by comparing claimed achievements against actual delivered outcomes
- Consistency in how the employee describes their impact and contributions over time
- Recurring topics and projects the employee has been working on

Focus your primary analysis on the current report while using these patterns for context and calibration of what's reasonable to expect.
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
  "risk_explanation": "Detailed explanation of why you assigned this risk level",
  "credibility_assessment": {
    "rating": "high/medium/low",
    "explanation": "Assessment of the report's credibility, focusing on potential exaggeration",
    "exaggeration_flags": ["Specific claim 1 that appears exaggerated", "Specific claim 2 that appears exaggerated"],
    "consistency_score": "high/medium/low"
  }
}

CRITICAL INSTRUCTIONS:
1. Your entire analysis MUST be consistent with your credibility assessment. The credibility rating should influence how you present achievements, challenges, and recommendations.

2. If credibility is "low" or "medium":
   - Achievement descriptions MUST use qualifying language (e.g., "Employee claims to have...")
   - Impact ratings MUST be adjusted downward proportionally
   - Action items MUST include verification steps
   - Risk level MUST reflect the reporting credibility concerns

3. Ensure your analysis is:
   - Detailed and specific with concrete examples from the report
   - Objective and fair in assessing achievements and challenges
   - Vigilant about detecting and flagging potential exaggeration in claims
   - Actionable with clear recommendations that address credibility concerns when present
   - Well-structured following the exact format above
   - ALWAYS ensure your response is valid JSON with no extraneous text
   - Do not write anything in the first person or use "I" or "we" in your analysis


Your analysis will help managers understand employee progress, determine where support is needed, and identify potential credibility concerns that require attention.
"""
        
        return prompt
    
    @staticmethod
    def exaggeration_prescreening_prompt(report_text: str) -> str:
        """
        Generate a prompt for pre-screening an employee report for exaggeration/credibility issues.
        This is used as a quality gate before proceeding with full analysis.
        
        Args:
            report_text: The report text to pre-screen
            
        Returns:
            Prompt for exaggeration pre-screening
        """
        prompt = f"""
You are an expert HR analyst specializing in credibility assessment. Your task is to pre-screen this employee report for exaggeration, unrealistic claims, or other credibility issues BEFORE it undergoes full analysis.

Focus exclusively on evaluating the trustworthiness of the information presented.

EMPLOYEE REPORT:
---
{report_text}
---

Analyze this report for the following credibility issues:
1. Exaggerated accomplishments (claims that seem unrealistically positive)
2. Inflated impact metrics (numbers or percentages that appear overstated)
3. Vague claims lacking specific, verifiable details
4. Inconsistencies between different sections of the report
5. "Perfect" outcomes with no challenges or obstacles
6. Unrealistic timelines for complex tasks
7. Language patterns associated with deception (excessive use of superlatives, absolutes)
8. Outcomes that seem disproportionate to the effort or time invested

Provide your analysis in this structured format:
{{
  "credibility_score": N,  // Integer from 1-10 where 10 is completely credible, 1 is highly questionable
  "decision": "ACCEPT" | "FLAG" | "REJECT",  // ACCEPT (7-10), FLAG (4-6), REJECT (1-3)
  "reasoning": "Detailed explanation of your decision with specific examples from the report",
  "red_flags": [
    "Specific example 1 of potential exaggeration or credibility issue",
    "Specific example 2 of potential exaggeration or credibility issue"
  ],
  "improvement_suggestions": [
    "Specific suggestion 1 to improve credibility",
    "Specific suggestion 2 to improve credibility"
  ]
}}

Guidelines:
- ACCEPT: Reports with specific, reasonable claims supported by details
- FLAG: Reports with some questionable elements but not severely problematic
- REJECT: Reports with significant credibility issues that need revision
- Be specific in identifying problematic claims and provide actionable improvement suggestions
- Focus solely on credibility, not on performance evaluation
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
