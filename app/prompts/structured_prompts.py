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
    
    @staticmethod
    def quarterly_analysis_prompt(quarterly_data: Dict[str, Any]) -> str:
        """
        Generate a prompt for analyzing an employee's performance over a quarter (3 months).
        
        Args:
            quarterly_data: Dictionary containing all data needed for quarterly analysis
                including employee info, monthly analyses, weekly analyses, and vision data
        Returns:
            Prompt for quarterly employee performance analysis
        """
        # Extract key data from the quarterly_data dictionary
        employee_info = quarterly_data.get("employee_info", {})
        monthly_analyses = quarterly_data.get("monthly_analyses", [])
        weekly_analyses = quarterly_data.get("weekly_analyses", [])  
        metrics = quarterly_data.get("metrics", {})
        period_start = quarterly_data.get("period_start")
        period_end = quarterly_data.get("period_end")
        quarter = quarterly_data.get("quarter")
        year = quarterly_data.get("year")
        
        # Format employee information
        employee_name = employee_info.get("name", "Unknown Employee")
        employee_position = employee_info.get("position", "Unknown Position")
        employee_wing = employee_info.get("wing", "Unknown Department")
        
        # Format quarter information
        quarter_name = f"Q{quarter}" if quarter else "Quarter"
        quarter_description = f"{quarter_name} {year}" if year else quarter_name
        
        # Format monthly analyses section
        monthly_analyses_section = ""
        for i, monthly_analysis in enumerate(monthly_analyses):
            month_name = monthly_analysis.get("month_name", f"Month {i+1}")
            month_num = monthly_analysis.get("month", i+1)
            month_start = monthly_analysis.get("period_start", "Unknown Start")
            month_end = monthly_analysis.get("period_end", "Unknown End")
            
            # Extract key metrics from monthly analysis
            performance_trend = monthly_analysis.get("progress_trends", {}).get("performance_trend", "stable")
            sentiment_trend = monthly_analysis.get("progress_trends", {}).get("sentiment_trend", "stable")
            risk_level = monthly_analysis.get("monthly_risk_assessment", {}).get("overall_risk_level", "medium")
            
            # Extract achievements and challenges
            achievements = monthly_analysis.get("monthly_achievements", [])
            challenges = monthly_analysis.get("recurring_challenges", [])
            
            # Extract consistency assessment
            consistency = monthly_analysis.get("consistency_assessment", {})
            task_reliability = consistency.get("task_completion_reliability", "medium")
            work_quality = consistency.get("work_quality_consistency", "medium")
            performance_stability = consistency.get("performance_stability", "medium")
            
            # Extract growth indicators
            growth = monthly_analysis.get("growth_indicators", {})
            
            # Extract focus areas
            focus_areas = monthly_analysis.get("focus_areas", [])
            
            # Extract recommendations
            recommendations = monthly_analysis.get("strategic_recommendations", [])
            
            # Extract summary
            summary = monthly_analysis.get("monthly_summary", "No summary provided")
            
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
                status = challenge.get("status", "ongoing")
                challenges_text += f"- {desc} (Severity: {severity}, Status: {status})\n"
            
            # Format focus areas
            focus_text = ""
            for focus in focus_areas or []:
                project = focus.get("project", "Unknown project")
                time_inv = focus.get("time_investment", "medium")
                priority = focus.get("priority_level", "medium")
                focus_text += f"- {project} (Time: {time_inv}, Priority: {priority})\n"
            
            # Format recommendations
            recommendations_text = ""
            for rec in recommendations or []:
                action = rec.get("action", "No action")
                priority = rec.get("priority", "medium")
                recommendations_text += f"- {action} (Priority: {priority})\n"
            
            # Add formatted monthly analysis to the section
            monthly_analyses_section += f"""
MONTHLY ANALYSIS: {month_name} ({month_start} to {month_end})
Summary: {summary}

Performance: {performance_trend}
Sentiment: {sentiment_trend}
Risk Level: {risk_level}

Key Achievements:
{achievements_text or "None reported"}

Key Challenges:
{challenges_text or "None reported"}

Consistency Assessment:
- Task Completion: {task_reliability}
- Work Quality: {work_quality}
- Performance Stability: {performance_stability}

Growth Indicators:
- Task Complexity: {growth.get("complexity_of_tasks", "unchanged")}
- Skill Development: {growth.get("skill_development_evidence", "medium")}
- Confidence Level: {growth.get("confidence_level_change", "unchanged")}
- Challenge Approach: {growth.get("approach_to_challenges", "unchanged")}

Focus Areas:
{focus_text or "None specified"}

Strategic Recommendations:
{recommendations_text or "None provided"}
"""

            # Find weekly analyses for this month
            month_weekly_analyses = []
            for weekly_analysis in weekly_analyses:
                week_date = weekly_analysis.get("date")
                if week_date and hasattr(week_date, "month") and week_date.month == month_num:
                    month_weekly_analyses.append(weekly_analysis)

            # Format and add weekly analyses for this month if available
            if month_weekly_analyses:
                weekly_analyses_section = f"\nWEEKLY ANALYSES FOR {month_name.upper()}:\n"
                
                for w, weekly_analysis in enumerate(month_weekly_analyses):
                    # Extract weekly data
                    week_start = weekly_analysis.get("period_start", "Unknown")
                    week_end = weekly_analysis.get("date", "Unknown")
                    
                    # Calculate start date (7 days before end date)
                    week_start = "Unknown"
                    if isinstance(week_end, date):
                        from datetime import timedelta
                        week_start = (week_end - timedelta(days=7)).isoformat()
                    elif hasattr(week_end, 'isoformat'):
                        from datetime import timedelta
                        try:
                            week_start = (week_end - timedelta(days=7)).isoformat()
                        except:
                            week_start = "Unknown"
                    
                    week_sentiment = weekly_analysis.get("sentiment", "neutral")
                    week_risk = weekly_analysis.get("risk_level", "medium")
                    week_risk_explanation = weekly_analysis.get("risk_explanation", "No explanation provided")
                    
                    # Extract achievements and challenges
                    week_achievements = weekly_analysis.get("achievements", [])
                    week_challenges = weekly_analysis.get("challenges", [])
                    week_topics = weekly_analysis.get("topics", [])
                    week_action_items = weekly_analysis.get("action_items", [])
                    
                    # Extract credibility assessment
                    credibility = weekly_analysis.get("credibility_assessment", {})
                    credibility_rating = credibility.get("rating", "medium")
                    credibility_explanation = credibility.get("explanation", "No explanation provided")
                    consistency_score = credibility.get("consistency_score", "medium")
                    exaggeration_flags = credibility.get("exaggeration_flags", [])
                    
                    # Extract performance assessment
                    performance = weekly_analysis.get("performance_assessment", {})
                    performance_rating = performance.get("rating", "medium")
                    performance_summary = performance.get("summary", "No summary provided")
                    strengths = performance.get("key_strengths", [])
                    improvement_areas = performance.get("improvement_areas", [])
                    
                    # Format achievements and challenges
                    week_achievements_text = ""
                    for achievement in week_achievements or []: 
                        desc = achievement.get("description", "No description")
                        impact = achievement.get("impact", "No impact")
                        week_achievements_text += f"- {desc} (Impact: {impact})\n"
                    
                    week_challenges_text = ""
                    for challenge in week_challenges or []: 
                        desc = challenge.get("description", "No description")
                        severity = challenge.get("severity", "medium")
                        week_challenges_text += f"- {desc} (Severity: {severity})\n"
                    
                    # Format other elements
                    week_topics_text = ", ".join(week_topics or []) or "None identified"
                    week_action_items_text = "\n".join([f"- {item}" for item in week_action_items or []]) or "None provided"
                    exaggeration_flags_text = "\n".join([f"- {flag}" for flag in exaggeration_flags or []]) or "None identified"
                    strengths_text = "\n".join([f"- {strength}" for strength in strengths or []]) or "None identified"
                    improvement_areas_text = "\n".join([f"- {area}" for area in improvement_areas or []]) or "None identified"
                    
                    # Add formatted weekly analysis
                    weekly_analyses_section += f"""
WEEK {w+1} ({week_start} to {week_end}):
Sentiment: {week_sentiment}
Risk Level: {week_risk}
Risk Explanation: {week_risk_explanation}

Weekly Achievements:
{week_achievements_text or "None reported"}

Weekly Challenges:
{week_challenges_text or "None reported"}

Topics: {week_topics_text}

Action Items:
{week_action_items_text}

Credibility Assessment:
- Rating: {credibility_rating}
- Explanation: {credibility_explanation}
- Consistency Score: {consistency_score}
- Exaggeration Flags:
{exaggeration_flags_text}

Performance Assessment:
- Rating: {performance_rating}
- Summary: {performance_summary}
- Key Strengths:
{strengths_text}
- Improvement Areas:
{improvement_areas_text}
"""
                
                # Add all weekly analyses for this month to the monthly section
                monthly_analyses_section += weekly_analyses_section
    
        # Format quarterly metrics
        avg_sentiment = metrics.get("avg_sentiment", 0.5)
        sentiment_trend = metrics.get("sentiment_trend", "stable")
        achievement_count = metrics.get("achievement_count", 0)
        challenge_count = metrics.get("challenge_count", 0)
        recurring_topics = metrics.get("recurring_topics", [])
        risk_levels = metrics.get("risk_levels", {})
        
        # Additional aggregated metrics from quarterly data
        weekly_report_count = metrics.get("weekly_report_count", 0)
        performance_stability = metrics.get("performance_stability", "medium")
        task_reliability_trend = metrics.get("task_reliability_trend", "stable")
        quality_consistency_trend = metrics.get("quality_consistency_trend", "stable")
        risk_trend = metrics.get("risk_trend", "stable")
        challenge_resolution_trend = metrics.get("challenge_resolution_trend", "stable")
        achievement_impact_avg = metrics.get("achievement_impact_avg", 0.0)
        
        # Get credibility data
        weekly_credibility_data = metrics.get("weekly_credibility_data", {})
        avg_credibility_rating = weekly_credibility_data.get("avg_credibility_rating", "medium")
        credibility_trend = weekly_credibility_data.get("credibility_trend", "stable")
        exaggeration_frequency = weekly_credibility_data.get("exaggeration_frequency", 0)
        
        # Get detailed topics
        detailed_topics = metrics.get("detailed_topics", [])
        detailed_topics_text = ""
        if detailed_topics:
            for topic_data in detailed_topics:
                topic = topic_data.get("topic", "Unknown")
                frequency = topic_data.get("frequency", 0)
                detailed_topics_text += f"  • {topic} (Frequency: {frequency})\n"
        else:
            detailed_topics_text = "  • No detailed topic data available\n"
        
        # Get performance rating data
        performance_rating_data = metrics.get("performance_rating_aggregation", {})
        most_common_rating = performance_rating_data.get("most_common_rating", "medium")
        rating_trend = performance_rating_data.get("rating_trend", "stable")
        rating_distribution = performance_rating_data.get("rating_distribution", {})
        rating_distribution_text = ""
        if rating_distribution:
            for rating, percentage in rating_distribution.items():
                rating_distribution_text += f"  • {rating}: {percentage:.1%}\n"
        else:
            rating_distribution_text = "  • No rating distribution data available\n"
        
        # Get monthly progress trends
        monthly_progress_trends = metrics.get("monthly_progress_trends", [])
        progress_trends_text = ""
        if monthly_progress_trends:
            for trend_data in monthly_progress_trends:
                month_num = trend_data.get("month", 0)
                month_names = ["January", "February", "March", "April", "May", "June", 
                              "July", "August", "September", "October", "November", "December"]
                month_name = month_names[month_num-1] if 1 <= month_num <= 12 else f"Month {month_num}"
                
                perf_trend = trend_data.get("performance_trend", "stable")
                sent_trend = trend_data.get("sentiment_trend", "stable")
                risk_pattern = trend_data.get("risk_level_pattern", "stable")
                challenge_prog = trend_data.get("challenge_resolution_progress", "unchanged")
                
                progress_trends_text += f"""
      • {month_name}:
        - Performance: {perf_trend}
        - Sentiment: {sent_trend}
        - Risk Pattern: {risk_pattern}
        - Challenge Resolution: {challenge_prog}
    """
        else:
            progress_trends_text = "  • No monthly progress trend data available\n"
        
        # Get monthly summaries
        monthly_summaries = metrics.get("monthly_summaries", [])
        monthly_summaries_text = ""
        if monthly_summaries:
            for summary_data in monthly_summaries:
                month = summary_data.get("month", "Unknown month")
                summary = summary_data.get("summary", "No summary available")
                monthly_summaries_text += f"  • {month}: {summary}\n"
        else:
            monthly_summaries_text = "  • No monthly summary data available\n"
        
        # Build the risk levels text with better formatting
        risk_text = ""
        if risk_levels:
            for level, count in risk_levels.items():
                risk_text += f"  • {level}: {count} reports/analyses\n"
        else:
            risk_text = "  • No risk data available\n"
        
        # Format recurring topics with better formatting
        if recurring_topics:
            topics_text = "\n".join([f"  • {topic}" for topic in recurring_topics])
        else:
            topics_text = "  • No recurring topics identified"
        
        # Build the full prompt
        prompt = f"""
    # QUARTERLY EMPLOYEE PERFORMANCE ANALYSIS

    ## TASK OVERVIEW AND EXPECTED OUTPUT
    You are an expert HR analyst conducting a quarterly performance review. Your task is to analyze an employee's performance across three months and synthesize a comprehensive quarterly assessment that identifies patterns, trends, and business impact not visible in shorter timeframes.

    Your analysis must be strategic, evidence-based, and focused on both evaluation and development. You should identify broader patterns and trends rather than focusing on individual events, evaluate business impact as a primary lens, and provide a forward-looking orientation for the next quarter.

    Your quarterly analysis must be provided as valid JSON following the exact structure specified later in this prompt.

    ## EMPLOYEE INFORMATION
    - Name: {employee_name}
    - Position: {employee_position}
    - Department: {employee_wing}
    - Analysis Period: {period_start} to {period_end} ({quarter_description})

    ## QUARTERLY SUMMARY METRICS
    - Total Achievements: {achievement_count}
    - Total Challenges: {challenge_count}
    - Average Sentiment: {avg_sentiment}
    - Sentiment Trend: {sentiment_trend}
    - Performance Stability: {performance_stability}
    - Weekly Reports Analyzed: {weekly_report_count}
    - Task Reliability Trend: {task_reliability_trend}
    - Quality Consistency Trend: {quality_consistency_trend}
    - Risk Trend: {risk_trend}
    - Challenge Resolution Trend: {challenge_resolution_trend}
    - Achievement Impact Average: {achievement_impact_avg}

    RISK LEVEL DISTRIBUTION:
    {risk_text}

    RECURRING TOPICS:
    {topics_text}

    DETAILED TOPIC FREQUENCY:
    {detailed_topics_text}

    PERFORMANCE RATING DISTRIBUTION:
    - Most Common Rating: {most_common_rating}
    - Rating Trend: {rating_trend}
    - Distribution:
    {rating_distribution_text}

    CREDIBILITY ASSESSMENT:
    - Average Credibility Rating: {avg_credibility_rating}
    - Credibility Trend: {credibility_trend}
    - Exaggeration Frequency: {exaggeration_frequency}

    MONTHLY PROGRESS TRENDS:
    {progress_trends_text}

    MONTHLY SUMMARIES:
    {monthly_summaries_text}

    ## MONTHLY AND WEEKLY ANALYSES SUMMARIES
    {monthly_analyses_section}
    """

        # Insert vision data from quarterly_data if available
        formatted_vision_data = quarterly_data.get("formatted_vision_data", "")
        if formatted_vision_data:
            prompt += f"""
## VISION SYSTEM ACTIVITY DATA
The following vision system data provides objective evidence to validate claims and identify patterns across the quarter:

{formatted_vision_data}

### USING THIS OBJECTIVE DATA IN YOUR ANALYSIS:
- Use this data as primary evidence to validate achievement claims and impact
- Identify patterns in activity types, focus areas, and intensity over the quarter
- Note any discrepancies between reported work and objectively tracked activities
- Consider shifts in work patterns as indicators of changing priorities or responsibilities
- Cross-reference against claimed achievements for credibility assessment
- Compare objective data across months to identify trends and trajectory
"""

        # Continue with comprehensive analysis requirements
        prompt += """
## COMPREHENSIVE ANALYSIS REQUIREMENTS
Analyze the quarterly data and provide the following comprehensive assessment:

1. STRATEGIC ALIGNMENT ASSESSMENT:
   - Identify how the employee's work connects to department/organizational goals
   - Evaluate the scope of impact (individual/team/department/organization)
   - Assess alignment between reported work and strategic priorities
   - Identify key initiatives and their business outcomes
   - Consider vision data as validation of strategic contributions
   - Provide 2-3 concrete examples of strategic alignment
   - Format as assessment of overall alignment with specific initiatives

2. ACHIEVEMENT THEME IDENTIFICATION:
   - Cluster related achievements from across the quarter into 3-7 themes
   - Name each theme based on business function or outcome area
   - Link 2-4 specific achievements under each theme
   - Rate impact on 1-10 scale with specific business justification
   - Indicate which achievements are verified by vision data
   - Identify compounding or sequential achievements that build on each other
   - Format as themed clusters with constituent achievements and cumulative impact

3. PERFORMANCE TRAJECTORY ANALYSIS:
   - Analyze direction of performance (improving/stable/declining/mixed)
   - Evaluate consistency across task completion, quality, and stability
   - Identify any significant shifts during the quarter
   - Determine factors driving performance changes
   - Consider vision data as objective performance indicator
   - Analyze relationship between workload and performance
   - Identify any notable shifts with month, description, and contributing factors
   - Incorporate week-to-week patterns to identify micro-trends within monthly data
   - Detect early warning signals in weekly data that developed into monthly challenges
   - Analyze weekly volatility within seemingly stable months

4. CHALLENGE PATTERN ANALYSIS:
   - Identify challenges that appeared multiple times across the quarter
   - Categorize as internal (organizational) or external
   - Assess frequency pattern (constant/intermittent/increasing/decreasing)
   - Evaluate resolution status and effectiveness
   - Determine if challenges are systemic or individual
   - Consider vision data for challenge validation
   - Format as list of recurring challenges with pattern analysis
   - Incorporate weekly challenge data to track the evolution of issues over time
   - Identify challenges that appeared frequently in weekly reports but were resolved before monthly aggregation

5. CROSS-FUNCTIONAL IMPACT ASSESSMENT:
   - Identify collaborations with other teams/departments
   - Assess effectiveness of cross-functional work
   - Evaluate impact on stakeholders outside immediate team
   - Identify knowledge sharing and capability building
   - Consider vision data for collaboration evidence
   - Format as collaboration effectiveness rating with stakeholder impact examples
   - Use weekly collaboration patterns to identify relationship-building trends

6. SKILL DEVELOPMENT EVALUATION:
   - Identify key capabilities demonstrated or developed during the quarter
   - Assess proficiency level for each key skill
   - Evaluate growth trajectory for each capability
   - Determine learning agility and adaptability
   - Assess autonomy level in role execution
   - Recommend next development focus area
   - Format as capability assessment with growth indicators
   - Use weekly performance data to identify gradual skill improvements not apparent at monthly level

7. BEHAVIORAL ASSESSMENT:
   - Evaluate five key behaviors with specific evidence:
     a) Ownership and accountability
     b) Collaboration and teamwork
     c) Communication effectiveness
     d) Problem-solving approach
     e) Quality standards and craft
   - For each behavior, provide specific observed examples
   - Rate as below/meets/exceeds expectations
   - Consider consistency of behaviors across quarter
   - Format as behavior-by-behavior assessment with evidence
   - Incorporate weekly credibility assessments to evaluate behavioral patterns over time

8. RISK ASSESSMENT:
   - Determine overall risk level for next quarter
   - Analyze risk trend (increasing/stable/decreasing)
   - Identify specific risk factors with potential impact
   - Recommend mitigation strategies for each risk
   - Consider credibility assessment in risk evaluation
   - Format as risk profile with specific factors and mitigations
   - Use weekly risk assessments to create a detailed risk trajectory
   - Identify risk volatility patterns and potential leading indicators

9. CREDIBILITY ASSESSMENT:
   - Apply consistent credibility framework from weekly/monthly analyses
   - Evaluate alignment between self-reported and vision-tracked activities
   - Assess consistency of reporting across quarter
   - Identify any exaggeration patterns
   - Determine impact on overall evaluation
   - Format as credibility rating with explanation and impact statement
   - Synthesize weekly credibility assessments to identify reporting pattern trends
   - Track exaggeration flags over time to detect improvement or deterioration in reporting accuracy

10. FORWARD PLANNING:
    - Recommend activities to continue (demonstrating value)
    - Suggest areas for improvement (addressing weaknesses)
    - Propose new initiatives to start (growth opportunities)
    - Identify activities to stop (low value or ineffective)
    - Specify support needed (resources, training, etc.)
    - Format as actionable KSBS framework
    - Incorporate trends from weekly action items to ensure continuous follow-through

11. QUARTERLY SUMMARY:
    - Provide a comprehensive executive summary (4-6 sentences)
    - Highlight most significant achievements and impact
    - Note important trends or pattern changes
    - Identify critical risk factors or support needs
    - Include forward-looking perspective
    - Balance positives and development areas
    - Focus on business impact and value creation

## HIERARCHICAL DATA ANALYSIS APPROACH
For this quarterly analysis, integrate data across three time levels:

1. WEEKLY LEVEL (Most Granular):
   - Use weekly analyses to identify micro-trends and early signals
   - Track the evolution of specific challenges, achievements, and performance ratings
   - Identify volatility patterns that may be smoothed out in monthly aggregations
   - Consider week-to-week consistency as a performance indicator
   - Use weekly credibility assessments to evaluate reporting patterns

2. MONTHLY LEVEL (Middle Layer):
   - Use monthly analyses to identify medium-term patterns and trends
   - Compare monthly summaries to detect trajectory changes
   - Evaluate consistency between months as a stability indicator
   - Identify recurring themes across multiple months
   - Use monthly growth indicators to track development progress

3. QUARTERLY LEVEL (Strategic Overview):
   - Synthesize insights from both weekly and monthly data
   - Focus on business impact and strategic alignment
   - Identify long-term patterns and significant trends
   - Evaluate overall trajectory and development path
   - Provide forward-looking recommendations based on comprehensive data
   - Assess readiness for advancement or role expansion

When integrating across levels, prioritize:
- Identifying patterns that persist across multiple time frames
- Detecting contradictions or anomalies between time levels
- Using granular weekly data to validate or challenge monthly conclusions
- Tracking the progression of specific issues/achievements over time
- Evaluating consistency as a performance metric in itself

## EVIDENCE STANDARDS AND ANALYSIS FRAMEWORK

### Evidence Requirements
- Each achievement theme needs 2-3 specific examples
- Behavioral assessments require concrete examples
- Performance trajectory claims need month-by-month evidence
- Risk assessments need specific supporting factors
- Any claim of "high" impact requires business outcome evidence

### Pattern Recognition Guidance
- Look for temporal patterns (changes over three months)
- Identify thematic patterns (recurring topics or areas of focus)
- Observe behavioral patterns (consistent approaches or styles)
- Analyze challenge patterns (recurring obstacles or barriers)
- Examine performance patterns (consistency or variability)

### Balance and Proportionality
- Balance achievement recognition with development opportunities
- Balance forward-looking vs. retrospective analysis
- Consider both individual and systemic factors
- Balance tactical and strategic focus
- Evaluate both process and outcome

### Bias Mitigation
- Avoid recency bias (overweighting last month)
- Avoid halo/horn effect (letting one area influence others)
- Consider both personal and situational factors
- Evaluate evidence objectively rather than confirming initial impressions
- Judge processes independently from outcomes

### Credibility Governance
- If credibility is "medium": Apply 15% discount to achievement impact ratings
- If credibility is "low": Apply 40% discount to achievement impact ratings and increase risk level
- Add verification steps to forward planning when credibility concerns exist
- Require stronger evidence for claims when credibility rating is lower

## OUTPUT STRUCTURE AND FORMAT
Your analysis must be provided as valid JSON following this exact structure:

{
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
      "vision_verified": true/false
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
        "systemic": true/false
      }
    ],
    "adaptation_effectiveness": "high/medium/low"
  },
  "cross_functional_impact": {
    "collaboration_effectiveness": "high/medium/low",
    "stakeholder_impacts": [
      {"stakeholder": "Team/department", "impact": "Impact description", "evidence": "Concrete example"}
    ],
    "knowledge_sharing": ["Specific knowledge sharing example"]
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

## EXAMPLE OUTPUT SECTIONS
Below are abbreviated examples for key sections. Your full analysis should be more comprehensive:

STRATEGIC ALIGNMENT EXAMPLE:
{
  "organizational_impact": "department",
  "key_initiatives": [
    {
      "initiative": "Customer Experience Transformation",
      "alignment": "high",
      "outcomes": "Reduced customer complaint rate by 15% through implementation of new response protocols"
    }
  ]
}

ACHIEVEMENT THEME EXAMPLE:
{
  "theme": "Data Quality Improvement",
  "related_achievements": [
    "Implemented automated validation system for customer records",
    "Trained team on new data quality standards",
    "Reduced error rate in monthly reporting by 40%"
  ],
  "impact": "8 (Significantly improved decision-making reliability for leadership team)",
  "business_outcome": "40% reduction in reporting errors leading to $50K in avoided rework costs",
  "vision_verified": true
}

PERFORMANCE TRAJECTORY EXAMPLE:
{
  "trend": "improving",
  "consistency": {
    "task_completion_reliability": "high",
    "work_quality_consistency": "medium",
    "performance_stability": "high"
  },
  "notable_shifts": [
    {
      "month": "February",
      "description": "Significant improvement in work quality",
      "factors": "Completed advanced training program and implemented new quality assurance steps"
    }
  ]
}

## TECHNICAL REQUIREMENTS
- Format your response as valid JSON with no markdown code fences or explanatory text
- Replace hyphens in compound words (write "five day" instead of "five-day") for proper JSON parsing
- Ensure your analysis contains no first-person references ("I" or "we")
- Use complete sentences in descriptions
- Verify all required fields are completed before submission
- Ensure your quarterly summary provides a holistic view that could stand alone as an executive briefing
- Apply credibility governance appropriately to achievement impact ratings and risk assessments

## CONTEXT PRIORITIZATION
If context limitations require prioritizing information:
- Monthly analyses take precedence over individual weekly reports
- Pattern indicators are more important than individual instances
- Vision-verified achievements have higher priority than self-reported only
- Significant changes or anomalies are more important than expected performance
- Forward-looking insights are more valuable than historical details
- When analyzing weekly data, focus on trends and patterns rather than isolated incidents
- Prioritize weekly data that shows progression or evolution of important issues

"""

        return prompt


