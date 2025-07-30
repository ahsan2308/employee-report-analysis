"""
Prompt templates for structured output generation.

This module contains templates for prompting LLMs to generate
structured outputs in specific JSON formats. Import these when
you need consistent prompt templates for structured data generation.
"""
from typing import Dict, Any, List
import json
from datetime import date

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

8. PERFORMANCE ASSESSMENT: Provide a concise evaluation of the employee's overall performance:
   - Rate the overall performance as "high", "medium", or "low"
   - Write a brief summary that holistically evaluates the employee's performance
   - Identify notable strengths demonstrated in the report
   - Identify specific areas where performance could be enhanced
   - Consider the following factors when determining the performance rating:
     * Task completion quality and quantity
     * Impact and significance of reported outcomes
     * Effectiveness in handling challenges
     * Quality of forward planning
     * Level of initiative and proactivity shown
     * Alignment of work with organizational objectives
   
GUIDELINES FOR PERFORMANCE RATING:
   - "high": Strong achievements with significant impact, effective challenge management, and solid planning
   - "medium": Adequate task completion with moderate impact, some challenges handled effectively, reasonable planning
   - "low": Limited achievements, minimal impact, ineffective challenge management, or poor planning
   
IMPORTANT PERFORMANCE ASSESSMENT CONSIDERATIONS:
   - The credibility assessment MUST influence the performance rating - lower credibility should result in a more conservative performance assessment
   - Focus on synthesizing an overall performance evaluation without repeating details from other sections
   - Be balanced - identify both strengths and improvement areas regardless of overall rating
   - Base your assessment on what was actually accomplished rather than just planned or attempted
   - Consider how effectively challenges were managed, not just whether they existed
   - Evaluate performance relative to the role and expectations, not against an absolute standard
   - Keep the assessment concise and evaluative rather than merely descriptive

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
                historical_data = parts[1].strip()  
            else:
                current_data = formatted_vision_data.strip()
                
        # Add both current and historical vision data together if available
        if formatted_vision_data:
            prompt += f"""
OBJECTIVE TRACKING DATA FROM VISION SYSTEM (Activities that can be used for verifying claims in weekly reports as well as for overall analysis):

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
    {"description": "Another detailed achievement", "impact": "6 (Brief reason for this rating)"}
  ],
  "challenges": [
    {"description": "Detailed challenge description", "severity": "low/medium/high"},
    {"description": "Another challenge", "severity": "low/medium/high"}
  ],
  "sentiment": "positive/negative/neutral",
  "topics": ["Topic 1", "Topic 2", "Topic 3"],
  "action_items": ["Specific action recommendation 1", "Specific action recommendation 2"],
  "risk_level": "low/medium/high",
  "risk_explanation": "Detailed explanation of why this risk level was assigned, including specific factors and trends observed across the month",
  "credibility_assessment": {
    "rating": "high/medium/low",
    "explanation": "Assessment of the report's credibility, focusing on potential exaggeration",
    "exaggeration_flags": ["Specific claim 1 that appears exaggerated", "Specific claim 2 that appears exaggerated"],
    "consistency_score": "high/medium/low"
  },
  "performance_assessment": {
    "rating": "high/medium/low",
    "summary": "Brief overall performance assessment summarizing key findings",
    "key_strengths": ["Notable strength identified from the report", "Another strength identified"],
    "improvement_areas": ["Specific area where performance could be enhanced", "Another improvement area"]
  }
}

CRITICAL INSTRUCTIONS:
1. Your entire analysis MUST be consistent with your credibility assessment. The credibility rating should influence how you present achievements, challenges, and recommendations.

2. If credibility is "low" or "medium":
   - Achievement descriptions MUST use qualifying language (e.g., "Employee claims to have...")
   - Impact ratings MUST be adjusted downward proportionally
   - Action items MUST include verification steps
   - Risk level MUST reflect the reporting credibility concerns
   - Performance rating MUST be more conservative

3. Ensure your analysis is:
   - Detailed and specific with concrete examples from the report
   - Objective and fair in assessing achievements and challenges
   - Vigilant about detecting and flagging potential exaggeration in claims
   - Actionable with clear recommendations that address credibility concerns when present
   - Well-structured following the exact format above
   - ALWAYS ensure your response is valid JSON with no extraneous text
   - Do not write anything in the first person or use "I" or "we" in your analysis
   - Make sure to replace hyphens in compound words (write "five day" instead of "five-day") to ensure proper JSON parsing. No hyphens should be used in the output.

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
    
    @staticmethod
    def monthly_analysis_prompt(monthly_data: Dict[str, Any]) -> str:
        """
        Generate a prompt for analyzing an employee's performance over a month.
        
        Args:
            monthly_data: Dictionary containing all data needed for monthly analysis
                
        Returns:
            Prompt for monthly employee performance analysis
        """
        # Extract key data from the monthly_data dictionary
        employee_info = monthly_data.get("employee_info", {})
        reports = monthly_data.get("reports", [])
        analyses = monthly_data.get("analyses", [])
        metrics = monthly_data.get("metrics", {})
        period_start = monthly_data.get("period_start")
        period_end = monthly_data.get("period_end")
        month = monthly_data.get("month")
        year = monthly_data.get("year")
        
        # Determine month name
        month_names = ["January", "February", "March", "April", "May", "June", 
                      "July", "August", "September", "October", "November", "December"]
        month_name = month_names[month-1] if 1 <= month <= 12 else f"Month {month}"
        
        # Format employee information
        employee_name = employee_info.get("name", "Unknown Employee")
        employee_position = employee_info.get("position", "Unknown Position")
        employee_wing = employee_info.get("wing", "Unknown Department")
        
        # Format reports section
        reports_section = ""
        for i, report in enumerate(reports):
            report_date = report.get("date", "Unknown Date")
            report_text = report.get("text", "No content")
            if isinstance(report_date, date):
                report_date = report_date.isoformat()
            reports_section += f"\nREPORT {i+1} ({report_date}):\n{report_text}\n"
        
        # Format analyses section - include all important details
        analyses_section = ""
        for i, analysis in enumerate(analyses):
            analysis_date = analysis.get("date", "Unknown Date")
            if isinstance(analysis_date, date):
                analysis_date = analysis_date.isoformat()
                
            # Extract key details from the analysis
            sentiment = analysis.get("sentiment_score", 0.5)
            risk = analysis.get("risk_level", "medium")
            risk_explanation = analysis.get("risk_explanation", "No explanation provided")
            achievements = analysis.get("achievements", [])
            challenges = analysis.get("challenges", [])
            action_items = analysis.get("action_items", [])
            topics = analysis.get("topics", [])
            
            # Extract credibility assessment
            credibility = analysis.get("credibility_rating", "medium")
            credibility_explanation = analysis.get("credibility_explanation", "No explanation provided")
            consistency_score = analysis.get("consistency_score", "medium")
            
            # Extract performance assessment
            performance = analysis.get("performance_rating", "medium")
            performance_summary = analysis.get("performance_summary", "No summary provided")
            strengths = analysis.get("performance_strengths", [])
            improvement_areas = analysis.get("performance_improvement_areas", [])
            
            # Format achievements and challenges for readability
            achievements_text = ""
            for achievement in achievements or []: 
                desc = achievement.get("description", "No description")
                impact = achievement.get("impact", "No impact")
                achievements_text += f"- {desc} (Impact: {impact})\n"
            
            challenges_text = ""
            for challenge in challenges or []: 
                desc = challenge.get("description", "No description")
                severity = challenge.get("severity", "medium")
                challenges_text += f"- {desc} (Severity: {severity})\n"
            
            # Format action items 
            action_items_text = "\n".join([f"- {item}" for item in action_items or []]) or "None provided"
            
            # Format topics
            topics_text = ", ".join(topics or []) or "None identified"
            
            # Format strengths and improvement areas 
            strengths_text = "\n".join([f"- {strength}" for strength in (strengths or [])]) or "None identified"
            improvement_areas_text = "\n".join([f"- {area}" for area in (improvement_areas or [])]) or "None identified"
            
            # Add formatted analysis to the section
            analyses_section += f"""
ANALYSIS {i+1} ({analysis_date}):
Sentiment Score: {sentiment}
Risk Level: {risk}
Risk Explanation: {risk_explanation}

Key Achievements:
{achievements_text or "None reported"}

Key Challenges:
{challenges_text or "None reported"}

Topics: {topics_text}

Action Items:
{action_items_text}

Credibility Assessment:
- Rating: {credibility}
- Explanation: {credibility_explanation}
- Consistency Score: {consistency_score}

Performance Assessment:
- Rating: {performance}
- Summary: {performance_summary}
- Key Strengths:
{strengths_text}
- Improvement Areas:
{improvement_areas_text}
"""
        
        # Format metrics
        avg_sentiment = metrics.get("avg_sentiment", 0.5)
        sentiment_trend = metrics.get("sentiment_trend", "stable")
        report_count = metrics.get("report_count", 0)
        achievement_count = metrics.get("achievement_count", 0)
        challenge_count = metrics.get("challenge_count", 0)
        recurring_topics = metrics.get("recurring_topics", [])
        risk_levels = metrics.get("risk_levels", {})
        
        # Build the risk levels text with better formatting
        risk_text = ""
        if risk_levels:
            for level, count in risk_levels.items():
                risk_text += f"  • {level}: {count} reports\n"
        else:
            risk_text = "  • No risk data available\n"
        
        # Format recurring topics with better formatting
        if recurring_topics:
            topics_text = "\n".join([f"  • {topic}" for topic in recurring_topics])
        else:
            topics_text = "  • No recurring topics identified"
        
        # Build the full prompt
        prompt = f"""
You are an expert HR analyst conducting a monthly performance review. Your task is to analyze all weekly reports and analyses for an employee over the past month and synthesize the information into a comprehensive monthly assessment.

EMPLOYEE INFORMATION:
- Name: {employee_name}
- Position: {employee_position}
- Department: {employee_wing}
- Analysis Period: {period_start} to {period_end} ({month_name} {year})

MONTHLY SUMMARY METRICS:
- Number of Reports: {report_count}
- Total Achievements: {achievement_count}
- Total Challenges: {challenge_count}
- Average Sentiment: {avg_sentiment}
- Sentiment Trend: {sentiment_trend}

RISK LEVEL DISTRIBUTION:
{risk_text}

RECURRING TOPICS:
{topics_text}

WEEKLY REPORTS:
{reports_section}

WEEKLY ANALYSIS SUMMARIES:
{analyses_section}

Your task is to analyze this information and provide a comprehensive monthly assessment of the employee's performance, focusing on identifying patterns, trends, and key insights that may not be apparent in individual weekly analyses.

Specifically, you should:

1. PROGRESS TRENDS: Identify and analyze trends in the employee's progress across the month.
   - Has performance been improving, declining, or remaining stable?
   - How has the sentiment changed over the course of the month?
   - Are there patterns in risk levels throughout the month?
   - Has the employee shown progress in addressing challenges from earlier weeks?

2. MONTHLY ACHIEVEMENTS: Identify the most significant achievements for the entire month.
   - Which accomplishments had the highest impact?
   - Which achievements represent substantial progress in ongoing projects?
   - Are there achievements that build upon each other across weeks?
   - What is the overall pattern of achievement focus areas?

3. RECURRING CHALLENGES: Analyze challenges that have appeared multiple times.
   - Which challenges have persisted throughout the month?
   - Has the employee made progress in addressing recurring challenges?
   - Are there escalating challenges that require intervention?
   - What patterns exist in the types of challenges faced?


4. CONSISTENCY ASSESSMENT: Evaluate the employee's consistency in performance over the month.
   - How reliable has the employee been in completing planned tasks (task_completion_reliability)?
   - Has work quality remained consistent throughout the month (work_quality_consistency)?
   - How stable has the employee's performance been week-to-week (performance_stability)?
   - Note that this assessment focuses on performance consistency over time, not the consistency of reports seen in weekly analyses. The consitency score from weekly reports represents a different field.

5. GROWTH INDICATORS: Identify signs of professional growth during the month.
   - Has the employee taken on increasingly complex tasks?
   - Is there evidence of skill development or improved capabilities?
   - Has the employee shown increased confidence or independence?
   - Are there changes in how the employee approaches challenges?

6. FOCUS AREAS: Determine the primary areas of work focus during the month.
   - What projects or responsibilities dominated the employee's time?
   - Has the focus shifted during the month, and if so, how?
   - Are there emerging priorities that appear in later weeks?
   - Is the employee's focus aligned with departmental priorities?

7. MONTHLY RISK ASSESSMENT: Provide an overall risk assessment for the month.
   - What are the most significant risks identified across all weeks?
   - Are there escalating risk patterns that require attention?
   - What is the overall risk level for the employee's projects and responsibilities?
   - What specific factors contribute most to the current risk profile?
   - For the risk explnation field, provide a detailed explanation of your risk assessment reasoning, including specific evidence and trends observed across the month that justify the assigned risk level.

8. STRATEGIC RECOMMENDATIONS: Suggest strategic actions based on the monthly analysis.
   - What specific interventions would help address persistent challenges?
   - What support or resources would enhance the employee's strengths?
   - What adjustments to workload or responsibilities might improve performance?
   - What development opportunities would benefit the employee based on the monthly patterns?

9. MONTHLY SUMMARY: Provide a comprehensive overview of the employee's performance for the entire month.
   - Synthesize the key findings from all sections into a cohesive narrative
   - Highlight the most significant achievements and challenges
   - Evaluate overall performance trajectory and risk profile
   - Consider both quantitative metrics and qualitative assessments
   - Keep the summary concise but comprehensive (about 3-5 sentences)

Please provide your analysis in the following structured format:
{{
  "progress_trends": {{
    "performance_trend": "improving/declining/stable",
    "sentiment_trend": "positive/negative/stable",
    "risk_level_pattern": "increasing/decreasing/stable",
    "challenge_resolution_progress": "improved/declined/unchanged"
  }},
  "monthly_achievements": [
    {{"description": "Significant achievement description", "impact": "8 (Reason for high impact)"}},
    {{"description": "Another significant achievement", "impact": "7 (Reason for substantial progress)"}}
  ],
  "recurring_challenges": [
    {{"description": "Persistent challenge description", "severity": "medium/high", "status": "resolved/ongoing"}},
    {{"description": "Another recurring challenge", "severity": "low/medium", "status": "resolved/ongoing"}}
  ],
  "consistency_assessment": {{
    "task_completion_reliability": "high/medium/low",
    "work_quality_consistency": "high/medium/low",
    "performance_stability": "high/medium/low",
    "notable_strengths": ["Consistent strength 1", "Consistent strength 2"],
    "notable_weaknesses": ["Inconsistent area 1", "Inconsistent area 2"]
  }},
  "growth_indicators": {{
    "complexity_of_tasks": "increased/decreased/unchanged",
    "skill_development_evidence": "high/medium/low",
    "confidence_level_change": "increased/decreased/unchanged",
    "approach_to_challenges": "more proactive/more reactive/unchanged"
  }},
  "focus_areas": [
    {{"project": "Primary project or responsibility", "time_investment": "high/medium/low", "priority_level": "high/medium/low"}},
    {{"project": "Secondary project or responsibility", "time_investment": "medium/low", "priority_level": "medium/low"}}
  ],
  "monthly_risk_assessment": {{
    "overall_risk_level": "low/medium/high",
    "risk_explanation": "Detailed explanation of why this risk level was assigned, including specific factors and trends observed across the month",
    "significant_risks": ["Risk factor 1", "Risk factor 2"],
    "escalating_risks": ["Escalating risk 1", "Escalating risk 2"],
    "risk_mitigation_recommendations": ["Recommendation 1", "Recommendation 2"]
  }},
  "strategic_recommendations": [
    {{"action": "Specific action to address challenge or enhance performance", "priority": "high/medium/low"}},
    {{"action": "Another strategic action", "priority": "high/medium/low"}}
  ],
  
  "monthly_summary": "A concise but comprehensive narrative overview of the employee's performance during the month, highlighting key achievements, challenges, performance trajectory, and overall assessment."
}}

CRITICAL INSTRUCTIONS:
1. Your analysis should focus on identifying patterns and trends across the monthly data, rather than re-evaluating individual reports.
2. Pay special attention to:
   - Changes in performance, sentiment, and risk levels over the month
   - Recurring challenges and whether they have been addressed
   - Consistency in task completion and work quality
   - Significant achievements and their impact
   - Areas of professional growth or concern
   - Alignment of focus areas with organizational priorities
   - Overall risk assessment based on cumulative data
3. Ensure your recommendations are strategic and targeted at enhancing performance and addressing challenges.
4. Structure your response exactly as specified, with clear and concise information in each section.
5. Validate that your response is a well-formed JSON object with no extraneous text before submission.
6. Do not write anything in the first person or use "I" or "we" in your analysis
7. Make sure to replace hyphens in compound words (write "five day" instead of "five-day") to ensure proper JSON parsing. No hyphens should be used in the output.
8. Ensure your monthly summary provides a holistic view of the employee's performance that could stand alone as an executive briefing.

"""
        
        return prompt


# Add more specialized prompt templates as needed
