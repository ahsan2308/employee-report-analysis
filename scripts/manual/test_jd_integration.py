"""
Comprehensive test script for Job Description (JD) integration - Phases 1-3

This script tests:
- Phase 1: JD Retrieval (get_employee_job_descriptions_for_period)
- Phase 2: JD Mapping (map_reports_to_jds with week range calculation)
- Phase 3: JD Formatting (all three prompt formatting functions)

Test scenarios cover:
1. Single stable JD throughout period
2. Single JD transitioning to another single JD
3. Stable concurrent JDs throughout period
4. Single JD transitioning to concurrent JDs
5. Concurrent JDs transitioning to different concurrent JDs
6. No JD data (unmapped reports)
7. Mixed scenarios with gaps
"""

import sys
import os
from datetime import date, timedelta
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.repositories.job_descriptions import get_employee_job_descriptions_for_period
from app.services.analysis.jd_mapping import map_reports_to_jds
from app.prompts.job_descriptions import (
    format_job_descriptions_for_weekly_prompt,
    format_job_descriptions_for_monthly_prompt,
    format_job_descriptions_for_quarterly_prompt,
)
from app.core.logger import logger


# ============================================================================
# TEST DATA GENERATORS
# ============================================================================

def create_test_jd(jd_id: str, description: str, assigned_date: date, 
                   end_date: date = None, is_current: bool = True) -> Dict[str, Any]:
    """Create a test JD record matching the database structure."""
    return {
        "jd_id": jd_id,
        "job_description": description,
        "assigned_date": assigned_date,
        "end_date": end_date,
        "is_current": is_current
    }

def create_test_report(report_id: str, report_date: date, text: str = "Sample report") -> Dict[str, Any]:
    """Create a test report record."""
    return {
        "report_id": report_id,
        "date": report_date,
        "text": text
    }

def simulate_jd_retrieval(jds: List[Dict[str, Any]], period_start: date, 
                          period_end: date) -> List[Dict[str, Any]]:
    """
    Simulate get_employee_job_descriptions_for_period logic.
    
    This mimics the database query logic without needing actual database access.
    """
    result_jds = []
    
    for jd in jds:
        # Check overlap conditions (same as Phase 1 logic)
        if jd["assigned_date"] <= period_end:
            if jd["is_current"] or (jd["end_date"] and jd["end_date"] >= period_start):
                # Calculate effective period
                effective_start = max(jd["assigned_date"], period_start)
                
                if jd["end_date"] is None:
                    effective_end = period_end
                else:
                    effective_end = min(jd["end_date"], period_end)
                
                result_jds.append({
                    "jd_id": jd["jd_id"],
                    "job_description": jd["job_description"],
                    "assigned_date": jd["assigned_date"],
                    "end_date": jd["end_date"],
                    "is_current": jd["is_current"],
                    "effective_during_period": {
                        "start": effective_start,
                        "end": effective_end
                    }
                })
    
    return result_jds


# ============================================================================
# TEST SCENARIOS
# ============================================================================

class TestScenario:
    """Base class for test scenarios."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.jds = []
        self.reports = []
        self.period_start = None
        self.period_end = None
    
    def setup(self):
        """Override this to set up test data."""
        raise NotImplementedError
    
    def run(self):
        """Execute the test scenario."""
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST SCENARIO: {self.name}")
        logger.info(f"Description: {self.description}")
        logger.info(f"{'='*80}\n")
        
        self.setup()
        
        # Phase 1: JD Retrieval
        logger.info("PHASE 1: JD RETRIEVAL")
        logger.info(f"Period: {self.period_start} to {self.period_end}")
        logger.info(f"Total JDs in database: {len(self.jds)}")
        
        retrieved_jds = simulate_jd_retrieval(self.jds, self.period_start, self.period_end)
        
        logger.info(f"Retrieved {len(retrieved_jds)} JDs overlapping with period:")
        for jd in retrieved_jds:
            logger.info(f"  - {jd['jd_id']}: {jd['effective_during_period']['start']} to {jd['effective_during_period']['end']}")
        
        # Phase 2: JD Mapping
        logger.info(f"\nPHASE 2: JD MAPPING")
        logger.info(f"Total reports to map: {len(self.reports)}")
        
        mapping_result = map_reports_to_jds(self.reports, retrieved_jds)
        
        logger.info(f"Created {len(mapping_result['jd_groups'])} JD groups:")
        for i, group in enumerate(mapping_result['jd_groups']):
            logger.info(f"  Group {i+1}: JDs {group['jd_ids']}")
            logger.info(f"    Effective: {group['effective_dates']['start']} to {group['effective_dates']['end']}")
            logger.info(f"    Reports: {len(group['reports'])}")
            for report in group['reports']:
                logger.info(f"      - Report {report['report_id'][:8]}... week {report['week_start_date']} to {report['week_end_date']}")
        
        logger.info(f"Unmapped reports: {len(mapping_result['unmapped_reports'])}")
        for report in mapping_result['unmapped_reports']:
            logger.info(f"  - Report {report['report_id'][:8]}... dated {report['date']}")
        
        # Phase 3: JD Formatting
        logger.info(f"\nPHASE 3: JD FORMATTING")
        
        # Weekly format (using retrieved JDs directly)
        logger.info("\n--- WEEKLY PROMPT FORMAT ---")
        weekly_format = format_job_descriptions_for_weekly_prompt(retrieved_jds)
        logger.info(weekly_format if weekly_format else "(No JD data)")
        
        # Monthly format (using mapping result)
        logger.info("\n--- MONTHLY PROMPT FORMAT ---")
        monthly_format = format_job_descriptions_for_monthly_prompt(mapping_result)
        logger.info(monthly_format if monthly_format else "(No JD data)")
        
        # Quarterly format (using mapping result)
        logger.info("\n--- QUARTERLY PROMPT FORMAT ---")
        quarterly_format = format_job_descriptions_for_quarterly_prompt(mapping_result)
        logger.info(quarterly_format if quarterly_format else "(No JD data)")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"SCENARIO COMPLETE: {self.name}")
        logger.info(f"{'='*80}\n\n")


# ============================================================================
# SCENARIO 1: Single Stable JD Throughout Period
# ============================================================================

class Scenario1_SingleStableJD(TestScenario):
    """Employee has one JD that remains constant throughout the analysis period."""
    
    def setup(self):
        self.period_start = date(2025, 1, 1)
        self.period_end = date(2025, 3, 31)  # Q1
        
        # Single JD assigned before period starts, still current
        self.jds = [
            create_test_jd(
                jd_id="JD_001",
                description="Data Analyst - Responsible for analyzing employee performance data, creating reports, and providing insights to management.",
                assigned_date=date(2024, 11, 1),
                end_date=None,
                is_current=True
            )
        ]
        
        # Weekly reports throughout Q1
        self.reports = [
            create_test_report("R001", date(2025, 1, 10), "Week 1 report"),
            create_test_report("R002", date(2025, 1, 17), "Week 2 report"),
            create_test_report("R003", date(2025, 1, 24), "Week 3 report"),
            create_test_report("R004", date(2025, 1, 31), "Week 4 report"),
            create_test_report("R005", date(2025, 2, 7), "Week 5 report"),
            create_test_report("R006", date(2025, 2, 14), "Week 6 report"),
            create_test_report("R007", date(2025, 2, 21), "Week 7 report"),
            create_test_report("R008", date(2025, 2, 28), "Week 8 report"),
            create_test_report("R009", date(2025, 3, 7), "Week 9 report"),
            create_test_report("R010", date(2025, 3, 14), "Week 10 report"),
            create_test_report("R011", date(2025, 3, 21), "Week 11 report"),
            create_test_report("R012", date(2025, 3, 28), "Week 12 report"),
        ]


# ============================================================================
# SCENARIO 2: Single JD Transitioning to Another Single JD
# ============================================================================

class Scenario2_SingleToSingleTransition(TestScenario):
    """Employee transitions from one JD to another during the period."""
    
    def setup(self):
        self.period_start = date(2025, 1, 1)
        self.period_end = date(2025, 3, 31)  # Q1
        
        # JD transition mid-quarter (promoted from Analyst to Senior Analyst)
        self.jds = [
            create_test_jd(
                jd_id="JD_001",
                description="Data Analyst - Responsible for analyzing employee performance data and creating basic reports.",
                assigned_date=date(2024, 11, 1),
                end_date=date(2025, 2, 15),  # Ended mid-Q1
                is_current=False
            ),
            create_test_jd(
                jd_id="JD_002",
                description="Senior Data Analyst - Leads data analysis projects, mentors junior analysts, and presents insights to senior management.",
                assigned_date=date(2025, 2, 16),  # Started mid-Q1
                end_date=None,
                is_current=True
            )
        ]
        
        # Weekly reports spanning the transition
        self.reports = [
            # Before transition (JD_001)
            create_test_report("R001", date(2025, 1, 10), "Report under old JD"),
            create_test_report("R002", date(2025, 1, 17), "Report under old JD"),
            create_test_report("R003", date(2025, 1, 24), "Report under old JD"),
            create_test_report("R004", date(2025, 1, 31), "Report under old JD"),
            create_test_report("R005", date(2025, 2, 7), "Report under old JD"),
            create_test_report("R006", date(2025, 2, 14), "Last week under old JD"),
            
            # During transition week (overlaps both JDs)
            create_test_report("R007", date(2025, 2, 21), "Transition week - new JD started 2/16"),
            
            # After transition (JD_002)
            create_test_report("R008", date(2025, 2, 28), "First full week under new JD"),
            create_test_report("R009", date(2025, 3, 7), "Report under new JD"),
            create_test_report("R010", date(2025, 3, 14), "Report under new JD"),
            create_test_report("R011", date(2025, 3, 21), "Report under new JD"),
            create_test_report("R012", date(2025, 3, 28), "Report under new JD"),
        ]


# ============================================================================
# SCENARIO 3: Stable Concurrent JDs Throughout Period
# ============================================================================

class Scenario3_StableConcurrentJDs(TestScenario):
    """Employee holds two concurrent JDs that both remain active throughout period."""
    
    def setup(self):
        self.period_start = date(2025, 1, 1)
        self.period_end = date(2025, 3, 31)  # Q1
        
        # Two concurrent JDs (dual role)
        self.jds = [
            create_test_jd(
                jd_id="JD_001",
                description="Data Analyst - Primary role focusing on employee performance analytics and reporting.",
                assigned_date=date(2024, 11, 1),
                end_date=None,
                is_current=True
            ),
            create_test_jd(
                jd_id="JD_003",
                description="Project Coordinator - Secondary role managing cross-functional data quality improvement projects.",
                assigned_date=date(2024, 12, 1),  # Added additional role
                end_date=None,
                is_current=True
            )
        ]
        
        # All reports during concurrent role period
        self.reports = [
            create_test_report("R001", date(2025, 1, 10), "Working both roles"),
            create_test_report("R002", date(2025, 1, 17), "Working both roles"),
            create_test_report("R003", date(2025, 1, 24), "Working both roles"),
            create_test_report("R004", date(2025, 1, 31), "Working both roles"),
            create_test_report("R005", date(2025, 2, 7), "Working both roles"),
            create_test_report("R006", date(2025, 2, 14), "Working both roles"),
            create_test_report("R007", date(2025, 2, 21), "Working both roles"),
            create_test_report("R008", date(2025, 2, 28), "Working both roles"),
            create_test_report("R009", date(2025, 3, 7), "Working both roles"),
            create_test_report("R010", date(2025, 3, 14), "Working both roles"),
            create_test_report("R011", date(2025, 3, 21), "Working both roles"),
            create_test_report("R012", date(2025, 3, 28), "Working both roles"),
        ]


# ============================================================================
# SCENARIO 4: Single JD Transitioning to Concurrent JDs
# ============================================================================

class Scenario4_SingleToConcurrent(TestScenario):
    """Employee starts with one JD, then takes on additional concurrent role."""
    
    def setup(self):
        self.period_start = date(2025, 1, 1)
        self.period_end = date(2025, 3, 31)  # Q1
        
        # Transition from single to concurrent
        self.jds = [
            create_test_jd(
                jd_id="JD_001",
                description="Data Analyst - Responsible for analyzing employee performance data and creating reports.",
                assigned_date=date(2024, 11, 1),
                end_date=None,  # Continues
                is_current=True
            ),
            create_test_jd(
                jd_id="JD_003",
                description="Project Coordinator - Managing cross-functional data quality improvement projects.",
                assigned_date=date(2025, 2, 1),  # Added mid-quarter
                end_date=None,
                is_current=True
            )
        ]
        
        # Reports spanning single to concurrent
        self.reports = [
            # Single role period
            create_test_report("R001", date(2025, 1, 10), "Single role"),
            create_test_report("R002", date(2025, 1, 17), "Single role"),
            create_test_report("R003", date(2025, 1, 24), "Single role"),
            create_test_report("R004", date(2025, 1, 31), "Last week single role"),
            
            # Concurrent role period (both JDs active)
            create_test_report("R005", date(2025, 2, 7), "First week with both roles"),
            create_test_report("R006", date(2025, 2, 14), "Both roles"),
            create_test_report("R007", date(2025, 2, 21), "Both roles"),
            create_test_report("R008", date(2025, 2, 28), "Both roles"),
            create_test_report("R009", date(2025, 3, 7), "Both roles"),
            create_test_report("R010", date(2025, 3, 14), "Both roles"),
            create_test_report("R011", date(2025, 3, 21), "Both roles"),
            create_test_report("R012", date(2025, 3, 28), "Both roles"),
        ]


# ============================================================================
# SCENARIO 5: Concurrent JDs Transitioning to Different Concurrent JDs
# ============================================================================

class Scenario5_ConcurrentToConcurrent(TestScenario):
    """Employee's concurrent role configuration changes during period."""
    
    def setup(self):
        self.period_start = date(2025, 1, 1)
        self.period_end = date(2025, 3, 31)  # Q1
        
        # Complex transition: JD_001 + JD_003 → JD_002 + JD_004
        self.jds = [
            # Initial concurrent roles
            create_test_jd(
                jd_id="JD_001",
                description="Data Analyst - Primary role focusing on employee performance analytics.",
                assigned_date=date(2024, 11, 1),
                end_date=date(2025, 2, 10),  # Ended mid-quarter
                is_current=False
            ),
            create_test_jd(
                jd_id="JD_003",
                description="Project Coordinator - Managing data quality projects.",
                assigned_date=date(2024, 12, 1),
                end_date=date(2025, 2, 10),  # Ended mid-quarter
                is_current=False
            ),
            
            # New concurrent roles
            create_test_jd(
                jd_id="JD_002",
                description="Senior Data Analyst - Leading analytics team and strategy.",
                assigned_date=date(2025, 2, 11),  # Started mid-quarter
                end_date=None,
                is_current=True
            ),
            create_test_jd(
                jd_id="JD_004",
                description="Training Coordinator - Developing and delivering data analytics training programs.",
                assigned_date=date(2025, 2, 11),  # Started mid-quarter
                end_date=None,
                is_current=True
            )
        ]
        
        # Reports spanning the complex transition
        self.reports = [
            # Old concurrent period (JD_001 + JD_003)
            create_test_report("R001", date(2025, 1, 10), "Old concurrent roles"),
            create_test_report("R002", date(2025, 1, 17), "Old concurrent roles"),
            create_test_report("R003", date(2025, 1, 24), "Old concurrent roles"),
            create_test_report("R004", date(2025, 1, 31), "Old concurrent roles"),
            create_test_report("R005", date(2025, 2, 7), "Last week old roles"),
            
            # Transition week (may overlap all 4 JDs depending on week boundaries)
            create_test_report("R006", date(2025, 2, 14), "Transition week - change on 2/11"),
            
            # New concurrent period (JD_002 + JD_004)
            create_test_report("R007", date(2025, 2, 21), "First full week new roles"),
            create_test_report("R008", date(2025, 2, 28), "New concurrent roles"),
            create_test_report("R009", date(2025, 3, 7), "New concurrent roles"),
            create_test_report("R010", date(2025, 3, 14), "New concurrent roles"),
            create_test_report("R011", date(2025, 3, 21), "New concurrent roles"),
            create_test_report("R012", date(2025, 3, 28), "New concurrent roles"),
        ]


# ============================================================================
# SCENARIO 6: No JD Data (Unmapped Reports)
# ============================================================================

class Scenario6_NoJDData(TestScenario):
    """Employee has reports but no JD assigned during the period."""
    
    def setup(self):
        self.period_start = date(2025, 1, 1)
        self.period_end = date(2025, 3, 31)  # Q1
        
        # JD exists but outside the analysis period
        self.jds = [
            create_test_jd(
                jd_id="JD_001",
                description="Data Analyst - Basic analytics role.",
                assigned_date=date(2025, 4, 1),  # Starts AFTER period
                end_date=None,
                is_current=True
            )
        ]
        
        # Reports during period without JD coverage
        self.reports = [
            create_test_report("R001", date(2025, 1, 10), "Report before JD assignment"),
            create_test_report("R002", date(2025, 1, 17), "Report before JD assignment"),
            create_test_report("R003", date(2025, 2, 14), "Report before JD assignment"),
            create_test_report("R004", date(2025, 3, 21), "Report before JD assignment"),
        ]


# ============================================================================
# SCENARIO 7: Mixed - Gaps and Transitions
# ============================================================================

class Scenario7_MixedWithGaps(TestScenario):
    """Complex scenario with JD gaps and transitions."""
    
    def setup(self):
        self.period_start = date(2025, 1, 1)
        self.period_end = date(2025, 3, 31)  # Q1
        
        # Multiple transitions with gaps
        self.jds = [
            create_test_jd(
                jd_id="JD_001",
                description="Data Analyst - Initial role.",
                assigned_date=date(2024, 11, 1),
                end_date=date(2025, 1, 20),  # Ended in Jan
                is_current=False
            ),
            # GAP: Jan 21 - Feb 10 (no JD)
            create_test_jd(
                jd_id="JD_002",
                description="Senior Data Analyst - Promoted role after gap.",
                assigned_date=date(2025, 2, 11),  # Started in Feb
                end_date=date(2025, 2, 28),  # Short tenure
                is_current=False
            ),
            # GAP: Mar 1 - Mar 10 (no JD)
            create_test_jd(
                jd_id="JD_003",
                description="Project Coordinator - New role assignment.",
                assigned_date=date(2025, 3, 11),  # Started in Mar
                end_date=None,
                is_current=True
            )
        ]
        
        # Reports spanning gaps and transitions
        self.reports = [
            # Covered by JD_001
            create_test_report("R001", date(2025, 1, 10), "Under JD_001"),
            create_test_report("R002", date(2025, 1, 17), "Under JD_001"),
            
            # In gap (no JD coverage)
            create_test_report("R003", date(2025, 1, 24), "In gap period"),
            create_test_report("R004", date(2025, 1, 31), "In gap period"),
            create_test_report("R005", date(2025, 2, 7), "In gap period"),
            
            # Covered by JD_002
            create_test_report("R006", date(2025, 2, 14), "Under JD_002"),
            create_test_report("R007", date(2025, 2, 21), "Under JD_002"),
            create_test_report("R008", date(2025, 2, 28), "Under JD_002"),
            
            # In gap (no JD coverage)
            create_test_report("R009", date(2025, 3, 7), "In gap period"),
            
            # Covered by JD_003
            create_test_report("R010", date(2025, 3, 14), "Under JD_003"),
            create_test_report("R011", date(2025, 3, 21), "Under JD_003"),
            create_test_report("R012", date(2025, 3, 28), "Under JD_003"),
        ]


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test scenarios."""
    scenarios = [
        Scenario1_SingleStableJD(
            "Scenario 1: Single Stable JD",
            "Employee has one JD throughout the entire quarter"
        ),
        Scenario2_SingleToSingleTransition(
            "Scenario 2: Single JD to Different Single JD",  # Changed arrow
            "Employee transitions from one role to another mid-quarter"
        ),
        Scenario3_StableConcurrentJDs(
            "Scenario 3: Stable Concurrent JDs",
            "Employee holds two roles concurrently throughout the quarter"
        ),
        Scenario4_SingleToConcurrent(
            "Scenario 4: Single JD to Concurrent JDs",  # Changed arrow
            "Employee adds a second concurrent role mid-quarter"
        ),
        Scenario5_ConcurrentToConcurrent(
            "Scenario 5: Concurrent JDs to Different Concurrent JDs",  # Changed arrow
            "Employee's concurrent role configuration changes completely"
        ),
        Scenario6_NoJDData(
            "Scenario 6: No JD Data",
            "Employee has reports but no JD coverage during the period"
        ),
        Scenario7_MixedWithGaps(
            "Scenario 7: Mixed with Gaps",
            "Complex scenario with JD transitions and gaps in coverage"
        ),
    ]
    
    logger.info("\n" + "="*80)
    logger.info("JD INTEGRATION TEST SUITE - PHASES 1-3")
    logger.info("="*80)
    logger.info(f"Total scenarios: {len(scenarios)}")
    logger.info("="*80 + "\n")
    
    for scenario in scenarios:
        try:
            scenario.run()
        except Exception as e:
            logger.error(f"ERROR in {scenario.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info("\n" + "="*80)
    logger.info("ALL TESTS COMPLETE")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    run_all_tests()
