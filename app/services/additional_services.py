from typing import Dict, Any, List
from datetime import date
from app.core.logger import logger

def _truncate_content_value(value: Any, max_length: int = 300) -> str:
    """
    Truncate a content value to prevent context overflow.
    
    Args:
        value: The value to truncate (can be any type)
        max_length: Maximum character length for the value
        
    Returns:
        Truncated string representation with ellipsis if needed
    """
    if value is None:
        return ""
    
    value_str = str(value)
    
    if len(value_str) <= max_length:
        return value_str
    
    # Truncate and add ellipsis
    return value_str[:max_length] + "..."

def filter_vision_data(vision_data: Dict[str, Any], sub_entity_descriptions: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Filter vision data to remove zero-value sub-entities and add descriptions.
    
    Args:
        vision_data: The vision data as returned by get_employee_vision_data
        sub_entity_descriptions: A dictionary mapping sub-entity names to their descriptions
        
    Returns:
        Filtered vision data with descriptions added
    """
    if not vision_data:
        return {}

    if not sub_entity_descriptions:
        # Descriptions for all sub-entities
        sub_entity_descriptions = {
            # Persons
            "Persons": "New Person records created",
            "Numbers": "Numbers linked with Persons (Mobile, Residence, Office, Intercom etc.)",
            "Pictures": "Pictures uploaded with Persons (Profile Pictures)",
            "Addresses": "Addresses linked with Persons (Present, Permanent, Native, Office etc.)",
            "Features": "Physical features added with Persons (Complexion, Height, Face description, Appearance etc.)",
            "Skills": "Skills added with Persons (Also include Langauges, Hobbies, Interests)",
            "Education": "Education details linked with persons",
            "Profession": "Profession / Work history details linked with persons",
            "Docs": "Identity documents, Passports, Licenses, Bank Accounts, Tax certificates etc.",
            "Doc Attach": "File attachments for identity documents (Passport, Licenses, Bank Accounts, Tax certificates etc.)",
            "POIs": "Persons marked as Person of Interest",
            "Labels": "Persons marked with specific labels",
            "Groups": "Persons marked with specific groups (muli-level labeling)",
            "History Sheet": "History sheet / organized and comprehensive details added with persons",
            "HS Attachments": "History sheet attachments added with persons",
            "LDs": "Lowdown profiles created for persons",
            "Crime Status": "Crime Status details added with persons (Proscribed, Arrested, On bail, etc.)",
            "Lookup": "Lookup details added with persons (Related to wanted criminals)",
            "Special Reports": "Special report attachments added with persons",
            
            # Organizations
            "Orgs": "New organization records created",
            "OOIs": "Organizations marked as Organization of Interest",
            "Particulars": "Particulars / organized and comprehensive details added with organizations",
            "Attachments": "Attachments uploaded with organization Particulars",
            "OPs": "Organization profiles created",
            "Groups": "Long term categorization of an organization (e.g. its type, etc.)",
            "Label": "Short term (task-specific) categorization of the organization",
            "Lookup": "A general purpose repository where records are stored for later reference, usually includes generic fields like Name, Description, Reference/Purpose of Entry, etc.",
            "Special Reports": "On-demand reports which are created on special request from the HQ and contain information specific to a subject as requested by the authority.",

            # Links
            "Per-Per": "Persons linked with another Person (Family, Friends, Allies etc.)",
            "Per-Org": "Persons linked with Organizations (with Portfolio like Chairman, Vice chairman etc.)",
            "Per-Event": "Persons linked with Events (Participants, Organizers, Involved, Arrested etc.)",
            "Per-Activity": "Persons linked with Activities (Participants, Organizers, Involved etc.)",
            "Per-Case": "Persons linked with Cases (Complainant, Accused, Arrested etc.)",
            "Per-Task": "Persons linked with Tasks (For reference)",
            "Per-News Report": "Persons linked with News / Media reports",
            "Per-Correspondence": "Persons linked with Correspondence (For reference)",
            "Org-Event": "Organizations linked with Events ((Participants, Organizers, Associated, Claimed etc.)",
            "Org-Task": "Organizations linked with Tasks",
            "Org-Activity": "Organizations linked with Activities (Participants, Organizers etc.)",
            "Org-News Report": "Organizations linked with News / Media reports",
            "Org-Case": "Organizations linked with Cases",
            "Org-Correspondence": "Organizations linked with correspondences",
            "Event-Case": "Events linked with cases",
            "Event-Activity": "Events linked with activities",
            "Event-Event": "Events linked with events",
            "Event-News Report": "Events linked with news / media reports",
            "Event-Task": "Events linked with tasks",
            "Event-Correspondence": "Events linked with correspondences",
            "Activity-Case": "Activties linked with Cases",
            "Activity-News Report": "Activties linked with News / Media reports",
            "Activity-Task": "Activties linked with Tasks",
            "Activity-Correspondence": "Activties linked with Correspondences",
            "Task-Correspondence": "Tasks linked with Correspondences",
            "Task-Case": "Tasks linked with Cases",
            "Task-News Report": "Tasks linked with News / Media reports",
            "Correspondence-Case": "Correspondences linked with Cases",
            "Case-News Report": "Cases linked with News / Media reports",
            
            # Tasks
            "Tasks": "New Tasks created",
            "Task Updates": "Updates added with Tasks",
            "Task Attachments": "Attachments added with Task Updates",
            "Assigned/CC": "Tasks assigned/CCed by the employee",
            
            # Correspondence
            "DFA": "Correspondence created with status as Draft",
            "Correspondence": "Correspondence created with status as Sent",
            "Notings": "Notings added with correspondence",
            "Attachments": "Attachments added with correspondence",
            
            # Events
            "Events": "Event records created (Incidents, Protests, Strikes, Press conferences, etc.)",
            "EOIs": "Events marked as Event of Interest",
            "Information": "Information / organized and comprehensive details added with events",
            "Labels": "Events marked with specific labels",
            "Groups": "Events marked with specific groups (muli-level labeling)",
            "Special Reports": "Special report attachments uploaded with events",
            "Attachments": "Attachments uploaded with events",
            
            # Activities and Cases
            "Activities": "Activities created (Minor events, Meetings / Movements of politicians, diplomats etc.)",
            "Activity Information": "Information / organized and comprehensive details added with activities",
            "Activity Attachments": "Information attachments added with activities",
            "Cases": "FIR details (Police station, FIR number, Location coordinates)",
            "Case Attachments": "Attachments added with Cases",
            
            # Media
            "Issues": "New current issues created e.g. Corruption, Governance, Covid, etc.",
            "Issues Briefs": "Briefs (description) added with current issues",
            "Old Sit-Rep": "Situation report attachments related to issues added",
            "News/Media Reports": "News / Media reports created e.g. Talk show record, Import news clippings, etc.",
            "News/Media Reports Briefs": "Briefs added with news / media reports",
            "SM Profiles": "Social media profiles added",
            "SM Attachments": "Profile pictures added with social media profiles",

            # PER (Performance Evaluation Reports)
            "Initiated": "PER initiated by HR department and sent to Reporting Officer (RO)",
            "Drafted as RO": "PER drafted and saved by Reporting Officer (RO)",
            "Received as RO": "PER received by Reporting Officer (RO) for review or action",
            "Submitted as RO": "PER submitted by Reporting Officer (RO) after completion",
            "Received as CSO2": "PER received by Counter Signing Officer 2 (CSO2) for review",
            "Recieved as CSO1": "PER received by Counter Signing Officer 1 (CSO1) for review",
            "Submitted as CSO1": "PER submitted by Counter Signing Officer 1 (CSO1) after review",
            "Submitted as CSO2": "PER submitted by Counter Signing Officer 2 (CSO2) after review",

            # Nadra
            "Files Uploaded": "Files containing Citizenship Verification requests by NADRA",
            "Requests": "NADRA person verification requests added",
            "Forwarded": "NADRA person verification requests frowardred to concernd field offices of IB",
            "Notings": "Notings added with NADRA person verification requests",
            "Feedbacks": "Feedbacks received from concernd field offices of IB for NADRA person verification requests",
            "VeriSys": "CNIC details viewed / retrieved from Nadra via Live Link",
            "Family Tree": "Family tree details viewed / retrieved from Nadra via Live Link"
        }
    
    result = {
        "date_context": vision_data.get("date_context", {}),
        "current_data": [],
        "previous_data": [],
        "weeks_data": [],
        "months_data": []
    }
    
    # Handle weekly format
    if "current_data" in vision_data or "previous_data" in vision_data:
        if "current_data" in vision_data:
            result["current_data"] = _process_entity_data(vision_data["current_data"], sub_entity_descriptions)
        if "previous_data" in vision_data:
            result["previous_data"] = _process_entity_data(vision_data["previous_data"], sub_entity_descriptions)
        return result

    # Handle monthly format (weeks_data)
    if "weeks_data" in vision_data:
        processed_weeks = []
        for week in vision_data["weeks_data"]:
            processed_activities = _process_entity_data(week.get("activities", []), sub_entity_descriptions)
            if processed_activities:
                processed_weeks.append({
                    "week_number": week.get("week_number"),
                    "iso_week": week.get("iso_week"),
                    "activities": processed_activities
                })
        result["weeks_data"] = processed_weeks
        return result
    
    # Handle quarterly format (months_data with nested weeks_data)
    if "months_data" in vision_data:
        processed_months = []
        for month in vision_data["months_data"]:
            # Create a temporary structure for processing this month's weeks_data
            month_data = {
                "date_context": month.get("date_context", {}),
                "weeks_data": month.get("weeks_data", [])
            }
            
            # Process the month's weeks_data using the monthly format logic
            filtered_month = filter_vision_data(month_data)
            
            # Only include months with non-empty weeks_data
            if filtered_month.get("weeks_data"):
                processed_months.append({
                    "month_name": month.get("month_name", "Unknown"),
                    "date_context": month.get("date_context", {}),
                    "weeks_data": filtered_month.get("weeks_data", [])
                })
        
        result["months_data"] = processed_months
        return result

    return result

def _process_entity_data(entity_data: List[Dict[str, Any]], sub_entity_descriptions: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Process a list of entity data items, filtering zero values and adding descriptions.
    
    Args:
        entity_data: List of entity data items
        sub_entity_descriptions: Dictionary mapping sub-entity names to descriptions
        
    Returns:
        Processed entity data list
    """
    processed_data = []
    
    for item in entity_data:
        # Skip processing if no sub_entities
        if not item.get("sub_entities"):
            continue
            
        # Create a new sub_entities dict with only non-zero values and added descriptions
        filtered_sub_entities = {}
        has_non_zero = False
        
        for sub_entity, value in item["sub_entities"].items():
            if value != 0:
                has_non_zero = True
                # Include sub-entity even if it doesn't have a description
                description = sub_entity_descriptions.get(sub_entity, "")
                filtered_sub_entities[sub_entity] = {
                    "value": value,
                    "description": description
                }
        
        # Skip this entity if all values were zero
        if not has_non_zero:
            continue
            
        # Create new item with filtered sub_entities
        new_item = item.copy()
        new_item["sub_entities"] = filtered_sub_entities
        processed_data.append(new_item)
    
    return processed_data

def format_vision_data_for_weekly_analysis_prompt(
    vision_data: Dict[str, Any], 
    max_content_items_per_entity: int = 5,
    max_content_item_length: int = 300
) -> str:
    """
    Format filtered vision data into a string representation suitable for prompt inclusion.
    Integrates sub_entities_content for each sub-entity, limiting the number of entities to show.
    
    Args:
        vision_data: Filtered vision data with descriptions
        max_content_items_per_entity: Maximum number of entities to show per sub-entity's content list
        max_content_item_length: Maximum character length for each content item value
        
    Returns:
        Formatted string for inclusion in prompts
    """
    if not vision_data:
        return ""

    def format_sub_entity_content(sub_entity, item):
        content = item.get("sub_entities_content", {})
        entity_items = content.get(sub_entity, [])
        if not entity_items:
            return ""
        lines = []
        display_count = min(len(entity_items), max_content_items_per_entity)
        for entry in entity_items[:display_count]:
            if entry:
                # Truncate each value to prevent context overflow
                entry_str = ", ".join(
                    f"{k}: {_truncate_content_value(v, max_content_item_length)}" 
                    for k, v in entry.items() if v
                )
                if entry_str:
                    lines.append(f"      ---> {entry_str}")  
        if len(entity_items) > max_content_items_per_entity:
            lines.append(f"      ---> and {len(entity_items) - max_content_items_per_entity} more...")
        if lines:
            return "\n".join(lines)
        return ""

    formatted_text = ""

    # Handle weekly format
    if vision_data.get("current_data") or vision_data.get("previous_data"):
        if vision_data.get("current_data"):
            formatted_text += "\nCurrent Report Period Activity Data:\n"
            for item in vision_data["current_data"]:
                formatted_text += f"\n- Time Period: {item.get('from_date')} to {item.get('to_date')}\n"
                formatted_text += f"  Main Activity: {item.get('main_entity')}\n"
                formatted_text += "  Details:\n"
                
                for sub_entity, data in item.get("sub_entities", {}).items():
                    formatted_text += f"    - Number of {sub_entity}: {data['value']} ({data['description']})\n"
                    sub_content = format_sub_entity_content(sub_entity, item)
                    if sub_content:
                        formatted_text += f"{sub_content}\n"
        if vision_data.get("previous_data"):
            formatted_text += "\nHistorical Activity Data:\n"
            for item in vision_data["previous_data"]:
                formatted_text += f"\n- Time Period: {item.get('from_date')} to {item.get('to_date')}\n"
                formatted_text += f"  Main Activity: {item.get('main_entity')}\n"
                formatted_text += "  Details:\n"
                
                for sub_entity, data in item.get("sub_entities", {}).items():
                    formatted_text += f"    - Number of {sub_entity}: {data['value']} ({data['description']})\n"
                    sub_content = format_sub_entity_content(sub_entity, item)
                    if sub_content:
                        formatted_text += f"{sub_content}\n"
        return formatted_text

    return formatted_text

def format_vision_data_for_monthly_analysis_prompt(
    vision_data: Dict[str, Any],
    max_content_items_per_entity: int = 5,
    max_content_item_length: int = 250
) -> str:
    """
    Format filtered vision data into a string representation suitable for monthly analysis prompt.
    Displays week-wise activity data, efficiently using the weekly format logic, but labels each section as "Week N".
    
    Args:
        vision_data: Filtered vision data with descriptions
        max_content_items_per_entity: Maximum number of entities to show per sub-entity's content list
        max_content_item_length: Maximum character length for each content item value (default: 250)
        
    Returns:
        Formatted string for inclusion in monthly analysis prompts
    """

    logger.info(f"Formatting vision data for monthly analysis: {vision_data.keys()}")
    if not vision_data:
        return ""

    def format_sub_entity_content(sub_entity, item):
        content = item.get("sub_entities_content", {})
        entity_items = content.get(sub_entity, [])
        if not entity_items:
            return ""
        lines = []
        display_count = min(len(entity_items), max_content_items_per_entity)
        for entry in entity_items[:display_count]:
            if entry:
                # Truncate each value to prevent context overflow
                entry_str = ", ".join(
                    f"{k}: {_truncate_content_value(v, max_content_item_length)}" 
                    for k, v in entry.items() if v
                )
                if entry_str:
                    lines.append(f"      ---> {entry_str}")
        if len(entity_items) > max_content_items_per_entity:
            lines.append(f"      ---> and {len(entity_items) - max_content_items_per_entity} more...")
        if lines:
            return "\n".join(lines)
        return ""
    
    formatted_text = ""

    # Handle monthly format (weeks_data)
    if vision_data.get("weeks_data"):
        for week in vision_data["weeks_data"]:
            week_number = week.get("week_number")
            activities = week.get("activities", [])
            if activities:
                from_date = activities[0].get('from_date')
                to_date = activities[0].get('to_date')
                formatted_text += f"\nWeek {week_number} Activity Data ({from_date} to {to_date}):\n"
                for item in activities:
                    formatted_text += f"  Main Activity: {item.get('main_entity')}\n"
                    formatted_text += "  Details:\n"
                    for sub_entity, data in item.get("sub_entities", {}).items():
                        formatted_text += f"    - Number of {sub_entity}: {data['value']} ({data['description']})\n"
                        sub_content = format_sub_entity_content(sub_entity, item)
                        if sub_content:
                            formatted_text += f"{sub_content}\n"
        return formatted_text

    return formatted_text

def format_vision_data_for_quarterly_analysis_prompt(
    vision_data: Dict[str, Any], 
    max_content_items_per_entity: int = 10,
    max_content_item_length: int = 200
) -> str:
    """
    Format quarterly vision data into a structured string for inclusion in a quarterly analysis prompt.
    
    Args:
        vision_data: Dictionary containing vision data from get_employee_vision_data_for_quarter
        max_content_items_per_entity: Maximum number of content items to include per entity
        max_content_item_length: Maximum character length for each content item value 
        
    Returns:
        Formatted string for inclusion in the quarterly analysis prompt
    """
    if not vision_data or not vision_data.get("months_data"):
        return "No vision data available for the quarter."
    
    # Quarter header information
    quarter_info = (
        f"# QUARTERLY VISION DATA ({vision_data['date_context']['year']}-Q{vision_data['date_context']['quarter']})\n"
        f"Period: {vision_data['date_context']['period_start']} to {vision_data['date_context']['period_end']}\n\n"
    )
    
    # Add quarter-level summary
    total_weeks = sum(len(month.get("weeks_data", [])) for month in vision_data.get("months_data", []))
    total_entities = set()
    for month in vision_data.get("months_data", []):
        for week in month.get("weeks_data", []):
            for activity in week.get("activities", []):
                total_entities.add(activity.get("main_entity"))
    
    quarter_summary = (
        f"**Quarter Summary:**\n"
        f"- Data spans {len(vision_data.get('months_data', []))} months with {total_weeks} total weeks of activity\n"
        f"- {len(total_entities)} main activity types recorded: {', '.join(sorted(total_entities))}\n\n"
    )
    
    formatted_text = quarter_info + quarter_summary
    
    # Helper function for formatting content similar to weekly/monthly functions
    def format_sub_entity_content(sub_entity, content_dict, max_items):
        entity_items = content_dict.get(sub_entity, [])
        if not entity_items:
            return ""
        
        lines = []
        display_count = min(len(entity_items), max_items)
        for entry in entity_items[:display_count]:
            if entry:
                if isinstance(entry, dict):
                    # Truncate each value to prevent context overflow
                    entry_str = ", ".join(
                        f"{k}: {_truncate_content_value(v, max_content_item_length)}" 
                        for k, v in entry.items() if v
                    )
                else:
                    entry_str = _truncate_content_value(entry, max_content_item_length)
                
                if entry_str:
                    lines.append(f"      ---> {entry_str}")
        
        if len(entity_items) > max_items:
            lines.append(f"      ---> and {len(entity_items) - max_items} more...")
        
        if lines:
            return "\n".join(lines)
        return ""
    
    # Format each month's data
    for month_data in vision_data.get("months_data", []):
        month_name = month_data.get("month_name", "Unknown Month")
        weeks_data = month_data.get("weeks_data", [])
        
        if not weeks_data:
            continue
        
        formatted_text += f"\n## {month_name.upper()} ACTIVITY DATA\n"
        
        # Process each week
        for week in weeks_data:
            week_number = week.get("week_number")
            activities = week.get("activities", [])
            
            if activities:
                from_date = activities[0].get('from_date')
                to_date = activities[0].get('to_date')
                formatted_text += f"\nWeek {week_number} Activity Data ({from_date} to {to_date}):\n"
                # Process each activity in the week (similar to monthly format)
                for item in activities:
                    formatted_text += f"  Main Activity: {item.get('main_entity')}\n"
                    formatted_text += "  Details:\n"
                    
                    for sub_entity, data in item.get("sub_entities", {}).items():
                        formatted_text += f"    - Number of {sub_entity}: {data['value']} ({data['description']})\n"
                        # Format sub-entity content similar to weekly/monthly
                        sub_content = format_sub_entity_content(
                            sub_entity, 
                            item.get("sub_entities_content", {}), 
                            max_content_items_per_entity
                        )
                        if sub_content:
                            formatted_text += f"{sub_content}\n"
    
    return formatted_text

def map_reports_to_jds(
    reports: List[Dict[str, Any]],
    jds: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Map reports to their applicable job description(s) based on temporal overlap.
    
    Groups reports by their applicable JD configuration, handling scenarios where:
    - Employee has single stable JD throughout period
    - Employee transitions between JDs during period  
    - Employee holds multiple concurrent JDs
    
    Args:
        reports: List of report dictionaries with at least 'date' field
        jds: List of JD dictionaries from get_employee_job_descriptions_for_period()
        
    Returns:
        Dictionary with 'jd_groups' (reports grouped by applicable JDs) and 
        'unmapped_reports' (reports without applicable JD)
        
    Example:
        >>> reports = [{"text": "...", "date": date(2025, 1, 5), "report_id": "..."}]
        >>> jds = [{"jd_id": "JD_001", "effective_during_period": {...}, ...}]
        >>> result = map_reports_to_jds(reports, jds)
        >>> # Returns grouped reports with their applicable JDs
    """
    from datetime import timedelta
    
    # Input validation - return empty structure if no data
    if not reports:
        logger.info("No reports provided for JD mapping")
        return {"jd_groups": [], "unmapped_reports": []}
    
    if not jds:
        logger.warning(f"No JDs provided for mapping {len(reports)} reports - all reports will be unmapped")
        return {"jd_groups": [], "unmapped_reports": reports}
    
    logger.info(f"Mapping {len(reports)} reports to {len(jds)} job descriptions")
    
    # Data structure to group reports by their applicable JD configuration
    # Key: tuple of sorted jd_ids (for consistent grouping)
    # Value: list of reports applicable to that JD configuration
    jd_groups_map = {}
    unmapped_reports = []
    
    # Process each report
    for report in reports:
        report_date = report.get("date")
        
        # Skip reports without dates
        if not report_date:
            logger.warning(f"Report {report.get('report_id', 'unknown')} has no date - adding to unmapped")
            unmapped_reports.append(report)
            continue
        
        # Convert date to date object if it's a string
        if isinstance(report_date, str):
            try:
                from datetime import datetime
                report_date = datetime.fromisoformat(report_date).date()
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse date '{report_date}' for report {report.get('report_id', 'unknown')}")
                unmapped_reports.append(report)
                continue
        
        # Calculate the week period for this report
        # report_date is the END of the week, so start is 6 days before (7-day week)
        week_start_date = report_date - timedelta(days=6)
        week_end_date = report_date
        
        logger.debug(f"Report {report.get('report_id', 'unknown')[:8]} covers week: {week_start_date} to {week_end_date}")
        
        # Find all JDs applicable to this report's week
        # A JD is applicable if it overlaps with ANY part of the report week
        applicable_jds = []
        for jd in jds:
            effective_period = jd.get("effective_during_period", {})
            effective_start = effective_period.get("start")
            effective_end = effective_period.get("end")
            
            # Check if JD overlaps with the report week
            # JD overlaps if: JD_start <= week_end AND JD_end >= week_start
            if effective_start and effective_end:
                if effective_start <= week_end_date and effective_end >= week_start_date:
                    applicable_jds.append(jd)
                    logger.debug(
                        f"  JD {jd['jd_id']} applicable: JD period ({effective_start} to {effective_end}) "
                        f"overlaps with week ({week_start_date} to {week_end_date})"
                    )
        
        # If no applicable JDs found, add to unmapped
        if not applicable_jds:
            logger.debug(f"Report week {week_start_date} to {week_end_date} has no applicable JD")
            unmapped_reports.append(report)
            continue
        
        # Create a unique key for this JD configuration
        # Sort JD IDs to ensure consistent grouping (e.g., [JD_A, JD_B] same as [JD_B, JD_A])
        jd_ids = sorted([jd["jd_id"] for jd in applicable_jds])
        group_key = tuple(jd_ids)
        
        # Add report to the appropriate group with week range information
        if group_key not in jd_groups_map:
            jd_groups_map[group_key] = {
                "jd_ids": jd_ids,
                "jd_texts": [jd["job_description"] for jd in applicable_jds],
                "reports": [],
                "jd_metadata": applicable_jds  # Store full JD info for date range calculation
            }
        
        # Add week range information to the report before storing
        report_with_week_range = report.copy()
        report_with_week_range["week_start_date"] = week_start_date
        report_with_week_range["week_end_date"] = week_end_date
        
        jd_groups_map[group_key]["reports"].append(report_with_week_range)
    
    # Convert the map to a list and calculate effective date ranges for each group
    jd_groups = []
    for group_key, group_data in jd_groups_map.items():
        # Calculate the date range for this group based on its reports' week ranges
        reports_with_weeks = group_data["reports"]
        
        if reports_with_weeks:
            # Get all week start and end dates
            week_starts = [r.get("week_start_date") for r in reports_with_weeks if r.get("week_start_date")]
            week_ends = [r.get("week_end_date") for r in reports_with_weeks if r.get("week_end_date")]
            
            # Group effective dates span from earliest week start to latest week end
            group_start = min(week_starts) if week_starts else None
            group_end = max(week_ends) if week_ends else None
        else:
            # Fallback to JD effective dates if no valid report dates
            jd_starts = [jd["effective_during_period"]["start"] for jd in group_data["jd_metadata"]]
            jd_ends = [jd["effective_during_period"]["end"] for jd in group_data["jd_metadata"]]
            group_start = min(jd_starts) if jd_starts else None
            group_end = max(jd_ends) if jd_ends else None
        
        # Build final group structure without internal metadata
        jd_groups.append({
            "jd_ids": group_data["jd_ids"],
            "jd_texts": group_data["jd_texts"],
            "effective_dates": {
                "start": group_start,
                "end": group_end
            },
            "reports": group_data["reports"]
        })
    
    # Sort groups by effective start date for chronological order
    jd_groups.sort(key=lambda g: g["effective_dates"]["start"] if g["effective_dates"]["start"] else date.min)
    
    # Log summary
    logger.info(f"Created {len(jd_groups)} JD groups with {len(unmapped_reports)} unmapped reports")
    for i, group in enumerate(jd_groups):
        logger.debug(
            f"  Group {i+1}: JDs {group['jd_ids']} - "
            f"{len(group['reports'])} reports covering weeks from {group['effective_dates']['start']} to {group['effective_dates']['end']}"
        )
    
    return {
        "jd_groups": jd_groups,
        "unmapped_reports": unmapped_reports
    }

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
            quarter_num = f"Q{(start.month - 1) // 3 + 1}"
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
                    end_str = week_end.isoformat() if hasattr(end, "isoformat") else str(week_end)
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