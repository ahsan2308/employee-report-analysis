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
"""

        # Insert vision data from monthly_data
        formatted_vision_data = monthly_data.get("formatted_vision_data", "")
        if formatted_vision_data:
            prompt += f"""
VISION SYSTEM ACTIVITY DATA (Week-wise objective tracking for monthly analysis):
{formatted_vision_data}

"""

        # Continue with weekly analysis summaries and the rest of the prompt
        prompt += f"""
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
9. INSTRUCTIONS FOR USING VISION SYSTEM DATA:
    - Use the week-wise vision system activity data to cross-validate reported achievements, challenges, and trends.
    - This data provides objective evidence for the employee’s activities and should inform your monthly synthesis, risk assessment, and recommendations.

"""
        
        return prompt


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
        
        # Format recent reports with dates for temporal context
        recent_context = ""
        if recent_reports and len(recent_reports) > 0:
            recent_context = "\n\n".join([
                f"Recent Report from {report['date'].isoformat()}:\n{report['text']}" 
                for report in recent_reports
            ])
        
        # Format similar historical reports with dates
        similar_context = ""
        if similar_reports and len(similar_reports) > 0:
            similar_context = "\n\n".join([
                f"Similar Historical Report from {report['date'].isoformat()}:\n{report['text']}" 
                for report in similar_reports
            ])
                
        # Build the restructured prompt with optimized information flow
        prompt = f"""
# WEEKLY EMPLOYEE PERFORMANCE ANALYSIS

## TASK OVERVIEW AND EXPECTED OUTPUT
You are an expert HR analyst reviewing an employee's weekly performance report. Your task is to analyze the report, extract key information, and provide a structured assessment that helps managers understand employee progress, identify required support, and detect any credibility concerns.
IMPORTANT: While assessing credibility is one aspect of your analysis, your primary goal is to provide a balanced and fair assessment of the employee's report. Do not be overly skeptical of reasonable positive statements or measured claims.

Your analysis must be provided as valid JSON following this exact structure:
{{
  "achievements": [
    {{"description": "Detailed achievement description in complete sentences", "impact": "8 (Brief reason for this impact rating)"}},
    {{"description": "Another detailed achievement", "impact": "6 (Brief reason for this rating)"}}
  ],
  "challenges": [
    {{"description": "Detailed challenge description", "severity": "low/medium/high"}},
    {{"description": "Another challenge", "severity": "low/medium/high"}}
  ],
  "sentiment": "positive/negative/neutral",
  "topics": ["Topic 1", "Topic 2", "Topic 3"],
  "action_items": ["Specific action recommendation 1", "Specific action recommendation 2"],
  "risk_level": "low/medium/high",
  "risk_explanation": "Detailed explanation of why this risk level was assigned",
  "credibility_assessment": {{
    "rating": "high/medium/low",
    "explanation": "Assessment of the report's credibility, focusing on potential exaggeration",
    "exaggeration_flags": ["Specific claim 1 that appears exaggerated", "Specific claim 2 that appears exaggerated"],
    "consistency_score": "high/medium/low"
  }},
  "performance_assessment": {{
    "rating": "high/medium/low",
    "summary": "Brief overall performance assessment summarizing key findings",
    "key_strengths": ["Notable strength identified from the report", "Another strength identified"],
    "improvement_areas": ["Specific area where performance could be enhanced", "Another improvement area"]
  }}
}}

## CRITICAL ANALYSIS INSTRUCTIONS
Your analysis must follow these critical guidelines:

1. CREDIBILITY ASSESSMENT APPROACH:
   - Begin with a presumption of honesty (most employees report honestly)
   - Focus on detecting clear exaggeration rather than being overly skeptical
   - Flag as exaggeration only when claims are unrealistic, vague, or contradictory
   - Don't flag measured positive statements or normal positive outcomes with appropriate qualifiers
   - Use vision system data as objective evidence to validate claims where available
   - Identify inconsistencies between report sections, such as achievements that conflict with reported challenges or resources
   - Evaluate language patterns for potential exaggeration, particularly excessive superlatives ('revolutionary', 'unprecedented') and absolutes ('always', 'never')
   - Scrutinize reports claiming flawless outcomes with minimal challenges, as complex work typically involves some obstacles
   - Assess whether claimed metrics and outcomes appear proportionate to the effort, time, and resources described in the report

2. CREDIBILITY RATING GUIDELINES:
   - "high": Normal reports with realistic claims, even if positive (default rating)
   - "medium": Reports with 1-2 specific instances of unrealistically positive or vague claims
   - "low": Reports with multiple clear examples of significant exaggeration or contradictory claims

3. CREDIBILITY IMPACTS ANALYSIS:
   - If credibility is "medium": Use qualifying language ("The employee reports that...") and adjust impact ratings
   - If credibility is "low": Use clear qualifying language ("The employee claims...") and significantly reduce impact ratings
   - Adjust risk levels upward for lower credibility ratings
   - Include verification steps in action items when credibility concerns exist

4. TECHNICAL REQUIREMENTS:
   - Format impact ratings EXACTLY as: "N (reason)" where N is an integer and reason is brief
   - Use complete sentences in descriptions without mentioning the impact rating
   - Replace hyphens in compound words (write "five day" instead of "five-day") for proper JSON parsing
   - Ensure your analysis contains no first-person references ("I" or "we")
   - Provide ONLY the JSON response with no extraneous text or formatting markers

## REPORT STRUCTURE CONTEXT
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
   - Scale of 1-5 (1=lowest, 5=highest)
   - Indicator of anticipated challenges
   - Reflects perceived ability to complete tasks on time

## EMPLOYEE REPORT TO ANALYZE:
---
{report_text}
---
"""

        # Add vision data immediately after the report to facilitate direct validation
        if formatted_vision_data:
            prompt += f"""
## OBJECTIVE TRACKING DATA
The following vision system data provides evidence to cross-validate claims in the report and to perform the overall analysis as well:

=== CURRENT PERIOD ACTIVITY DATA ===
{current_data}

=== HISTORICAL ACTIVITY DATA ===
{historical_data}

### USING THIS OBJECTIVE DATA IN YOUR ANALYSIS:
- Cross-reference claims in the report against these tracked activities
- Identify any discrepancies between reported and tracked activities
- Note when major accomplishments align with main entities tracked
- Use this objective data as a primary factor in your credibility assessment
- Compare current activities with historical patterns to identify trends
- Explicitly note in your analysis when vision data supports or contradicts claims
- This objective tracking data should factor into the overall analysis.

"""

        # Add recent reports with enhanced temporal context guidance
        if recent_context:
            prompt += f"""
## CHRONOLOGICAL CONTEXT: RECENT REPORTS
---
{recent_context}
---

### TEMPORAL ANALYSIS GUIDANCE:
- Compare what was planned in previous reports with what was completed in this report
- Track whether challenges from recent reports persist or have been resolved
- Identify patterns of consistency or inconsistency in reporting style
- Note any evolving confidence levels or sentiment over time
- Pay attention to recurring resource requests that remain unaddressed
- Use this chronological context to assess follow-through on commitments
"""

        # Add similar reports with enhanced pattern recognition guidance
        if similar_context:
            prompt += f"""
## PATTERN RECOGNITION: SIMILAR HISTORICAL REPORTS
---
{similar_context}
---

### PATTERN ANALYSIS GUIDANCE:
- Identify how the employee typically handles similar tasks or situations
- Compare claimed achievements against actual delivered outcomes in similar contexts
- Note recurring challenges the employee faces in similar work scenarios
- Assess typical outcomes when working on similar projects
- Use these patterns to calibrate your expectations and credibility assessment
- Focus primarily on the current report while using these patterns for context
"""

        # Add comprehensive analysis requirements with clearer structure
        prompt += """
## COMPREHENSIVE ANALYSIS REQUIREMENTS
Analyze the report and provide the following:

1. ACHIEVEMENTS ANALYSIS:
   - Identify specific accomplishments from the "Tasks completed" and "Impact" sections
   - Provide detailed descriptions that capture what was accomplished
   - Rate impact on scale 1-10 (10=highest) based on organizational significance
   - Format: "8 (reason)" where reason links to impact level (individual/team/department/organization)
   - Note any important decisions resulting from the employee's work
   - If vision data is available, indicate which achievements are objectively verified

2. CHALLENGES ASSESSMENT:
   - Extract obstacles from "Challenges/obstacles faced" section
   - Assess whether challenges seem proportionate to claimed achievements
   - Distinguish between internal (organizational) vs. external factors
   - Rate severity as "low", "medium", or "high" based on impact
   - Determine if each challenge is one-time or recurring (based on previous reports)
   - Assess scope of impact (affects only this employee or has broader impact)

3. SENTIMENT DETERMINATION:
   - Evaluate if overall tone is "positive", "negative", or "neutral"
   - Consider confidence level reported (1-5 scale)
   - Analyze language used when describing challenges
   - Assess how resource requests are framed (urgent vs. helpful)
   - Evaluate balance between achievements and challenges
   - Consider outlook on planned tasks

4. TOPIC EXTRACTION:
   - Identify specific projects and initiatives mentioned
   - Capture technical systems and tools referenced
   - Note stakeholders and departments mentioned
   - Cross-reference topics across different sections
   - Compare with topics in previous reports if available

5. ACTION ITEM RECOMMENDATIONS:
   - Address explicit resource requests from section 4
   - Suggest interventions for immediate challenges
   - Recommend support for planned tasks
   - Propose follow-up on important decisions
   - Include verification steps only when credibility issues exist
   - Ensure verification items never exceed 50% of total recommendations

6. RISK ASSESSMENT:
   - Rate overall risk as "low", "medium", or "high"
   - Consider unfulfilled resource requests
   - Evaluate confidence levels below 3 as potential risks
   - Assess external challenges beyond employee control
   - Consider risks to projects, quality, wellbeing, and team dynamics
   - Include organizational culture risks from credibility concerns
   - Provide specific evidence from the report for your assessment

7. CREDIBILITY ASSESSMENT:
   - Evaluate based on specificity, consistency, and realism
   - Look for vague statements, inflated claims, contradictions
   - Compare self-reported activities with vision system data
   - Consider proportion of challenges to achievements
   - Assess consistency between sections
   - Cite specific examples of potential exaggeration if found
   - Rate consistency between report sections as high/medium/low

8. PERFORMANCE ASSESSMENT:
   - Consider task completion quality and quantity
   - Evaluate impact and outcomes
   - Assess challenge management effectiveness
   - Review quality of forward planning
   - Measure initiative and proactivity
   - Rate as "high" (strong achievements, effective management, solid planning),
     "medium" (adequate completion, moderate impact, reasonable planning), or
     "low" (limited achievements, minimal impact, poor planning)
   - Ensure this rating is influenced by your credibility assessment
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
"""

        # Insert vision data from monthly_data
        formatted_vision_data = monthly_data.get("formatted_vision_data", "")
        if formatted_vision_data:
            prompt += f"""
VISION SYSTEM ACTIVITY DATA (Week-wise objective tracking for monthly analysis):
{formatted_vision_data}

"""

        # Continue with weekly analysis summaries and the rest of the prompt
        prompt += f"""
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
9. INSTRUCTIONS FOR USING VISION SYSTEM DATA:
    - Use the week-wise vision system activity data to cross-validate reported achievements, challenges, and trends.
    - This data provides objective evidence for the employee’s activities and should inform your monthly synthesis, risk assessment, and recommendations.

"""
        
        return prompt

#     @staticmethod
#     def periodic_analysis_prompt(periodic_data: Dict[str, Any]) -> str:
#         """
#         Generate a prompt for analyzing an employee's performance over a flexible time period.
#         This is for periods longer than 1 month, as single-month analysis should use monthly_analysis_prompt.
        
#         Args:
#             periodic_data: Dictionary containing all data needed for periodic analysis
#         Returns:
#             Prompt for periodic employee performance analysis
#         """
#         # Extract key data from the periodic_data dictionary
#         employee_info = periodic_data.get("employee_info", {})
#         reports = periodic_data.get("reports", [])
#         analyses = periodic_data.get("analyses", [])
#         monthly_analyses = periodic_data.get("monthly_analyses", [])
#         metrics = periodic_data.get("metrics", {})
#         period_start = periodic_data.get("period_start")
#         period_end = periodic_data.get("period_end")
#         period_length_months = periodic_data.get("period_length_months", 0)
        
#         # Early exit with error message if period is exactly 1 month
#         if period_length_months == 1:
#             return "Error: For 1-month periods, use monthly_analysis_prompt instead of periodic_analysis_prompt."
        
#         # Format employee information
#         employee_name = employee_info.get("name", "Unknown Employee")
#         employee_position = employee_info.get("position", "Unknown Position")
#         employee_department = employee_info.get("department", "Unknown Department")
        
#         # Create a description of the period for the prompt
#         period_description = f"{period_start} to {period_end}"
#         if period_length_months <= 3:
#             period_type = f"{period_length_months} months (short-term)"
#         elif period_length_months <= 12:
#             period_type = f"{period_length_months} months (medium-term)"
#         else:
#             years = period_length_months // 12
#             remaining_months = period_length_months % 12
#             period_type = f"{years} year{'s' if years > 1 else ''}"
#             if remaining_months > 0:
#                 period_type += f" and {remaining_months} month{'s' if remaining_months > 1 else ''}"
#             period_type += " (long-term)"
        
#         # Format monthly analyses section
#         monthly_analyses_section = ""
#         for i, analysis in enumerate(monthly_analyses):
#             month = analysis.get("month", "Unknown")
#             year = analysis.get("year", "Unknown")
#             summary = analysis.get("monthly_summary", "No summary provided")
#             performance_trend = analysis.get("performance_trend", "stable")
#             sentiment_trend = analysis.get("sentiment_trend", "stable")
#             risk_level = analysis.get("risk_level", "medium")
#             achievements = analysis.get("monthly_achievements", [])
#             challenges = analysis.get("recurring_challenges", [])
            
#             # Format achievements and challenges for readability
#             achievements_text = ""
#             for achievement in achievements or []: 
#                 desc = achievement.get("description", "No description")
#                 impact = achievement.get("impact", "No impact")
#                 achievements_text += f"- {desc} (Impact: {impact})\n"
            
#             challenges_text = ""
#             for challenge in challenges or []: 
#                 desc = challenge.get("description", "No description")
#                 severity = challenge.get("severity", "medium")
#                 status = challenge.get("status", "ongoing")
#                 challenges_text += f"- {desc} (Severity: {severity}, Status: {status})\n"
            
#             monthly_analyses_section += f"""
# MONTHLY ANALYSIS {i+1} ({month}/{year}):
# Summary: {summary}
# Performance Trend: {performance_trend}
# Sentiment Trend: {sentiment_trend}
# Risk Level: {risk_level}

# Key Achievements:
# {achievements_text or "None reported"}

# Key Challenges:
# {challenges_text or "None reported"}
# """
        
#         # Format metrics (adapt based on period length)
#         avg_sentiment = metrics.get("avg_sentiment", 0.5)
#         sentiment_trend = metrics.get("sentiment_trend", "stable")
#         report_count = metrics.get("report_count", 0)
#         achievement_count = metrics.get("achievement_count", 0)
#         challenge_count = metrics.get("challenge_count", 0)
#         recurring_topics = metrics.get("recurring_topics", [])
#         risk_levels = metrics.get("risk_levels", {})
        
#         # Build the risk levels text with better formatting
#         risk_text = ""
#         if risk_levels:
#             for level, count in risk_levels.items():
#                 risk_text += f"  • {level}: {count} reports\n"
#         else:
#             risk_text = "  • No risk data available\n"
        
#         # Format recurring topics with better formatting
#         if recurring_topics:
#             topics_text = "\n".join([f"  • {topic}" for topic in recurring_topics])
#         else:
#             topics_text = "  • No recurring topics identified"
        
#         # Build the full prompt
#         prompt = f"""
# You are an expert HR analyst conducting a comprehensive performance review over a flexible time period. Your task is to analyze an employee's performance over {period_type} and synthesize this information into a strategic assessment.

# EMPLOYEE INFORMATION:
# - Name: {employee_name}
# - Position: {employee_position}
# - Department: {employee_department}
# - Analysis Period: {period_description} ({period_type})

# PERIOD SUMMARY METRICS:
# - Number of Reports: {report_count}
# - Total Achievements: {achievement_count}
# - Total Challenges: {challenge_count}
# - Average Sentiment: {avg_sentiment}
# - Overall Sentiment Trend: {sentiment_trend}

# RISK LEVEL DISTRIBUTION:
# {risk_text}

# RECURRING TOPICS:
# {topics_text}
# """

#         # Include different levels of detail based on period length
#         if period_length_months <= 3:
#             # For short periods (1-3 months), include all weekly reports
#             reports_section = ""
#             for i, report in enumerate(reports):
#                 report_date = report.get("date", "Unknown Date")
#                 report_text = report.get("text", "No content")
#                 if isinstance(report_date, date):
#                     report_date = report_date.isoformat()
#                 reports_section += f"\nREPORT {i+1} ({report_date}):\n{report_text}\n"
            
#             prompt += f"""
# WEEKLY REPORTS:
# {reports_section}
# """
        
#         # Include monthly analyses summaries for all period lengths
#         if monthly_analyses and monthly_analyses_section:
#             prompt += f"""
# MONTHLY ANALYSIS SUMMARIES:
# {monthly_analyses_section}
# """

#         # Insert vision data from periodic_data if available
#         formatted_vision_data = periodic_data.get("formatted_vision_data", "")
#         if formatted_vision_data:
#             prompt += f"""
# VISION SYSTEM ACTIVITY DATA (Objective tracking data across the period):
# {formatted_vision_data}

# """

#         # Add specific analysis instructions based on period length
#         prompt += f"""
# Your task is to analyze this information and provide a comprehensive assessment of the employee's performance over this {period_type}, focusing on identifying long-term patterns, development trajectories, and strategic insights.

# """

#         # Add specific analysis sections with appropriate instructions based on period length
#         if period_length_months <= 3:
#             # Short-term period instructions (more detailed)
#             prompt += """
# For this short-term analysis, focus on:
# - Detailed progress in specific projects
# - Immediate impact of achievements
# - Resolution status of recent challenges
# - Short-term skill development indicators
# - Concrete next steps for improvement
# """
#         elif period_length_months <= 12:
#             # Medium-term period instructions
#             prompt += """
# For this medium-term analysis, focus on:
# - Quarterly progress patterns
# - Skill development trajectories
# - Recurring challenges and resolution patterns
# - Consistency in performance across months
# - Medium-term career development opportunities
# """
#         else:
#             # Long-term period instructions
#             prompt += """
# For this long-term analysis, focus on:
# - Career trajectory and development milestones
# - Evaluate readiness for significant role advancements
# - Provide more strategic long-term recommendations
# - Assess organizational impact at a broader level
# - Focus on pattern recognition and development arcs
# - Use aggregated monthly/quarterly data rather than individual reports

# """

#         # Continue with the main analysis sections
#         prompt += """
# Specifically, you should analyze and provide the following:

# 1. LONG-TERM TRAJECTORY ANALYSIS: Analyze the overall career and performance direction.
#    - Evaluate the overall arc of the employee's development during this period
#    - Identify inflection points where performance significantly changed
#    - Assess whether the employee is on an upward, stable, or declining trajectory
#    - Determine if the employee's career progression aligns with organizational needs

# 2. DEVELOPMENT MILESTONES: Identify key moments of growth or significant challenges.
#    - Highlight major achievements that represent meaningful career progression
#    - Note significant challenges that tested or developed the employee's capabilities
#    - Identify periods of accelerated growth or learning
#    - Recognize formal or informal role expansions that occurred

# 3. CONSISTENCY EVALUATION: Assess reliability and stability throughout the period.
#    - Evaluate the predictability of the employee's performance quality
#    - Analyze work output consistency across different projects and timeframes
#    - Assess reliability in meeting commitments and deadlines
#    - Identify any cyclical patterns in performance (seasonal effects, project-dependent variation)

# 4. SKILL ACQUISITION TIMELINE: Document how capabilities evolved throughout the period.
#    - Track the development of technical skills relevant to the role
#    - Assess growth in soft skills and leadership capabilities
#    - Identify skills that have plateaued or require further development
#    - Evaluate the employee's learning agility and adaptation to new requirements

# 5. PERFORMANCE TREND ANALYSIS: Analyze changes in performance indicators over time.
#    - Trace the evolution of performance ratings across the period
#    - Identify trends in the impact and significance of achievements
#    - Assess changes in the employee's ability to handle challenges
#    - Evaluate trends in risk levels and their underlying causes
#    - Analyze sentiment patterns and their correlation with performance

# 6. RECURRING CHALLENGE PATTERNS: Identify persistent obstacles and resolution approaches.
#    - Highlight challenges that have appeared multiple times throughout the period
#    - Assess the employee's evolving approach to addressing recurring challenges
#    - Evaluate the effectiveness of resolution strategies
#    - Identify systemic issues that may require organizational intervention

# 7. STRATEGIC CONTRIBUTION ASSESSMENT: Evaluate alignment with organizational goals.
#    - Assess how the employee's work has contributed to strategic objectives
#    - Evaluate the cumulative impact of achievements on department/organizational success
#    - Identify shifts in the employee's strategic focus areas over time
#    - Determine if the employee's contributions have grown in scope and impact

# 8. ROLE READINESS ASSESSMENT: Evaluate preparation for advancement opportunities.
#    - Assess readiness for promotion or role expansion based on demonstrated capabilities
#    - Identify specific role transitions the employee appears prepared for
#    - Highlight development areas needed before advancement can be recommended
#    - Compare current capabilities against requirements for next-level positions

# 9. STRATEGIC RECOMMENDATIONS: Provide long-term development suggestions.
#    - Recommend specific development opportunities aligned with career trajectory
#    - Suggest role adjustments to better leverage the employee's strengths
#    - Identify formal learning or experiential opportunities to address skill gaps
#    - Propose mentorship or exposure opportunities to accelerate development
#    - Recommend strategic project assignments for the coming period

# 10. COMPREHENSIVE PERIOD SUMMARY: Provide an executive summary of the entire period.
#     - Synthesize key findings across all sections into a cohesive narrative
#     - Highlight the most significant achievements, challenges, and growth areas
#     - Evaluate overall performance trajectory and readiness for advancement
#     - Keep the summary concise but comprehensive (about 4-6 sentences)

# Please provide your analysis in the following structured format:
# {
#   "long_term_trajectory": {
#     "direction": "upward/stable/downward/mixed",
#     "assessment": "Detailed assessment of the employee's career trajectory",
#     "key_inflection_points": [
#       {"time_period": "Month/Year or Quarter", "description": "Description of significant change in trajectory"},
#       {"time_period": "Month/Year or Quarter", "description": "Another significant change point"}
#     ]
#   },
#   "development_milestones": [
#     {"type": "achievement/challenge/role_expansion", "time_period": "Month/Year", "description": "Description of the milestone", "significance": "Impact on employee's development"},
#     {"type": "achievement/challenge/role_expansion", "time_period": "Month/Year", "description": "Another milestone", "significance": "Impact on employee's development"}
#   ],
#   "consistency_evaluation": {
#     "overall_consistency": "high/medium/low",
#     "quality_consistency": "high/medium/low",
#     "reliability_rating": "high/medium/low",
#     "pattern_description": "Description of any patterns or cycles in performance",
#     "stability_factors": ["Factor contributing to stability", "Another stability factor"],
#     "variability_factors": ["Factor contributing to variability", "Another variability factor"]
#   },
#   "skill_acquisition_timeline": [
#     {"skill": "Specific skill name", "development_level": "beginner/intermediate/advanced/expert", "progression": "improved/plateau/declined", "evidence": "Evidence supporting this assessment"},
#     {"skill": "Another skill name", "development_level": "beginner/intermediate/advanced/expert", "progression": "improved/plateau/declined", "evidence": "Evidence supporting this assessment"}
#   ],
#   "performance_trend_analysis": {
#     "overall_trend": "improving/stable/declining/fluctuating",
#     "achievement_impact_trend": "increasing/stable/decreasing",
#     "challenge_handling_trend": "improving/stable/declining",
#     "risk_level_trend": "increasing/decreasing/stable",
#     "sentiment_pattern": "improving/declining/cyclical/stable",
#     "notable_performance_periods": [
#       {"period": "Month/Year or Quarter", "performance_level": "high/medium/low", "key_factors": ["Factor 1", "Factor 2"]}
#     ]
#   },
#   "recurring_challenge_patterns": [
#     {"challenge": "Description of recurring challenge", "frequency": "constant/intermittent/decreasing/increasing", "resolution_trend": "improving/stable/worsening", "impact": "high/medium/low"},
#     {"challenge": "Another recurring challenge", "frequency": "constant/intermittent/decreasing/increasing", "resolution_trend": "improving/stable/worsening", "impact": "high/medium/low"}
#   ],
#   "strategic_contribution_assessment": {
#     "overall_contribution_level": "high/medium/low",
#     "contribution_trend": "increasing/stable/decreasing",
#     "impact_scope": "individual/team/department/organization",
#     "key_strategic_contributions": [
#       {"area": "Strategic area", "impact": "Description of impact", "alignment": "high/medium/low"}
#     ],
#     "strategic_focus_evolution": "Description of how strategic focus has evolved"
#   },
#   "role_readiness_assessment": {
#     "current_role_mastery": "complete/substantial/partial",
#     "advancement_readiness": "ready_now/ready_soon/not_ready",
#     "recommended_next_role": "Specific role recommendation",
#     "readiness_timeline": "immediate/6_months/1_year/2+_years",
#     "critical_development_needs": ["Development need 1", "Development need 2"]
#   },
#   "strategic_recommendations": [
#     {"category": "skill_development/role_adjustment/experience/mentorship/education", "recommendation": "Specific recommendation", "priority": "high/medium/low", "timeline": "immediate/short_term/long_term"},
#     {"category": "skill_development/role_adjustment/experience/mentorship/education", "recommendation": "Another recommendation", "priority": "high/medium/low", "timeline": "immediate/short_term/long_term"}
#   ],
#   "comprehensive_period_summary": "A concise but comprehensive narrative overview of the employee's performance during the entire period, highlighting key achievements, challenges, growth trajectory, and overall assessment."
# }

# INSTRUCTIONS FOR ADAPTING ANALYSIS BASED ON PERIOD LENGTH:
# For shorter periods (1-3 months):
# - Focus more on specific achievements and direct evidence
# - Provide more detailed short-term recommendations
# - Be more conservative in trajectory assessments
# - Use weekly reports as primary data sources
# - Consider this a snapshot rather than a definitive assessment

# For medium periods (4-12 months):
# - Focus on quarterly patterns and medium-term trends
# - Evaluate consistency across different projects and responsibilities
# - Assess skill development progression more definitively
# - Balance between specific examples and pattern recognition
# - Use monthly analyses as primary data sources with selected weekly examples

# For longer periods (>12 months):
# - Emphasize career trajectory and development milestones
# - Evaluate readiness for significant role advancements
# - Provide more strategic long-term recommendations
# - Assess organizational impact at a broader level
# - Focus on pattern recognition and development arcs
# - Use aggregated monthly/quarterly data rather than individual reports

# DATA HIERARCHICAL APPROACH:
# - For short periods: Analyze individual reports and achievements directly
# - For medium periods: Focus on monthly analyses with selective examples
# - For longer periods: Synthesize quarterly or semi-annual patterns
# 8. Do not write anything in the first person or use "I" or "we" in your analysis.
# 9. Make sure to replace hyphens in compound words (write "five day" instead of "five-day") to ensure proper JSON parsing.
# 10. INSTRUCTIONS FOR USING VISION SYSTEM DATA:
#    - Use the vision system activity data to cross-validate reported achievements and trends
#    - This data provides objective evidence for the employee's activities
#    - For longer periods, focus on identifying shifts in activity patterns rather than specific instances
#    - Use vision data to validate consistency between reported and observed work patterns
# """
# """
#   "recurring_challenge_patterns": [
#     {"challenge": "Description of recurring challenge", "frequency": "constant/intermittent/decreasing/increasing", "resolution_trend": "improving/stable/worsening", "impact": "high/medium/low"},
#     {"challenge": "Another recurring challenge", "frequency": "constant/intermittent/decreasing/increasing", "resolution_trend": "improving/stable/worsening", "impact": "high/medium/low"}
#   ],
#   "strategic_contribution_assessment": {
#     "overall_contribution_level": "high/medium/low",
#     "contribution_trend": "increasing/stable/decreasing",
#     "impact_scope": "individual/team/department/organization",
#     "key_strategic_contributions": [
#       {"area": "Strategic area", "impact": "Description of impact", "alignment": "high/medium/low"}
#     ],
#     "strategic_focus_evolution": "Description of how strategic focus has evolved"
#   },
#   "role_readiness_assessment": {
#     "current_role_mastery": "complete/substantial/partial",
#     "advancement_readiness": "ready_now/ready_soon/not_ready",
#     "recommended_next_role": "Specific role recommendation",
#     "readiness_timeline": "immediate/6_months/1_year/2+_years",
#     "critical_development_needs": ["Development need 1", "Development need 2"]
#   },
#   "strategic_recommendations": [
#     {"category": "skill_development/role_adjustment/experience/mentorship/education", "recommendation": "Specific recommendation", "priority": "high/medium/low", "timeline": "immediate/short_term/long_term"},
#     {"category": "skill_development/role_adjustment/experience/mentorship/education", "recommendation": "Another recommendation", "priority": "high/medium/low", "timeline": "immediate/short_term/long_term"}
#   ],
#   "comprehensive_period_summary": "A concise but comprehensive narrative overview of the employee's performance during the entire period, highlighting key achievements, challenges, growth trajectory, and overall assessment."
# }

# INSTRUCTIONS FOR ADAPTING ANALYSIS BASED ON PERIOD LENGTH:
# For shorter periods (1-3 months):
# - Focus more on specific achievements and direct evidence
# - Provide more detailed short-term recommendations
# - Be more conservative in trajectory assessments
# - Use weekly reports as primary data sources
# - Consider this a snapshot rather than a definitive assessment

# For medium periods (4-12 months):
# - Focus on quarterly patterns and medium-term trends
# - Evaluate consistency across different projects and responsibilities
# - Assess skill development progression more definitively
# - Balance between specific examples and pattern recognition
# - Use monthly analyses as primary data sources with selected weekly examples

# For longer periods (>12 months):
# - Emphasize career trajectory and development milestones
# - Evaluate readiness for significant role advancements
# - Provide more strategic long-term recommendations
# - Assess organizational impact at a broader level
# - Focus on pattern recognition and development arcs
# - Use aggregated monthly/quarterly data rather than individual reports

# DATA HIERARCHICAL APPROACH:
# - For short periods: Analyze individual reports and achievements directly
# - For medium periods: Focus on monthly analyses with selective examples
# - For longer periods: Synthesize quarterly or semi-annual patterns
# 8. Do not write anything in the first person or use "I" or "we" in your analysis.
# 9. Make sure to replace hyphens in compound words (write "five day" instead of "five-day") to ensure proper JSON parsing.
# 10. INSTRUCTIONS FOR USING VISION SYSTEM DATA:
#    - Use the vision system activity data to cross-validate reported achievements and trends
#    - This data provides objective evidence for the employee's activities
#    - For longer periods, focus on identifying shifts in activity patterns rather than specific instances
#    - Use vision data to validate consistency between reported and observed work patterns
# """

