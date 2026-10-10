import unittest
from unittest.mock import patch
from datetime import date
import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.quarterly_analysis_db_service import get_quarterly_data_for_analysis

class TestQuarterlyAnalysisDBService(unittest.TestCase):
    """Comprehensive test cases for quarterly analysis database service functions."""

    @patch('app.services.quarterly_analysis_db_service.get_quarter_date_range')
    @patch('app.services.quarterly_analysis_db_service.get_employee_info')
    @patch('app.services.quarterly_analysis_db_service.get_monthly_analyses_for_quarter')
    @patch('app.services.quarterly_analysis_db_service.get_weekly_analyses_for_quarter')
    def test_get_quarterly_data_for_analysis(self, mock_get_weekly, mock_get_monthly, mock_get_employee, mock_get_date_range):
        """Test that quarterly analysis data is correctly aggregated with all fields properly calculated."""
        # Set up date range mock
        mock_get_date_range.return_value = (date(2023, 1, 1), date(2023, 3, 31))
        
        # Set up employee info mock
        mock_get_employee.return_value = {
            "id": 123,
            "name": "Test Employee",
            "wing": "Engineering",
            "position": "Software Developer"
        }
        
        # Create test monthly analyses with comprehensive test data
        monthly_analyses = [
            {
                # January data with improving metrics
                "analysis_id": 1,
                "month": 1,
                "month_name": "January",
                "year": 2023,
                "period_start": date(2023, 1, 1),
                "period_end": date(2023, 1, 31),
                "progress_trends": {
                    "performance_trend": "improving",
                    "sentiment_trend": "stable",
                    "risk_level_pattern": "decreasing",
                    "challenge_resolution_progress": "improved"
                },
                "monthly_achievements": [
                    {"description": "Achievement 1", "impact": "8 (High business impact)"},
                    {"description": "Achievement 2", "impact": "7 (Significant progress)"}
                ],
                "recurring_challenges": [
                    {"description": "Challenge 1", "severity": "medium", "status": "ongoing"}
                ],
                "consistency_assessment": {
                    "task_completion_reliability": "high",
                    "work_quality_consistency": "medium",
                    "performance_stability": "high",
                    "notable_strengths": ["Strength 1"],
                    "notable_weaknesses": ["Weakness 1"]
                },
                "growth_indicators": {
                    "complexity_of_tasks": "increased",
                    "skill_development_evidence": "high",
                    "confidence_level_change": "increased",
                    "approach_to_challenges": "more proactive"
                },
                "achievement_impact_avg": 7.5,
                "monthly_risk_assessment": {
                    "overall_risk_level": "medium",
                    "risk_explanation": "Some risks present",
                    "significant_risks": ["Risk 1"],
                    "escalating_risks": [],
                    "risk_mitigation_recommendations": ["Mitigation 1"]
                },
                "weekly_report_ids": ["id1", "id2", "id3", "id4"],
                "avg_sentiment_score": 0.7,
                "monthly_summary": "January summary"
            },
            {
                # February data with further improvement
                "analysis_id": 2,
                "month": 2,
                "month_name": "February",
                "year": 2023,
                "period_start": date(2023, 2, 1),
                "period_end": date(2023, 2, 28),
                "progress_trends": {
                    "performance_trend": "improving",
                    "sentiment_trend": "improving",
                    "risk_level_pattern": "stable",
                    "challenge_resolution_progress": "improved"
                },
                "monthly_achievements": [
                    {"description": "Achievement 3", "impact": "9 (Major business impact)"}
                ],
                "recurring_challenges": [
                    {"description": "Challenge 1", "severity": "low", "status": "improving"},
                    {"description": "Challenge 2", "severity": "medium", "status": "ongoing"}
                ],
                "consistency_assessment": {
                    "task_completion_reliability": "high",
                    "work_quality_consistency": "high",
                    "performance_stability": "high",
                    "notable_strengths": ["Strength 1", "Strength 2"],
                    "notable_weaknesses": []
                },
                "growth_indicators": {
                    "complexity_of_tasks": "increased",
                    "skill_development_evidence": "high",
                    "confidence_level_change": "increased",
                    "approach_to_challenges": "more proactive"
                },
                "achievement_impact_avg": 9.0,
                "monthly_risk_assessment": {
                    "overall_risk_level": "low",
                    "risk_explanation": "Risks mitigated",
                    "significant_risks": [],
                    "escalating_risks": [],
                    "risk_mitigation_recommendations": []
                },
                "weekly_report_ids": ["id5", "id6", "id7", "id8"],
                "avg_sentiment_score": 0.85,
                "monthly_summary": "February summary"
            },
            {
                # March data with slight performance plateau
                "analysis_id": 3,
                "month": 3,
                "month_name": "March",
                "year": 2023,
                "period_start": date(2023, 3, 1),
                "period_end": date(2023, 3, 31),
                "progress_trends": {
                    "performance_trend": "stable",
                    "sentiment_trend": "stable",
                    "risk_level_pattern": "decreasing",
                    "challenge_resolution_progress": "unchanged"
                },
                "monthly_achievements": [
                    {"description": "Achievement 4", "impact": "8 (High business impact)"},
                    {"description": "Achievement 5", "impact": "7 (Significant progress)"}
                ],
                "recurring_challenges": [
                    {"description": "Challenge 2", "severity": "low", "status": "improving"}
                ],
                "consistency_assessment": {
                    "task_completion_reliability": "medium",
                    "work_quality_consistency": "high",
                    "performance_stability": "medium",
                    "notable_strengths": ["Strength 3"],
                    "notable_weaknesses": ["Weakness 2"]
                },
                "growth_indicators": {
                    "complexity_of_tasks": "unchanged",
                    "skill_development_evidence": "medium",
                    "confidence_level_change": "unchanged",
                    "approach_to_challenges": "unchanged"
                },
                "achievement_impact_avg": 7.5,
                "monthly_risk_assessment": {
                    "overall_risk_level": "low",
                    "risk_explanation": "Minimal risks",
                    "significant_risks": [],
                    "escalating_risks": [],
                    "risk_mitigation_recommendations": []
                },
                "weekly_report_ids": ["id9", "id10", "id11", "id12"],
                "avg_sentiment_score": 0.8,
                "monthly_summary": "March summary"
            }
        ]
        
        mock_get_monthly.return_value = monthly_analyses
        
        # Create detailed weekly analyses for comprehensive testing
        weekly_analyses = []
        
        # Create January weekly analyses (4 weeks)
        january_dates = [date(2023, 1, 7), date(2023, 1, 14), date(2023, 1, 21), date(2023, 1, 28)]
        for i, week_date in enumerate(january_dates):
            weekly_analyses.append({
                "analysis_id": 100 + i,
                "report_id": f"id{i+1}",
                "date": week_date,
                "sentiment_score": 0.7 + (i * 0.05),  # Gradually increasing sentiment
                "risk_level": "medium",
                "risk_explanation": "Some technical challenges present",
                "credibility_rating": "high",
                "credibility_explanation": "Report is detailed and realistic",
                "exaggeration_flags": [],
                "consistency_score": "high",
                "performance_rating": "medium" if i < 2 else "high",  # Improving performance
                "performance_summary": f"Week {i+1} performance summary",
                "topics": ["API Design", "Testing", "Code Quality"]
            })
        
        # Create February weekly analyses (4 weeks)
        february_dates = [date(2023, 2, 4), date(2023, 2, 11), date(2023, 2, 18), date(2023, 2, 25)]
        for i, week_date in enumerate(february_dates):
            weekly_analyses.append({
                "analysis_id": 200 + i,
                "report_id": f"id{i+5}",
                "date": week_date,
                "sentiment_score": 0.85,
                "risk_level": "low" if i > 1 else "medium",  # Decreasing risk
                "risk_explanation": "Risks being mitigated",
                "credibility_rating": "high",
                "credibility_explanation": "Report is detailed and realistic",
                "exaggeration_flags": [f"Slight exaggeration {i}"] if i == 2 else [],  # One week with exaggeration
                "consistency_score": "high",
                "performance_rating": "high",
                "performance_summary": f"Week {i+1} of February performance summary",
                "topics": ["Deployment", "CI/CD", "Documentation", "Testing"]
            })
        
        # Create March weekly analyses (4 weeks)
        march_dates = [date(2023, 3, 4), date(2023, 3, 11), date(2023, 3, 18), date(2023, 3, 25)]
        for i, week_date in enumerate(march_dates):
            weekly_analyses.append({
                "analysis_id": 300 + i,
                "report_id": f"id{i+9}",
                "date": week_date,
                "sentiment_score": 0.8,
                "risk_level": "low",
                "risk_explanation": "Minimal risks",
                "credibility_rating": "medium" if i == 0 else "high",  # One week with medium credibility
                "credibility_explanation": "Report is generally realistic",
                "exaggeration_flags": [],
                "consistency_score": "high",
                "performance_rating": "high" if i < 2 else "medium",  # Slight decline in performance
                "performance_summary": f"Week {i+1} of March performance summary",
                "topics": ["Maintenance", "Documentation", "Code Review", "Mentoring"]
            })
        
        mock_get_weekly.return_value = weekly_analyses
        
        # Call the function
        result = get_quarterly_data_for_analysis(123, 2023, 1)
        
        # PART 1: TEST BASIC STRUCTURE AND METADATA
        print("\n=== Testing Basic Structure and Metadata ===")
        self.assertEqual(result["year"], 2023, "Year should be 2023")
        self.assertEqual(result["quarter"], 1, "Quarter should be 1")
        self.assertEqual(result["employee_id"], 123, "Employee ID should be 123")
        self.assertEqual(result["period_start"], date(2023, 1, 1), "Period start should be Jan 1, 2023")
        self.assertEqual(result["period_end"], date(2023, 3, 31), "Period end should be Mar 31, 2023")
        self.assertEqual(result["employee_info"]["name"], "Test Employee", "Employee name should be Test Employee")
        self.assertEqual(len(result["monthly_analyses"]), 3, "Should have 3 monthly analyses")
        self.assertEqual(len(result["weekly_analyses"]), 12, "Should have 12 weekly analyses")
        
        # PART 2: TEST METRICS - GENERAL STATS
        print("\n=== Testing General Metrics ===")
        metrics = result["metrics"]
        
        # Test sentiment aggregation (weighted average)
        expected_sentiment = ((0.7 * 4) + (0.85 * 4) + (0.8 * 4)) / 12
        self.assertAlmostEqual(metrics["avg_sentiment"], expected_sentiment, delta=0.05, 
                             msg="Average sentiment should be weighted by report count")
        
        # Verify all trend fields have valid values, with special handling for risk_trend
        # risk_trend uses "increasing/decreasing" while other trends use "improving/declining"
        trend_fields = ["sentiment_trend", "performance_trend", 
                       "task_reliability_trend", "quality_consistency_trend",
                       "challenge_resolution_trend"]
        for field in trend_fields:
            self.assertIn(metrics[field], ["improving", "declining", "stable"], 
                        msg=f"{field} should have a valid trend value")
        
        # Risk trend uses a different set of valid values
        self.assertIn(metrics["risk_trend"], ["increasing", "decreasing", "stable"],
                    msg="risk_trend should be one of increasing/decreasing/stable")
        
        # Test achievement and challenge counts
        self.assertEqual(metrics["achievement_count"], 5, 
                       msg="Achievement count should be the sum of all monthly achievements")
        self.assertEqual(metrics["challenge_count"], 4, 
                       msg="Challenge count should be the sum of all monthly challenges")
        
        # Verify risk_levels object structure
        self.assertIsInstance(metrics["risk_levels"], dict, 
                            msg="Risk levels should be a dictionary")
        
        # Verify all stability metrics have valid values
        self.assertIn(metrics["performance_stability"], ["high", "medium", "low"], 
                    msg="Performance stability should be a valid value")
        
        # PART 3: TEST ACHIEVEMENT IMPACT AVERAGE - MORE DETAILED
        print("\n=== Testing Achievement Impact Average ===")
        # Jan: 2 achievements with avg 7.5, Feb: 1 achievement with avg 9.0, Mar: 2 achievements with avg 7.5
        # Weighted average: ((7.5 * 2) + (9.0 * 1) + (7.5 * 2)) / 5 = 7.8
        expected_impact_avg = ((7.5 * 2) + (9.0 * 1) + (7.5 * 2)) / 5
        self.assertAlmostEqual(metrics["achievement_impact_avg"], expected_impact_avg, delta=0.1,
                             msg="Achievement impact average should be weighted by achievement count")
        
        # Test specific calculation method to ensure it's properly weighted by achievement count
        # Validate individual month contributions
        jan_contribution = 7.5 * 2  # Jan impact avg * Jan achievement count
        feb_contribution = 9.0 * 1  # Feb impact avg * Feb achievement count
        mar_contribution = 7.5 * 2  # Mar impact avg * Mar achievement count
        self.assertAlmostEqual(metrics["achievement_impact_avg"], 
                             (jan_contribution + feb_contribution + mar_contribution) / 5, 
                             delta=0.1,
                             msg="Achievement impact calculation should use correct weighting formula")
        
        # PART 4: TEST CONSISTENCY METRICS
        print("\n=== Testing Consistency Metrics ===")
        self.assertIn(metrics["performance_stability"], ["high", "medium", "low"], 
                    msg="Performance stability should be a valid value")
        self.assertIn(metrics["task_reliability_trend"], ["improving", "declining", "stable"], 
                    msg="Task reliability trend should be a valid trend value")
        self.assertIn(metrics["quality_consistency_trend"], ["improving", "declining", "stable"], 
                    msg="Quality consistency trend should be a valid trend value")
        
        # PART 5: TEST RISK TREND (CONTEXT-AWARE) - DETAILED TESTING
        print("\n=== Testing Risk Trend (Context-Aware) ===")
        # Risk levels: Jan: medium, Feb: low, Mar: low - should show a decreasing trend
        self.assertEqual(metrics["risk_trend"], "decreasing", 
                       msg="Risk trend should be decreasing based on the mock data")
        
        # Verify that the risk trend inversion logic works correctly
        # In this case, risk values go from 1 (medium) to 0 (low) which in raw numbers is declining
        # But should be reported as "decreasing" risk which is good
        self.assertNotEqual(metrics["risk_trend"], "declining",
                          msg="Risk trend should use context-aware inversion")
        
        # PART 6: TEST MONTHLY SUMMARIES COLLECTION - EXPANDED
        print("\n=== Testing Monthly Summaries Collection ===")
        self.assertEqual(len(metrics["monthly_summaries"]), 3, 
                       msg="Should have 3 monthly summaries")
        # Verify month names are present
        month_names = [summary["month"] for summary in metrics["monthly_summaries"]]
        for month in ["January", "February", "March"]:
            self.assertIn(month, month_names, 
                        msg=f"Month {month} should be in the summaries")
        
        # PART 7: TEST WEEKLY CREDIBILITY DATA - MORE COMPREHENSIVE
        print("\n=== Testing Weekly Credibility Data ===")
        credibility_data = metrics["weekly_credibility_data"]
        self.assertIn(credibility_data["avg_credibility_rating"], ["high", "medium", "low", None], 
                    msg="Average credibility rating should be a valid value")
        self.assertIn(credibility_data["credibility_trend"], ["improving", "declining", "stable"], 
                    msg="Credibility trend should be a valid trend value")
        self.assertEqual(credibility_data["exaggeration_frequency"], 1, 
                       msg="Should have 1 exaggeration instance in the test data")
        
        # Verify average credibility is calculated correctly
        # In our test data, most ratings are "high" with a few "medium"
        self.assertEqual(credibility_data["avg_credibility_rating"], "high",
                       msg="Average credibility should be high based on test data")
        
        # PART 8: TEST PERFORMANCE RATING AGGREGATION - EXPANDED
        print("\n=== Testing Performance Rating Aggregation ===")
        perf_aggregation = metrics["performance_rating_aggregation"]
        self.assertEqual(perf_aggregation["most_common_rating"], "high", 
                       msg="Most common rating should be 'high' based on test data")
        
        # Test specific distribution values
        self.assertIsInstance(perf_aggregation["rating_distribution"], dict, 
                            msg="Rating distribution should be a dictionary")
        # Check specific distribution values
        self.assertGreater(perf_aggregation["rating_distribution"].get("high", 0), 
                         perf_aggregation["rating_distribution"].get("medium", 0),
                         msg="Distribution should show more high ratings than medium")
        
        # Check that rating distribution percentages add up to 1.0
        total_percentage = sum(perf_aggregation["rating_distribution"].values())
        self.assertAlmostEqual(total_percentage, 1.0, delta=0.001, 
                             msg="Rating distribution percentages should add up to 1.0")
                          
        # Test performance rating count matches the actual number of ratings
        total_rating_count = len([a for a in weekly_analyses if a.get("performance_rating")])
        
        # Calculate the actual counts from the distribution percentages and total count
        calculated_total = 0
        if perf_aggregation["rating_distribution"] and len(metrics["weekly_performance_ratings"]) > 0:
            calculated_total = len(metrics["weekly_performance_ratings"])
            self.assertEqual(calculated_total, total_rating_count,
                           msg="Total ratings in distribution should match number of ratings in data")
        
        # PART 9: TEST TOPIC ANALYSIS - EXPANDED
        print("\n=== Testing Topic Analysis ===")
        # Test recurring topics
        self.assertIsInstance(metrics["recurring_topics"], list, 
                            msg="Recurring topics should be a list")
        # Verify specific topics from our test data
        expected_topics = ["Testing", "Documentation"]
        for topic in expected_topics:
            self.assertIn(topic, metrics["recurring_topics"], 
                        msg=f"'{topic}' should be identified as a recurring topic")
        
        # Test detailed topics structure
        self.assertIsInstance(metrics["detailed_topics"], list, 
                            msg="Detailed topics should be a list")
        self.assertLessEqual(len(metrics["detailed_topics"]), 10, 
                           msg="Should have at most 10 detailed topics")
        if metrics["detailed_topics"]:
            topic_item = metrics["detailed_topics"][0]
            self.assertIn("topic", topic_item, 
                        msg="Each detailed topic should have a 'topic' field")
            self.assertIn("frequency", topic_item, 
                        msg="Each detailed topic should have a 'frequency' field")
            self.assertIsInstance(topic_item["frequency"], int,
                               msg="Topic frequency should be an integer")
        
        # Verify detailed topics are ordered by frequency
        if len(metrics["detailed_topics"]) >= 2:
            first_freq = metrics["detailed_topics"][0]["frequency"]
            second_freq = metrics["detailed_topics"][1]["frequency"]
            self.assertGreaterEqual(first_freq, second_freq,
                                 msg="Detailed topics should be ordered by frequency (most common first)")
        
        # PART 10: TEST WEEKLY PERFORMANCE RATINGS STRUCTURE
        print("\n=== Testing Weekly Performance Ratings Structure ===")
        self.assertIsInstance(metrics["weekly_performance_ratings"], list,
                            msg="Weekly performance ratings should be a list")
        if metrics["weekly_performance_ratings"]:
            rating_entry = metrics["weekly_performance_ratings"][0]
            self.assertIn("date", rating_entry,
                        msg="Each performance rating should have a date")
            self.assertIn("rating", rating_entry,
                        msg="Each performance rating should have a rating value")
        
        # PART 11: TEST THAT ALL METRICS FIELDS ARE PRESENT
        print("\n=== Testing Completeness of Metrics ===")
        expected_metrics = [
            "avg_sentiment", "sentiment_trend", "risk_levels", "recurring_topics",
            "achievement_count", "challenge_count", "weekly_report_count",
            "performance_stability", "monthly_progress_trends", "task_reliability_trend",
            "quality_consistency_trend", "risk_trend", "challenge_resolution_trend",
            "monthly_summaries", "achievement_impact_avg", "weekly_credibility_data",
            "detailed_topics", "weekly_performance_ratings", "performance_rating_aggregation"
        ]
        for field in expected_metrics:
            self.assertIn(field, metrics, f"Metrics should include '{field}'")
        
        print("\nAll tests passed successfully! Function is working correctly.")
        
        # Return the result for potential further tests
        return result

    def test_edge_cases(self):
        """Test handling of edge cases such as missing data."""
        with patch('app.services.quarterly_analysis_db_service.get_quarter_date_range') as mock_get_date_range, \
             patch('app.services.quarterly_analysis_db_service.get_employee_info') as mock_get_employee, \
             patch('app.services.quarterly_analysis_db_service.get_monthly_analyses_for_quarter') as mock_get_monthly, \
             patch('app.services.quarterly_analysis_db_service.get_weekly_analyses_for_quarter') as mock_get_weekly:
            
            # Set up basic mocks
            mock_get_date_range.return_value = (date(2023, 1, 1), date(2023, 3, 31))
            mock_get_employee.return_value = {"id": 123, "name": "Test Employee", "wing": "Engineering", "position": "Developer"}
            
            # CASE 1: No monthly or weekly data
            print("\n=== Testing Edge Case: No Monthly or Weekly Data ===")
            mock_get_monthly.return_value = []
            mock_get_weekly.return_value = []
            
            result = get_quarterly_data_for_analysis(123, 2023, 1)
            
            # Verify default values are used when no data is available
            self.assertEqual(result["metrics"]["avg_sentiment"], 0.0, "Default sentiment should be 0.0")
            self.assertEqual(result["metrics"]["sentiment_trend"], "stable", "Default sentiment trend should be 'stable'")
            self.assertEqual(result["metrics"]["risk_trend"], "stable", "Default risk trend should be 'stable'")
            self.assertEqual(result["metrics"]["achievement_count"], 0, "Achievement count should be 0")
            
            # CASE 2: Only one month of data (no trend analysis possible)
            print("\n=== Testing Edge Case: Single Month Data ===")
            mock_get_monthly.return_value = [{
                "analysis_id": 1,
                "month": 1,
                "month_name": "January",
                "year": 2023,
                "avg_sentiment_score": 0.8,
                "monthly_achievements": [{"description": "Achievement", "impact": "8 (Impact)"}],
                "monthly_risk_assessment": {"overall_risk_level": "medium"},
                "weekly_report_ids": ["id1", "id2"],
                "achievement_impact_avg": 8.0,
                "monthly_summary": "Summary"
            }]
            mock_get_weekly.return_value = []
            
            result = get_quarterly_data_for_analysis(123, 2023, 1)
            
            # Verify values from single month are used, but trends remain stable
            self.assertEqual(result["metrics"]["avg_sentiment"], 0.8, "Should use single month sentiment")
            self.assertEqual(result["metrics"]["sentiment_trend"], "stable", "Trend should be 'stable' with only one month")
            self.assertEqual(result["metrics"]["achievement_count"], 1, "Should count the single achievement")
            
            # CASE 3: Employee not found
            print("\n=== Testing Edge Case: Employee Not Found ===")
            mock_get_employee.return_value = None
            
            result = get_quarterly_data_for_analysis(999, 2023, 1)
            
            # Verify early return with empty structure
            self.assertIsNone(result["employee_info"], "Employee info should be None")
            self.assertEqual(result["metrics"]["avg_sentiment"], 0.0, "Metrics should have default values")
            
            print("\nEdge case tests completed successfully!")

if __name__ == "__main__":
    unittest.main()
