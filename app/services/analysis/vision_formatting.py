"""Filter vision system activity data and format it for analysis prompts."""
from typing import Dict, Any, List, Optional
from app.core.logger import logger
from app.domain.vision_catalog import describe_sub_entity


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
        sub_entity_descriptions: A dictionary mapping sub-entity names to their descriptions.
            By default each sub-entity is described within its item's main entity.
        
    Returns:
        Filtered vision data with descriptions added
    """
    if not vision_data:
        return {}

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



def _process_entity_data(entity_data: List[Dict[str, Any]], sub_entity_descriptions: Optional[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Process a list of entity data items, filtering zero values and adding descriptions.
    
    Args:
        entity_data: List of entity data items
        sub_entity_descriptions: Dictionary mapping sub-entity names to descriptions,
            or None to use the catalog entry for each item's main entity
        
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
                if sub_entity_descriptions:
                    description = sub_entity_descriptions.get(sub_entity, "")
                else:
                    description = describe_sub_entity(item.get("main_entity"), sub_entity)
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
