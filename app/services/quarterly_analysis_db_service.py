"""
Quarterly Analysis DB Service

Provides functionality for aggregating and analyzing quarterly employee data.
This service acts as a layer between the database and analysis tasks.
"""
from typing import Dict, Any
from collections import Counter

from app.core.logger import logger
from app.domain.periods import get_quarter_date_range
from app.domain.scoring import consistency_level_score
from app.repositories.analyses import get_monthly_analyses_for_quarter, get_weekly_analyses_for_quarter
from app.repositories.employees import get_employee_info

from app.repositories.job_descriptions import get_employee_job_descriptions_for_period
from app.services.analysis.jd_mapping import map_reports_to_jds

def get_quarterly_data_for_analysis(employee_id: int, year: int, quarter: int) -> Dict[str, Any]:
    """
    Aggregate all data needed for quarterly analysis, including monthly analyses,
    weekly analyses, and employee information.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        Dictionary containing all data needed for quarterly analysis
    """
    logger.info(f"Gathering quarterly analysis data for employee {employee_id}, {year}-Q{quarter}")
    
    result = {
        "year": year,
        "quarter": quarter,
        "employee_id": employee_id,
        "employee_info": None,
        "monthly_analyses": [],
        "weekly_analyses": [],
        "period_start": None,
        "period_end": None,
        "metrics": {
            "avg_sentiment": 0.0,
            "sentiment_trend": "stable",
            "risk_levels": {},
            "recurring_topics": [],
            "achievement_count": 0,
            "challenge_count": 0,
            "weekly_report_count": 0,
            "performance_stability": "medium",
            "monthly_progress_trends": [],
            "task_reliability_trend": "stable",
            "quality_consistency_trend": "stable",
            "risk_trend": "stable",
            "challenge_resolution_trend": "stable",
            "monthly_summaries": [],
            "achievement_impact_avg": 0.0,
            "weekly_credibility_data": {
                "avg_credibility_rating": None,
                "credibility_trend": "stable",
                "exaggeration_frequency": 0
            },
            "detailed_topics": [],
            "weekly_performance_ratings": [],
            "performance_rating_aggregation": {
                "most_common_rating": None,
                "rating_distribution": {},
                "rating_trend": "stable"
            }
        }
    }
    
    try:
        # Get date range for the quarter
        start_date, end_date = get_quarter_date_range(year, quarter)
        result["period_start"] = start_date
        result["period_end"] = end_date
        
        # Get employee information using db_service
        employee_info = get_employee_info(employee_id)
        if not employee_info:
            logger.error(f"Employee with ID {employee_id} not found")
            return result
            
        result["employee_info"] = employee_info
        
        # Get all monthly analyses for the quarter
        monthly_analyses = get_monthly_analyses_for_quarter(employee_id, year, quarter)
        result["monthly_analyses"] = monthly_analyses
        
        # Get all weekly analyses for the quarter
        weekly_analyses = get_weekly_analyses_for_quarter(employee_id, year, quarter)
        result["weekly_analyses"] = weekly_analyses
        result["metrics"]["weekly_report_count"] = len(weekly_analyses)
        
        # Create monthly-indexed weekly analyses for better pattern detection
        monthly_indexed_weekly_analyses = {}
        for week_analysis in weekly_analyses:
            week_date = week_analysis.get("date")
            if week_date:
                month = week_date.month if hasattr(week_date, "month") else None
                if month:
                    if month not in monthly_indexed_weekly_analyses:
                        monthly_indexed_weekly_analyses[month] = []
                    monthly_indexed_weekly_analyses[month].append(week_analysis)
        
        # Calculate metrics from monthly analyses (avoiding duplication and redundancy)
        monthly_report_counts = {}
        monthly_summaries = []
        monthly_risk_levels = {}
        total_monthly_reports = 0
        
        # Process monthly analyses to extract key metrics
        for monthly_analysis in monthly_analyses:
            month_num = monthly_analysis.get("month", 0)
            month_name = monthly_analysis.get("month_name", f"Month {month_num}")
            
            # Extract monthly summary once (avoid duplication)
            monthly_summary = monthly_analysis.get("monthly_summary", "")
            if monthly_summary:
                monthly_summaries.append({
                    "month": month_name,
                    "summary": monthly_summary
                })
            
            # Extract report count for weighted averages
            report_count = len(monthly_analysis.get("weekly_report_ids", []))
            monthly_report_counts[month_num] = report_count
            total_monthly_reports += report_count
            
            # Extract progress trends once (avoid duplication)
            progress_trends = monthly_analysis.get("progress_trends", {})
            if progress_trends:
                result["metrics"]["monthly_progress_trends"].append({
                    "month": month_num,
                    "performance_trend": progress_trends.get("performance_trend", "stable"),
                    "sentiment_trend": progress_trends.get("sentiment_trend", "stable"),
                    "risk_level_pattern": progress_trends.get("risk_level_pattern", "stable"),
                    "challenge_resolution_progress": progress_trends.get("challenge_resolution_progress", "unchanged")
                })
            
            # Extract risk levels (avoid re-aggregation)
            risk_assessment = monthly_analysis.get("monthly_risk_assessment", {})
            risk_level = risk_assessment.get("overall_risk_level")
            if risk_level:
                monthly_risk_levels[month_num] = risk_level
            
            # Accumulate achievement and challenge counts
            monthly_achievements = monthly_analysis.get("monthly_achievements", [])
            recurring_challenges = monthly_analysis.get("recurring_challenges", [])
            result["metrics"]["achievement_count"] += len(monthly_achievements)
            result["metrics"]["challenge_count"] += len(recurring_challenges)
        
        # Store monthly summaries only once
        result["metrics"]["monthly_summaries"] = monthly_summaries
        
        # Calculate weighted average sentiment across months (avoid redundant calculation)
        if monthly_analyses and total_monthly_reports > 0:
            weighted_sentiment = 0.0
            for monthly_analysis in monthly_analyses:
                month_num = monthly_analysis.get("month", 0)
                avg_sentiment = monthly_analysis.get("avg_sentiment_score")
                if avg_sentiment is not None and month_num in monthly_report_counts:
                    weight = monthly_report_counts[month_num] / total_monthly_reports
                    weighted_sentiment += avg_sentiment * weight
            
            result["metrics"]["avg_sentiment"] = round(weighted_sentiment, 2)

        # Calculate achievement impact average from monthly analyses
        total_achievements = 0
        weighted_impact = 0.0
        
        for monthly_analysis in monthly_analyses:
            monthly_achievements = monthly_analysis.get("monthly_achievements", [])
            achievement_count = len(monthly_achievements)
            
            if achievement_count > 0:
                total_achievements += achievement_count
                impact_avg = monthly_analysis.get("achievement_impact_avg")
                if impact_avg is not None:
                    weighted_impact += impact_avg * achievement_count
        
        if total_achievements > 0:
            result["metrics"]["achievement_impact_avg"] = round(weighted_impact / total_achievements, 2)
        
        # Standardize trend analysis with a consistent method
        def analyze_trend(values, keys=None, context="default"):
            """
            Analyze trend using a standardized method across all metrics

            Numeric values are levels (higher is "improving" when they rise);
            strings are monthly trend labels, whose directions are aggregated.
            
            Args:
                values: List of values to analyze
                keys: Optional keys for sorting values (e.g., months)
                context: The context of analysis (default, risk, complexity)
            """
            if not values or len(values) < 2:
                return "stable"
                
            # If keys are provided, organize values by keys (e.g., months) in chronological order
            if keys:
                sorted_items = sorted(zip(keys, values))
                values = [v for _, v in sorted_items]
            
            # Convert string trend values to numeric scores for comparison
            labels = all(isinstance(v, str) for v in values)
            if labels:
                numeric_values = []
                for v in values:
                    # Default context (performance, sentiment, quality)
                    if context == "default":
                        if v in ["improving", "improved", "increased"]:
                            numeric_values.append(1)
                        elif v in ["declining", "declined", "decreased"]:
                            numeric_values.append(-1)
                        elif v == "mixed":
                            numeric_values.append(0)  # Treat mixed as neutral
                        else:  # stable, unchanged
                            numeric_values.append(0)
                    
                    # Risk context (risk level, challenges)
                    elif context == "risk":
                        if v in ["decreasing", "improved"]:
                            numeric_values.append(1)  # Decreasing risk is good
                        elif v in ["increasing", "declined"]:
                            numeric_values.append(-1)  # Increasing risk is bad
                        else:  # stable, unchanged
                            numeric_values.append(0)
                    
                    # Complexity/Growth context
                    elif context == "complexity":
                        if v in ["increased", "more proactive"]:
                            numeric_values.append(1)  # Increased complexity/proactivity is good
                        elif v in ["decreased", "more reactive"]:
                            numeric_values.append(-1)  # Decreased complexity/reactivity is bad
                        else:  # stable, unchanged
                            numeric_values.append(0)
                            
                values = numeric_values
            
            if not labels:
                # Levels (scores, ratings, risk levels): the direction they moved in. The
                # least-squares change across the period, ignoring moves under 5% of the scale.
                count = len(values)
                mean_x = (count - 1) / 2
                mean_y = sum(values) / count
                slope = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(values)) / sum(
                    (x - mean_x) ** 2 for x in range(count))
                change = slope * (count - 1)
                tolerance = 0.05 * max(abs(v) for v in values)
                if change > tolerance:
                    return "improving"
                if change < -tolerance:
                    return "declining"
                return "stable"

            # Trend labels (one direction per month): aggregate the directions
            first, last = values[0], values[-1]
            avg = sum(values) / len(values)
            
            # If the trend is consistent throughout
            if all(v > 0 for v in values):
                return "improving"
            elif all(v < 0 for v in values):
                return "declining"
            
            # If trend is mixed but the last value shows clear direction
            if last > first + 0.1:
                return "improving"
            elif last < first - 0.1:
                return "declining"
            
            # If average shows a clear bias
            if avg > 0.3:
                return "improving"
            elif avg < -0.3:
                return "declining"
                
            return "stable"
        
        # Apply standardized trend analysis to sentiment
        if monthly_analyses and len(monthly_analyses) >= 2:
            sentiment_values = [ma.get("avg_sentiment_score", 0.5) for ma in monthly_analyses if ma.get("avg_sentiment_score") is not None]
            month_keys = [ma.get("month", 0) for ma in monthly_analyses if ma.get("avg_sentiment_score") is not None]
            
            if sentiment_values and month_keys:
                result["metrics"]["sentiment_trend"] = analyze_trend(sentiment_values, month_keys)
        
        # Apply standardized trend analysis to risk levels
        if monthly_risk_levels and len(monthly_risk_levels) >= 2:
            # Convert risk levels to numeric values for trend analysis
            risk_values = []
            month_keys = []
            for month, risk in sorted(monthly_risk_levels.items()):
                risk_value = 2 if risk == "high" else (1 if risk == "medium" else 0)
                risk_values.append(risk_value)
                month_keys.append(month)
                
                # Also count occurrence of each risk level
                result["metrics"]["risk_levels"][risk] = result["metrics"]["risk_levels"].get(risk, 0) + 1
            
            if risk_values:
                trend = analyze_trend(risk_values, month_keys, context="risk")
                # Invert the trend for risk (higher risk is worse)
                result["metrics"]["risk_trend"] = "decreasing" if trend == "declining" else ("increasing" if trend == "improving" else "stable")
        
        # Extract consistency metrics from monthly analyses
        task_reliability_by_month = {}
        work_quality_by_month = {}
        performance_stability_by_month = {}
        
        for monthly_analysis in monthly_analyses:
            month_num = monthly_analysis.get("month", 0)
            consistency = monthly_analysis.get("consistency_assessment", {})
            
            task_reliability = consistency.get("task_completion_reliability")
            if task_reliability:
                task_reliability_by_month[month_num] = consistency_level_score(task_reliability)
            
            work_quality = consistency.get("work_quality_consistency")
            if work_quality:
                work_quality_by_month[month_num] = consistency_level_score(work_quality)
            
            performance_stability = consistency.get("performance_stability")
            if performance_stability:
                performance_stability_by_month[month_num] = consistency_level_score(performance_stability)

        # Apply standardized trend analysis to consistency metrics
        if task_reliability_by_month and len(task_reliability_by_month) >= 2:
            values = [v for _, v in sorted(task_reliability_by_month.items())]
            result["metrics"]["task_reliability_trend"] = analyze_trend(values)
        
        if work_quality_by_month and len(work_quality_by_month) >= 2:
            values = [v for _, v in sorted(work_quality_by_month.items())]
            result["metrics"]["quality_consistency_trend"] = analyze_trend(values)
        
        # Calculate overall performance stability from monthly values
        if performance_stability_by_month:
            avg_stability = sum(performance_stability_by_month.values()) / len(performance_stability_by_month)
            if avg_stability > 2.5:
                result["metrics"]["performance_stability"] = "high"
            elif avg_stability > 1.5:
                result["metrics"]["performance_stability"] = "medium"
            else:
                result["metrics"]["performance_stability"] = "low"
        
        # Aggregate monthly progress trends into quarterly trends
        if result["metrics"]["monthly_progress_trends"] and len(result["metrics"]["monthly_progress_trends"]) >= 2:
            # Aggregate performance trends
            performance_trends = [pt.get("performance_trend", "stable") for pt in result["metrics"]["monthly_progress_trends"]]
            if performance_trends:
                result["metrics"]["performance_trend"] = analyze_trend(performance_trends)
            
            # Aggregate challenge resolution progress
            challenge_resolution = [pt.get("challenge_resolution_progress", "unchanged") for pt in result["metrics"]["monthly_progress_trends"]]
            if challenge_resolution:
                result["metrics"]["challenge_resolution_trend"] = analyze_trend(challenge_resolution)
        
        # Now utilize weekly analyses data for metrics not covered by monthly analyses
        # This prevents double-counting while still using the valuable weekly data
        if weekly_analyses:
            # Extract weekly credibility data (not aggregated in monthly analyses)
            credibility_ratings = []
            credibility_by_month = {}
            exaggeration_count = 0
            
            # Extract performance ratings for more granular performance insight
            performance_ratings = []
            
            # Extract detailed topic data for comprehensive topic analysis
            all_topics = []
            
            for analysis in weekly_analyses:
                week_date = analysis.get("date")
                if not week_date:
                    continue
                
                month = week_date.month if hasattr(week_date, "month") else None
                
                # Process credibility data
                credibility = analysis.get("credibility_rating")
                if credibility:
                    credibility_ratings.append(credibility)
                    if month:
                        if month not in credibility_by_month:
                            credibility_by_month[month] = []
                        credibility_by_month[month].append(credibility)
                
                # Count exaggeration flags
                exaggeration_flags = analysis.get("exaggeration_flags", [])
                if exaggeration_flags:
                    exaggeration_count += len(exaggeration_flags)
                
                # Process performance ratings
                performance_rating = analysis.get("performance_rating")
                if performance_rating:
                    performance_ratings.append({
                        "date": week_date.isoformat() if hasattr(week_date, "isoformat") else str(week_date),
                        "rating": performance_rating
                    })
                
                # Process topics for detailed topic analysis
                topics = analysis.get("topics", [])
                if topics:
                    all_topics.extend(topics)
            
            # Calculate credibility metrics
            if credibility_ratings:
                # Map textual ratings to numeric values
                numeric_ratings = []
                for rating in credibility_ratings:
                    if rating == "high":
                        numeric_ratings.append(3)
                    elif rating == "medium":
                        numeric_ratings.append(2)
                    elif rating == "low":
                        numeric_ratings.append(1)
                
                if numeric_ratings:
                    avg_rating = sum(numeric_ratings) / len(numeric_ratings)
                    if avg_rating > 2.5:
                        result["metrics"]["weekly_credibility_data"]["avg_credibility_rating"] = "high"
                    elif avg_rating > 1.5:
                        result["metrics"]["weekly_credibility_data"]["avg_credibility_rating"] = "medium"
                    else:
                        result["metrics"]["weekly_credibility_data"]["avg_credibility_rating"] = "low"
            
            # Calculate credibility trend
            if credibility_by_month and len(credibility_by_month) >= 2:
                # Convert textual ratings to numeric for trend analysis
                monthly_avg_credibility = {}
                for month, ratings in credibility_by_month.items():
                    numeric_vals = []
                    for r in ratings:
                        if r == "high":
                            numeric_vals.append(3)
                        elif r == "medium":
                            numeric_vals.append(2)
                        elif r == "low":
                            numeric_vals.append(1)
                    
                    if numeric_vals:
                        monthly_avg_credibility[month] = sum(numeric_vals) / len(numeric_vals)
                
                if monthly_avg_credibility:
                    values = [v for _, v in sorted(monthly_avg_credibility.items())]
                    result["metrics"]["weekly_credibility_data"]["credibility_trend"] = analyze_trend(values)
            
            # Store exaggeration frequency
            result["metrics"]["weekly_credibility_data"]["exaggeration_frequency"] = exaggeration_count
            
            # Store performance ratings
            result["metrics"]["weekly_performance_ratings"] = performance_ratings
            
            # Aggregate performance rating metrics
            if performance_ratings:
                # Count occurrences of each rating
                rating_counts = {}
                for entry in performance_ratings:
                    rating = entry.get("rating")
                    if rating:
                        rating_counts[rating] = rating_counts.get(rating, 0) + 1
                
                # Find most common rating
                most_common_rating = max(rating_counts.items(), key=lambda x: x[1])[0] if rating_counts else None
                result["metrics"]["performance_rating_aggregation"]["most_common_rating"] = most_common_rating
                
                # Calculate distribution percentages
                total_ratings = len(performance_ratings)
                rating_distribution = {rating: count/total_ratings for rating, count in rating_counts.items()}
                result["metrics"]["performance_rating_aggregation"]["rating_distribution"] = rating_distribution
                
                # Analyze performance rating trend if we have enough data
                if len(performance_ratings) >= 3:
                    # Sort by date
                    sorted_ratings = sorted(performance_ratings, key=lambda x: x.get("date", ""))
                    
                    # Convert ratings to numeric values
                    rating_values = []
                    for entry in sorted_ratings:
                        rating = entry.get("rating")
                        if rating:
                            # Performance rating scale: high, medium, low
                            if rating == "high":
                                rating_values.append(3)
                            elif rating == "medium":
                                rating_values.append(2)
                            elif rating == "low":
                                rating_values.append(1)
                            else:
                                # Use a neutral value for unrecognized ratings
                                rating_values.append(2)
                    
                    # Use the standardized trend analysis function
                    if rating_values:
                        result["metrics"]["performance_rating_aggregation"]["rating_trend"] = analyze_trend(rating_values)
            
            # Analyze topics for recurring topics and store detailed topic data
            if all_topics:
                topic_counter = Counter(all_topics)
                result["metrics"]["recurring_topics"] = [topic for topic, count in topic_counter.most_common() if count > 1]
                
                # Store detailed topic frequency data
                result["metrics"]["detailed_topics"] = [{"topic": topic, "frequency": count} 
                                                      for topic, count in topic_counter.most_common(10)]
        


        # Retrieve job descriptions that overlap with the quarterly period
        employee_jds = get_employee_job_descriptions_for_period(
            employee_id=employee_id,
            period_start=start_date,
            period_end=end_date
        )

        # For quarterly analysis, we map WEEKLY ANALYSES (not raw reports) to JDs
        # This provides career progression context across the quarter
        # Transform weekly_analyses to look like reports for mapping
        weekly_analyses_as_reports = []
        for analysis in weekly_analyses:
            weekly_analyses_as_reports.append({
                "report_id": analysis.get("report_id"),
                "report_date": analysis.get("date"), 
                "date": analysis.get("date")
            })

        # Map weekly analyses to JDs
        jd_analysis_mapping = map_reports_to_jds(weekly_analyses_as_reports, employee_jds)

        # Store in result dictionary
        result["jd_analysis_mapping"] = jd_analysis_mapping
        result["employee_jds"] = employee_jds

        logger.info(
            f"Quarterly analysis: Retrieved {len(employee_jds)} JD(s), "
            f"created {len(jd_analysis_mapping.get('jd_groups', []))} JD phases"
        )



        logger.info(f"Successfully gathered quarterly data for employee {employee_id}, {year}-Q{quarter}")
        return result
        
    except Exception as e:
        logger.error(f"Error gathering quarterly analysis data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return result

