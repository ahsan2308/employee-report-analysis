"""Monthly analysis prompt."""
from typing import Dict, Any
from datetime import date


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
        # Convert numeric sentiment to categorical
        if sentiment < 0.5:
          sentiment = "negative"
        elif sentiment > 0.5:
          sentiment = "positive"
        else:
          sentiment = "neutral"
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
        exaggeration_flags = analysis.get("exaggeration_flags", [])

        # Extract performance assessment
        performance = analysis.get("performance_rating", "medium")
        performance_summary = analysis.get("performance_summary", "No summary provided")
        strengths = analysis.get("performance_strengths", [])
        improvement_areas = analysis.get("performance_improvement_areas", [])
        
        # Format achievements and challenges for readability
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
Sentiment: {sentiment}
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
- Exaggeration Flags: {exaggeration_flags or "None"}

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
    
    # Build the full prompt with organizational context header
    prompt = f"""# MONTHLY EMPLOYEE PERFORMANCE ANALYSIS

## TASK OVERVIEW AND EXPECTED OUTPUT
You are an expert HR analyst conducting a monthly performance review FOR A FEDERAL INTELLIGENCE AGENCY. Your task is to synthesize all weekly reports and analyses into a comprehensive monthly assessment identifying patterns, trends, and strategic insights not visible in individual weekly analyses.

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

### Monthly Analysis Focus
- Identify PATTERNS across weeks (not individual events). 
- Synthesize weekly findings into strategic insights. 
- Assess trajectory (improving/declining/stable) 
- Provide forward-looking recommendations based on trends.

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
- Wing/Department (Office Hierarchy): {employee_wing}
- Analysis Period: {period_start} to {period_end} ({month_name} {year})

## MONTHLY SUMMARY METRICS
- Number of Weekly Reports: {report_count}
- Total Achievements Recorded: {achievement_count}
- Total Challenges Recorded: {challenge_count}
- Average Sentiment Score: {avg_sentiment}
- Sentiment Trend: {sentiment_trend}

**Metrics Interpretation Guide:**
- Average Sentiment: Overall employee morale trajectory (0.0-1.0 scale; >0.6 positive, <0.4 concerns)
- Sentiment Trend: Key indicator for intervention needs (declining = monitor closely)
- Risk Distribution: Pattern indicates systemic vs isolated issues

RISK LEVEL DISTRIBUTION:
{risk_text}

RECURRING TOPICS:
{topics_text}

## REQUIRED JSON OUTPUT FORMAT
{{{{
  "progress_trends": {{{{
    "performance_trend": "improving/declining/stable",
    "sentiment_trend": "positive/negative/stable",
    "risk_level_pattern": "increasing/decreasing/stable",
    "challenge_resolution_progress": "improved/declined/unchanged"
  }}}},
  "monthly_achievements": [
    {{{{"description": "Significant achievement description in complete sentences", "impact_score": 8, "impact_reason": "Brief reason for this impact rating", "vision_verification": "supported/contradicted/none"}}}}
  ],
  "recurring_challenges": [
    {{{{"description": "Persistent challenge description", "severity": "low/medium/high", "status": "resolved/ongoing"}}}}
  ],
  "consistency_assessment": {{{{
    "task_completion_reliability": "high/medium/low",
    "work_quality_consistency": "high/medium/low",
    "performance_stability": "high/medium/low",
    "notable_strengths": ["Consistent strength 1", "Consistent strength 2"],
    "notable_weaknesses": ["Inconsistent area 1", "Inconsistent area 2"]
  }}}},
  "growth_indicators": {{{{
    "complexity_of_tasks": "increased/decreased/unchanged",
    "skill_development_evidence": "high/medium/low",
    "confidence_level_change": "increased/decreased/unchanged",
    "approach_to_challenges": "more proactive/more reactive/unchanged"
  }}}},
  "focus_areas": [
    {{{{"project": "Primary project or responsibility", "time_investment": "high/medium/low", "priority_level": "high/medium/low"}}}}
  ],
  "monthly_risk_assessment": {{{{
    "overall_risk_level": "low/medium/high",
    "risk_explanation": "Detailed explanation including specific factors and trends observed across the month",
    "significant_risks": ["Risk factor 1", "Risk factor 2"],
    "escalating_risks": ["Escalating risk 1"],
    "risk_mitigation_recommendations": ["Recommendation 1", "Recommendation 2"]
  }}}},
  "strategic_recommendations": [
    {{{{"action": "Specific action to address challenge or enhance performance", "priority": "high/medium/low"}}}}
  ],
  "monthly_summary": "A concise but comprehensive narrative overview (3-5 sentences) of the employee's performance during the month."
}}}}

## TECHNICAL OUTPUT REQUIREMENTS

- Impact ratings use separate fields: impact_score (integer 1-10) and impact_reason (max 120 characters)
- Use complete sentences for achievement/challenge descriptions
- Replace hyphens in compound words: write "five day" not "five-day"
- Avoid first-person references: no "I" or "we"
- Output valid JSON only: begin with "{" and end with "}", no extra text

**Tone:** Professional/formal for HR/senior management. Objective, fact-based. Coaching-oriented recommendations. Balance critique with strengths recognition.

## DATA CONTEXT

### Weekly Reports (Raw Employee Submissions)
{reports_section}
"""

    # Insert vision data from monthly_data with enhanced guidance
    formatted_vision_data = monthly_data.get("formatted_vision_data", "")
    if formatted_vision_data:
        prompt += f"""
## VISION SYSTEM ACTIVITY DATA (Objective Tracking)

{formatted_vision_data}

### Using Vision Data for Monthly Analysis

**Data Presentation Note:** The Vision data displays detailed content items for each sub-entity with a configured limit per entity. When you see text like "and X more..." at the end of a content list, this indicates additional tracked items beyond those displayed. For validation, calculate totals by adding displayed items plus the "X more" count. Truncated display ≠ incomplete tracking.

**CRITICAL FAIRNESS PRINCIPLE:** Many employees have NO vision tracking data (strategic, liaison, field, administrative roles). This is the NORMAL state. Vision data absence should NOT be mentioned or weighed negatively in your analysis.

**Vision Verification Field Usage in Monthly Achievements:**
When assigning the optional `vision_verification` field to monthly achievements:
- Set to "supported": ONLY when vision data confirms this achievement
- Set to "contradicted": ONLY when vision data conflicts with this claimed achievement (credibility concern)
- Set to "none": When no vision data exists OR vision data is not applicable to this achievement type (MOST COMMON CASE)

**DO NOT create summary statements about vision data availability. Simply use it when it exists and is relevant.**

**How to Use Vision Data Across the Month:**

**1. CROSS-VERIFICATION (Quality Assurance):**
   **CRITICAL:** Do not blindly trust weekly `vision_verification` values. Independently verify key achievements against the raw Vision System Data above:
   
   - **Review weekly verification decisions:** Check if weekly LLM's "supported"/"contradicted" determinations align with the actual vision data
   - **Document discrepancies:** If you find weekly verification was incorrect, note this in your monthly assessment and apply correct verification status
   
   **IMPORTANT DATA PRESENTATION CAVEAT:**
   The vision data you see in this monthly prompt may be TRUNCATED compared to what the weekly LLM saw (e.g., 5 items per sub-entity shown here vs. 10 items shown in weekly analysis due to context length constraints). Therefore:
   
   - **Absence of evidence ≠ Evidence of absence:** If weekly marked "supported" but you don't see specific supporting evidence in the truncated monthly view, this does NOT automatically mean weekly was wrong
   - **Trust "supported" unless contradicted:** Only override weekly "supported" to "contradicted" if you see ACTIVE CONTRADICTORY evidence (e.g., achievement claims 50 emails sent but vision shows only 5 emails), NOT just because you can't find confirming evidence in truncated data
   - **Verify "contradicted" more strictly:** Weekly "contradicted" decisions should be based on clear conflicts that remain visible even in truncated data—these are worth verifying
   - **Use entity-level totals:** When cross-verifying, rely on entity-level activity counts and date ranges (these are not truncated) rather than requiring specific content items to match
   
   **When to override weekly verification:**
   - Weekly marked "supported" but vision data shows CONTRADICTORY activity (conflicting evidence, wrong timeframe, impossible volumes) → Change to "contradicted"
   - Weekly marked "contradicted" but vision data actually supports the claim → Change to "supported"
   - Weekly omitted verification but clear vision data exists in monthly view → Add appropriate verification status
   - Weekly marked "supported" and monthly vision shows consistent entity-level patterns → Confirm as "supported"
   
   **Quality principle:** Weekly analysis is your starting point with access to more detailed data. Cross-verify for contradictions and errors, but respect weekly decisions when monthly data is inconclusive due to truncation.

**2. AGGREGATE VERIFIED PATTERNS:**
   After cross-verification, identify monthly achievement patterns:
   - If multiple weeks show CONFIRMED `vision_verification: "supported"` for related achievements → Set monthly achievement to "supported"
   - If multiple weeks show CONFIRMED `vision_verification: "contradicted"` for related achievements → Significant credibility concern, set monthly achievement to "contradicted"
   - If weekly achievements lack vision_verification fields AND raw vision data doesn't apply to the achievement → Set monthly achievement's vision_verification field to "none".

**3. ACTIVITY PATTERN ANALYSIS:**
   Across the month, assess:
   - **Workload Trends:** Increasing/decreasing/stable activity volume week-over-week
   - **Focus Consistency:** Same entities tracked throughout (stable focus) vs. shifting entities (evolving priorities)
   - **Effort Distribution:** Even spread vs. concentrated bursts (project deadlines vs. reactive work)

**4. APPLICATION TO MONTHLY CREDIBILITY:**
   - Achievements with VERIFIED `vision_verification: "supported"` → Cite as strengthening credibility
   - Achievements with VERIFIED `vision_verification: "contradicted"` → Significant credibility concern, discount impact and flag for review
   - Achievements without vision_verification field → Assess on merit using JD alignment, consistency, and specificity (STANDARD CASE)

**Vision Data Limitations:** Vision tracking is not applicable for many roles. Only flag clear, repeated contradictions when vision data exists—never penalize absence of vision data.

"""
        

    # STRATEGIC PLACEMENT: Insert JD data AFTER vision data, BEFORE weekly analyses
    formatted_jd_data = monthly_data.get("formatted_jd_data", "")
    if formatted_jd_data:
        prompt += f"""
## ROLE CONTEXT FOR MONTHLY PERIOD (Job Description Data)

{formatted_jd_data}

### ROLE-BASED MONTHLY ANALYSIS GUIDANCE

### Performance Expectations Framework for Monthly Assessment

**EXCEEDS EXPECTATIONS** (one or more of):
- Scope expansion: Work consistently impacted higher organizational levels than JD specifies
- Innovation: Introduced process improvements or efficiency gains beyond role requirements
- Leadership: Mentored colleagues, led initiatives, or took ownership beyond assigned tasks
- Mission impact: Delivered measurable outcomes beyond routine task completion

**MEETS EXPECTATIONS:**
- Completes all JD-specified responsibilities reliably across the month
- Handles challenges appropriate to role level effectively
- Collaborates within defined scope and demonstrates required competencies

**BELOW EXPECTATIONS:**
- Consistently misses JD-required deliverables or deadlines across weeks
- Requires excessive support for routine role responsibilities
- Struggles with tasks that should be manageable at this role level

### Role-Appropriate Assessment by Seniority

**JUNIOR ROLES (BPS-17 to 18):**
- Focus on: Execution quality, learning agility, growth trajectory
- Expected challenges: Learning systems, needing guidance, time management
- Red flags: Basic skill gaps, inability to complete routine tasks independently

**MID-LEVEL ROLES (BPS-19 to 20):**
- Focus on: Section/wing coordination, process mastery, reliability
- Expected challenges: Cross-team coordination, resource constraints, competing priorities
- Red flags: Excessive need for guidance, inability to work independently

**SENIOR ROLES (BPS-21 to 22):**
- Focus on: Strategic thinking, leadership impact, organizational outcomes
- Expected challenges: Strategic ambiguity, organizational politics, change management
- Red flags: Struggling with tactical execution (should delegate), requiring excessive guidance

### Special Role Scenarios

**MULTIPLE CONCURRENT ROLES:**
- Assess achievements against combined responsibilities from all JDs
- Evaluate workload distribution and prioritization across roles
- Identify role synergies and conflicts
- Consider total workload complexity, not individual roles in isolation

**MID-MONTH ROLE TRANSITIONS:**
- Split assessment: Evaluate work against applicable JD for each period
- Transition credit: Acknowledge learning curve in new role (first 2-3 weeks)
- Proportional evaluation: Weight by time in each role
- Document adaptation quality and early performance indicators

### Authority & Autonomy Assessment

Consider whether employee exercised appropriate decision-making authority for their grade:
- BPS-17 to 18: Work with guidance, escalate major decisions, coordinate within section
- BPS-19 to 20: Make section/wing-level decisions independently, provide guidance to subordinates
- BPS-21 to 22: Make strategic HQ-level decisions, represent organization externally

Monthly patterns to note:
- Consistent appropriate authority usage → Positive indicator
- Pattern of exceeding authority without oversight → Governance concern
- Pattern of under-utilizing authority → Development need or confidence gap

"""

    # Continue with weekly analysis summaries
    prompt += f"""
## WEEKLY ANALYSIS SUMMARIES (AI-Generated from Weekly Reports)
{analyses_section}

## MONTHLY CREDIBILITY AGGREGATION FRAMEWORK

Credibility is assessed at the monthly level by aggregating weekly findings. This is critical because credibility affects achievement scores, performance ratings, and risk assessments.

### Step 1: Aggregate Weekly Credibility Ratings

From the weekly analyses above, count:
- HIGH credibility weeks: ___
- MEDIUM credibility weeks: ___
- LOW credibility weeks: ___

### Step 2: Assess Credibility Trajectory

Determine if credibility improved, declined, or remained stable across the month:
- **IMPROVING:** Earlier weeks had concerns, later weeks show better specificity/realism
- **DECLINING:** Earlier weeks were credible, later weeks show increased exaggeration/credibilitgy concerns
- **STABLE:** Consistent credibility level throughout

### Step 3: Calculate Monthly Credibility Rating

**MONTHLY HIGH CREDIBILITY:**
- All weeks rated HIGH, OR
- Mostly HIGH with clear improvement trajectory in any MEDIUM weeks

**MONTHLY MEDIUM CREDIBILITY:**
- Mixed HIGH/MEDIUM ratings without clear trajectory
- Some LOW weeks but clear improvement demonstrated
- Pattern of vague or unsubstantiated claims without contradictions

**MONTHLY LOW CREDIBILITY:**
- Multiple LOW weeks (2+) without improvement
- Vision data contradictions in 2+ weeks
- Pattern of escalating exaggeration across the month

### Step 4: Apply Timeframe-Based Evaluation

Evaluate claims by the timeframe they occurred:
- Earlier claims: Apply skepticism level appropriate to that period's credibility
- Later claims: If improvement occurred, give more benefit of the doubt
- Document trajectory in your assessment

### Step 5: Monthly Credibility Impact

**Impact Score Adjustments (same as weekly):**
- MONTHLY HIGH: No discount
- MONTHLY MEDIUM: 15% discount on achievement impact scores
- MONTHLY LOW: 40% discount on achievement impact scores

**Risk Level Adjustments:**
- MONTHLY HIGH: No adjustment
- MONTHLY MEDIUM: Increase base risk by one tier
- MONTHLY LOW: Increase base risk by two tiers

**Performance Rating Caps:**
- MONTHLY HIGH: No cap
- MONTHLY MEDIUM: HIGH performance requires strong evidence
- MONTHLY LOW: Maximum MEDIUM performance rating

**Qualifying Language:**
- MONTHLY HIGH: "The employee demonstrated..."
- MONTHLY MEDIUM: "Based on reported activities..."
- MONTHLY LOW: "The employee claims..."

### Step 6: Document Aggregated Findings

Synthesize weekly exaggeration flags into monthly patterns. Note:
- Recurring exaggeration types (superlatives, vague claims, impossible timelines)
- Improvement or regression in reporting quality
- Specific examples that justify the monthly credibility rating

## DATA HANDLING GUIDELINES

### Data Precedence (When Sources Conflict)
1. **Vision system data** (highest priority - objective evidence)
2. **Original employee reports** (primary source)
3. **Weekly AI analyses** (synthesis, may contain interpretation)

When discrepancies exist:
- Vision contradicts reports → Flag, investigate, apply credibility discount
- Weekly analyses differ from reports → Trust reports, note analytical interpretation
- Multiple sources align → Higher confidence in findings

### Temporal Weighting
- **For RECOMMENDATIONS:** Weight recent weeks more heavily (forward planning)
- **For OVERALL EVALUATION:** Weight all weeks equally (balanced assessment)
- **For CREDIBILITY:** Apply timeframe-based evaluation (earlier skepticism if warranted, later trust if improved)

### Data Completeness
If weeks are missing (leave, incomplete data):
- Explicitly state data limitations
- Avoid over-confident conclusions
- Assess based on available data with appropriate caveats
- Note which weeks are missing and impact on analysis confidence

## IMPACT RATING SCALE FOR MONTHLY ACHIEVEMENTS

Rate cumulative/significant achievements using this scale:

**1-3: Individual/Cell/Desk-level Impact**
- Routine task completion patterns
- Personal skill development
- Individual case file maintenance
- THQ/DHQ routine operations

**4-6: Unit/Branch and Section-level Impact**
- Value addition in immediate team
- Process improvements within section
- Coordination across multiple desks/cells
- DHQ/ZHQ coordination activities

**7-8: Wing-level Impact at HQ Facilities**
- Intelligence assessments briefed to senior management
- Coordination with partner LEAs
- Reports delivered to provincial/federal authorities
- Process changes affecting multiple sections
- ZHQ/PHQ/RHQ level coordination

**9-10: IBD HQ-level/Strategic Impact**
- Intelligence products briefed to PMO/Cabinet
- Contributions to federal security directives
- Strategic partnerships with multiple LEAs
- Mission-critical operational successes
- IBD HQ strategic initiatives

**Monthly Application:**
- Rate cumulative impact of achievement clusters, not individual items
- Weight achievements that built upon each other across weeks
- Consider sustained impact vs. one-time achievements
- Apply credibility discounts as determined above

## COMPREHENSIVE MONTHLY ANALYSIS REQUIREMENTS

Complete all analyses in order. The sequence reflects logical dependencies.

### CONTENT SYNTHESIS & VALIDATION

**1. PROGRESS TRENDS ANALYSIS:**

Synthesize weekly patterns into monthly trajectory:

**Performance Trend:**
- IMPROVING: Weekly ratings show upward movement (e.g., MEDIUM→HIGH, or LOW→MEDIUM→MEDIUM)
- DECLINING: Weekly ratings show downward movement
- STABLE: Consistent ratings throughout (note whether stable-high, stable-medium, or stable-low)

**Sentiment Trend:**
- POSITIVE: Employee morale and outlook improved across the month
- NEGATIVE: Increasing frustration, declining confidence, or pessimistic framing
- STABLE: Consistent emotional tone throughout

**Risk Level Pattern:**
- INCREASING: More weeks with HIGH risk, or escalating from LOW→MEDIUM→HIGH
- DECREASING: Risk mitigation evident, fewer HIGH risk weeks over time
- STABLE: Consistent risk profile throughout

**Challenge Resolution Progress:**
- IMPROVED: Challenges from early weeks were addressed/resolved in later weeks
- DECLINED: New challenges emerged or existing ones worsened
- UNCHANGED: Same challenges persisted without progress

**2. MONTHLY ACHIEVEMENTS SYNTHESIS:**

From weekly achievements, identify the MOST SIGNIFICANT for the month:
- Prioritize achievements with highest impact ratings
- Highlight achievements that built upon each other across weeks
- Identify achievement clusters (related accomplishments in same project/area)
- Apply credibility discounts to impact scores as determined above

**Achievement Categories to Consider:**
- Mission-critical deliverables
- Process improvements with lasting impact
- Cross-functional collaboration outcomes
- Skill development demonstrated through work quality
- Leadership/mentorship contributions

**3. RECURRING CHALLENGES ASSESSMENT:**

Identify challenges appearing in 2+ weeks:
- **RESOLVED:** Challenge was addressed and did not recur in later weeks
- **ONGOING:** Challenge persisted throughout the month
- **ADDRESSED:** Challenge was mitigated but not fully resolved
- **WORSENING:** Challenge escalated in severity or impact

**Challenge Analysis Framework:**
- Distinguish internal (organizational) vs. external challenges
- Identify systemic vs. individual-specific challenges
- Assess if challenges are role-appropriate or indicate skill gaps
- Note escalating severity patterns

### PATTERN RECOGNITION

**4. CONSISTENCY ASSESSMENT:**

This assesses PERFORMANCE CONSISTENCY over time, distinct from weekly report consistency scores.

**Task Completion Reliability:**
- HIGH: Planned tasks consistently completed across all weeks
- MEDIUM: Most planned tasks completed, occasional misses
- LOW: Frequent incomplete tasks or missed commitments

**Work Quality Consistency:**
- HIGH: Uniform quality standards maintained throughout
- MEDIUM: Generally consistent with minor quality variations
- LOW: Significant quality fluctuations week-to-week

**Performance Stability:**
- HIGH: Predictable, reliable output level throughout month
- MEDIUM: Some variation but within acceptable range
- LOW: Volatile performance, unpredictable output levels

**Notable Strengths:** Identify 2-3 areas of consistent excellence if applicable
**Notable Weaknesses:** Identify 2-3 areas of inconsistency or concern if applicable

**5. GROWTH INDICATORS ANALYSIS:**

**Complexity of Tasks:**
- INCREASED: Employee took on progressively more complex work
- DECREASED: Task complexity reduced (may indicate role change or capacity issues)
- UNCHANGED: Consistent complexity level appropriate to role

**Skill Development Evidence:**
- HIGH: Clear demonstration of new skills or improved capabilities
- MEDIUM: Some skill growth visible in specific areas
- LOW: No evident skill development during the month

**Confidence Level Change:**
- INCREASED: Growing self-assurance in weekly reports
- DECREASED: Declining confidence or increased uncertainty
- UNCHANGED: Stable confidence level throughout

**Approach to Challenges:**
- MORE PROACTIVE: Anticipating and preventing issues
- MORE REACTIVE: Responding to problems after they occur
- UNCHANGED: Consistent approach throughout

**6. FOCUS AREAS DETERMINATION:**

Identify primary work focus areas based on recurring topics and achievement patterns:

**For Each Focus Area, Assess:**
- Time Investment: HIGH/MEDIUM/LOW based on frequency and depth of engagement
- Priority Level: HIGH/MEDIUM/LOW based on organizational importance and mission alignment

**Strategic Alignment Check:**
- Do focus areas align with organizational goals (PMO priorities, federal security directives)?
- Do focus areas align with wing-specific priorities?
- Do focus areas align with JD responsibilities?

Note any misalignment between employee focus and organizational priorities.

### RISK & CREDIBILITY SYNTHESIS

**7. MONTHLY CREDIBILITY DETERMINATION:**

Apply the Monthly Credibility Aggregation Framework (detailed above).
Document:
- Weekly credibility rating counts
- Credibility trajectory (improving/declining/stable)
- Monthly credibility rating (HIGH/MEDIUM/LOW)
- Specific evidence supporting the rating

**8. MONTHLY RISK ASSESSMENT:**

**Step 1 - Aggregate Situational Risk:**
- Count HIGH/MEDIUM/LOW risk weeks
- Identify risk trends (escalating, de-escalating, stable)
- Note any critical risk events

**Step 2 - Apply Credibility Adjustment:**
- MONTHLY HIGH credibility: No adjustment
- MONTHLY MEDIUM credibility: Increase risk by one tier
- MONTHLY LOW credibility: Increase risk by two tiers

**Step 3 - Document Risk Factors:**
- Significant Risks: Top 2-3 risk factors affecting the employee/projects
- Escalating Risks: Risks that worsened during the month
- Risk Mitigation Recommendations: Specific actions to reduce risk

**Risk Explanation Requirements:**
Provide detailed explanation including:
- Specific evidence from weekly analyses
- Trends observed across the month
- Credibility adjustment rationale if applicable
- Connection to organizational impact

### STRATEGIC SYNTHESIS

**9. ROLE ALIGNMENT & TRANSITION ASSESSMENT:**

**Role Alignment Rating:**
- STRONG ALIGNMENT: Work consistently matches JD responsibilities
- PARTIAL ALIGNMENT: Some work matches JD, some outside scope
- WEAK ALIGNMENT: Significant gaps between JD and actual work

**Stretch Contributions:** Areas where employee exceeded role scope (document for promotion consideration)

**Gaps:** Systematic differences between role requirements and work patterns (document for development planning)

**Transition Analysis (if applicable):**
- Effectiveness of role transition
- Adaptation quality and speed
- Learning curve observations
- Recommendations for transition support

**10. STRATEGIC RECOMMENDATIONS:**

Generate recommendations in priority order:

**Priority Categories:**
1. **HIGH:** Immediate intervention needed (risk mitigation, performance concerns)
2. **MEDIUM:** Should be addressed within next month (development needs, resource requests)
3. **LOW:** Desirable improvements (optimization, growth opportunities)

**Recommendation Types:**
- Resource/support needs identified across weeks
- Development opportunities based on skill gaps
- Workload adjustments if sustainability concerns noted
- Recognition/advancement if exceptional performance demonstrated
- Verification steps if credibility concerns exist (supportive tone, max 30-40% of recommendations)

**Crafting Actionable Recommendations:**
- Technical skills gap → "Provide [specific tool/system] training"
- Process knowledge gap → "Share documentation/SOPs for [specific process]"
- Soft skills gap → "Assign mentor for [specific skill]"
- Resource constraint → "Prioritize [specific resource request] to enable [outcome]"

**11. PERFORMANCE ASSESSMENT SYNTHESIS:**

**Performance Priority Framework** (highest to lowest importance):
1. **Consistency** (reliability across weeks, meeting commitments, predictable delivery)
2. **Innovation** (proactive initiative, process improvements)
3. **Strategic alignment** (work supports wing/organizational mission)
4. **Quality** (accuracy, thoroughness, professionalism)
5. **Collaboration** (effective teamwork and coordination)

**NOT a ranking factor:** Output volume—fewer high-quality, mission-aligned deliverables outweigh high-volume, lower-quality work.

**Monthly Performance Rating Criteria:**

**HIGH Performance (Monthly):**
- Consistent, reliable delivery across ALL weeks
- Work aligns with organizational mission objectives
- High-quality outputs with minimal errors
- Effective challenge management and adaptive planning
- Excellence indicators appropriate to role level demonstrated

**MEDIUM Performance (Monthly):**
- Generally reliable with occasional gaps
- Adequate quality with minor inconsistencies
- Meets baseline JD requirements
- Reactive rather than proactive approach
- Some weeks underperformed relative to others

**LOW Performance (Monthly):**
- Significant inconsistencies across weeks
- Quality concerns or repeated errors
- Work misaligned with mission priorities
- Struggles with routine responsibilities

**Apply credibility cap:**
- MONTHLY MEDIUM credibility + would-be HIGH → Requires strong evidence
- MONTHLY LOW credibility → Maximum MEDIUM rating

**12. MONTHLY SUMMARY:**

Synthesize all findings into a cohesive 3-5 sentence executive summary:
- Overall performance trajectory
- Most significant achievements (with impact context)
- Key challenges and their status
- Risk profile summary
- Forward-looking outlook

This summary should stand alone as an executive briefing.

## EDGE CASE HANDLING

**Exceptional Monthly Performance:**
If performance is exceptional across all dimensions:
- Celebrate and document thoroughly with specific examples
- Verify against Vision data [] data patterns (high performance requires high evidence)
- Check for consistency across ALL weeks (truly exceptional, or one standout week?)
- Note credibility assessment (exceptional claims need exceptional evidence)
- Document for promotion/recognition consideration

**Consistently Low Monthly Performance:**
If performance is low across multiple dimensions:
- Document clearly and objectively for performance management
- Focus recommendations on specific, actionable development steps
- Include escalation recommendation: "Recommend manager intervention and formal performance improvement plan"
- Identify root causes from patterns (skill gaps, resource constraints, role misfit)
- Maintain professional, fact-based tone

**Mid-Month Role Changes:**
- Explicitly note and evaluate each period against applicable JD
- Highlight adaptability during transition
- Weight performance by time in each role
- Apply learning curve expectations for new role portion

**Sparse Data (Missing Weeks):**
- Explicitly state which weeks are missing and why if known
- Acknowledge impact on analysis confidence
- Avoid over-confident conclusions
- Recommend data completion if ongoing issue

---

## FINAL OUTPUT REQUIREMENTS

**Output Validation Rules:**
- Begin output with "{{" and end with "}}"
- Include all required top-level fields: progress_trends, monthly_achievements, recurring_challenges, consistency_assessment, growth_indicators, focus_areas, monthly_risk_assessment, strategic_recommendations, monthly_summary
- Use only allowed enum values (improving/declining/stable, high/medium/low, etc.)
- All arrays must contain valid entries or be empty arrays []
- No hyphens in compound words
- No first-person references
- Output valid JSON only with no additional commentary, preamble, or explanation

**Cross-Functional Impact Recognition:**
All collaboration types are equally valued:
- Leading cross-functional initiatives (coordinating across Wings/Sections)
- Contributing specialized expertise to other teams
- Mentoring/knowledge-sharing activities
- Process improvements benefiting multiple units

Proceed with your structured JSON analysis now.
"""

    
    return prompt
