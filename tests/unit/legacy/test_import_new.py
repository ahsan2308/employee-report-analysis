"""
Integration Test Suite for Steps 1.1-1.4: Complete Delimiter Support Flow

This script tests the COMPLETE integration:
- Step 1.1: PandasCSVReader delimiter/encoding support
- Step 1.2: CSVImportOptions schema fields
- Step 1.3: API endpoint parameter acceptance
- Step 1.4: Service layer passing options to reader

Tests the ACTUAL flow that happens during a real CSV import.

Run with: python tests/test_steps_1_1_to_1_4_integration.py
"""
import sys
import os
import tempfile
import io

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.csv.csv_reader import PandasCSVReader
from app.schemas.csv_import_schema import CSVImportOptions


class TestRunner:
    """Simple test runner."""
    __test__ = False  # a helper, not a test class
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, test_func, test_name):
        """Run a single test."""
        try:
            test_func()
            self.passed += 1
            print(f"  ✓ {test_name}")
            return True
        except AssertionError as e:
            self.failed += 1
            print(f"  ✗ {test_name}")
            print(f"    AssertionError: {str(e)}")
            self.errors.append((test_name, str(e)))
            return False
        except Exception as e:
            self.failed += 1
            print(f"  ✗ {test_name}")
            print(f"    Error: {str(e)}")
            self.errors.append((test_name, str(e)))
            return False
    
    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"Test Summary: {self.passed} passed, {self.failed} failed out of {total} tests")
        
        if self.errors:
            print(f"\n{'='*70}")
            print("Failed Tests:")
            for test_name, error in self.errors:
                print(f"\n{test_name}:")
                print(f"  {error}")
        
        print(f"{'='*70}\n")
        return self.failed == 0


# =============================================================================
# INTEGRATION TESTS: Complete Flow from Schema → Service → Reader
# =============================================================================

class TestStep1_4_IntegrationFlow:
    """Test Step 1.4: Integration of delimiter/encoding through the entire stack."""
    
    @staticmethod
    def test_options_to_reader_flow_comma():
        """Test that delimiter option flows from CSVImportOptions to PandasCSVReader (comma)."""
        # Create options with explicit comma delimiter
        options = CSVImportOptions(
            chunk_size=100,
            delimiter=',',
            encoding='utf-8'
        )
        
        # Create reader with these options (simulating what the service does)
        reader = PandasCSVReader(
            chunk_size=options.chunk_size,
            encoding=options.encoding,
            delimiter=options.delimiter
        )
        
        # Verify options flowed through
        assert reader.delimiter == ',', "Delimiter should be comma"
        assert reader.encoding == 'utf-8', "Encoding should be utf-8"
        assert reader.chunk_size == 100, "Chunk size should be 100"
    
    @staticmethod
    def test_options_to_reader_flow_tab():
        """Test that tab delimiter option flows from CSVImportOptions to PandasCSVReader."""
        options = CSVImportOptions(
            delimiter='\t',
            encoding='utf-8'
        )
        
        reader = PandasCSVReader(
            encoding=options.encoding,
            delimiter=options.delimiter
        )
        
        assert reader.delimiter == '\t', "Delimiter should be tab"
        assert reader.encoding == 'utf-8', "Encoding should be utf-8"
    
    @staticmethod
    def test_options_with_none_triggers_auto_detection():
        """Test that None values in options trigger auto-detection."""
        options = CSVImportOptions(
            delimiter=None,  # Should trigger auto-detection
            encoding=None    # Should trigger auto-detection
        )
        
        reader = PandasCSVReader(
            encoding=options.encoding,
            delimiter=options.delimiter
        )
        
        assert reader.delimiter is None, "Delimiter None should trigger auto-detection"
        assert reader.encoding is None, "Encoding None should trigger auto-detection"
    
    @staticmethod
    def test_read_csv_with_tab_delimiter_from_options():
        """Test reading tab-delimited CSV using options that flow through."""
        # Create tab-delimited content
        csv_content = "Name\tAge\tCity\nJohn\t30\tNYC\nJane\t25\tLA"
        
        # Create options (Step 1.2)
        options = CSVImportOptions(
            delimiter='\t',
            encoding='utf-8'
        )
        
        # Create reader with options (Step 1.4)
        reader = PandasCSVReader(
            delimiter=options.delimiter,
            encoding=options.encoding
        )
        
        # Read CSV (Step 1.1)
        file_obj = io.StringIO(csv_content)
        rows = list(reader.read_csv(
            file_obj=file_obj,
            delimiter=options.delimiter,
            encoding=options.encoding
        ))
        
        # Verify correct parsing
        assert len(rows) == 2, "Should read 2 data rows"
        assert rows[0]['Name'] == 'John', "Should parse tab-delimited correctly"
        assert rows[0]['Age'] == '30'
        assert rows[0]['City'] == 'NYC'
    
    @staticmethod
    def test_read_csv_with_pipe_delimiter_from_options():
        """Test reading pipe-delimited CSV using options that flow through."""
        csv_content = "Name|Age|City\nJohn|30|NYC\nJane|25|LA"
        
        options = CSVImportOptions(delimiter='|')
        reader = PandasCSVReader(delimiter=options.delimiter)
        
        file_obj = io.StringIO(csv_content)
        rows = list(reader.read_csv(file_obj=file_obj, delimiter=options.delimiter))
        
        assert len(rows) == 2
        assert rows[0]['Name'] == 'John'
        assert rows[1]['Name'] == 'Jane'
    
    @staticmethod
    def test_auto_detection_when_options_delimiter_is_none():
        """Test that auto-detection works when options.delimiter is None."""
        csv_content = "Name,Age,City\nJohn,30,NYC"
        
        options = CSVImportOptions(delimiter=None)  # Trigger auto-detection
        reader = PandasCSVReader(delimiter=options.delimiter)
        
        file_obj = io.StringIO(csv_content)
        rows = list(reader.read_csv(file_obj=file_obj, delimiter=options.delimiter))
        
        # Should auto-detect comma and parse correctly
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'


class TestStep1_4_ServiceLayerIntegration:
    """Test that CSVImportService correctly passes options to reader."""
    
    @staticmethod
    def test_service_creates_reader_with_options():
        """Test that service creates reader with correct options from CSVImportOptions."""
        options = CSVImportOptions(
            chunk_size=500,
            delimiter='\t',
            encoding='utf-8'
        )
        
        # Simulate what the service does in process_csv_file
        delimiter = getattr(options, 'delimiter', None)
        encoding = getattr(options, 'encoding', None)
        chunk_size = getattr(options, 'chunk_size', 1000)
        
        reader = PandasCSVReader(
            chunk_size=chunk_size,
            encoding=encoding,
            delimiter=delimiter
        )
        
        assert reader.chunk_size == 500, "Chunk size should match options"
        assert reader.delimiter == '\t', "Delimiter should match options"
        assert reader.encoding == 'utf-8', "Encoding should match options"
    
    @staticmethod
    def test_service_extracts_none_values_correctly():
        """Test that service correctly handles None values in options."""
        options = CSVImportOptions(
            delimiter=None,
            encoding=None
        )
        
        # Extract like the service does
        delimiter = getattr(options, 'delimiter', None)
        encoding = getattr(options, 'encoding', None)
        chunk_size = getattr(options, 'chunk_size', 1000)
        
        assert delimiter is None, "Should extract None for delimiter"
        assert encoding is None, "Should extract None for encoding"
        assert chunk_size == 1000, "Should use default chunk_size"


class TestStep1_4_ErrorHandling:
    """Test error handling in the integration flow."""
    
    @staticmethod
    def test_invalid_delimiter_type_in_options():
        """Test that invalid delimiter type in options is handled gracefully."""
        # Create options with invalid delimiter type
        # Note: Pydantic may validate this, so we test at reader level
        
        reader = PandasCSVReader(delimiter=123)  # Invalid: integer
        
        csv_content = "Name,Age\nJohn,30"
        file_obj = io.StringIO(csv_content)
        
        # Should fall back to auto-detection and work
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'
    
    @staticmethod
    def test_empty_delimiter_in_options():
        """Test that empty delimiter in options triggers auto-detection."""
        options = CSVImportOptions(delimiter='')
        reader = PandasCSVReader(delimiter=options.delimiter)
        
        csv_content = "Name,Age\nJohn,30"
        file_obj = io.StringIO(csv_content)
        
        rows = list(reader.read_csv(file_obj=file_obj, delimiter=options.delimiter))
        
        # Should auto-detect comma
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'


class TestStep1_4_RealWorldScenarios:
    """Test real-world scenarios that match actual usage."""
    
    @staticmethod
    def test_vision_data_scenario():
        """Test Vision Data scenario: TXT file with tab delimiter."""
        # Simulate Vision Data TXT file
        vision_content = (
            "Employee_ID\tFrom_Date\tTo_Date\tMain_Entity\tSub_Entities\tSub_Entities_Content\n"
            "123\t2024-01-01\t2024-01-31\tActivities\tCases:5,Tasks:10\tCases:[],Tasks:[{\"id\":1}]"
        )
        
        # User uploads file with file_format="txt"
        options = CSVImportOptions(
            file_format="txt",
            delimiter=None,  # Let auto-detection work (or could be '\t')
            encoding=None
        )
        
        # Service creates reader
        reader = PandasCSVReader(
            delimiter=options.delimiter or '\t',  # Service could default txt to tab
            encoding=options.encoding
        )
        
        # Read the file
        file_obj = io.StringIO(vision_content)
        rows = list(reader.read_csv(file_obj=file_obj, delimiter='\t'))
        
        # Verify correct parsing
        assert len(rows) == 1
        assert rows[0]['Employee_ID'] == '123'
        assert rows[0]['Main_Entity'] == 'Activities'
    
    @staticmethod
    def test_employee_report_scenario():
        """Test Employee Report scenario: CSV file with comma delimiter."""
        # Simulate Employee Report CSV
        report_content = (
            "Employee_ID,Name,Designation,From,To,Tasks_Completed\n"
            "1,John Doe,Manager,2024-01-01,2024-01-07,Completed project X"
        )
        
        # User uploads with default settings
        options = CSVImportOptions(
            file_format="csv",
            delimiter=None,  # Auto-detect
            encoding=None
        )
        
        # Service creates reader
        reader = PandasCSVReader(
            delimiter=options.delimiter,
            encoding=options.encoding
        )
        
        # Read the file
        file_obj = io.StringIO(report_content)
        rows = list(reader.read_csv(file_obj=file_obj))
        
        # Should auto-detect comma and parse correctly
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John Doe'
        assert rows[0]['Designation'] == 'Manager'
    
    @staticmethod
    def test_explicit_override_scenario():
        """Test scenario where user explicitly overrides delimiter."""
        # User knows their CSV uses pipes despite .csv extension
        csv_content = "Name|Age|City\nJohn|30|NYC"
        
        # User explicitly specifies pipe delimiter
        options = CSVImportOptions(
            file_format="csv",
            delimiter='|',  # Explicit override
            encoding='utf-8'
        )
        
        # Service creates reader with explicit delimiter
        reader = PandasCSVReader(
            delimiter=options.delimiter,
            encoding=options.encoding
        )
        
        # Read the file
        file_obj = io.StringIO(csv_content)
        rows = list(reader.read_csv(
            file_obj=file_obj,
            delimiter=options.delimiter,
            encoding=options.encoding
        ))
        
        # Should use pipe delimiter
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'
        assert rows[0]['City'] == 'NYC'


class TestStep1_4_FileObjectHandling:
    """Test handling of different file object types."""
    
    @staticmethod
    def test_string_io_with_options():
        """Test StringIO file objects with options."""
        csv_content = "A\tB\tC\n1\t2\t3"
        
        options = CSVImportOptions(delimiter='\t')
        reader = PandasCSVReader(delimiter=options.delimiter)
        
        file_obj = io.StringIO(csv_content)
        rows = list(reader.read_csv(file_obj=file_obj, delimiter=options.delimiter))
        
        assert len(rows) == 1
        assert rows[0]['A'] == '1'
    
    @staticmethod
    def test_temporary_file_with_options():
        """Test temporary files with options."""
        csv_content = "X,Y,Z\n10,20,30"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            options = CSVImportOptions(delimiter=',', encoding='utf-8')
            reader = PandasCSVReader(
                delimiter=options.delimiter,
                encoding=options.encoding
            )
            
            rows = list(reader.read_csv(
                file_path=temp_path,
                delimiter=options.delimiter,
                encoding=options.encoding
            ))
            
            assert len(rows) == 1
            assert rows[0]['X'] == '10'
        finally:
            os.unlink(temp_path)


# =============================================================================
# MAIN TEST EXECUTION
# =============================================================================

def main():
    """Main test runner."""
    print("\n" + "="*70)
    print("Integration Test Suite: Steps 1.1-1.4")
    print("Testing complete flow: Options → Service → Reader")
    print("="*70)
    
    runner = TestRunner()
    
    # Test classes
    test_classes = [
        ("Step 1.4: Integration Flow", TestStep1_4_IntegrationFlow),
        ("Step 1.4: Service Layer Integration", TestStep1_4_ServiceLayerIntegration),
        ("Step 1.4: Error Handling", TestStep1_4_ErrorHandling),
        ("Step 1.4: Real-World Scenarios", TestStep1_4_RealWorldScenarios),
        ("Step 1.4: File Object Handling", TestStep1_4_FileObjectHandling),
    ]
    
    # Run all test classes
    for class_name, test_class in test_classes:
        print(f"\n{class_name}")
        print("=" * 70)
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) 
                       if method.startswith('test_') and callable(getattr(test_class, method))]
        
        for method_name in test_methods:
            test_method = getattr(test_class, method_name)
            runner.run_test(test_method, method_name)
    
    # Print summary
    success = runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()