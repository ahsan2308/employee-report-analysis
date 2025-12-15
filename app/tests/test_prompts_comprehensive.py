"""
Comprehensive Test Suite for Analysis Prompts

This script tests all three analysis prompt types (weekly, monthly, quarterly)
to ensure they generate correctly with all expected sections and fields.

Tests cover:
1. Weekly analysis prompt with/without JD, vision, historical data
2. Monthly analysis prompt with/without JD, vision, role transitions
3. Quarterly analysis prompt with/without JD, vision, career progression

Run with: python -m pytest tests/test_prompts_comprehensive.py -v
Or: python tests/test_prompts_comprehensive.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, Any, List
import json
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.prompts.structured_prompts import StructuredPrompts


class TestData:
    """Mock test data generator for prompt testing"""
    
    @staticmethod
    def create_weekly_report() -> str:
        """Create a mock weekly report"""
        return """
WEEKLY PERFORMANCE REPORT - Week Ending 2025-12-12

1. TASKS COMPLETED:
- Completed data migration for customer database (500+ records)
- Implemented new authentication system for admin portal
- Resolved 15 critical bug tickets from backlog
- Conducted code review for 3 team members' pull requests

2. IMPACT/OUTCOMES:
- Data migration reduced query time by 40%
- Authentication system improved security compliance score from 75% to 95%
- Bug resolution improved system stability metrics
- Code reviews identified 8 potential issues before production

3. CHALLENGES/OBSTACLES:
- Legacy system compatibility issues delayed testing by 1 day
- Limited documentation for authentication module required extra research time
- High priority production issue interrupted planned work on Wednesday

4. REQUIRED TOOLS/SUPPORT:
- Access to staging environment for testing (currently restricted)
- Documentation for legacy API endpoints
- Additional QA resource for regression testing

5. TASKS PLANNED FOR NEXT WEEK:
- Complete integration testing for authentication system
- Begin work on payment gateway refactoring
- Update technical documentation for data migration process
- Mentor junior developer on code review best practices

6. CONFIDENCE LEVEL: 4/5
- Well prepared for planned tasks
- Some uncertainty around payment gateway complexity
"""

    @staticmethod
    def create_vision_data() -> str:
        """Create mock vision system data"""
        return """
Current Period Activity Data:

Main Entities Tracked (Week of 2025-12-06 to 2025-12-12):
- customer_database: 47 activities (migrations, queries, optimizations)
- authentication_system: 31 activities (implementation, testing, configuration)
- bug_tracker: 23 activities (ticket resolution, status updates)
- code_review_system: 12 activities (reviews, comments, approvals)

Entity Details:
customer_database:
  - Last Activity: 2025-12-12 16:30 (migration completion)
  - Activity Pattern: High intensity Mon-Thu, reduced Fri
  - Key Milestones: Initial migration (Mon), testing (Wed), completion (Thu)

authentication_system:
  - Last Activity: 2025-12-12 14:15 (security testing)
  - Activity Pattern: Consistent throughout week
  - Key Milestones: Module implementation (Tue), integration (Wed-Thu)

Historical Activity Data:

customer_database (Previous 4 weeks):
  - Week 1: 12 activities
  - Week 2: 18 activities
  - Week 3: 25 activities
  - Week 4: 47 activities (current)
  - Trend: Steadily increasing engagement

authentication_system:
  - Week 1: 0 activities (not started)
  - Week 2: 8 activities (planning)
  - Week 3: 15 activities (initial implementation)
  - Week 4: 31 activities (full implementation)
"""

    @staticmethod
    def create_recent_reports() -> List[Dict[str, Any]]:
        """Create mock recent reports"""
        return [
            {
                "date": date(2025, 12, 5),
                "text": """Previous Week Report:
- Completed requirements gathering for authentication system
- Fixed 8 bug tickets
- Prepared data migration plan
- Challenges: Unclear requirements for authentication
- Planning: Start data migration next week
- Confidence: 3/5"""
            },
            {
                "date": date(2025, 11, 28),
                "text": """Two Weeks Ago Report:
- Completed user dashboard redesign
- Resolved 12 support tickets
- Updated API documentation
- Challenges: Limited testing resources
- Planning: Requirements gathering for auth system
- Confidence: 4/5"""
            }
        ]

    @staticmethod
    def create_similar_reports() -> List[Dict[str, Any]]:
        """Create mock similar reports"""
        return [
            {
                "date": date(2025, 10, 15),
                "text": """Similar Task Report (Data Migration):
- Completed migration of order database
- Migrated 1000+ records with validation
- Improved performance by 35%
- Challenges: Data integrity issues in legacy system
- Outcome: Successful migration with zero downtime"""
            },
            {
                "date": date(2025, 9, 20),
                "text": """Similar Task Report (Authentication):
- Implemented OAuth2 authentication for API
- Integrated with existing user management
- Challenges: Third-party service integration delays
- Outcome: Improved API security significantly"""
            }
        ]

    @staticmethod
    def create_single_jd() -> str:
        """Create mock single job description"""
        return """## EMPLOYEE JOB DESCRIPTION

Role: Senior Software Developer
Effective since: 2024-11-01

**Core Responsibilities**:
- Design, develop, and maintain software applications
- Write clean, maintainable, and well-documented code
- Conduct code reviews and mentor junior developers
- Participate in architectural decisions
- Debug and resolve production issues
- Collaborate with cross-functional teams

**Required Competencies**:
- Proficiency in Python, JavaScript, and SQL
- Experience with web frameworks (Django, React)
- Strong problem-solving and debugging skills
- Effective communication and collaboration
- Ability to work independently and manage priorities
- Understanding of software development best practices

**Performance Expectations**:
- Deliver high-quality code on schedule
- Maintain system reliability and performance
- Contribute to technical documentation
- Mentor and support team members
- Proactively identify and address technical debt"""

    @staticmethod
    def create_concurrent_jds() -> str:
        """Create mock concurrent job descriptions"""
        return """## EMPLOYEE JOB DESCRIPTIONS

The employee currently holds multiple roles:

### Job Description #1 (Effective since 2024-11-01):
**Role**: Senior Software Developer

**Core Responsibilities**:
- Design and develop software applications
- Code review and mentoring
- Technical architecture participation

### Job Description #2 (Effective since 2025-09-15):
**Role**: Team Lead (Acting)

**Core Responsibilities**:
- Coordinate team activities and sprint planning
- Conduct performance reviews for 3 junior developers
- Liaison between development team and product management
- Resource allocation and workload balancing

**ANALYSIS GUIDANCE**:
- Evaluate achievements against expectations from BOTH roles
- Consider workload distribution across multiple responsibilities
- Assess time management and prioritization given dual role requirements"""

    @staticmethod
    def create_transition_jd() -> str:
        """Create mock job description showing role transition"""
        return """## EMPLOYEE JOB DESCRIPTIONS AND ROLE TRANSITIONS

The employee's role changed during this month:

### PERIOD 1: 2025-11-01 to 2025-11-30
**Previous Role**: Software Developer

**Core Responsibilities**:
- Develop and maintain applications
- Write and review code
- Fix bugs and resolve issues

Reports from this period:
- Report for week 2025-11-01 to 2025-11-07
- Report for week 2025-11-08 to 2025-11-14
- Report for week 2025-11-15 to 2025-11-21
- Report for week 2025-11-22 to 2025-11-30

---

### PERIOD 2: 2025-12-01 to 2025-12-31
**Current Role**: Senior Software Developer

**Core Responsibilities**:
- Lead technical initiatives and architecture decisions
- Mentor junior developers and conduct code reviews
- Own critical system components
- Participate in hiring and technical planning

Reports from this period:
- Report for week 2025-12-01 to 2025-12-07
- Report for week 2025-12-08 to 2025-12-14 (current)

**ANALYSIS GUIDANCE**:
- Evaluate each report against the JD applicable during that time period
- Assess transition effectiveness from Developer to Senior Developer
- Note performance trajectory across the role change
- Consider adaptation to increased responsibilities"""

    @staticmethod
    def create_monthly_data_basic() -> Dict[str, Any]:
        """Create mock monthly analysis data without JD"""
        return {
            "employee_info": {
                "name": "John Smith",
                "position": "Senior Software Developer",
                "wing": "Engineering Department"
            },
            "year": 2025,
            "month": 12,
            "period_start": date(2025, 12, 1),
            "period_end": date(2025, 12, 31),
            "reports": [
                {
                    "date": date(2025, 12, 7),
                    "text": "Week 1 report: Completed authentication system planning..."
                },
                {
                    "date": date(2025, 12, 14),
                    "text": "Week 2 report: Implemented authentication and data migration..."
                }
            ],
            "analyses": [
                {
                    "date": date(2025, 12, 7),
                    "sentiment_score": 0.7,
                    "risk_level": "medium",
                    "risk_explanation": "Resource constraints may impact timeline",
                    "achievements": [
                        {"description": "Completed auth system requirements", "impact": "7 (Team level planning completed)"}
                    ],
                    "challenges": [
                        {"description": "Limited documentation", "severity": "medium"}
                    ],
                    "action_items": ["Request staging access", "Schedule QA resource"],
                    "topics": ["authentication", "planning", "requirements"],
                    "credibility_rating": "high",
                    "credibility_explanation": "Specific deliverables with realistic scope",
                    "consistency_score": "high",
                    "performance_rating": "high",
                    "performance_summary": "Strong planning and execution",
                    "performance_strengths": ["Thorough requirements gathering", "Proactive planning"],
                    "performance_improvement_areas": ["Documentation gaps"]
                },
                {
                    "date": date(2025, 12, 14),
                    "sentiment_score": 0.8,
                    "risk_level": "low",
                    "risk_explanation": "On track with strong progress",
                    "achievements": [
                        {"description": "Implemented authentication system", "impact": "9 (Department level security improvement)"},
                        {"description": "Completed data migration", "impact": "8 (Team level performance boost)"}
                    ],
                    "challenges": [
                        {"description": "Legacy compatibility issues", "severity": "medium"}
                    ],
                    "action_items": ["Complete integration testing", "Update documentation"],
                    "topics": ["authentication", "data migration", "testing"],
                    "credibility_rating": "high",
                    "credibility_explanation": "Measurable outcomes with evidence",
                    "consistency_score": "high",
                    "performance_rating": "high",
                    "performance_summary": "Excellent execution and delivery",
                    "performance_strengths": ["High quality implementation", "Problem solving"],
                    "performance_improvement_areas": ["Time estimation accuracy"]
                }
            ],
            "metrics": {
                "avg_sentiment": 0.75,
                "sentiment_trend": "improving",
                "report_count": 2,
                "achievement_count": 3,
                "challenge_count": 2,
                "recurring_topics": ["authentication", "testing", "documentation"],
                "risk_levels": {"low": 1, "medium": 1}
            }
        }

    @staticmethod
    def create_monthly_data_with_jd() -> Dict[str, Any]:
        """Create mock monthly analysis data with JD"""
        data = TestData.create_monthly_data_basic()
        data["formatted_jd_data"] = TestData.create_transition_jd()
        data["formatted_vision_data"] = "Week 1: 45 activities on auth_system...\nWeek 2: 78 activities on database_migration..."
        return data

    @staticmethod
    def create_quarterly_data_basic() -> Dict[str, Any]:
        """Create mock quarterly analysis data without JD"""
        return {
            "employee_info": {
                "name": "John Smith",
                "position": "Senior Software Developer",
                "wing": "Engineering Department"
            },
            "year": 2025,
            "quarter": 4,
            "period_start": date(2025, 10, 1),
            "period_end": date(2025, 12, 31),
            "monthly_analyses": [
                {
                    "month": 10,
                    "month_name": "October",
                    "period_start": date(2025, 10, 1),
                    "period_end": date(2025, 10, 31),
                    "monthly_summary": "Strong performance with successful dashboard redesign and consistent bug resolution",
                    "progress_trends": {
                        "performance_trend": "improving",
                        "sentiment_trend": "positive"
                    },
                    "monthly_risk_assessment": {
                        "overall_risk_level": "low"
                    },
                    "monthly_achievements": [
                        {"description": "Completed user dashboard redesign", "impact": "8 (Improved UX for 1000+ users)"}
                    ],
                    "recurring_challenges": [
                        {"description": "Limited testing resources", "severity": "medium", "status": "ongoing"}
                    ],
                    "consistency_assessment": {
                        "task_completion_reliability": "high",
                        "work_quality_consistency": "high",
                        "performance_stability": "high"
                    },
                    "growth_indicators": {
                        "complexity_of_tasks": "increased",
                        "skill_development_evidence": "high"
                    },
                    "focus_areas": [
                        {"project": "User Dashboard", "time_investment": "high", "priority_level": "high"}
                    ],
                    "strategic_recommendations": [
                        {"action": "Expand testing resources", "priority": "high"}
                    ]
                },
                {
                    "month": 11,
                    "month_name": "November",
                    "period_start": date(2025, 11, 1),
                    "period_end": date(2025, 11, 30),
                    "monthly_summary": "Solid performance with focus on authentication planning and bug resolution",
                    "progress_trends": {
                        "performance_trend": "stable",
                        "sentiment_trend": "positive"
                    },
                    "monthly_risk_assessment": {
                        "overall_risk_level": "medium"
                    },
                    "monthly_achievements": [
                        {"description": "Completed authentication requirements", "impact": "7 (Foundation for security improvement)"}
                    ],
                    "recurring_challenges": [
                        {"description": "Documentation gaps", "severity": "medium", "status": "ongoing"}
                    ],
                    "consistency_assessment": {
                        "task_completion_reliability": "high",
                        "work_quality_consistency": "high",
                        "performance_stability": "high"
                    },
                    "growth_indicators": {
                        "complexity_of_tasks": "increased",
                        "skill_development_evidence": "medium"
                    },
                    "focus_areas": [
                        {"project": "Authentication System", "time_investment": "high", "priority_level": "high"}
                    ],
                    "strategic_recommendations": [
                        {"action": "Improve documentation practices", "priority": "medium"}
                    ]
                },
                {
                    "month": 12,
                    "month_name": "December",
                    "period_start": date(2025, 12, 1),
                    "period_end": date(2025, 12, 31),
                    "monthly_summary": "Excellent performance with successful authentication implementation and data migration",
                    "progress_trends": {
                        "performance_trend": "improving",
                        "sentiment_trend": "positive"
                    },
                    "monthly_risk_assessment": {
                        "overall_risk_level": "low"
                    },
                    "monthly_achievements": [
                        {"description": "Implemented authentication system", "impact": "9 (Major security improvement)"},
                        {"description": "Completed data migration", "impact": "8 (Performance optimization)"}
                    ],
                    "recurring_challenges": [
                        {"description": "Legacy system compatibility", "severity": "medium", "status": "resolved"}
                    ],
                    "consistency_assessment": {
                        "task_completion_reliability": "high",
                        "work_quality_consistency": "high",
                        "performance_stability": "high"
                    },
                    "growth_indicators": {
                        "complexity_of_tasks": "increased",
                        "skill_development_evidence": "high"
                    },
                    "focus_areas": [
                        {"project": "Authentication & Migration", "time_investment": "high", "priority_level": "high"}
                    ],
                    "strategic_recommendations": [
                        {"action": "Continue mentoring junior developers", "priority": "high"}
                    ]
                }
            ],
            "weekly_analyses": [],  # Would include weekly data
            "metrics": {
                "avg_sentiment": 0.77,
                "sentiment_trend": "improving",
                "achievement_count": 12,
                "challenge_count": 6,
                "recurring_topics": ["authentication", "testing", "documentation", "migration"],
                "risk_levels": {"low": 8, "medium": 4},
                "weekly_report_count": 12,
                "performance_stability": "high",
                "task_reliability_trend": "stable",
                "quality_consistency_trend": "stable",
                "risk_trend": "decreasing",
                "challenge_resolution_trend": "improved",
                "achievement_impact_avg": 7.8,
                "weekly_credibility_data": {
                    "avg_credibility_rating": "high",
                    "credibility_trend": "stable",
                    "exaggeration_frequency": 0
                },
                "detailed_topics": [
                    {"topic": "authentication", "frequency": 8},
                    {"topic": "testing", "frequency": 6},
                    {"topic": "documentation", "frequency": 5}
                ],
                "performance_rating_aggregation": {
                    "most_common_rating": "high",
                    "rating_trend": "improving",
                    "rating_distribution": {"high": 0.75, "medium": 0.25, "low": 0.0}
                },
                "monthly_progress_trends": [
                    {
                        "month": 10,
                        "performance_trend": "improving",
                        "sentiment_trend": "positive",
                        "risk_level_pattern": "stable",
                        "challenge_resolution_progress": "improved"
                    },
                    {
                        "month": 11,
                        "performance_trend": "stable",
                        "sentiment_trend": "positive",
                        "risk_level_pattern": "stable",
                        "challenge_resolution_progress": "unchanged"
                    },
                    {
                        "month": 12,
                        "performance_trend": "improving",
                        "sentiment_trend": "positive",
                        "risk_level_pattern": "decreasing",
                        "challenge_resolution_progress": "improved"
                    }
                ],
                "monthly_summaries": [
                    {"month": "October", "summary": "Strong dashboard redesign with consistent quality"},
                    {"month": "November", "summary": "Solid planning phase for authentication system"},
                    {"month": "December", "summary": "Excellent execution of authentication and migration"}
                ]
            }
        }

    @staticmethod
    def create_quarterly_data_with_jd() -> Dict[str, Any]:
        """Create mock quarterly analysis data with JD showing career progression"""
        data = TestData.create_quarterly_data_basic()
        data["formatted_jd_data"] = """## EMPLOYEE JOB DESCRIPTIONS AND CAREER PROGRESSION

📈 **CAREER TRAJECTORY ANALYSIS CONTEXT**:
The employee experienced 1 role transition(s) during this quarter.

### ROLE TIMELINE

PHASE 1: 2025-10-01 to 2025-11-30
Job Description: Software Developer

**Core Responsibilities**:
- Develop and maintain applications
- Write and review code
- Fix bugs and resolve issues

Weekly reports from this phase: 8 reports

---

PHASE 2: 2025-12-01 to 2025-12-31
Job Description: Senior Software Developer

**Core Responsibilities**:
- Lead technical initiatives and architecture decisions
- Mentor junior developers and conduct code reviews
- Own critical system components
- Participate in hiring and technical planning

Weekly reports from this phase: 4 reports

### STRATEGIC ANALYSIS GUIDANCE

1. ROLE PROGRESSION ASSESSMENT:
   - Analyze career trajectory across these role changes
   - Determine if transitions represent promotions (this is a promotion)
   - Evaluate readiness for the senior role based on Developer performance

2. TRANSITION IMPACT ANALYSIS:
   - Assess adaptation effectiveness for the promotion
   - Identify performance dips or spikes coinciding with role change
   - Evaluate whether transition required additional support"""
        
        data["formatted_vision_data"] = """October: 234 activities across 15 entities (dashboard_ui, testing_framework, bug_tracker...)
November: 198 activities across 12 entities (auth_requirements, api_design...)
December: 312 activities across 18 entities (auth_system, database_migration, code_reviews...)

Trend: Significant activity increase in December correlating with Senior Developer promotion"""
        
        return data


class PromptValidator:
    """Validates that prompts contain expected sections and content"""
    
    @staticmethod
    def validate_weekly_prompt(prompt: str, scenario: str) -> Dict[str, Any]:
        """Validate weekly analysis prompt structure"""
        results = {
            "scenario": scenario,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": [],
            "sections_found": []
        }
        
        # Core sections that should always be present
        required_sections = [
            "# WEEKLY EMPLOYEE PERFORMANCE ANALYSIS",
            "## TASK OVERVIEW AND EXPECTED OUTPUT",
            "## CRITICAL ANALYSIS INSTRUCTIONS",
            "## REPORT STRUCTURE CONTEXT",
            "## EMPLOYEE REPORT TO ANALYZE:",
            "## COMPREHENSIVE ANALYSIS REQUIREMENTS",
            "1. ACHIEVEMENTS ANALYSIS:",
            "2. CHALLENGES ASSESSMENT:",
            "3. SENTIMENT DETERMINATION:",
            "8. PERFORMANCE ASSESSMENT:"
        ]
        
        for section in required_sections:
            results["total_checks"] += 1
            if section in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append(section)
            else:
                results["failed_checks"].append(f"Missing section: {section}")
        
        # Check for JSON structure in output specification
        results["total_checks"] += 1
        if '"achievements":' in prompt and '"credibility_assessment":' in prompt:
            results["passed_checks"] += 1
            results["sections_found"].append("JSON Output Structure")
        else:
            results["failed_checks"].append("Missing JSON output structure")
        
        # Scenario-specific checks
        if "with_jd" in scenario:
            results["total_checks"] += 1
            if "## EMPLOYEE ROLE CONTEXT" in prompt and "JD-Based Performance Calibration" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("JD Integration")
            else:
                results["failed_checks"].append("Missing JD integration sections")
        
        if "with_vision" in scenario:
            results["total_checks"] += 1
            if "## OBJECTIVE TRACKING DATA" in prompt and "CURRENT PERIOD ACTIVITY DATA" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("Vision Data Integration")
            else:
                results["failed_checks"].append("Missing vision data sections")
        
        if "with_history" in scenario:
            results["total_checks"] += 1
            if "## CHRONOLOGICAL CONTEXT: RECENT REPORTS" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("Recent Reports Context")
            else:
                results["failed_checks"].append("Missing recent reports section")
            
            results["total_checks"] += 1
            if "## PATTERN RECOGNITION: SIMILAR HISTORICAL REPORTS" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("Similar Reports Pattern")
            else:
                results["failed_checks"].append("Missing similar reports section")
        
        return results
    
    @staticmethod
    def validate_monthly_prompt(prompt: str, scenario: str) -> Dict[str, Any]:
        """Validate monthly analysis prompt structure"""
        results = {
            "scenario": scenario,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": [],
            "sections_found": []
        }
        
        # Core sections
        required_sections = [
            "EMPLOYEE INFORMATION:",
            "MONTHLY SUMMARY METRICS:",
            "RISK LEVEL DISTRIBUTION:",
            "RECURRING TOPICS:",
            "WEEKLY REPORTS:",
            "WEEKLY ANALYSIS SUMMARIES:",
            "1. PROGRESS TRENDS:",
            "2. MONTHLY ACHIEVEMENTS:",
            "9. ROLE ALIGNMENT AND TRANSITION ASSESSMENT:",
            "10. MONTHLY SUMMARY:"
        ]
        
        for section in required_sections:
            results["total_checks"] += 1
            if section in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append(section)
            else:
                results["failed_checks"].append(f"Missing section: {section}")
        
        # Check for JSON structure
        results["total_checks"] += 1
        if '"progress_trends":' in prompt and '"monthly_achievements":' in prompt:
            results["passed_checks"] += 1
            results["sections_found"].append("JSON Output Structure")
        else:
            results["failed_checks"].append("Missing JSON output structure")
        
        # Scenario-specific checks
        if "with_jd" in scenario:
            results["total_checks"] += 1
            if "## ROLE CONTEXT FOR MONTHLY PERIOD" in prompt and "ROLE-BASED MONTHLY ANALYSIS GUIDANCE" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("JD Integration")
            else:
                results["failed_checks"].append("Missing JD integration sections")
        
        if "with_vision" in scenario:
            results["total_checks"] += 1
            if "VISION SYSTEM ACTIVITY DATA" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("Vision Data Integration")
            else:
                results["failed_checks"].append("Missing vision data section")
        
        if "transition" in scenario:
            results["total_checks"] += 1
            if "PERIOD 1:" in prompt and "PERIOD 2:" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("Role Transition Periods")
            else:
                results["failed_checks"].append("Missing role transition period markers")
        
        return results
    
    @staticmethod
    def validate_quarterly_prompt(prompt: str, scenario: str) -> Dict[str, Any]:
        """Validate quarterly analysis prompt structure"""
        results = {
            "scenario": scenario,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": [],
            "sections_found": []
        }
        
        # Core sections
        required_sections = [
            "# QUARTERLY EMPLOYEE PERFORMANCE ANALYSIS",
            "## TASK OVERVIEW AND EXPECTED OUTPUT",
            "## EMPLOYEE INFORMATION",
            "## QUARTERLY SUMMARY METRICS",
            "## MONTHLY AND WEEKLY ANALYSES SUMMARIES",
            "## COMPREHENSIVE ANALYSIS REQUIREMENTS",
            "1. STRATEGIC ALIGNMENT ASSESSMENT:",
            "6. SKILL DEVELOPMENT EVALUATION:",
            "11. QUARTERLY SUMMARY:",
            "## HIERARCHICAL DATA ANALYSIS APPROACH",
            "## EVIDENCE STANDARDS AND ANALYSIS FRAMEWORK",
            "## OUTPUT STRUCTURE AND FORMAT"
        ]
        
        for section in required_sections:
            results["total_checks"] += 1
            if section in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append(section)
            else:
                results["failed_checks"].append(f"Missing section: {section}")
        
        # Check for JSON structure
        results["total_checks"] += 1
        if '"strategic_alignment":' in prompt and '"achievement_themes":' in prompt:
            results["passed_checks"] += 1
            results["sections_found"].append("JSON Output Structure")
        else:
            results["failed_checks"].append("Missing JSON output structure")
        
        # Scenario-specific checks
        if "with_jd" in scenario:
            results["total_checks"] += 1
            if "STRATEGIC ROLE-BASED QUARTERLY ANALYSIS GUIDANCE" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("JD Strategic Guidance")
            else:
                results["failed_checks"].append("Missing JD strategic guidance")
        
        if "with_vision" in scenario:
            results["total_checks"] += 1
            if "## VISION SYSTEM ACTIVITY DATA" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("Vision Data Integration")
            else:
                results["failed_checks"].append("Missing vision data section")
        
        if "career_progression" in scenario:
            results["total_checks"] += 1
            if "PHASE 1:" in prompt and "PHASE 2:" in prompt:
                results["passed_checks"] += 1
                results["sections_found"].append("Career Progression Phases")
            else:
                results["failed_checks"].append("Missing career progression phase markers")
        
        return results


class TestRunner:
    """Runs comprehensive tests on all prompt types"""
    
    def __init__(self):
        self.test_data = TestData()
        self.validator = PromptValidator()
        self.results = []
    
    def test_weekly_prompt_minimal(self):
        """Test weekly prompt with just report text (minimal scenario)"""
        print("\n" + "="*80)
        print("TEST 1: Weekly Prompt - Minimal (Report Only)")
        print("="*80)
        
        report_text = self.test_data.create_weekly_report()
        
        prompt = StructuredPrompts.employee_analysis_prompt(
            report_text=report_text
        )
        
        validation = self.validator.validate_weekly_prompt(prompt, "minimal")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_weekly_prompt_with_jd(self):
        """Test weekly prompt with JD data"""
        print("\n" + "="*80)
        print("TEST 2: Weekly Prompt - With Job Description")
        print("="*80)
        
        report_text = self.test_data.create_weekly_report()
        jd_data = self.test_data.create_single_jd()
        
        prompt = StructuredPrompts.employee_analysis_prompt(
            report_text=report_text,
            formatted_jd_data=jd_data
        )
        
        validation = self.validator.validate_weekly_prompt(prompt, "with_jd")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_weekly_prompt_with_vision(self):
        """Test weekly prompt with vision data"""
        print("\n" + "="*80)
        print("TEST 3: Weekly Prompt - With Vision Data")
        print("="*80)
        
        report_text = self.test_data.create_weekly_report()
        vision_data = self.test_data.create_vision_data()
        
        prompt = StructuredPrompts.employee_analysis_prompt(
            report_text=report_text,
            formatted_vision_data=vision_data
        )
        
        validation = self.validator.validate_weekly_prompt(prompt, "with_vision")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_weekly_prompt_full(self):
        """Test weekly prompt with all data sources"""
        print("\n" + "="*80)
        print("TEST 4: Weekly Prompt - Full (All Data Sources)")
        print("="*80)
        
        report_text = self.test_data.create_weekly_report()
        jd_data = self.test_data.create_single_jd()
        vision_data = self.test_data.create_vision_data()
        recent_reports = self.test_data.create_recent_reports()
        similar_reports = self.test_data.create_similar_reports()
        
        prompt = StructuredPrompts.employee_analysis_prompt(
            report_text=report_text,
            formatted_jd_data=jd_data,
            formatted_vision_data=vision_data,
            recent_reports=recent_reports,
            similar_reports=similar_reports
        )
        
        validation = self.validator.validate_weekly_prompt(prompt, "full_with_jd_vision_history")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_weekly_prompt_concurrent_jds(self):
        """Test weekly prompt with concurrent job descriptions"""
        print("\n" + "="*80)
        print("TEST 5: Weekly Prompt - Concurrent Job Descriptions")
        print("="*80)
        
        report_text = self.test_data.create_weekly_report()
        jd_data = self.test_data.create_concurrent_jds()
        
        prompt = StructuredPrompts.employee_analysis_prompt(
            report_text=report_text,
            formatted_jd_data=jd_data
        )
        
        validation = self.validator.validate_weekly_prompt(prompt, "concurrent_jds")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_monthly_prompt_minimal(self):
        """Test monthly prompt without JD or vision data"""
        print("\n" + "="*80)
        print("TEST 6: Monthly Prompt - Minimal (No JD/Vision)")
        print("="*80)
        
        monthly_data = self.test_data.create_monthly_data_basic()
        
        prompt = StructuredPrompts.monthly_analysis_prompt(monthly_data)
        
        validation = self.validator.validate_monthly_prompt(prompt, "minimal")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_monthly_prompt_with_jd_transition(self):
        """Test monthly prompt with JD transition"""
        print("\n" + "="*80)
        print("TEST 7: Monthly Prompt - With Role Transition")
        print("="*80)
        
        monthly_data = self.test_data.create_monthly_data_with_jd()
        
        prompt = StructuredPrompts.monthly_analysis_prompt(monthly_data)
        
        validation = self.validator.validate_monthly_prompt(prompt, "with_jd_transition_vision")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_quarterly_prompt_minimal(self):
        """Test quarterly prompt without JD or vision data"""
        print("\n" + "="*80)
        print("TEST 8: Quarterly Prompt - Minimal (No JD/Vision)")
        print("="*80)
        
        quarterly_data = self.test_data.create_quarterly_data_basic()
        
        prompt = StructuredPrompts.quarterly_analysis_prompt(quarterly_data)
        
        validation = self.validator.validate_quarterly_prompt(prompt, "minimal")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def test_quarterly_prompt_with_career_progression(self):
        """Test quarterly prompt with career progression (JD + vision)"""
        print("\n" + "="*80)
        print("TEST 9: Quarterly Prompt - Career Progression")
        print("="*80)
        
        quarterly_data = self.test_data.create_quarterly_data_with_jd()
        
        prompt = StructuredPrompts.quarterly_analysis_prompt(quarterly_data)
        
        validation = self.validator.validate_quarterly_prompt(prompt, "with_jd_vision_career_progression")
        self._print_results(validation)
        self.results.append(validation)
        
        return prompt
    
    def _print_results(self, validation: Dict[str, Any]):
        """Print validation results"""
        print(f"\nScenario: {validation['scenario']}")
        print(f"Checks Passed: {validation['passed_checks']}/{validation['total_checks']}")
        
        if validation['failed_checks']:
            print("\n❌ Failed Checks:")
            for failure in validation['failed_checks']:
                print(f"  - {failure}")
        
        print("\n✅ Sections Found:")
        for section in validation['sections_found'][:10]:  # Show first 10
            print(f"  - {section}")
        if len(validation['sections_found']) > 10:
            print(f"  ... and {len(validation['sections_found']) - 10} more")
        
        # Calculate pass rate
        pass_rate = (validation['passed_checks'] / validation['total_checks'] * 100) if validation['total_checks'] > 0 else 0
        print(f"\n📊 Pass Rate: {pass_rate:.1f}%")
        
        if pass_rate == 100:
            print("✨ PERFECT! All checks passed.")
        elif pass_rate >= 90:
            print("✓ EXCELLENT! Almost all checks passed.")
        elif pass_rate >= 75:
            print("⚠ GOOD, but some improvements needed.")
        else:
            print("⚠ NEEDS ATTENTION - Multiple checks failed.")
    
    def print_summary(self):
        """Print overall test summary"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        total_checks = sum(r['total_checks'] for r in self.results)
        total_passed = sum(r['passed_checks'] for r in self.results)
        
        print(f"\nTotal Tests Run: {total_tests}")
        print(f"Total Checks: {total_checks}")
        print(f"Total Passed: {total_passed}")
        print(f"Total Failed: {total_checks - total_passed}")
        print(f"Overall Pass Rate: {(total_passed/total_checks*100):.1f}%")
        
        print("\n📋 Test Results by Scenario:")
        for result in self.results:
            pass_rate = (result['passed_checks'] / result['total_checks'] * 100)
            status = "✓" if pass_rate == 100 else "⚠" if pass_rate >= 75 else "✗"
            print(f"  {status} {result['scenario']}: {result['passed_checks']}/{result['total_checks']} ({pass_rate:.1f}%)")
        
        print("\n" + "="*80)
        if total_passed == total_checks:
            print("🎉 ALL TESTS PASSED! Prompts are generating correctly.")
        elif (total_passed / total_checks) >= 0.9:
            print("✨ EXCELLENT! Most tests passed with minor issues.")
        elif (total_passed / total_checks) >= 0.75:
            print("✓ GOOD! Tests mostly passed, some refinement needed.")
        else:
            print("⚠ ATTENTION NEEDED - Several tests failed.")
        print("="*80)
    
    def run_all_tests(self):
        """Run all comprehensive tests"""
        print("="*80)
        print("COMPREHENSIVE PROMPT TESTING SUITE")
        print("Testing all three prompt types with various scenarios")
        print("="*80)
        
        # Weekly prompt tests
        self.test_weekly_prompt_minimal()
        self.test_weekly_prompt_with_jd()
        self.test_weekly_prompt_with_vision()
        self.test_weekly_prompt_full()
        self.test_weekly_prompt_concurrent_jds()
        
        # Monthly prompt tests
        self.test_monthly_prompt_minimal()
        self.test_monthly_prompt_with_jd_transition()
        
        # Quarterly prompt tests
        self.test_quarterly_prompt_minimal()
        self.test_quarterly_prompt_with_career_progression()
        
        # Print summary
        self.print_summary()
        
        return self.results


def main():
    """Main test execution"""
    print("\n" + "🧪 " * 40)
    print("STARTING COMPREHENSIVE PROMPT VALIDATION TESTS")
    print("🧪 " * 40 + "\n")
    
    runner = TestRunner()
    results = runner.run_all_tests()
    
    # Optional: Save prompts to files for manual inspection
    print("\n💾 Saving sample prompts to files for manual inspection...")
    
    try:
        output_dir = Path(__file__).parent / "test_output"
        output_dir.mkdir(exist_ok=True)
        
        # Save a full weekly prompt
        full_weekly = runner.test_weekly_prompt_full()
        with open(output_dir / "sample_weekly_prompt.txt", "w", encoding="utf-8") as f:
            f.write(full_weekly)
        print(f"✓ Saved: {output_dir / 'sample_weekly_prompt.txt'}")
        
        # Save monthly with transition
        monthly_transition = runner.test_monthly_prompt_with_jd_transition()
        with open(output_dir / "sample_monthly_prompt.txt", "w", encoding="utf-8") as f:
            f.write(monthly_transition)
        print(f"✓ Saved: {output_dir / 'sample_monthly_prompt.txt'}")
        
        # Save quarterly with progression
        quarterly_progression = runner.test_quarterly_prompt_with_career_progression()
        with open(output_dir / "sample_quarterly_prompt.txt", "w", encoding="utf-8") as f:
            f.write(quarterly_progression)
        print(f"✓ Saved: {output_dir / 'sample_quarterly_prompt.txt'}")
        
        print(f"\n📁 All sample prompts saved to: {output_dir}")
        
    except Exception as e:
        print(f"⚠ Warning: Could not save sample prompts: {e}")
    
    print("\n" + "🏁 " * 40)
    print("TESTING COMPLETE")
    print("🏁 " * 40 + "\n")
    
    return results


if __name__ == "__main__":
    results = main()
