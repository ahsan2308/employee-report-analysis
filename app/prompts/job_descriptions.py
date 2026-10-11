"""Format job descriptions for weekly, monthly and quarterly analysis prompts."""
from typing import Dict, Any, List
from datetime import date
from app.domain.periods import quarter_of_month


def format_job_descriptions_for_weekly_prompt(
    jds: List[Dict[str, Any]]
) -> str:
    """
    Format job description(s) for weekly analysis prompt.
    
    Handles single JD, concurrent JDs, and empty cases.
    
    Args:
        jds: List of JD dictionaries from get_employee_job_descriptions_for_period()
        
    Returns:
        Formatted string for prompt insertion
    """
    # Empty check
    if not jds or len(jds) == 0:
        return ""
    
    # Sort JDs by assigned_date (oldest first = primary role)
    sorted_jds = sorted(jds, key=lambda j: j.get("assigned_date", date.min))
    
    # Single JD case
    if len(sorted_jds) == 1:
        jd = sorted_jds[0]
        assigned_date = jd.get("assigned_date")
        assigned_date_str = assigned_date.isoformat() if hasattr(assigned_date, "isoformat") else str(assigned_date)
        jd_text = jd.get("job_description", "No job description available")
        
        return f"""
## EMPLOYEE JOB DESCRIPTION

Effective Since: {assigned_date_str}

Job Description:\n{jd_text}
"""
    
    # Multiple concurrent JDs case
    formatted_text = """
## EMPLOYEE JOB DESCRIPTIONS

The employee currently holds multiple roles:

"""
    
    for i, jd in enumerate(sorted_jds):
        assigned_date = jd.get("assigned_date")
        assigned_date_str = assigned_date.isoformat() if hasattr(assigned_date, "isoformat") else str(assigned_date)
        jd_text = jd.get("job_description", "No job description available")
        
        
        formatted_text += f"""
### Job Description #{i+1} (Effective since {assigned_date_str}):
{jd_text}

"""
    
    # Add analysis guidance for concurrent roles
    formatted_text += """
ANALYSIS GUIDANCE:
- Evaluate achievements and challenges against expectations from BOTH roles
- Consider workload distribution across multiple responsibilities
- Assess time management and prioritization given dual role requirements
"""
    
    return formatted_text



def format_job_descriptions_for_monthly_prompt(
    jd_report_mapping: Dict[str, Any]
) -> str:
    """
    Format job description(s) with temporal groupings for monthly analysis prompt.
    
    Handles stable JD, transitions, concurrent roles, and unmapped reports.
    
    Args:
        jd_report_mapping: Output from map_reports_to_jds()
        
    Returns:
        Formatted string for prompt insertion
    """
    # Empty check
    if not jd_report_mapping or not jd_report_mapping.get("jd_groups"):
        return ""
    
    jd_groups = jd_report_mapping.get("jd_groups", [])
    unmapped_reports = jd_report_mapping.get("unmapped_reports", [])
    
    num_groups = len(jd_groups)
    
    # Case 1: Stable JD configuration (one group, can be single or concurrent JDs)
    if num_groups == 1:
        group = jd_groups[0]
        effective_dates = group.get("effective_dates", {})
        start = effective_dates.get("start")
        end = effective_dates.get("end")
        
        start_str = start.isoformat() if hasattr(start, "isoformat") else str(start)
        end_str = end.isoformat() if hasattr(end, "isoformat") else str(end)
        
        jd_ids = group.get("jd_ids", [])
        jd_texts = group.get("jd_texts", [])
        reports = group.get("reports", [])
        
        # Single JD - simple format
        if len(jd_ids) == 1:
            jd_text = jd_texts[0]
            
            formatted_text = f"""
## EMPLOYEE JOB DESCRIPTION

Role has been stable throughout the month.

Effective Period: {start_str} to {end_str}

Job Description:\n{jd_text}
"""
        else:
            # Multiple concurrent JDs that remained stable throughout
            formatted_text = f"""
## EMPLOYEE JOB DESCRIPTIONS

The employee held multiple concurrent roles that remained stable throughout the month.

Effective Period: {start_str} to {end_str}

"""
            for j, jd_text in enumerate(jd_texts):
                formatted_text += f"""
### Job Description #{j+1}:
{jd_text}

"""
            
            # Add concurrent role guidance
            formatted_text += """
ANALYSIS GUIDANCE:
- Evaluate workload management across all roles
- Assess prioritization and time allocation
- Consider cumulative expectations from all JDs
- Identify potential conflicts or synergies between roles
"""
        
        # Handle unmapped reports if any
        if unmapped_reports:
            formatted_text += _format_unmapped_reports_section(unmapped_reports)
        
        return formatted_text
    
    # Multiple groups = transitions or changing concurrent configurations
    # Check if we have transitions or concurrent roles
    has_concurrent = any(len(group.get("jd_ids", [])) > 1 for group in jd_groups)
    has_transition = num_groups > 1 and not has_concurrent
    
    # Case 2: JD Transition (multiple groups, each with single JD)
    if has_transition:
        formatted_text = """
## EMPLOYEE JOB DESCRIPTIONS AND ROLE TRANSITIONS

The employee's role changed during this month:

"""
        
        for i, group in enumerate(jd_groups):
            effective_dates = group.get("effective_dates", {})
            start = effective_dates.get("start")
            end = effective_dates.get("end")
            
            start_str = start.isoformat() if hasattr(start, "isoformat") else str(start)
            end_str = end.isoformat() if hasattr(end, "isoformat") else str(end)
            
            jd_text = group.get("jd_texts", ["No job description available"])[0]
            reports = group.get("reports", [])
            
            # Determine role label
            is_last = (i == num_groups - 1)
            role_label = "Current Role" if is_last else "Previous Role"
            
            formatted_text += f"""
### PERIOD {i+1}: {start_str} to {end_str}
{role_label}:
{jd_text}

Reports from this period:
"""
            
            # List report week ranges
            for report in reports:
                week_start = report.get("week_start_date")
                week_end = report.get("week_end_date")
                
                # Format week range
                if week_start and week_end:
                    start_str = week_start.isoformat() if hasattr(week_start, "isoformat") else str(week_start)
                    end_str = week_end.isoformat() if hasattr(week_end, "isoformat") else str(week_end)
                    formatted_text += f"- Report for week {start_str} to {end_str}\n"
                else:
                    # Fallback to original date if week range not available
                    report_date = report.get("date")
                    date_str = report_date.isoformat() if hasattr(report_date, "isoformat") else str(report_date)
                    formatted_text += f"- Report dated {date_str}\n"
            
            formatted_text += "\n"
        
        # Add transition guidance
        formatted_text += """
ANALYSIS GUIDANCE:
- Evaluate each report against the JD applicable during that time period
- Assess transition effectiveness - how well did the employee adapt?
- Consider if achievements in Period 1 helped prepare for Period 2
- Identify knowledge/skill gaps during transition
- Note performance trajectory across the role change
"""
        
        # Handle unmapped reports
        if unmapped_reports:
            formatted_text += _format_unmapped_reports_section(unmapped_reports)
        
        return formatted_text
    
    # Case 3: Complex scenario (transitions with concurrent roles)
    # If we reach here, num_groups > 1 (guaranteed by Case 1)
    formatted_text = """
## EMPLOYEE JOB DESCRIPTIONS

The employee's role configuration changed during this month:

"""
    
    for i, group in enumerate(jd_groups):
        effective_dates = group.get("effective_dates", {})
        start = effective_dates.get("start")
        end = effective_dates.get("end")
        
        start_str = start.isoformat() if hasattr(start, "isoformat") else str(start)
        end_str = end.isoformat() if hasattr(end, "isoformat") else str(end)
        
        jd_ids = group.get("jd_ids", [])
        jd_texts = group.get("jd_texts", [])
        reports = group.get("reports", [])
        
        # Determine period label
        if len(jd_ids) > 1:
            period_label = f"CONCURRENT PERIOD {i+1}"
        else:
            period_label = f"PERIOD {i+1}"
        
        formatted_text += f"### {period_label}: {start_str} to {end_str}\n"
        
        # Format each JD in this period
        for j, jd_text in enumerate(jd_texts):
            if len(jd_texts) > 1:
                formatted_text += f"Job Description #{j+1}:\n{jd_text}\n\n"
            else:
                formatted_text += f"Job Description:\n{jd_text}\n\n"
        
        # List reports from this period
        role_context = "holding both roles" if len(jd_ids) > 1 else "this period"
        formatted_text += f"Reports from {role_context}:\n"
        
        # Use week ranges
        for report in reports:
            week_start = report.get("week_start_date")
            week_end = report.get("week_end_date")
            
            # Format week range
            if week_start and week_end:
                start_str = week_start.isoformat() if hasattr(week_start, "isoformat") else str(week_start)
                end_str = week_end.isoformat() if hasattr(week_end, "isoformat") else str(week_end)
                formatted_text += f"- Report for week {start_str} to {end_str}\n"
            else:
                # Fallback to original date if week range not available
                report_date = report.get("date")
                date_str = report_date.isoformat() if hasattr(report_date, "isoformat") else str(report_date)
                formatted_text += f"- Report dated {date_str}\n"
        
        formatted_text += "\n"
    
    # Add appropriate guidance
    if has_concurrent:
        formatted_text += """
ANALYSIS GUIDANCE:
- Evaluate workload management across all roles
- Assess prioritization and time allocation
- Consider cumulative expectations from all JDs
- Identify potential conflicts or synergies between roles
"""
    
    # Handle unmapped reports
    if unmapped_reports:
        formatted_text += _format_unmapped_reports_section(unmapped_reports)
    
    return formatted_text



def _format_unmapped_reports_section(unmapped_reports: List[Dict[str, Any]]) -> str:
    """
    Helper function to format unmapped reports section.
    
    Args:
        unmapped_reports: List of report dictionaries without applicable JD
        
    Returns:
        Formatted unmapped reports section
    """
    formatted_text = """

## REPORTS WITHOUT JOB DESCRIPTION

The following reports were submitted before formal JD assignment:
"""
    
    for report in unmapped_reports:
        week_start = report.get("week_start_date")
        week_end = report.get("week_end_date")
        
        # Use week range if available
        if week_start and week_end:
            start_str = week_start.isoformat() if hasattr(week_start, "isoformat") else str(week_start)
            end_str = week_end.isoformat() if hasattr(week_end, "isoformat") else str(week_end)
            formatted_text += f"- Report for week {start_str} to {end_str}\n"
        else:
            # Fallback to original date
            report_date = report.get("date")
            date_str = report_date.isoformat() if hasattr(report_date, "isoformat") else str(report_date)
            formatted_text += f"- Report dated {date_str}\n"
    
    formatted_text += """
ANALYSIS GUIDANCE:
- Evaluate based on general role expectations
- Note this may indicate onboarding/transition period
- Focus on observable work quality rather than role alignment
"""
    
    return formatted_text



def format_job_descriptions_for_quarterly_prompt(
    jd_analysis_mapping: Dict[str, Any]
) -> str:
    """
    Format job description(s) with career progression context for quarterly analysis prompt.
    
    Handles stable JD and multiple role transitions with strategic framing.
    
    Args:
        jd_analysis_mapping: Output from map_reports_to_jds() called on weekly analyses
        
    Returns:
        Formatted string for prompt insertion
    """
    # Empty check
    if not jd_analysis_mapping or not jd_analysis_mapping.get("jd_groups"):
        return ""
    
    jd_groups = jd_analysis_mapping.get("jd_groups", [])
    num_groups = len(jd_groups)
    
    # Case 1: Stable JD configuration (one group, can be single or concurrent JDs)
    if num_groups == 1:
        group = jd_groups[0]
        effective_dates = group.get("effective_dates", {})
        start = effective_dates.get("start")
        end = effective_dates.get("end")
        
        start_str = start.isoformat() if hasattr(start, "isoformat") else str(start)
        end_str = end.isoformat() if hasattr(end, "isoformat") else str(end)
        
        jd_ids = group.get("jd_ids", [])
        jd_texts = group.get("jd_texts", [])
        report_count = len(group.get("reports", []))
        
        # Extract quarter info from dates
        quarter_num = "Q1"
        if hasattr(start, "month"):
            quarter_num = f"Q{quarter_of_month(start.month)}"
        year_num = start.year if hasattr(start, "year") else "Unknown"
        
        # Single JD - simple format
        if len(jd_ids) == 1:
            jd_text = jd_texts[0]
            
            formatted_text = f"""
## EMPLOYEE JOB DESCRIPTION

Role has remained stable throughout the quarter.

Effective Period: {quarter_num} {year_num} ({start_str} to {end_str})

Job Description:\n{jd_text}

Total weekly reports in this period: {report_count}
"""
        else:
            # Multiple concurrent JDs that remained stable throughout
            formatted_text = f"""
## EMPLOYEE JOB DESCRIPTIONS

The employee held multiple concurrent roles that remained stable throughout the quarter.

Effective Period: {quarter_num} {year_num} ({start_str} to {end_str})

"""
            for j, jd_text in enumerate(jd_texts):
                formatted_text += f"""
### Job Description #{j+1}:
{jd_text}

"""
            
            formatted_text += f"""
Total weekly reports in this period: {report_count}

ANALYSIS GUIDANCE:
- Evaluate sustained workload management across all roles over the quarter
- Assess long-term prioritization and time allocation patterns
- Consider cumulative expectations and performance across all JDs
- Identify how the employee balanced multiple responsibilities over time
- Evaluate skill development in handling concurrent roles
"""
        
        return formatted_text
    
    # Case 2: Role Progression (multiple transitions or concurrent roles)
    # If we reach here, num_groups > 1
    # Count number of unique JD configurations for context
    transition_count = num_groups - 1 if num_groups > 1 else 0
    
    formatted_text = f"""
## EMPLOYEE JOB DESCRIPTIONS AND CAREER PROGRESSION

The employee experienced {transition_count} role transition(s) during this quarter:

### ROLE TIMELINE

"""
    
    for i, group in enumerate(jd_groups):
        effective_dates = group.get("effective_dates", {})
        start = effective_dates.get("start")
        end = effective_dates.get("end")
        
        start_str = start.isoformat() if hasattr(start, "isoformat") else str(start)
        end_str = end.isoformat() if hasattr(end, "isoformat") else str(end)
        
        jd_texts = group.get("jd_texts", [])
        reports = group.get("reports", [])
        report_count = len(reports)
        
        # Format phase header
        formatted_text += f"PHASE {i+1}: {start_str} to {end_str}\n"
        
        # Format JD(s) for this phase
        if len(jd_texts) > 1:
            # Concurrent roles in this phase
            formatted_text += "Concurrent Roles:\n"
            for j, jd_text in enumerate(jd_texts):
                formatted_text += f"Job Description #{j+1}:\n{jd_text}\n"
        else:
            # Single role
            formatted_text += f"Job Description:\n{jd_texts[0]}\n"
        
        formatted_text += f"\nWeekly reports from this phase: {report_count} reports\n"
        
        # Optionally list week ranges for each report
        if report_count > 0:
            formatted_text += "Coverage:\n"
            for report in reports:
                week_start = report.get("week_start_date")
                week_end = report.get("week_end_date")
                
                if week_start and week_end:
                    start_str = week_start.isoformat() if hasattr(week_start, "isoformat") else str(week_start)
                    end_str = week_end.isoformat() if hasattr(week_end, "isoformat") else str(week_end)
                    formatted_text += f"  - Week {start_str} to {end_str}\n"
        
        # Add separator between phases
        if i < num_groups - 1:
            formatted_text += "\n---\n\n"
        else:
            formatted_text += "\n"
    
    # Add strategic analysis guidance
    formatted_text += """
### STRATEGIC ANALYSIS GUIDANCE

1. ROLE PROGRESSION ASSESSMENT:
   - Analyze career trajectory across these role changes
   - Determine if transitions represent promotions, lateral moves, or temporary assignments
   - Evaluate readiness for each new role based on performance in previous roles

2. TRANSITION IMPACT ANALYSIS:
   - Assess adaptation effectiveness for each transition
   - Identify performance dips or spikes coinciding with role changes
   - Evaluate whether transitions required additional support

3. CUMULATIVE CAPABILITY DEVELOPMENT:
   - Track skill development across different roles
   - Identify transferable skills leveraged across positions
   - Assess breadth of experience gained

4. PERFORMANCE CONSISTENCY:
   - Compare performance stability across different role contexts
   - Identify if certain role types align better with employee strengths

5. FUTURE READINESS:
   - Based on performance across multiple roles, assess readiness for advancement
   - Identify optimal role type based on demonstrated strengths
"""
    
    return formatted_text
