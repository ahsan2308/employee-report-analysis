"""The stored text of a weekly report, the same for every way a report arrives."""


def compose_report_text(tasks_completed=None, impact=None, challenges=None, support_required=None,
                        tasks_planned=None, confidence_level=None, period=None,
                        nothing_to_report_reason=None) -> str:
    """
    Report text from its fields; a missing field reads "N/A".

    period is "<from> to <to>" when the source knows the reporting window (CSV and
    sync rows do; the web form does not). nothing_to_report_reason is added only
    when given.
    """
    lines = [
        f"Tasks Completed: {tasks_completed or 'N/A'}",
        f"Impact: {impact or 'N/A'}",
        f"Challenges: {challenges or 'N/A'}",
        f"Support Required: {support_required or 'N/A'}",
        f"Tasks Planned: {tasks_planned or 'N/A'}",
        f"Confidence Level: {confidence_level or 'N/A'}",
    ]
    if period:
        lines.append(f"Report Period: {period}")
    if nothing_to_report_reason:
        lines.append(f"Nothing to Report Reason: {nothing_to_report_reason}")
    return "\n\n".join(lines)
