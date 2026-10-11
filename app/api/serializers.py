"""Response builders: how the API shapes ORM rows (one builder per response shape)."""


def task_status_response(task, with_duration: bool = False):
    """A task's status; GET /tasks/{id} also reports how long it ran (with_duration)."""
    response = {
        "task_id": task.task_id,
        "celery_task_id": task.celery_task_id,
        "status": task.status,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "is_complete": task.is_complete
    }
    if with_duration:
        response["duration"] = task.duration
    return response


def weekly_analysis_list_item(analysis, report):
    """One weekly analysis in an employee's list."""
    return {
        "analysis_id": analysis.analysis_id,
        "report_id": str(analysis.report_id),
        "report_date": report.report_date,
        "sentiment_score": analysis.sentiment_score,
        "risk_level": analysis.risk_level,
        "performance_rating": analysis.performance_rating
    }


def monthly_analysis_summary(analysis):
    """One monthly analysis in an employee's list."""
    return {
        "analysis_id": analysis.analysis_id,
        "employee_id": analysis.employee_id,
        "year": analysis.year,
        "month": analysis.month,
        "period_start": analysis.period_start,
        "period_end": analysis.period_end,
        "performance_trend": analysis.performance_trend,
        "sentiment_trend": analysis.sentiment_trend,
        "risk_level": analysis.risk_level,
        "achievement_count": len(analysis.monthly_achievements) if analysis.monthly_achievements else 0,
        "challenge_count": len(analysis.recurring_challenges) if analysis.recurring_challenges else 0,
        "monthly_summary": analysis.monthly_summary
    }


def sync_status_response(sync_job):
    """GET /sync/status/{id}: a sync job with its progress."""
    percent_complete = 0.0
    if sync_job.records_queried and sync_job.records_queried > 0:
        percent_complete = round((sync_job.records_synced / sync_job.records_queried) * 100, 1)
    return {
        "sync_id": sync_job.sync_id,
        "sync_type": sync_job.sync_type,
        "status": sync_job.status,
        "is_full_sync": sync_job.is_full_sync,
        "started_at": sync_job.started_at,
        "completed_at": sync_job.completed_at,
        "duration_seconds": sync_job.duration_seconds,
        "progress": {
            "records_queried": sync_job.records_queried or 0,
            "records_synced": sync_job.records_synced or 0,
            "records_created": sync_job.records_created or 0,
            "records_updated": sync_job.records_updated or 0,
            "records_skipped": sync_job.records_skipped or 0,
            "error_count": sync_job.error_count or 0,
            "percent_complete": percent_complete
        },
        "metrics": sync_job.sync_metadata or {},
        "last_sync_timestamp": sync_job.last_sync_timestamp,
        "error_message": sync_job.error_message
    }


def sync_history_item(sync_job):
    """One sync job in the history list."""
    return {
        "sync_id": sync_job.sync_id,
        "sync_type": sync_job.sync_type,
        "status": sync_job.status,
        "is_full_sync": sync_job.is_full_sync,
        "started_at": sync_job.started_at,
        "completed_at": sync_job.completed_at,
        "duration_seconds": sync_job.duration_seconds,
        "records_synced": sync_job.records_synced or 0,
        "records_queried": sync_job.records_queried or 0,
        "error_count": sync_job.error_count or 0,
        "last_sync_timestamp": sync_job.last_sync_timestamp
    }


def weekly_analysis_response(analysis, employee):
    return {
        "report_id": str(analysis.report_id),
        "employee_name": employee.name if employee else None,
        "sentiment": analysis.sentiment_score if analysis.sentiment_score is not None else 0.5,
        "sentiment_score": analysis.sentiment_score,
        "risk_level": analysis.risk_level,
        "risk_explanation": analysis.risk_explanation,
        "full_analysis_json": analysis.full_analysis_json,
        "achievements_json": analysis.achievements_json,
        "challenges_json": analysis.challenges_json,
        "topics": analysis.topics,
        "action_items": analysis.action_items,
        "credibility_assessment": {
            "rating": analysis.credibility_rating or "medium",
            "explanation": analysis.credibility_explanation or "No credibility assessment was performed for this analysis.",
            "exaggeration_flags": analysis.exaggeration_flags or [],
            "consistency_score": analysis.consistency_score or "medium"
        },
        "performance_assessment": {
            "rating": analysis.performance_rating or "medium",
            "summary": analysis.performance_summary or "No performance assessment was performed for this analysis.",
            "key_strengths": analysis.performance_strengths or [],
            "improvement_areas": analysis.performance_improvement_areas or []
        }
    }


def monthly_analysis_response(analysis, employee):
    return {
        "analysis_id": analysis.analysis_id,
        "employee_id": analysis.employee_id,
        "employee_name": employee.name if employee else None,
        "year": analysis.year,
        "month": analysis.month,
        "period_start": analysis.period_start,
        "period_end": analysis.period_end,
        "avg_sentiment_score": analysis.avg_sentiment_score,

        "progress_trends": {
            "sentiment_trend": analysis.sentiment_trend,
            "performance_trend": analysis.performance_trend,
            "risk_level_pattern": analysis.risk_level_pattern,
            "challenge_resolution_progress": analysis.challenge_resolution_progress
        },

        "monthly_achievements": analysis.monthly_achievements or [],
        "recurring_challenges": analysis.recurring_challenges or [],

        "consistency_assessment": {
            "task_completion_reliability": analysis.task_completion_reliability,
            "work_quality_consistency": analysis.work_quality_consistency,
            "performance_stability": analysis.performance_stability,
            "notable_strengths": analysis.consistency_notable_strengths or [],
            "notable_weaknesses": analysis.consistency_notable_weaknesses or []
        },

        "growth_indicators": {
            "complexity_of_tasks": analysis.complexity_of_tasks,
            "skill_development_evidence": analysis.skill_development_evidence,
            "confidence_level_change": analysis.confidence_level_change,
            "approach_to_challenges": analysis.approach_to_challenges
        },

        "focus_areas": analysis.focus_areas or [],

        "monthly_risk_assessment": {
            "overall_risk_level": analysis.risk_level,
            "risk_explanation": analysis.risk_explanation,
            "significant_risks": analysis.significant_risks or [],
            "escalating_risks": analysis.escalating_risks or [],
            "risk_mitigation_recommendations": analysis.risk_mitigation_recommendations or []
        },

        "strategic_recommendations": analysis.strategic_recommendations or [],
        "monthly_summary": analysis.monthly_summary
    }


def quarterly_analysis_response(analysis, employee):
    return {
        "analysis_id": analysis.analysis_id,
        "employee_id": analysis.employee_id,
        "employee_name": employee.name if employee else None,
        "year": analysis.year,
        "quarter": analysis.quarter,
        "period_start": analysis.period_start,
        "period_end": analysis.period_end,
        "monthly_analysis_ids": analysis.monthly_analysis_ids,

        # Strategic alignment
        "organizational_impact": analysis.organizational_impact,
        "strategic_alignment": analysis.strategic_alignment_json,

        # Performance assessment
        "performance_trend": analysis.performance_trend,
        "task_completion_reliability": analysis.task_completion_reliability,
        "work_quality_consistency": analysis.work_quality_consistency,
        "performance_stability": analysis.performance_stability,
        "achievement_themes": analysis.achievement_themes_json,
        "performance_trajectory": analysis.performance_trajectory_json,

        # Cross-functional and challenge data
        "collaboration_effectiveness": analysis.collaboration_effectiveness,
        "stakeholder_count": analysis.stakeholder_count,
        "challenge_patterns": analysis.challenge_patterns_json,
        "cross_functional_impact": analysis.cross_functional_impact_json,
        "adaptation_effectiveness": analysis.adaptation_effectiveness,

        # Risk assessment
        "risk_level": analysis.risk_level,
        "risk_trend": analysis.risk_trend,
        "risk_assessment": analysis.risk_assessment_json,

        # Skills and development
        "learning_agility": analysis.learning_agility,
        "autonomy_level": analysis.autonomy_level,
        "development_focus": analysis.development_focus,
        "skill_development": analysis.skill_development_json,
        "behavioral_assessment": analysis.behavioral_assessment_json,

        # Credibility assessment
        "credibility_rating": analysis.credibility_rating,
        "vision_data_alignment": analysis.vision_data_alignment,
        "credibility_assessment": analysis.credibility_assessment_json,

        # Forward planning
        "forward_planning": analysis.forward_planning_json,

        # Summary
        "quarterly_summary": analysis.quarterly_summary
    }


_ANALYSIS_RESPONSES = {
    "weekly": weekly_analysis_response,
    "monthly": monthly_analysis_response,
    "quarterly": quarterly_analysis_response,
}


def task_result_response(task_id, result):
    """GET /tasks/{id}/result: an analysis in its /analyses shape, else the task's stored result."""
    payload = result.result_data
    if result.analysis is not None:
        analysis = result.analysis
        payload = _ANALYSIS_RESPONSES[result.analysis_kind](analysis, result.employee)
        # Also kept from the task endpoint's earlier payload
        payload["analysis_id"] = analysis.analysis_id
        payload["full_analysis_json"] = analysis.full_analysis_json
        if result.analysis_kind == "quarterly":
            payload["analysis_date"] = analysis.analysis_date
    return {
        "task_id": task_id,
        "status": result.status,
        "result": payload,
        "error_message": result.error_message
    }
