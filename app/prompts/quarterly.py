"""Quarterly analysis prompt."""
from typing import Dict, Any
from datetime import date
from app.domain.periods import month_name as month_label, report_week_start
from app.domain.scoring import sentiment_label


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
        month_year = monthly_analysis.get("year", year)
        month_start = monthly_analysis.get("period_start", "Unknown Start")
        month_end = monthly_analysis.get("period_end", "Unknown End")
        
        # Extract summary
        summary = monthly_analysis.get("monthly_summary", "No summary provided")
        
        # Extract progress trends
        progress_trends = monthly_analysis.get("progress_trends", {})
        performance_trend = progress_trends.get("performance_trend", "stable")
        sentiment_trend = progress_trends.get("sentiment_trend", "stable")
        risk_level_pattern = progress_trends.get("risk_level_pattern", "stable")
        challenge_resolution = progress_trends.get("challenge_resolution_progress", "unchanged")
        
        # Extract achievements and challenges
        achievements = monthly_analysis.get("monthly_achievements", [])
        challenges = monthly_analysis.get("recurring_challenges", [])
        
        # Extract consistency assessment
        consistency = monthly_analysis.get("consistency_assessment", {})
        task_reliability = consistency.get("task_completion_reliability", "medium")
        work_quality = consistency.get("work_quality_consistency", "medium")
        performance_stability = consistency.get("performance_stability", "medium")
        notable_strengths = consistency.get("notable_strengths", [])
        notable_weaknesses = consistency.get("notable_weaknesses", [])
        
        # Extract growth indicators
        growth = monthly_analysis.get("growth_indicators", {})
        
        # Extract focus areas
        focus_areas = monthly_analysis.get("focus_areas", [])
        
        # Extract risk assessment
        risk_assessment = monthly_analysis.get("monthly_risk_assessment", {})
        risk_level = risk_assessment.get("overall_risk_level", "medium")
        risk_explanation = risk_assessment.get("risk_explanation", "No explanation provided")
        significant_risks = risk_assessment.get("significant_risks", [])
        escalating_risks = risk_assessment.get("escalating_risks", [])
        risk_mitigation = risk_assessment.get("risk_mitigation_recommendations", [])
        
        # Extract recommendations
        recommendations = monthly_analysis.get("strategic_recommendations", [])
        
        # Format achievements
        achievements_text = ""
        for achievement in achievements or []: 
            desc = achievement.get("description", "No description")
            impact_score = achievement.get("impact_score", "N/A")
            impact_reason = achievement.get("impact_reason", "No reason provided")
            vision_status = achievement.get("vision_verification")
            vision_indicator = ""
            if vision_status == "supported":
                vision_indicator = " [Verified - ✓]"
            elif vision_status == "contradicted":
                vision_indicator = " [Not Verified - ✗]"
            # Treat 'none' string same as None/null - no indicator
            achievements_text += f"- {desc} (Impact: {impact_score}/10 - {impact_reason}){vision_indicator}\n"
        
        # Format challenges
        challenges_text = ""
        for challenge in challenges or []: 
            desc = challenge.get("description", "No description")
            severity = challenge.get("severity", "medium")
            status = challenge.get("status", "ongoing")
            challenges_text += f"- {desc} (Severity: {severity}, Status: {status})\n"
        
        # Format notable strengths and weaknesses
        strengths_text = "\n".join([f"  • {strength}" for strength in notable_strengths]) if notable_strengths else "  • None identified"
        weaknesses_text = "\n".join([f"  • {weakness}" for weakness in notable_weaknesses]) if notable_weaknesses else "  • None identified"
        
        # Format focus areas
        focus_text = ""
        for focus in focus_areas or []:
            project = focus.get("project", "Unknown project")
            time_inv = focus.get("time_investment", "medium")
            priority = focus.get("priority_level", "medium")
            focus_text += f"- {project} (Time Investment: {time_inv}, Priority: {priority})\n"
        
        # Format risk assessment details
        sig_risks_text = "\n".join([f"  • {risk}" for risk in significant_risks]) if significant_risks else "  • None identified"
        esc_risks_text = "\n".join([f"  • {risk}" for risk in escalating_risks]) if escalating_risks else "  • None identified"
        mitigation_text = "\n".join([f"  • {rec}" for rec in risk_mitigation]) if risk_mitigation else "  • None provided"
        
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

Progress Trends:
- Performance: {performance_trend}
- Sentiment: {sentiment_trend}
- Risk Level Pattern: {risk_level_pattern}
- Challenge Resolution: {challenge_resolution}

Key Achievements:
{achievements_text or "None reported"}

Key Challenges:
{challenges_text or "None reported"}

Consistency Assessment:
- Task Completion: {task_reliability}
- Work Quality: {work_quality}
- Performance Stability: {performance_stability}
- Notable Strengths:
{strengths_text}
- Notable Weaknesses:
{weaknesses_text}

Growth Indicators:
- Task Complexity: {growth.get("complexity_of_tasks", "unchanged")}
- Skill Development: {growth.get("skill_development_evidence", "medium")}
- Confidence Level: {growth.get("confidence_level_change", "unchanged")}
- Challenge Approach: {growth.get("approach_to_challenges", "unchanged")}

Focus Areas:
{focus_text or "None specified"}

Risk Assessment:
- Overall Risk Level: {risk_level}
- Risk Explanation: {risk_explanation}
- Significant Risks:
{sig_risks_text}
- Escalating Risks:
{esc_risks_text}
- Mitigation Recommendations:
{mitigation_text}

Strategic Recommendations:
{recommendations_text or "None provided"}
"""

        # Find weekly analyses for this month
        month_weekly_analyses = []
        for weekly_analysis in weekly_analyses:
            week_date = weekly_analysis.get("date")
            if (week_date and hasattr(week_date, "month") and week_date.month == month_num
                    and (not month_year or getattr(week_date, "year", month_year) == month_year)):
                month_weekly_analyses.append(weekly_analysis)

        # Format and add weekly analyses for this month if available
        if month_weekly_analyses:
            weekly_analyses_section = f"\nWEEKLY ANALYSES FOR {month_name.upper()}:\n"
            
            for w, weekly_analysis in enumerate(month_weekly_analyses):
                # Extract date information
                week_end = weekly_analysis.get("date", "Unknown")
                
                # The week is the 7 days ending on the report date (as in the weekly prompt)
                if isinstance(week_end, date):
                    week_start = report_week_start(week_end).isoformat()
                    week_end = week_end.isoformat()
                elif hasattr(week_end, 'isoformat'):
                    try:
                        week_start = report_week_start(week_end).isoformat()
                        week_end = week_end.isoformat()
                    except:
                        week_start = "Unknown"
                        week_end = str(week_end) if week_end != "Unknown" else "Unknown"
                else:
                    week_start = "Unknown"
                    week_end = str(week_end) if week_end != "Unknown" else "Unknown"
                
                # Extract sentiment (numeric score, convert to categorical)
                week_sentiment = sentiment_label(weekly_analysis.get("sentiment_score", 0.5))

                # Extract risk assessment
                week_risk = weekly_analysis.get("risk_level", "medium")
                week_risk_explanation = weekly_analysis.get("risk_explanation", "No explanation provided")
                
                # Extract lists
                week_achievements = weekly_analysis.get("achievements", [])
                week_challenges = weekly_analysis.get("challenges", [])
                week_topics = weekly_analysis.get("topics", [])
                week_action_items = weekly_analysis.get("action_items", [])
                
                # Extract credibility assessment
                credibility_rating = weekly_analysis.get("credibility_rating", "medium")
                credibility_explanation = weekly_analysis.get("credibility_explanation", "No explanation provided")
                consistency_score = weekly_analysis.get("consistency_score", "medium")
                exaggeration_flags = weekly_analysis.get("exaggeration_flags", [])
                
                # Extract performance assessment
                performance_rating = weekly_analysis.get("performance_rating", "medium")
                performance_summary = weekly_analysis.get("performance_summary", "No summary provided")
                strengths = weekly_analysis.get("performance_strengths", [])
                improvement_areas = weekly_analysis.get("performance_improvement_areas", [])
                
                # Format achievements
                week_achievements_text = ""
                for achievement in week_achievements or []: 
                    desc = achievement.get("description", "No description")
                    impact_score = achievement.get("impact_score", "N/A")
                    impact_reason = achievement.get("impact_reason", "No reason provided")
                    vision_status = achievement.get("vision_verification")
                    vision_indicator = ""
                    if vision_status == "supported":
                        vision_indicator = " [Verified - ✓]"
                    elif vision_status == "contradicted":
                        vision_indicator = " [Not Verified - ✗]"
                    # Treat 'none' string same as None/null - no indicator
                    week_achievements_text += f"- {desc} (Impact: {impact_score}/10 - {impact_reason}){vision_indicator}\n"
                
                # Format challenges
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

    # ===== EXTRACT ALL QUARTERLY METRICS DATA =====
    
    # Basic metrics
    avg_sentiment = metrics.get("avg_sentiment", 0.5)
    sentiment_trend = metrics.get("sentiment_trend", "stable")
    achievement_count = metrics.get("achievement_count", 0)
    challenge_count = metrics.get("challenge_count", 0)
    recurring_topics = metrics.get("recurring_topics", [])
    risk_levels = metrics.get("risk_levels", {})
    
    # Aggregated performance metrics
    weekly_report_count = metrics.get("weekly_report_count", 0)
    performance_stability = metrics.get("performance_stability", "medium")
    task_reliability_trend = metrics.get("task_reliability_trend", "stable")
    quality_consistency_trend = metrics.get("quality_consistency_trend", "stable")
    risk_trend = metrics.get("risk_trend", "stable")
    challenge_resolution_trend = metrics.get("challenge_resolution_trend", "stable")
    achievement_impact_avg = metrics.get("achievement_impact_avg", 0.0)
    
    # Credibility data
    weekly_credibility_data = metrics.get("weekly_credibility_data", {})
    avg_credibility_rating = weekly_credibility_data.get("avg_credibility_rating", "medium")
    credibility_trend = weekly_credibility_data.get("credibility_trend", "stable")
    exaggeration_frequency = weekly_credibility_data.get("exaggeration_frequency", 0)
    
    # Topic data
    detailed_topics = metrics.get("detailed_topics", [])
    
    # Performance rating data
    performance_rating_data = metrics.get("performance_rating_aggregation", {})
    most_common_rating = performance_rating_data.get("most_common_rating", "medium")
    rating_trend = performance_rating_data.get("rating_trend", "stable")
    rating_distribution = performance_rating_data.get("rating_distribution", {})
    
    # Monthly progress trends
    monthly_progress_trends = metrics.get("monthly_progress_trends", [])
    
    # Monthly summaries
    monthly_summaries = metrics.get("monthly_summaries", [])
    
    # ===== BUILD ALL TEXT REPRESENTATIONS =====
    
    # Build risk levels text
    risk_text = ""
    if risk_levels:
        for level, count in risk_levels.items():
            risk_text += f"  • {level}: {count} reports/analyses\n"
    else:
        risk_text = "  • No risk data available\n"
    
    # Build recurring topics text
    if recurring_topics:
        topics_text = "\n".join([f"  • {topic}" for topic in recurring_topics])
    else:
        topics_text = "  • No recurring topics identified"
    
    # Build detailed topics text
    detailed_topics_text = ""
    if detailed_topics:
        for topic_data in detailed_topics:
            topic = topic_data.get("topic", "Unknown")
            frequency = topic_data.get("frequency", 0)
            detailed_topics_text += f"  • {topic} (Frequency: {frequency})\n"
    else:
        detailed_topics_text = "  • No detailed topic data available\n"
    
    # Build rating distribution text
    rating_distribution_text = ""
    if rating_distribution:
        for rating, percentage in rating_distribution.items():
            rating_distribution_text += f"  • {rating}: {percentage:.1%}\n"
    else:
        rating_distribution_text = "  • No rating distribution data available\n"
    
    # Build monthly progress trends text
    progress_trends_text = ""
    if monthly_progress_trends:
        for trend_data in monthly_progress_trends:
            month_num = trend_data.get("month", 0)
            month_name = month_label(month_num)
            
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
    
    # Build monthly summaries text
    monthly_summaries_text = ""
    if monthly_summaries:
        for summary_data in monthly_summaries:
            month = summary_data.get("month", "Unknown month")
            summary = summary_data.get("summary", "No summary available")
            monthly_summaries_text += f"  • {month}: {summary}\n"
    else:
        monthly_summaries_text = "  • No monthly summary data available\n"
    
    # Build the full prompt
    prompt = f"""# QUARTERLY EMPLOYEE PERFORMANCE ANALYSIS

## TASK OVERVIEW AND EXPECTED OUTPUT
You are an expert HR analyst conducting a quarterly performance review FOR A FEDERAL INTELLIGENCE AGENCY. Your task is to analyze an employee's performance across three months and synthesize a comprehensive quarterly assessment that identifies patterns, trends, and strategic mission impact not visible in shorter timeframes.

### Organizational Context
This is a civilian intelligence organization serving national security objectives. When analyzing performance:
- Use "mission impact" or "operational impact" instead of business terminology
- Highest-tier achievements contribute to "national security" or "federal security objectives"
- Primary stakeholders: State & citizens, federal government leadership (Prime Minister's Office/Cabinet Secretariat), provincial authorities, partner law enforcement agencies (LEAs)
- Outcomes are measured as "mission achievements," "operational outcomes," or "service delivery results"

**Organizational Structure:**
This organization operates through two parallel hierarchies:

*Functional Hierarchy* (bottom to top):
Cell/Desk → Unit/Branch → Section → Wing → HQ

*Geographic Hierarchy* (bottom to top):
Tehsil HQ (THQ) → District HQ (DHQ) → Zonal HQ (ZHQ) → Provincial HQ (PHQ) / Regional HQ (RHQ) → IBD HQ

*Terminology clarification:*
- Cell and Desk are interchangeable terms for the lowest functional unit
- Unit and Branch are interchangeable terms for mid-level functional grouping
- Officers operate within both hierarchies simultaneously (e.g., "Cell within Wing at DHQ")

*Impact Context:*
- Cell/Desk-level: Individual or small team outputs
- Unit/Branch and Section-level: Coordination within immediate organizational unit
- Wing-level: Cross-sectional coordination, departmental impact
- HQ-level (PHQ/RHQ/IBD HQ): Strategic organizational decisions, inter-agency coordination

### Quarterly Analysis Focus
- Identify PATTERNS across months (not individual events)
- Synthesize monthly findings into strategic insights
- Assess career trajectory and promotion readiness
- Provide forward-looking recommendations for next quarter

Your analysis must be strategic, evidence-based, and focused on both evaluation and development. Output must be valid JSON following the exact structure specified later in this prompt.

## SECURITY & SENSITIVITY BOUNDARIES

As this analysis may be viewed by HR, senior management, and the employee, you must adhere to strict operational security guidelines:

PROHIBITED CONTENT (Never include):
- Specific collection methods, technical tools, or covert operational procedures
- Identifiers or sensitive selectors (phone numbers, IMEI/IMSI, network identifiers)
- Speculation about personal motives, beliefs, family circumstances, or political/sectarian affiliations
- Details that could compromise ongoing investigations or intelligence operations

REQUIRED APPROACH:
✓ Use neutral, professional language focused on work outputs and documented facts
✓ When referencing sensitive work, use approved substitutes: "multi source corroboration," "analytical product," "validated intelligence requirement"
✓ If evidence is insufficient, state "insufficient evidence" rather than speculating

This is a mandatory security requirement. Violations could compromise operations or personnel safety.

    ## EMPLOYEE INFORMATION
    - Name: {employee_name}
    - Position: {employee_position}
    - Department/Wing (Office Hierarchy): {employee_wing}
    - Analysis Period: {period_start} to {period_end} ({quarter_description})

    ## QUARTERLY SUMMARY METRICS
    - Total Achievements: {achievement_count}
    - Total Challenges: {challenge_count}
    - Average Sentiment: {avg_sentiment} (scale: <0.5=negative, 0.5=neutral, >0.5=positive)
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
## VISION SYSTEM ACTIVITY DATA (Objective Tracking)
The following Vision system data provides objective evidence to validate claims and identify patterns across the quarter:

{formatted_vision_data}

### Using Vision Data for Quarterly Analysis

**Data Presentation Note:** The Vision data displays detailed content items for each sub-entity with a configured limit per entity. When you see text like "and X more..." at the end of a content list, this indicates additional tracked items beyond those displayed. For validation, calculate totals by adding displayed items plus the "X more" count. Truncated display ≠ incomplete tracking.

**CRITICAL FAIRNESS PRINCIPLE:** Many employees have NO vision tracking data (strategic, liaison, field, administrative roles). This is the NORMAL state. Vision data absence should NOT be mentioned or weighed negatively in your analysis.

**Vision Verification Field Usage in Quarterly Achievement Themes:**
When assigning the optional `vision_verification` field to achievement themes:
- Set to "supported": ONLY when vision data consistently confirms this achievement pattern across multiple weeks/months
- Set to "contradicted": ONLY when vision data consistently conflicts with this claimed achievement pattern (credibility concern)
- Set to "none": When no vision data exists OR vision data is not applicable to this type of achievement (MOST COMMON CASE)

**DO NOT create summary statements about vision data availability (e.g., "vision data not available for this quarter"). Simply use it when it exists and is relevant.**

**How to Use Vision Data Across the Quarter:**

**1. AGGREGATE VERIFICATION PATTERNS:**
   Review weekly and monthly analyses to identify patterns:
   - If multiple achievements across months show `vision_verification: "supported"` → This theme has strong verification, set theme to "supported"
   - If multiple achievements show `vision_verification: "contradicted"` → This is a significant credibility concern, set theme to "contradicted"
   - If achievements lack vision_verification fields → Set theme's vision_verification field to "none".

**2. QUARTERLY ACTIVITY PATTERN ANALYSIS:**
   Across the quarter, assess:
   - **Workload Trends:** Increasing/decreasing/stable activity volume month-over-month
   - **Focus Consistency:** Same entities tracked throughout (stable focus) vs. shifting entities (evolving priorities)
   - **Effort Distribution:** Even spread vs. concentrated bursts (project cycles vs. reactive work)
   - **Capacity Indicators:** Activity volume relative to role level and JD expectations

**3. APPLICATION TO QUARTERLY CREDIBILITY:**
   - Achievement themes with `vision_verification: "supported"` → Cite as strengthening credibility and confidence
   - Achievement themes with `vision_verification: "contradicted"` → Significant credibility concern, discount impact and flag for review
   - Achievement themes without vision_verification field → Assess on merit using JD alignment, consistency, and specificity across months (STANDARD CASE)

**Vision Data Limitations:** Vision tracking is not applicable for many roles. Only flag clear, repeated contradictions when vision data exists—never penalize absence of vision data.
"""


    # Insert JD data AFTER vision data, BEFORE requirements
    formatted_jd_data = quarterly_data.get("formatted_jd_data", "")
    if formatted_jd_data:
        prompt += f"""
## ROLE CONTEXT FOR QUARTERLY PERIOD (Job Description Data)

{formatted_jd_data}

### ROLE-BASED QUARTERLY ANALYSIS GUIDANCE

### Performance Expectations Framework for Quarterly Assessment

**EXCEEDS EXPECTATIONS** (one or more of):
- Scope expansion: Work consistently impacted higher organizational levels than JD specifies across multiple months
- Innovation: Introduced process improvements or efficiency gains beyond role requirements
- Leadership: Mentored colleagues, led initiatives, or took ownership beyond assigned tasks
- Mission impact: Delivered measurable outcomes beyond routine task completion

**MEETS EXPECTATIONS:**
- Completes all JD-specified responsibilities reliably across the quarter
- Handles challenges appropriate to role level effectively
- Collaborates within defined scope and demonstrates required competencies

**BELOW EXPECTATIONS:**
- Consistently misses JD-required deliverables or deadlines across months
- Requires excessive support for routine role responsibilities
- Struggles with tasks that should be manageable at this role level

### Role-Appropriate Assessment by Seniority

**JUNIOR ROLES (BPS-17 to 18):**
- Focus on: Execution quality, learning agility, growth trajectory across quarter
- Expected challenges: Learning systems, needing guidance, time management
- Red flags: Persistent basic skill gaps, inability to complete routine tasks independently

**MID-LEVEL ROLES (BPS-19 to 20):**
- Focus on: Section/wing coordination, process mastery, reliability across quarter
- Expected challenges: Cross-team coordination, resource constraints, competing priorities
- Red flags: Excessive need for guidance persisting across months, inability to work independently

**SENIOR ROLES (BPS-21 to 22):**
- Focus on: Strategic thinking, leadership impact, organizational outcomes across quarter
- Expected challenges: Strategic ambiguity, organizational politics, change management
- Red flags: Struggling with tactical execution (should delegate), requiring excessive guidance

### Career Progression Evaluation

**Analyze performance trajectory:**
- How well did employee master each role's core competencies over the quarter?
- Did role transitions represent career advancement or lateral moves?
- Track development of capabilities across multiple role contexts

**Readiness Assessment:**
- Evaluate readiness for role expansion or advancement based on JD requirements
- Identify systematic gaps between current role requirements and demonstrated capabilities
- Assess whether achievement themes demonstrate mastery beyond current role scope
- Determine if behavioral assessment patterns indicate promotion readiness

**Strategic Alignment:**
- Assess how employee's contributions align with formal role responsibilities
- Identify work performed beyond role scope (innovation, leadership, cross-functional impact)
- Evaluate whether organizational impact matches role level expectations
- Note misalignment between assigned role and actual work patterns (positive or negative)

### Special Role Scenarios

**MULTIPLE CONCURRENT ROLES:**
- Assess achievements against combined responsibilities from all JDs across quarter
- Evaluate workload distribution and prioritization across roles over time
- Identify role synergies and conflicts
- Consider total workload complexity, not individual roles in isolation

**ROLE TRANSITIONS DURING QUARTER:**
- Split assessment: Evaluate work against applicable JD for each period
- Transition credit: Acknowledge learning curve in new role
- Proportional evaluation: Weight by time in each role
- Document adaptation quality and early performance indicators
- Assess whether transition disrupted trajectory or accelerated growth

### Authority & Autonomy Assessment (Quarterly Pattern)

Consider whether employee exercised appropriate decision-making authority for their grade:
- **BPS-17 to 18:** Work with guidance, escalate major decisions, coordinate within section
- **BPS-19 to 20:** Make section/wing-level decisions independently, provide guidance to subordinates
- **BPS-21 to 22:** Make strategic HQ-level decisions, represent organization externally

Quarterly patterns to note:
- Consistent appropriate authority usage → Positive indicator for promotion readiness
- Pattern of exceeding authority without oversight → Governance concern
- Pattern of under-utilizing authority → Development need or confidence gap

"""


    # Continue with comprehensive analysis requirements
    prompt += """
## QUARTERLY CREDIBILITY AGGREGATION FRAMEWORK

Credibility is assessed at the quarterly level by aggregating monthly findings. This is critical because credibility affects achievement theme scores, performance ratings, and risk assessments.

### Step 1: Aggregate Monthly Credibility Ratings

From the monthly analyses above, count:
- HIGH credibility months: ___
- MEDIUM credibility months: ___
- LOW credibility months: ___

### Step 2: Assess Credibility Trajectory

Determine if credibility improved, declined, or remained stable across the quarter:
- **IMPROVING:** Earlier months had concerns, later months show better specificity/realism
- **DECLINING:** Earlier months were credible, later months show increased exaggeration/credibility concerns
- **STABLE:** Consistent credibility level throughout quarter

### Step 3: Calculate Quarterly Credibility Rating

**QUARTERLY HIGH CREDIBILITY:**
- All 3 months rated HIGH, OR
- 2 HIGH + 1 MEDIUM with improving trajectory

**QUARTERLY MEDIUM CREDIBILITY:**
- Mixed HIGH/MEDIUM ratings without clear trajectory
- 1 LOW month but clear improvement demonstrated
- Pattern of vague or unsubstantiated claims without contradictions

**QUARTERLY LOW CREDIBILITY:**
- 2+ LOW months without improvement
- Vision data contradictions across multiple months
- Declining trajectory (HIGH → MEDIUM → LOW)

### Step 4: Apply Timeframe-Based Evaluation

Evaluate claims by the timeframe they occurred:
- Earlier claims: Apply skepticism level appropriate to that period's credibility
- Later claims: If improvement occurred, give more benefit of the doubt
- Document trajectory in your assessment

### Step 5: Quarterly Credibility Impact

**Achievement Theme Impact Score Adjustments:**
- QUARTERLY HIGH: No discount
- QUARTERLY MEDIUM: 15% discount on achievement theme impact scores
- QUARTERLY LOW: 40% discount on achievement theme impact scores

**Risk Level Adjustments:**
- QUARTERLY HIGH: No adjustment
- QUARTERLY MEDIUM: Increase base risk by one tier
- QUARTERLY LOW: Increase base risk by two tiers

**Qualifying Language:**
- QUARTERLY HIGH: "The employee demonstrated..."
- QUARTERLY MEDIUM: "Based on reported activities..."
- QUARTERLY LOW: "The employee claims..."

### Step 6: Document Aggregated Findings

Synthesize monthly exaggeration patterns. Note:
- Recurring exaggeration types across months (superlatives, vague claims, impossible timelines)
- Improvement or regression in reporting quality
- Specific examples that justify the quarterly credibility rating

## DATA HANDLING GUIDELINES

### Data Precedence (When Sources Conflict)
1. **Vision system data** (highest priority - objective evidence)
2. **Original employee reports** (primary source)
3. **Monthly AI analyses** (synthesis of weekly data)
4. **Weekly AI analyses** (granular detail, may contain interpretation)

When discrepancies exist:
- Vision contradicts reports → Flag, investigate, apply credibility discount
- Monthly analyses differ from weekly → Trust monthly synthesis for trends
- Multiple sources align → Higher confidence in findings

### Temporal Weighting
- **For FORWARD PLANNING:** Weight recent months more heavily (forward planning)
- **For OVERALL EVALUATION:** Weight all months equally (balanced assessment)
- **For CREDIBILITY:** Apply timeframe-based evaluation (earlier skepticism if warranted, later trust if improved)

### Data Completeness
If months are missing (leave, incomplete data):
- Explicitly state data limitations
- Avoid over-confident conclusions
- Assess based on available data with appropriate caveats
- Note which months are missing and impact on analysis confidence

## IMPACT RATING SCALE FOR QUARTERLY ACHIEVEMENT THEMES

Rate cumulative/thematic achievements using this scale:

**1-3: Individual/Cell/Desk-level Impact**
- Routine task completion patterns across quarter
- Personal skill development
- Individual case file maintenance
- THQ/DHQ routine operations

**4-6: Unit/Branch and Section-level Impact**
- Sustained value addition to immediate team
- Process improvements within section
- Consistent coordination across multiple desks/cells
- DHQ/ZHQ coordination activities

**7-8: Wing-level Impact at HQ Facilities**
- Intelligence assessments regularly briefed to senior management
- Ongoing coordination with partner LEAs
- Regular reports delivered to provincial/federal authorities
- Process changes affecting multiple sections
- ZHQ/PHQ/RHQ level coordination

**9-10: IBD HQ-level/Strategic Impact**
- Intelligence products regularly briefed to PMO/Cabinet
- Contributions to federal security directives
- Strategic partnerships established with multiple LEAs
- Mission-critical operational successes with lasting impact
- IBD HQ strategic initiatives

**Quarterly Application:**
- Rate cumulative impact of achievement clusters, not individual items
- Weight achievements that built upon each other across months
- Consider sustained impact vs. one-time achievements
- Apply credibility discounts as determined above

## COMPREHENSIVE QUARTERLY ANALYSIS REQUIREMENTS

Complete all analyses in order. The sequence reflects logical dependencies.

### CONTENT SYNTHESIS & VALIDATION

**1. STRATEGIC ALIGNMENT ASSESSMENT:**

Synthesize monthly and weekly patterns into quarterly strategic assessment:

**Performance Priority Framework** (highest to lowest importance):
1. **Consistency** (reliability across weeks/months, meeting commitments, predictable delivery)
2. **Innovation** (proactive initiative, process improvements)
3. **Strategic alignment** (work supports wing/organizational mission)
4. **Quality** (accuracy, thoroughness, professionalism)
5. **Collaboration** (effective teamwork and coordination)

**NOT a ranking factor:** Output volume—fewer high-quality, mission-aligned deliverables outweigh high-volume work.

Evaluate how employee's work connects to both role expectations AND organizational goals:
- Assess scope of impact (individual/cell/unit/section/wing/hq) relative to role level
- Identify work performed beyond role scope (innovation, leadership, cross-functional impact)
- Determine role mastery level: developing/proficient/exceeding expectations
- For role transitions: Assess readiness for new role based on previous role performance
- Evaluate whether achievement themes align with strategic role responsibilities
- Identify key initiatives and their mission outcomes
- Consider Vision data (if available) as validation of strategic contributions
- Provide 2-3 concrete examples of strategic alignment with specific initiatives

**Role Alignment Assessment (Job Description (JD) Fit Across Quarter):**
Evaluate how well employee's actual work aligns with job description responsibilities:
- **Strong alignment:** Work consistently matches JD responsibilities across all 3 months; achievement themes directly support role requirements
- **Partial alignment:** Some work matches JD, some work outside scope; may indicate role evolution or scope creep
- **Weak alignment:** Significant gaps between JD and actual work; systematic misalignment suggests role-fit issues

Document in role_fit_assessment field:
- **Stretch contributions:** Areas where employee exceeded role scope (document for promotion consideration)
- **Gaps:** JD-required responsibilities absent from work patterns (document for development planning)
- **Role evolution:** How role has organically expanded/contracted relative to original JD
- **Recommendations:** Whether JD should be updated to reflect actual work or work should be realigned to JD

Format as comprehensive alignment assessment with:
- Role expectations baseline (what the JD requires)
- Performance relative to baseline (meets/exceeds/below with evidence)
- Role alignment rating (strong/partial/weak)
- Detailed role fit assessment (stretch contributions, gaps, evolution)
- Readiness indicators for advancement
- Overall alignment with organizational strategic priorities
    
**2. ACHIEVEMENT THEME IDENTIFICATION:**

From monthly achievements, cluster into 3-7 strategic themes:
- Name each theme based on mission function or outcome area
- Link 2-4 specific achievements under each theme (include both activities performed and their measurable outcomes)
- Rate impact using 1-10 scale (using the impact rating scale) with separate score and reason (1-3: individual, 4-6: section, 7-8: wing, 9-10: HQ strategic)
- Provide brief reason explaining the organizational level impacted
- Indicate which achievements are verified by Vision data
- Identify compounding or sequential achievements that build on each other
- Apply credibility discounts to impact scores as determined above

**Each achievement should capture both the work done AND its measurable result** (e.g., "Developed cross-reference methodology reducing reporting discrepancies by 35%" rather than separating activity from outcome).

**Achievement Categories to Consider (but not limited to):**
- Mission-critical deliverables
- Process improvements with lasting impact
- Cross-functional collaboration outcomes
- Skill development demonstrated through work quality
- Leadership/mentorship contributions

Format as themed clusters with constituent achievements (including their outcomes) and cumulative impact.

**3. PERFORMANCE TRAJECTORY ANALYSIS:**

Analyze direction of performance (improving/stable/declining/mixed):
- Determine overall trend classification for the quarter
- Evaluate consistency using three metrics:
  * **task_completion_reliability** (high/medium/low): Reliability in completing planned tasks
  * **work_quality_consistency** (high/medium/low): Consistency of work quality throughout quarter
  * **performance_stability** (high/medium/low): Stability of performance across the quarter
- Identify any significant shifts during the quarter with:
  * Month when shift occurred
  * Description of what changed in performance
  * Factors that contributed to this change
- Determine factors driving performance changes (from weekly/monthly analyses content, outcomes, and consistency patterns)
- If Vision data is available and applicable, consider as additional objective performance validation
- Analyze relationship between workload and performance
- Incorporate week-to-week patterns to identify micro-trends within monthly data
- Detect early warning signals in weekly data that developed into monthly challenges
- Analyze weekly volatility within seemingly stable months
- Consider role transitions when evaluating performance trajectory
- Assess whether performance changes correlate with role changes or other factors

Format with trend classification, three consistency metrics, and notable shifts documentation.

**4. CHALLENGE PATTERN ANALYSIS:**

Identify challenges appearing across multiple weeks/months and document for each:
- **Description:** Clear description of the recurring challenge
- **Type:** Categorize as internal (organizational) or external
- **Frequency:** Assess pattern (constant/intermittent/increasing/decreasing)
- **Resolution Status:** Current state (resolved/ongoing)
- **Systemic:** Determine if systemic issue or specific to employee
- If Vision data is available and applicable, consider for additional challenge context
- Incorporate weekly challenge data to track evolution of issues over time
- Identify challenges that appeared frequently in weekly reports but were resolved

**Adaptation Effectiveness Assessment:**
Evaluate how effectively the employee adapted to recurring challenges across the quarter:
- **HIGH:** Consistently demonstrated effective coping strategies; challenges diminished in severity or were resolved; learned from obstacles and adjusted approach proactively
- **MEDIUM:** Mixed adaptation; some challenges addressed effectively, others persisted; reactive adjustments rather than proactive problem-solving
- **LOW:** Struggled to adapt; recurring challenges showed no improvement or worsened; same ineffective approaches repeated without learning

Consider patterns across all three months: Did challenge management improve over time? Were resources/support effectively utilized? Did employee demonstrate resilience and problem-solving agility?

Format as list of recurring challenges with pattern analysis, resolution assessment, and overall adaptation effectiveness rating.

**5. CROSS-FUNCTIONAL IMPACT ASSESSMENT:**

Identify collaborations with other teams/departments:
- Assess overall effectiveness of cross-functional work across the quarter
- For each collaboration, specify the type and evaluate impact on stakeholders
- If Vision data is available and applicable (e.g., email/document collaboration tracking), consider for additional collaboration validation
- Use weekly collaboration patterns to identify distinct collaboration activities

**Collaboration Types** (specify for each stakeholder impact):
- **Leading Initiative:** Coordinating cross-functional projects across Wings/Sections
- **Contributing Expertise:** Providing specialized knowledge to other teams
- **Mentoring:** Knowledge transfer and capability building activities
- **Process Improvement:** Improvements benefiting multiple units

**Evidence Requirements:**
- Provide concrete examples for each collaboration
- Include knowledge sharing details when applicable (e.g., "Trained 5 analysts on new methodology")
- Document measurable outcomes where possible

Format as collaboration effectiveness rating with stakeholder impact examples.

**6. SKILL DEVELOPMENT EVALUATION:**

Identify key capabilities demonstrated or developed during the quarter. For each capability document:
- **Skill name:** Name of the specific skill or capability
- **Proficiency level:** Current level (developing/proficient/advanced)
- **Growth trajectory:** How skill changed over quarter (improved/stable/declined)

Additionally assess:
- **Learning agility:** Employee's ability to learn and adapt to new information (high/medium/low)
- **Autonomy level:** Level of independence in executing responsibilities (high/medium/low)
- **Development focus:** Recommended skill or capability to develop next

Analysis considerations:
- Use weekly performance data to identify gradual skill improvements not apparent at monthly level
- Map demonstrated capabilities to role competency requirements
- Identify skills that exceed current role expectations (readiness indicators)
- Assess skill development relative to role complexity and requirements
- Evaluate whether skills align with career progression path

Format as capability assessment with growth indicators and role-fit analysis.
   
**7. BEHAVIORAL ASSESSMENT:**

Evaluate five key behaviors with specific evidence across the quarter:

a) **Ownership and accountability**
b) **Collaboration and teamwork**
c) **Communication effectiveness**
d) **Problem-solving approach**
e) **Quality standards and craft**

For each behavior:
- Provide specific observed examples spanning the quarter (drawn from monthly/weekly analysis)
- Rate as below/meets/exceeds expectations relative to BPS level
- Consider consistency of behaviors across quarter
- Incorporate weekly credibility assessments to evaluate behavioral patterns over time

Target 2-3 specific examples per behavior, spanning early/mid/late quarter when possible.

**8. RISK ASSESSMENT:**

**Step 1 - Aggregate Situational Risk:**
- Count HIGH/MEDIUM/LOW risk months
- Identify risk trends (escalating, de-escalating, stable)
- Note any critical risk events
- Use weekly risk assessments to create detailed risk trajectory
- Identify risk volatility patterns and potential leading indicators

**Step 2 - Apply Credibility Adjustment:**
- QUARTERLY HIGH credibility: No adjustment
- QUARTERLY MEDIUM credibility: Increase risk by one tier
- QUARTERLY LOW credibility: Increase risk by two tiers

**Step 3 - Document Risk Factors:**
- Determine overall risk level for next quarter
- Analyze risk trend (increasing/stable/decreasing)
- Identify specific risk factors with potential impact
- Recommend mitigation strategies for each risk

Format as risk profile with specific factors and mitigations.

**9. CREDIBILITY ASSESSMENT:**

Apply the Quarterly Credibility Aggregation Framework (detailed above).

Document:
- Monthly credibility rating counts
- Credibility trajectory (improving/declining/stable)
- Quarterly credibility rating (HIGH/MEDIUM/LOW)
- Vision data alignment assessment (high/medium/low)
- Specific evidence supporting the rating
- Impact on overall evaluation (how credibility affected achievement scores, risk, performance rating)
- Synthesize weekly credibility assessments to identify reporting pattern trends
- Track exaggeration flags over time to detect improvement or deterioration

**10. FORWARD PLANNING:**

Generate structured recommendations with explicit priority and ownership assignments.

**Recommendation Structure:**
Each recommendation must include:
- **Action:** Clear, actionable description of what should be done
- **Priority:** high/medium/low classification
- **Ownership:** employee/manager/hr/cross-team assignment

**Priority Guidelines:**
- **High:** Immediate intervention needed (risk mitigation, performance concerns, critical skill gaps)
- **Medium:** Should be addressed within next quarter (development needs, resource requests)
- **Low:** Desirable improvements (optimization opportunities, stretch goals)

**Ownership Guidelines:**
- **Employee:** Actions employee can take independently
- **Manager:** Manager intervention or approval required
- **HR:** HR resources, training programs, or policy support needed
- **Cross-Team:** Requires coordination with other Wings/Sections

**Recommendation Categories:**
- **Keep Doing:** Activities demonstrating value (explain why they're effective)
- **Improve:** Areas for enhancement (be specific about how to improve)
- **Start:** New initiatives to begin (growth opportunities aligned with career path)
- **Stop:** Activities to discontinue (explain why ineffective and suggest alternatives)
- **Support Needed:** Resources/training required (justify need and suggest timeline)

**Crafting Examples:**
- Technical skills gap → action: "Provide advanced SQL querying and data analysis training", ownership: "hr", priority: "medium"
- Process knowledge gap → action: "Share documentation and SOPs for multi-source corroboration process", ownership: "manager", priority: "high"
- Soft skills gap → action: "Assign senior analyst as mentor for stakeholder communication", ownership: "manager", priority: "medium"
- Resource constraint → action: "Prioritize access to classified intelligence database for counter-terrorism research", ownership: "manager", priority: "high"

Incorporate trends from weekly action items to ensure continuous follow-through.

**11. QUARTERLY SUMMARY:**

Synthesize all findings into a cohesive 4-6 sentence executive summary:
- Overall performance trajectory across the quarter
- Most significant achievements (with mission impact context)
- Key challenges and their status/resolution
- Risk profile summary
- Forward-looking outlook for next quarter
- Include confidence indicators when appropriate

This summary should stand alone as an executive briefing.

## HIERARCHICAL DATA ANALYSIS APPROACH

For this quarterly analysis, integrate data across three time levels:

**1. WEEKLY LEVEL (Most Granular):**
- Use weekly analyses to identify micro-trends and early signals
- Track evolution of specific challenges, achievements, and performance ratings
- Identify volatility patterns that may be smoothed out in monthly aggregations
- Consider week-to-week consistency as a performance indicator
- Use weekly credibility assessments to evaluate reporting patterns

**2. MONTHLY LEVEL (Middle Layer):**
- Use monthly analyses to identify medium-term patterns and trends
- Compare monthly summaries to detect trajectory changes
- Evaluate consistency between months as a stability indicator
- Identify recurring themes across multiple months
- Use monthly growth indicators to track development progress

**3. QUARTERLY LEVEL (Strategic Overview):**
- Synthesize insights from both weekly and monthly data
- Focus on mission impact and strategic alignment
- Identify long-term patterns and significant trends
- Evaluate overall trajectory and development path
- Provide forward-looking recommendations based on comprehensive data
- Assess readiness for advancement or role expansion

**Integration Priorities:**
- Identify patterns that persist across multiple time frames
- Detect contradictions or anomalies between time levels
- Use granular weekly data to validate or challenge monthly conclusions
- Track progression of specific issues/achievements over time
- Evaluate consistency as a performance metric in itself

**Resolving Contradictions Across Levels:**
When data levels conflict:
1. **Trust the more granular level for specifics** (weekly > monthly for pinpointing timing)
2. **Trust the aggregated level for overall trends** (monthly > weekly for pattern significance)
3. **Document the contradiction explicitly** in your analysis
4. **Investigate the cause**: Was it weekly volatility or a genuine shift?

## EDGE CASE HANDLING

**Exceptional Quarterly Performance:**

If performance is exceptional across all dimensions:
- Celebrate and document thoroughly with specific examples
- Verify MORE rigorously: High performance requires high evidence quality (detailed monthly/weekly analyses with specific, measurable outcomes across all 3 months)
- Check consistency across ALL 3 months (truly exceptional vs. one standout month?)
- When Vision data is available and applicable, verify against those patterns for additional validation
- Note credibility assessment (exceptional claims need exceptional evidence from analysis consistency, documented outcomes, and achievement specificity)
- Document for promotion/recognition consideration
- Include confidence indicators: "High confidence based on consistent, detailed analyses across quarter with specific measurable outcomes" OR (if vision applicable): "High confidence further validated by Vision data patterns"
- Assess promotion readiness explicitly in strategic alignment section

**Consistently Low Quarterly Performance:**

If performance is low across multiple dimensions:
- Document clearly and objectively for performance management
- Focus recommendations on specific, actionable development steps
- Include escalation recommendation: "Recommend manager intervention and formal performance improvement plan"
- Identify root causes from patterns (skill gaps, resource constraints, role misfit)
- Maintain professional, fact-based tone
- Assess whether quarterly pattern indicates role-fit issues vs. temporary factors
- Include confidence level: "High confidence due to consistent pattern across 3 months"

**Mid-Quarter Role Changes:**

- Explicitly note and evaluate each period against applicable JD
- Highlight adaptability during transition
- Weight performance by time in each role
- Apply learning curve expectations for new role portion (first 2-3 weeks)
- Assess whether transition disrupted trajectory or accelerated growth
- Identify transferable skills leveraged across different roles
- Determine optimal role type based on performance patterns

**Sparse Data (Missing Months):**

- Explicitly state which months are missing and why if known
- Acknowledge impact on analysis confidence: "Medium confidence due to incomplete data for Month 2"
- Avoid over-confident conclusions
- Recommend data completion if ongoing issue
- Note in quarterly summary: "Assessment based on 2 of 3 months; limited visibility into [specific period]"

## EVIDENCE STANDARDS AND ANALYSIS FRAMEWORK

### Evidence Requirements

**Evidence Sources (in order of objectivity):**
1. **Analysis detail and specificity:** Detailed monthly/weekly analyses with measurable achievements and concrete outcomes (available for all employees)
2. **Internal consistency:** Coherent patterns across analyses with no contradictions between months/weeks (available for all employees)
3. **Vision data validation:** Objective tracking data (ONLY available for applicable roles; absence is NORMAL)

**Evidence Standards by Assessment Type:**
- Each achievement theme needs atleast 2-3 specific examples from different months
- Behavioral assessments require concrete examples spanning the quarter
- Performance trajectory claims need month-by-month evidence
- Risk assessments need specific supporting factors with temporal context
- Any claim of "high" impact (7+) requires mission outcome evidence
- Include confidence indicators when making significant claims (based on analysis detail, consistency across months, and specificity of outcomes)

**Critical Fairness Principle:** Vision data is NOT required for high confidence or high impact assessments. Detailed, consistent monthly/weekly analyses with measurable outcomes and specific achievements provide sufficient evidence. Vision data (when available and applicable) provides additional validation but is not the primary evidence source.

### Pattern Recognition Guidance
- Temporal patterns: Changes over three months (early/mid/late quarter comparison)
- Thematic patterns: Recurring topics or areas of focus across weeks/months
- Behavioral patterns: Consistent approaches or styles demonstrated repeatedly
- Challenge patterns: Recurring obstacles or barriers (constant/intermittent/escalating)
- Performance patterns: Consistency or variability in delivery quality

### Balance and Proportionality
- Balance achievement recognition with development opportunities
- Balance forward-looking vs. retrospective analysis (60% forward / 40% retrospective)
- Consider both individual performance and systemic factors
- Balance tactical (execution) and strategic (mission alignment) focus
- Evaluate both process (how work was done) and outcome (results achieved)

### Bias Mitigation
- Avoid recency bias (overweighting last month): Weight all 3 months equally for overall evaluation
- Avoid halo/horn effect: Assess each dimension independently
- Consider both personal and situational factors (external challenges, resource constraints)
- Evaluate evidence objectively rather than confirming initial impressions
- Judge processes independently from outcomes (good process + bad luck ≠ poor performance)

### Credibility Governance
- QUARTERLY MEDIUM credibility: Apply 15% discount to achievement theme impact scores
- QUARTERLY LOW credibility: Apply 40% discount to achievement theme impact scores and increase risk level
- Add verification steps to forward planning when credibility concerns exist (max 30-40% of recommendations)
- Document impact on evaluation: Explain how credibility affected scoring in credibility_assessment.impact_on_evaluation

## OUTPUT STRUCTURE AND FORMAT

Your analysis must be provided as valid JSON following this exact structure:

{
  "strategic_alignment": {
    "organizational_impact": "individual/cell/unit/section/wing/hq",
    "key_initiatives": [
      {
        "initiative": "Initiative name",
        "alignment": "high/medium/low",
        "outcomes": "Concrete mission outcomes achieved"
      }
    ],
    "role_alignment": "strong/partial/weak",
    "role_fit_assessment": "Detailed assessment of JD fit including stretch contributions, gaps, and evolution"
  },
  "achievement_themes": [
    {
      "theme": "Theme name (max 60 characters)",
      "related_achievements": ["Achievement 1", "Achievement 2", "Achievement 3"],
      "impact_score": "N",
      "impact_reason": "Reason for rating",
      "vision_verification": "supported/contradicted/none"
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
      {"stakeholder": "Wing/Section/Partner LEA", "collaboration_type": "Leading Initiative/Contributing Expertise/Mentoring/Process Improvement", "impact": "Impact description", "evidence": "Concrete example"}
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
    "explanation": "Assessment rationale with quarterly aggregation methodology",
    "vision_data_alignment": "high/medium/low/none",
    "impact_on_evaluation": "Description of how credibility affected overall assessment"
  },
  "forward_planning": {
    "keep_doing": [
      {"action": "Activity description", "priority": "high/medium/low", "ownership": "employee/manager/hr/cross-team"}
    ],
    "improve": [
      {"action": "Improvement action", "priority": "high/medium/low", "ownership": "employee/manager/hr/cross-team"}
    ],
    "start": [
      {"action": "New initiative", "priority": "high/medium/low", "ownership": "employee/manager/hr/cross-team"}
    ],
    "stop": [
      {"action": "Activity to discontinue", "priority": "high/medium/low", "ownership": "employee/manager/hr/cross-team"}
    ],
    "support_needed": [
      {"action": "Resource/support needed", "priority": "high/medium/low", "ownership": "employee/manager/hr/cross-team"}
    ]
  },
  "quarterly_summary": "Executive summary of quarterly performance (4-6 sentences)"
}

## TECHNICAL REQUIREMENTS

**Formatting Standards:**
- Format your response as valid JSON with no markdown code fences or explanatory text
- Replace hyphens in compound words (write "five day" instead of "five-day") for proper JSON parsing
- Ensure your analysis contains no first-person references ("I" or "we")
- Use complete sentences in descriptions
- Verify all required fields are completed before submission

**Confidence Indicators:**

**CRITICAL:** Evidence quality is based on analysis detail, consistency across months/weeks, measurable outcomes, and internal coherence—NOT on vision data presence. Many roles have no vision data (strategic, liaison, field, administrative), which is NORMAL and does not reduce confidence.

- HIGH CONFIDENCE: Use when 3/3 months have detailed analyses with clear, measurable outcomes AND no contradictions between monthly/weekly assessments. Vision data validation (when available and applicable) strengthens confidence but is NOT required.
  - Example: "High confidence based on consistent pattern across all three monthly analyses with specific, measurable outcomes"
  - Example: "High confidence due to detailed monthly analyses with coherent, verifiable achievement patterns"
  - Example (with vision): "High confidence due to detailed analysis evidence further validated by Vision data"

- MEDIUM CONFIDENCE: Use when only 2/3 months available OR analyses lack specificity (vague achievement descriptions, no measurable outcomes) OR minor inconsistencies between months
  - Example: "Medium confidence due to incomplete data for Month 2"
  - Example: "Medium confidence due to limited detail in achievement outcomes across analyses"
  - Example: "Medium confidence due to minor inconsistencies in timelines between monthly analyses"

- LOW CONFIDENCE: Use when only 1 month of data OR significant contradictions between analyses (e.g., achievement claimed complete in Month 1 analysis but reported as ongoing in Month 3 analysis) OR Vision data contradicts claims (when applicable)
  - Example: "Low confidence due to sparse analyses across quarter with minimal detail"
  - Example: "Low confidence due to contradictions between monthly analyses (e.g., achievement status conflicts across months)"
  - Example (with vision): "Low confidence due to contradictions between analyzed achievements and Vision data"

**Tone Specifications:**
- Professional and formal (suitable for HR and senior management review)
- Objective and fact-based (avoid subjective language without evidence)
- Coaching-oriented for recommendations (actionable, specific, supportive)
- Mission-focused language
- Security-conscious (no prohibited content, use approved substitutes)

**Quality Assurance:**
- Ensure quarterly summary provides a holistic view that could stand alone as an executive briefing
- Apply credibility governance appropriately to achievement theme impact scores and risk assessments
- Cross-check that all BPS-level assessments are appropriate for the employee's grade
- Confirm all examples are intelligence-relevant (no corporate/business examples)

## CONTEXT PRIORITIZATION

If context limitations require prioritizing information:
- Monthly analyses take precedence over individual weekly reports
- Pattern indicators are more important than individual instances
- Vision-verified achievements have higher priority than self-reported only
- Significant changes or anomalies are more important than expected performance
- Forward-looking insights are more valuable than historical details
- When analyzing weekly data, focus on trends and patterns rather than isolated incidents

"""


    return prompt
