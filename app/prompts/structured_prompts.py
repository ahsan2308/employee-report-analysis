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
            
            # Add formatted analysis to the section with week number for better temporal context
            week_number = i + 1
            analyses_section += f"""
ANALYSIS FOR WEEK {week_number} ({analysis_date}):
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
        
        # Build the full prompt - restructured with task description and instructions first
        prompt = f"""
# MONTHLY EMPLOYEE PERFORMANCE ANALYSIS TASK

## TASK OVERVIEW
You are an expert HR analyst conducting a comprehensive monthly performance review. Your task is to synthesize weekly reports and analyses into a strategic monthly assessment that identifies patterns, trends, and actionable insights that may not be apparent when looking at individual weeks.

## EXPECTED OUTPUT FORMAT
Your analysis must be provided as a well-formed JSON object with no extraneous text, following this exact structure:
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

## CRITICAL ANALYSIS INSTRUCTIONS
1. FOCUS ON PATTERNS AND TRENDS: Identify developments across the month rather than re-evaluating individual reports
2. CONNECT REPORTS CHRONOLOGICALLY: Track how topics, challenges, and achievements evolve week-to-week
3. EMPHASIZE PROGRESSION: Note improvements or declines in performance, sentiment, and risk levels
4. CONSOLIDATE ACHIEVEMENTS: Identify the most significant accomplishments with highest impact
5. RECOGNIZE PERSISTENT CHALLENGES: Highlight issues that appear repeatedly and track resolution status
6. ASSESS CONSISTENCY: Evaluate reliability in task completion and quality across the month
7. IDENTIFY GROWTH: Look for evidence of increasing skill, complexity, or confidence
8. EVALUATE RISK PATTERNS: Determine if risks are increasing, decreasing, or remaining stable
9. PROVIDE STRATEGIC GUIDANCE: Recommend specific actions with clear priorities

## IMPORTANT TECHNICAL REQUIREMENTS
- Replace hyphens in compound words (write "five day" instead of "five-day") to ensure proper JSON parsing
- Do not write in first person or use "I" or "we" in your analysis
- Ensure your monthly summary can stand alone as an executive briefing
- Validate your response is a well-formed JSON object with no extraneous text

## EMPLOYEE AND PERIOD INFORMATION:
- Name: {employee_name}
- Position: {employee_position}
- Department: {employee_wing}
- Analysis Period: {period_start} to {period_end} ({month_name} {year})

## MONTHLY METRICS OVERVIEW:
- Number of Reports: {report_count}
- Total Achievements: {achievement_count}
- Total Challenges: {challenge_count}
- Average Sentiment: {avg_sentiment}
- Sentiment Trend: {sentiment_trend}

## RISK LEVEL DISTRIBUTION:
{risk_text}

## RECURRING TOPICS:
{topics_text}
"""

        # Insert vision data from monthly_data with better contextualization
        formatted_vision_data = monthly_data.get("formatted_vision_data", "")
        if formatted_vision_data:
            prompt += f"""
## OBJECTIVE TRACKING DATA
The following vision system data provides objective evidence of the employee's activities that should be used to:
- Cross-validate reported achievements against actual tracked activities
- Identify any discrepancies between claims and objective evidence
- Track the employee's focus areas based on system-detected activities
- Validate consistency between reported plans and observed execution
- Support your assessment of work patterns and effort distribution

{formatted_vision_data}

"""

        # Continue with weekly reports and analyses, now with clearer temporal organization
        prompt += f"""
## WEEKLY REPORTS IN CHRONOLOGICAL ORDER:
The following reports show the employee's self-reported activities week by week:
{reports_section}

## WEEKLY ANALYSES IN CHRONOLOGICAL ORDER:
The following analyses provide expert assessment of each weekly report:
{analyses_section}

## ANALYSIS REQUIREMENTS
Your task is to analyze the above information and provide a comprehensive monthly assessment of the employee's performance. Pay particular attention to how performance, challenges, and achievements evolve across the weeks.

Specifically, you should provide:

1. PROGRESS TRENDS: Analyze the chronological development in the employee's work across the month.
   - Track performance trajectory: improving, declining, or remaining stable over the 4/5 weeks
   - Note sentiment evolution from week 1 through week 4
   - Identify patterns in risk levels and whether they intensify or diminish over time
   - Assess whether challenges from earlier weeks show resolution in later weeks

2. MONTHLY ACHIEVEMENTS: Synthesize the most significant accomplishments across all weeks.
   - Identify achievements with highest impact ratings across all reports
   - Recognize accomplishments that show progression or build upon each other over time
   - Determine which achievements contributed most to organizational objectives
   - Look for achievements that represent completion of projects spanning multiple weeks

3. RECURRING CHALLENGES: Identify obstacles that appear in multiple weekly reports.
   - Track which challenges persist across consecutive weeks
   - Note whether recurring challenges show signs of resolution by month's end
   - Identify if challenges escalate in severity from week to week
   - Determine patterns in the types of obstacles faced (technical, interpersonal, resource-related)

4. CONSISTENCY ASSESSMENT: Evaluate the employee's reliability throughout the month.
   - Compare planned tasks in one week with completed tasks in subsequent weeks
   - Assess whether work quality remained stable or fluctuated between weeks
   - Evaluate week-to-week stability in performance ratings
   - Note: Focus on performance consistency over time, not report consistency

5. GROWTH INDICATORS: Identify evidence of professional development during the month.
   - Compare complexity of tasks from early weeks to later weeks
   - Look for new skills mentioned in later reports that weren't evident earlier
   - Track changes in confidence levels from week 1 through week 4/5
   - Note evolution in how challenges are addressed as the month progresses

6. FOCUS AREAS: Determine primary work concentrations throughout the month.
   - Identify projects mentioned consistently across multiple weeks
   - Note shifts in priorities from early to later weeks
   - Track emerging responsibilities that appear in later reports
   - Assess alignment between focus areas and departmental priorities

7. MONTHLY RISK ASSESSMENT: Provide an overall risk evaluation across the entire month.
   - Identify highest-risk items from all weekly assessments
   - Determine if risks show a pattern of escalation across weeks
   - Assess the overall risk profile considering all weeks collectively
   - Explain your risk assessment with specific evidence from the chronological reports

8. STRATEGIC RECOMMENDATIONS: Suggest actions based on the complete monthly picture.
   - Recommend interventions for challenges that persist across multiple weeks
   - Suggest support that would enhance demonstrated strengths
   - Propose adjustments based on observed patterns in performance
   - Offer development opportunities aligned with growth trajectory seen across weeks

9. MONTHLY SUMMARY: Provide a holistic overview of the employee's performance across the entire month.
   - Synthesize key findings from all sections and all weeks
   - Highlight significant achievements and persistent challenges
   - Describe the overall performance arc from week 1 through week 4/5
   - Keep concise and evaluative rather than merely descriptive
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
