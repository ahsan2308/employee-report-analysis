"""
Comprehensive test for the quarterly analysis prompt generation.

This test creates a complex quarterly data structure and passes it to the
quarterly_analysis_prompt method to verify all aspects of prompt generation.
"""
import sys
import os
import json
from datetime import date, datetime, timedelta
from pprint import pprint

# Add the parent directory to the path so we can import the app modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from prompts.structured_prompts import StructuredPrompts

def create_test_quarterly_data():
    """Create a comprehensive test dataset for quarterly analysis"""
    
    # Create base quarterly data structure
    quarter_data = {
        "year": 2025,
        "quarter": 1,
        "employee_id": 12345,
        "employee_info": {
            "name": "Jane Smith",
            "position": "Senior Software Engineer",
            "wing": "Engineering Department",
            "employee_id": 12345,
            "join_date": "2022-01-15"
        },
        "period_start": "2025-01-01",
        "period_end": "2025-03-31",
        "monthly_analyses": [],
        "weekly_analyses": [],
        "metrics": {
            "avg_sentiment": 0.78,
            "sentiment_trend": "improving",
            "achievement_count": 24,
            "challenge_count": 12,
            "weekly_report_count": 12,
            "performance_stability": "high",
            "task_reliability_trend": "improving",
            "quality_consistency_trend": "stable",
            "risk_trend": "decreasing",
            "challenge_resolution_trend": "improving",
            "achievement_impact_avg": 7.5,
            "risk_levels": {
                "high": 1,
                "medium": 3,
                "low": 8
            },
            "recurring_topics": [
                "API Development",
                "Documentation",
                "Code Reviews",
                "Performance Optimization",
                "Team Collaboration"
            ],
            "weekly_credibility_data": {
                "avg_credibility_rating": "high",
                "credibility_trend": "stable",
                "exaggeration_frequency": 2
            },
            "detailed_topics": [
                {"topic": "API Development", "frequency": 10},
                {"topic": "Documentation", "frequency": 8},
                {"topic": "Code Reviews", "frequency": 7},
                {"topic": "Performance Optimization", "frequency": 6},
                {"topic": "Team Collaboration", "frequency": 5},
                {"topic": "Bug Fixes", "frequency": 4},
                {"topic": "Testing", "frequency": 3}
            ],
            "performance_rating_aggregation": {
                "most_common_rating": "high",
                "rating_trend": "improving",
                "rating_distribution": {
                    "high": 0.65,
                    "medium": 0.30,
                    "low": 0.05
                }
            },
            "monthly_progress_trends": [
                {
                    "month": 1,
                    "performance_trend": "stable",
                    "sentiment_trend": "positive",
                    "risk_level_pattern": "stable",
                    "challenge_resolution_progress": "improved"
                },
                {
                    "month": 2,
                    "performance_trend": "improving",
                    "sentiment_trend": "positive",
                    "risk_level_pattern": "decreasing",
                    "challenge_resolution_progress": "improved"
                },
                {
                    "month": 3,
                    "performance_trend": "improving",
                    "sentiment_trend": "positive",
                    "risk_level_pattern": "decreasing",
                    "challenge_resolution_progress": "improved"
                }
            ],
            "monthly_summaries": [
                {
                    "month": "January",
                    "summary": "Jane demonstrated solid performance in January, focusing on API development and documentation. She successfully completed the authentication module and resolved several critical bugs while maintaining high code quality standards."
                },
                {
                    "month": "February",
                    "summary": "In February, Jane showed significant improvement in performance and productivity. She took on more complex tasks, completed the data migration module ahead of schedule, and actively mentored junior team members. Resource challenges were handled effectively."
                },
                {
                    "month": "March",
                    "summary": "March was Jane's strongest month, showing continued improvement and growth. She led the implementation of performance optimizations resulting in 35% faster API response times, facilitated cross-team collaboration, and proactively identified and mitigated potential risks."
                }
            ]
        },
        "formatted_vision_data": """
QUARTERLY VISION SYSTEM TRACKING DATA

## JANUARY ACTIVITY SUMMARY
- Code Commits: 47 commits across 8 repositories
- Documentation Updates: 12 documents created/updated
- Code Reviews: 15 reviews performed (avg. comment count: 8)
- Meetings Attended: 18 meetings (6 team, 8 cross-functional, 4 planning)
- System Interactions: Heavy usage of IDE (43 hours), Git (15 hours), Jira (8 hours)
- Keywords: authentication, API endpoints, documentation, schema design

## FEBRUARY ACTIVITY SUMMARY
- Code Commits: 53 commits across 6 repositories
- Documentation Updates: 8 documents created/updated
- Code Reviews: 22 reviews performed (avg. comment count: 10)
- Meetings Attended: 22 meetings (7 team, 10 cross-functional, 5 planning)
- System Interactions: Heavy usage of IDE (47 hours), Git (18 hours), Jira (10 hours)
- Keywords: data migration, performance, mentoring, testing automation

## MARCH ACTIVITY SUMMARY
- Code Commits: 61 commits across 7 repositories
- Documentation Updates: 14 documents created/updated
- Code Reviews: 28 reviews performed (avg. comment count: 12)
- Meetings Attended: 24 meetings (8 team, 12 cross-functional, 4 planning)
- System Interactions: Heavy usage of IDE (52 hours), Git (20 hours), Jira (12 hours)
- Keywords: performance optimization, cross-team collaboration, risk mitigation, API response time

## QUARTERLY PATTERNS
- Increasing code commit velocity (47 → 53 → 61)
- Increasing code review engagement (15 → 22 → 28)
- Consistent documentation contribution
- Increasing cross-functional meeting participation
- Progressive increase in system interaction time
- Evolution from implementation focus to optimization and collaboration
"""
    }
    
    # Create monthly analyses
    start_date = date(2025, 1, 1)
    
    # Create monthly analyses for January, February, and March
    for month in range(1, 4):
        # Calculate month period
        month_start = date(2025, month, 1)
        if month == 2:
            month_end = date(2025, month, 28)
        else:
            month_end = date(2025, month, 31)
        
        # Different patterns for each month to test trend detection
        if month == 1:
            performance_trend = "stable"
            sentiment_trend = "positive"
            risk_level = "medium"
            task_reliability = "medium"
            work_quality = "high"
            performance_stability = "medium"
        elif month == 2:
            performance_trend = "improving"
            sentiment_trend = "positive"
            risk_level = "low"
            task_reliability = "high"
            work_quality = "high"
            performance_stability = "high"
        else:  # month 3
            performance_trend = "improving"
            sentiment_trend = "positive"
            risk_level = "low"
            task_reliability = "high"
            work_quality = "high"
            performance_stability = "high"
        
        # Month-specific achievements and challenges to show progression
        if month == 1:
            achievements = [
                {
                    "description": "Completed implementation of the authentication module with multi-factor authentication support",
                    "impact": "8 (Critical security feature that protects all user data)"
                },
                {
                    "description": "Created comprehensive API documentation for five core endpoints",
                    "impact": "7 (Enabled frontend team to begin implementation ahead of schedule)"
                },
                {
                    "description": "Resolved three critical bugs affecting the login flow",
                    "impact": "6 (Fixed issues affecting approximately 15% of users)"
                }
            ]
            challenges = [
                {
                    "description": "Limited access to the security team for consultation on authentication requirements",
                    "severity": "medium",
                    "status": "ongoing"
                },
                {
                    "description": "Technical debt in the legacy code affecting schema design",
                    "severity": "medium",
                    "status": "ongoing"
                }
            ]
        elif month == 2:
            achievements = [
                {
                    "description": "Designed and implemented the data migration module for the platform upgrade",
                    "impact": "9 (Enables smooth transition to new platform for all customers)"
                },
                {
                    "description": "Automated regression test suite covering core authentication and data access features",
                    "impact": "7 (Reduced QA testing time by 40% for core features)"
                },
                {
                    "description": "Mentored two junior developers on API design principles and best practices",
                    "impact": "6 (Improved team capability and knowledge sharing)"
                }
            ]
            challenges = [
                {
                    "description": "Limited computing resources for data migration testing",
                    "severity": "low",
                    "status": "resolved"
                },
                {
                    "description": "Technical debt in the legacy code affecting schema design",
                    "severity": "medium",
                    "status": "ongoing"
                }
            ]
        else:  # month 3
            achievements = [
                {
                    "description": "Implemented performance optimizations resulting in 35% faster API response times",
                    "impact": "9 (Significantly improved user experience and reduced infrastructure costs)"
                },
                {
                    "description": "Led cross-team initiative to standardize API error handling across services",
                    "impact": "8 (Improved developer experience and system reliability)"
                },
                {
                    "description": "Developed and documented five new API endpoints for the reporting module",
                    "impact": "7 (Enabled new reporting features planned for Q2)"
                }
            ]
            challenges = [
                {
                    "description": "Coordinating with multiple teams for the error handling standardization",
                    "severity": "low",
                    "status": "resolved"
                }
            ]
        
        # Growth indicators with progression across months
        if month == 1:
            growth_indicators = {
                "complexity_of_tasks": "unchanged",
                "skill_development_evidence": "medium",
                "confidence_level_change": "unchanged",
                "approach_to_challenges": "unchanged"
            }
        elif month == 2:
            growth_indicators = {
                "complexity_of_tasks": "increased",
                "skill_development_evidence": "high",
                "confidence_level_change": "increased",
                "approach_to_challenges": "more proactive"
            }
        else:  # month 3
            growth_indicators = {
                "complexity_of_tasks": "increased",
                "skill_development_evidence": "high",
                "confidence_level_change": "increased",
                "approach_to_challenges": "more proactive"
            }
        
        # Focus areas with evolution across months
        if month == 1:
            focus_areas = [
                {
                    "project": "Authentication System",
                    "time_investment": "high",
                    "priority_level": "high"
                },
                {
                    "project": "API Documentation",
                    "time_investment": "medium",
                    "priority_level": "medium"
                }
            ]
        elif month == 2:
            focus_areas = [
                {
                    "project": "Data Migration Module",
                    "time_investment": "high",
                    "priority_level": "high"
                },
                {
                    "project": "Test Automation",
                    "time_investment": "medium",
                    "priority_level": "medium"
                },
                {
                    "project": "Mentoring",
                    "time_investment": "low",
                    "priority_level": "medium"
                }
            ]
        else:  # month 3
            focus_areas = [
                {
                    "project": "Performance Optimization",
                    "time_investment": "high",
                    "priority_level": "high"
                },
                {
                    "project": "Error Handling Standardization",
                    "time_investment": "medium",
                    "priority_level": "high"
                },
                {
                    "project": "Reporting API Development",
                    "time_investment": "medium",
                    "priority_level": "medium"
                }
            ]
        
        # Strategic recommendations that evolve with the employee's development
        if month == 1:
            recommendations = [
                {
                    "action": "Schedule regular sessions with the security team for authentication requirements",
                    "priority": "high"
                },
                {
                    "action": "Allocate time for refactoring legacy code affecting schema design",
                    "priority": "medium"
                }
            ]
        elif month == 2:
            recommendations = [
                {
                    "action": "Expand mentoring role to help develop team capabilities",
                    "priority": "medium"
                },
                {
                    "action": "Continue focus on test automation to improve code quality",
                    "priority": "high"
                },
                {
                    "action": "Provision additional computing resources for data migration testing",
                    "priority": "medium"
                }
            ]
        else:  # month 3
            recommendations = [
                {
                    "action": "Consider leadership role in cross-team initiatives based on recent success",
                    "priority": "high"
                },
                {
                    "action": "Document performance optimization techniques for knowledge sharing",
                    "priority": "medium"
                },
                {
                    "action": "Explore advanced architectural patterns for next-gen API design",
                    "priority": "medium"
                }
            ]
        
        # Monthly analysis structure
        month_name = ["January", "February", "March"][month-1]
        monthly_analysis = {
            "month": month,
            "month_name": month_name,
            "period_start": month_start.isoformat(),
            "period_end": month_end.isoformat(),
            "progress_trends": {
                "performance_trend": performance_trend,
                "sentiment_trend": sentiment_trend,
                "risk_level_pattern": "decreasing" if month > 1 else "stable",
                "challenge_resolution_progress": "improved" if month > 1 else "unchanged"
            },
            "monthly_achievements": achievements,
            "recurring_challenges": challenges,
            "consistency_assessment": {
                "task_completion_reliability": task_reliability,
                "work_quality_consistency": work_quality,
                "performance_stability": performance_stability,
                "notable_strengths": [
                    f"Consistent code quality standards in all {month_name} deliverables",
                    f"Reliable documentation practices throughout {month_name}"
                ],
                "notable_weaknesses": [
                    "Occasional delays in responding to code review comments" if month == 1 else None,
                    "Some variability in estimation accuracy" if month < 3 else None
                ]
            },
            "growth_indicators": growth_indicators,
            "focus_areas": focus_areas,
            "monthly_risk_assessment": {
                "overall_risk_level": risk_level,
                "risk_explanation": f"Risk assessment for {month_name} based on task complexity, dependencies, and resource constraints.",
                "significant_risks": [
                    "Security review delays affecting authentication timeline" if month == 1 else None,
                    "Technical debt in legacy code" if month < 3 else None
                ],
                "escalating_risks": [
                    "Increasing scope of schema changes" if month == 1 else None
                ],
                "risk_mitigation_recommendations": [
                    "Proactive engagement with security team" if month == 1 else None,
                    "Incremental refactoring approach for legacy code" if month < 3 else None,
                    "Knowledge sharing sessions for critical components" if month == 3 else None
                ]
            },
            "strategic_recommendations": recommendations,
            "monthly_summary": f"Monthly performance summary for {month_name} 2025.",
            "avg_sentiment_score": 0.65 + (month * 0.1),  # Increasing sentiment over months
            "achievement_impact_avg": 7.0 + (month * 0.25)  # Increasing impact over months
        }
        
        # Filter out None values
        for key in ["notable_weaknesses", "significant_risks", "escalating_risks", "risk_mitigation_recommendations"]:
            if monthly_analysis["consistency_assessment"].get(key):
                monthly_analysis["consistency_assessment"][key] = [item for item in monthly_analysis["consistency_assessment"][key] if item is not None]
            if monthly_analysis["monthly_risk_assessment"].get(key):
                monthly_analysis["monthly_risk_assessment"][key] = [item for item in monthly_analysis["monthly_risk_assessment"][key] if item is not None]
        
        quarter_data["monthly_analyses"].append(monthly_analysis)
    
    # Create weekly analyses - 4 weeks per month = 12 total
    current_date = start_date
    for week in range(12):
        month = (week // 4) + 1  # 0-3: month 1, 4-7: month 2, 8-11: month 3
        
        # Week period
        week_start = current_date
        week_end = current_date + timedelta(days=6)
        current_date = week_end + timedelta(days=1)
        
        # Different patterns based on week/month for testing trend detection
        if week < 4:  # January
            sentiment = "neutral" if week == 0 else ("positive" if week > 1 else "neutral")
            risk_level = "medium"
            performance_rating = "medium" if week < 2 else "high"
            credibility_rating = "high"
        elif week < 8:  # February
            sentiment = "positive"
            risk_level = "medium" if week == 4 else "low"
            performance_rating = "high"
            credibility_rating = "high"
        else:  # March
            sentiment = "positive"
            risk_level = "low"
            performance_rating = "high"
            credibility_rating = "high"
        
        # Create week-specific achievements and challenges
        week_achievements = [
            {
                "description": f"Weekly achievement {week+1}-1: Specific task completed in week {week+1}",
                "impact": f"{min(7 + (week // 2), 9)} (Impact reason for week {week+1})"
            },
            {
                "description": f"Weekly achievement {week+1}-2: Another task for week {week+1}",
                "impact": f"{min(6 + (week // 3), 8)} (Impact reason for this achievement)"
            }
        ]
        
        week_challenges = [
            {
                "description": f"Weekly challenge {week+1}: Issue faced in week {week+1}",
                "severity": "low" if week > 6 else ("medium" if week > 2 else "high")
            }
        ]
        
        # Add some extra achievements/challenges for variety
        if week % 3 == 0:
            week_achievements.append({
                "description": f"Bonus achievement for week {week+1}: Extra work completed",
                "impact": f"{min(6 + (week // 2), 9)} (Additional impact details)"
            })
        
        if week < 6:
            week_challenges.append({
                "description": f"Additional challenge for early week {week+1}: Extra obstacle",
                "severity": "medium" if week < 3 else "low"
            })
        
        # Create weekly topics with some consistency and some variation
        common_topics = ["API Development", "Documentation", "Code Quality"]
        week_specific_topics = [f"Week {week+1} Specific Topic", f"Feature {(week % 4) + 1}"]
        
        if week < 4:
            topics = common_topics + ["Authentication", "Security"] + week_specific_topics
        elif week < 8:
            topics = common_topics + ["Data Migration", "Testing"] + week_specific_topics
        else:
            topics = common_topics + ["Performance", "Optimization"] + week_specific_topics
        
        # Create weekly analysis
        weekly_analysis = {
            "date": week_start,
            "period_start": week_start.isoformat(),
            "period_end": week_end.isoformat(),
            "sentiment": sentiment,
            "risk_level": risk_level,
            "risk_explanation": f"Risk explanation for week {week+1} of Q1 2025",
            "achievements": week_achievements,
            "challenges": week_challenges,
            "topics": topics,
            "action_items": [
                f"Action item 1 for week {week+1}",
                f"Action item 2 for week {week+1}"
            ],
            "credibility_assessment": {
                "rating": credibility_rating,
                "explanation": f"Credibility explanation for week {week+1}",
                "consistency_score": "high",
                "exaggeration_flags": [] if week != 2 and week != 6 else [f"Minor exaggeration in week {week+1}"]
            },
            "performance_assessment": {
                "rating": performance_rating,
                "summary": f"Performance summary for week {week+1}",
                "key_strengths": [
                    f"Key strength 1 for week {week+1}",
                    f"Key strength 2 for week {week+1}"
                ],
                "improvement_areas": [
                    f"Improvement area for week {week+1}"
                ]
            }
        }
        
        quarter_data["weekly_analyses"].append(weekly_analysis)
    
    return quarter_data

def test_quarterly_analysis_prompt():
    """Test the quarterly analysis prompt with comprehensive test data"""
    # Create test data
    quarterly_data = create_test_quarterly_data()
    
    # Generate the prompt
    prompt = StructuredPrompts.quarterly_analysis_prompt(quarterly_data)
    
    # Output the prompt and test data for inspection
    with open("quarterly_analysis_test_data.json", "w", encoding="utf-8") as f:
        json.dump(quarterly_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"Test data written to quarterly_analysis_test_data.json")
    
    with open("quarterly_analysis_test_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
        print(f"Generated prompt written to quarterly_analysis_test_prompt.txt")
    
    # Print entire prompt for manual inspection
    print("\n========== FULL PROMPT FOR MANUAL INSPECTION ==========")
    print(prompt)
    print("========== END OF FULL PROMPT ==========")
    
    # Comprehensive metric verification
    print("\nComprehensive Metrics Verification:")
    
    # Employee info verification
    employee_info = quarterly_data["employee_info"]
    verify_text_present(prompt, f"Name: {employee_info['name']}", "Employee name")
    verify_text_present(prompt, f"Position: {employee_info['position']}", "Employee position")
    verify_text_present(prompt, f"Department: {employee_info['wing']}", "Employee department")
    
    # General metrics verification
    metrics = quarterly_data["metrics"]
    verify_text_present(prompt, f"Total Achievements: {metrics['achievement_count']}", "Achievement count")
    verify_text_present(prompt, f"Total Challenges: {metrics['challenge_count']}", "Challenge count")
    verify_text_present(prompt, f"Average Sentiment: {metrics['avg_sentiment']}", "Average sentiment")
    verify_text_present(prompt, f"Sentiment Trend: {metrics['sentiment_trend']}", "Sentiment trend")
    verify_text_present(prompt, f"Performance Stability: {metrics['performance_stability']}", "Performance stability")
    verify_text_present(prompt, f"Weekly Reports Analyzed: {metrics['weekly_report_count']}", "Weekly report count")
    verify_text_present(prompt, f"Task Reliability Trend: {metrics['task_reliability_trend']}", "Task reliability trend")
    verify_text_present(prompt, f"Quality Consistency Trend: {metrics['quality_consistency_trend']}", "Quality consistency trend")
    verify_text_present(prompt, f"Risk Trend: {metrics['risk_trend']}", "Risk trend")
    verify_text_present(prompt, f"Challenge Resolution Trend: {metrics['challenge_resolution_trend']}", "Challenge resolution trend")
    verify_text_present(prompt, f"Achievement Impact Average: {metrics['achievement_impact_avg']}", "Achievement impact average")
    
    # Credibility data verification
    credibility_data = metrics['weekly_credibility_data']
    verify_text_present(prompt, f"Average Credibility Rating: {credibility_data['avg_credibility_rating']}", "Average credibility rating")
    verify_text_present(prompt, f"Credibility Trend: {credibility_data['credibility_trend']}", "Credibility trend")
    verify_text_present(prompt, f"Exaggeration Frequency: {credibility_data['exaggeration_frequency']}", "Exaggeration frequency")
    
    # Performance rating verification
    perf_rating = metrics['performance_rating_aggregation']
    verify_text_present(prompt, f"Most Common Rating: {perf_rating['most_common_rating']}", "Most common performance rating")
    verify_text_present(prompt, f"Rating Trend: {perf_rating['rating_trend']}", "Performance rating trend")
    
    # Verify all months are included
    monthly_analyses = quarterly_data["monthly_analyses"]
    for monthly_analysis in monthly_analyses:
        month_name = monthly_analysis.get("month_name")
        verify_text_present(prompt, f"MONTHLY ANALYSIS: {month_name}", f"Monthly analysis for {month_name}")
    
    # Verify all weeks are included
    weekly_analyses = quarterly_data["weekly_analyses"]
    week_count = 0
    for week_analysis in weekly_analyses:
        week_start = week_analysis.get("period_start", "Unknown")
        if week_start in prompt:
            week_count += 1
    
    print(f"\n✅ Weekly analyses included in prompt: {week_count}/{len(weekly_analyses)}")
    if week_count != len(weekly_analyses):
        print(f"⚠️ WARNING: Not all weekly analyses were included in the prompt!")
    
    # Check recurring topics
    if metrics.get("recurring_topics"):
        for topic in metrics["recurring_topics"][:3]:  # Check first 3 topics
            verify_text_present(prompt, topic, f"Recurring topic: {topic}")
    
    # Check detailed topics
    if metrics.get("detailed_topics"):
        for topic_data in metrics["detailed_topics"][:3]:  # Check first 3 detailed topics
            topic = topic_data.get("topic")
            verify_text_present(prompt, topic, f"Detailed topic: {topic}")
    
    # Check monthly summaries
    if metrics.get("monthly_summaries"):
        for summary_data in metrics["monthly_summaries"]:
            month = summary_data.get("month")
            verify_text_present(prompt, month, f"Monthly summary for {month}")
    
    # Basic structure check
    print("\nPrompt Statistics:")
    print(f"Prompt length: {len(prompt)} characters")
    print(f"Number of lines: {prompt.count(chr(10)) + 1}")
    print(f"Monthly analyses included: {prompt.count('MONTHLY ANALYSIS:')}")
    print(f"Weekly analyses included: {prompt.count('WEEK')}")
    
    return prompt

def verify_text_present(text, search_text, label):
    """Helper function to verify text is present and output formatted result"""
    if search_text in text:
        print(f"✅ {label} - PRESENT")
    else:
        print(f"❌ {label} - MISSING")

if __name__ == "__main__":
    print("Running comprehensive test for quarterly analysis prompt...")
    prompt = test_quarterly_analysis_prompt()
    print("\nTest completed.")
