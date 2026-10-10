"""
Comprehensive test suite for CSV delimiter support functionality.

Tests all aspects of delimiter detection, handling, and file processing
for various delimiter types (comma, tab, pipe, semicolon).

Run with: python tests/test_csv_delimiter_support.py
"""
import sys
import os
import tempfile
import io

# Add the parent directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.csv.csv_reader import PandasCSVReader


class TestRunner:
    """Simple test runner that mimics pytest output."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.current_class = None
    
    def run_test(self, test_func, test_name, class_name):
        """Run a single test function."""
        try:
            test_func()
            self.passed += 1
            print(f"  ✓ {test_name}")
            return True
        except AssertionError as e:
            self.failed += 1
            print(f"  ✗ {test_name}")
            print(f"    AssertionError: {str(e)}")
            self.errors.append((class_name, test_name, str(e)))
            return False
        except Exception as e:
            self.failed += 1
            print(f"  ✗ {test_name}")
            print(f"    Error: {str(e)}")
            self.errors.append((class_name, test_name, str(e)))
            return False
    
    def run_test_class(self, test_class):
        """Run all tests in a test class."""
        class_name = test_class.__name__
        print(f"\n{class_name}")
        print("=" * 70)
        
        # Get all test methods (methods starting with 'test_')
        test_methods = [method for method in dir(test_class) 
                       if method.startswith('test_') and callable(getattr(test_class, method))]
        
        for method_name in test_methods:
            test_method = getattr(test_class, method_name)
            self.run_test(test_method, method_name, class_name)
    
    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"Test Summary: {self.passed} passed, {self.failed} failed out of {total} tests")
        
        if self.errors:
            print(f"\n{'='*70}")
            print("Failed Tests:")
            for class_name, test_name, error in self.errors:
                print(f"\n{class_name}.{test_name}:")
                print(f"  {error}")
        
        print(f"{'='*70}\n")
        return self.failed == 0


class TestDelimiterDetection:
    """Test delimiter auto-detection functionality."""
    
    @staticmethod
    def test_detect_comma_delimiter():
        """Test detection of comma-delimited CSV."""
        csv_content = "Name,Age,City\nJohn,30,NYC\nJane,25,LA"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == ',', f"Expected comma delimiter, got {repr(delimiter)}"
    
    @staticmethod
    def test_detect_tab_delimiter():
        """Test detection of tab-delimited file."""
        csv_content = "Name\tAge\tCity\nJohn\t30\tNYC\nJane\t25\tLA"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == '\t', f"Expected tab delimiter, got {repr(delimiter)}"
    
    @staticmethod
    def test_detect_pipe_delimiter():
        """Test detection of pipe-delimited file."""
        csv_content = "Name|Age|City\nJohn|30|NYC\nJane|25|LA"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == '|', f"Expected pipe delimiter, got {repr(delimiter)}"
    
    @staticmethod
    def test_detect_semicolon_delimiter():
        """Test detection of semicolon-delimited file."""
        csv_content = "Name;Age;City\nJohn;30;NYC\nJane;25;LA"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == ';', f"Expected semicolon delimiter, got {repr(delimiter)}"
    
    @staticmethod
    def test_detect_delimiter_from_file_path():
        """Test delimiter detection from actual file on disk."""
        csv_content = "Name\tAge\tCity\nJohn\t30\tNYC\nJane\t25\tLA"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            reader = PandasCSVReader()
            delimiter = reader._detect_delimiter(temp_path)
            
            assert delimiter == '\t', f"Expected tab delimiter from file, got {repr(delimiter)}"
        finally:
            os.unlink(temp_path)
    
    @staticmethod
    def test_specified_delimiter_overrides_detection():
        """Test that explicitly specified delimiter overrides auto-detection."""
        csv_content = "Name,Age,City\nJohn,30,NYC"
        
        reader = PandasCSVReader(delimiter='\t')
        file_obj = io.StringIO(csv_content)
        
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == '\t', "Specified delimiter should override auto-detection"
    
    @staticmethod
    def test_delimiter_caching():
        """Test that detected delimiter is cached."""
        csv_content = "Name\tAge\tCity\nJohn\t30\tNYC"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        delimiter1 = reader._detect_delimiter(file_obj)
        delimiter2 = reader._detect_delimiter(file_obj)
        
        assert delimiter1 == delimiter2 == '\t'
        assert reader._detected_delimiter == '\t'
    
    @staticmethod
    def test_fallback_to_comma_on_detection_failure():
        """Test fallback to comma when delimiter cannot be detected."""
        csv_content = "SingleColumnNoDelimiter\nValue1\nValue2"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == ',', "Should fallback to comma when detection fails"


class TestExplicitDelimiterParameter:
    """Test explicit delimiter parameter in constructor and methods."""
    
    @staticmethod
    def test_constructor_delimiter_parameter():
        """Test setting delimiter in constructor."""
        reader = PandasCSVReader(delimiter='\t')
        assert reader.delimiter == '\t'
    
    
    @staticmethod
    def test_default_delimiter_is_none():
        """Test that default delimiter is None (triggers auto-detection)."""
        reader = PandasCSVReader()
        # Default is None, which will trigger auto-detection when reading
        assert reader.delimiter is None, f"Expected None but got {repr(reader.delimiter)}"
   
    @staticmethod
    def test_explicit_comma_delimiter():
        """Test explicitly setting comma delimiter."""
        reader = PandasCSVReader(delimiter=',')
        assert reader.delimiter == ','

    @staticmethod
    def test_read_csv_with_explicit_delimiter():
        """Test reading CSV with explicitly specified delimiter."""
        csv_content = "Name\tAge\tCity\nJohn\t30\tNYC\nJane\t25\tLA"
        
        reader = PandasCSVReader(delimiter='\t')
        file_obj = io.StringIO(csv_content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 2
        assert rows[0]['Name'] == 'John'
        assert rows[0]['Age'] == '30'
        assert rows[0]['City'] == 'NYC'
    
    @staticmethod
    def test_read_csv_delimiter_parameter_override():
        """Test that delimiter parameter in read_csv overrides constructor."""
        csv_content = "Name|Age|City\nJohn|30|NYC"
        
        reader = PandasCSVReader(delimiter=',')
        file_obj = io.StringIO(csv_content)
        
        rows = list(reader.read_csv(file_obj=file_obj, delimiter='|'))
        
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'
    
    @staticmethod
    def test_read_dataframes_with_explicit_delimiter():
        """Test reading DataFrames with explicitly specified delimiter."""
        csv_content = "Name;Age;City\nJohn;30;NYC\nJane;25;LA"
        
        reader = PandasCSVReader(delimiter=';')
        file_obj = io.StringIO(csv_content)
        
        chunks = list(reader.read_dataframes(file_obj=file_obj))
        
        assert len(chunks) == 1
        df = chunks[0]
        assert len(df) == 2
        assert list(df.columns) == ['Name', 'Age', 'City']


class TestTabDelimitedFiles:
    """Test handling of tab-delimited (.txt) files."""
    
    @staticmethod
    def test_read_tab_delimited_txt_file():
        """Test reading a tab-delimited .txt file."""
        txt_content = "Employee_ID\tName\tDesignation\n1\tJohn Doe\tManager\n2\tJane Smith\tDeveloper"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(txt_content)
            temp_path = f.name
        
        try:
            reader = PandasCSVReader(delimiter='\t')
            rows = list(reader.read_csv(file_path=temp_path))
            
            assert len(rows) == 2
            assert rows[0]['Employee_ID'] == '1'
            assert rows[0]['Name'] == 'John Doe'
            assert rows[0]['Designation'] == 'Manager'
        finally:
            os.unlink(temp_path)
    
    @staticmethod
    def test_auto_detect_tab_delimiter_in_txt():
        """Test auto-detection of tab delimiter in .txt file."""
        txt_content = "Col1\tCol2\tCol3\nVal1\tVal2\tVal3"
        
        # Use None as delimiter to trigger auto-detection
        reader = PandasCSVReader(delimiter=None)
        file_obj = io.StringIO(txt_content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 1, f"Expected 1 row but got {len(rows)}"
        assert 'Col1' in rows[0], f"Expected 'Col1' key in row, got keys: {list(rows[0].keys())}"
        assert rows[0]['Col1'] == 'Val1'
        assert rows[0]['Col2'] == 'Val2'
        assert rows[0]['Col3'] == 'Val3'
    
    @staticmethod
    def test_tab_delimited_with_special_characters():
        """Test tab-delimited file with special characters in values."""
        txt_content = "Name\tDescription\tNotes\nJohn\tSenior, experienced\tNeeds support"
        
        reader = PandasCSVReader(delimiter='\t')
        file_obj = io.StringIO(txt_content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 1
        assert rows[0]['Description'] == 'Senior, experienced'
    
    @staticmethod
    def test_tab_delimited_with_empty_fields():
        """Test tab-delimited file with empty fields."""
        txt_content = "Col1\tCol2\tCol3\nVal1\t\tVal3\n\tVal2\t"
        
        reader = PandasCSVReader(delimiter='\t')
        file_obj = io.StringIO(txt_content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 2
        assert rows[0]['Col1'] == 'Val1'
        assert rows[0]['Col2'] is None
        assert rows[0]['Col3'] == 'Val3'


class TestVisionDataScenario:
    """Test specific Vision Data import scenario (tab-delimited)."""
    
    @staticmethod
    def test_vision_data_tab_delimited():
        """Test reading Vision Data format with tab delimiter."""
        vision_content = (
            "Employee_ID\tFrom_Date\tTo_Date\tMain_Entity\tSub_Entities\tSub_Entities_Content\n"
            "123\t2024-01-01\t2024-01-31\tActivities\tCases:5,Tasks:10\tCases:[],Tasks:[{\"id\":1}]"
        )
        
        reader = PandasCSVReader(delimiter='\t')
        file_obj = io.StringIO(vision_content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 1
        assert rows[0]['Employee_ID'] == '123'
        assert rows[0]['Main_Entity'] == 'Activities'


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @staticmethod
    def test_single_column_no_delimiter():
        """Test file with single column (no delimiter needed)."""
        content = "Name\nJohn\nJane"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 2
        assert rows[0]['Name'] == 'John'
    
    @staticmethod
    def test_empty_file():
        """Test handling of empty file."""
        reader = PandasCSVReader(delimiter='\t')
        file_obj = io.StringIO("")
        
        # Empty files will raise an error from pandas - this is expected behavior
        error_raised = False
        try:
            rows = list(reader.read_csv(file_obj=file_obj))
            # If no error, verify it's empty
            assert len(rows) == 0
        except Exception as e:
            # Pandas will raise an error for empty files - this is acceptable
            error_raised = True
            error_msg = str(e).lower()
            # Just verify it's an expected error type (not some other unexpected error)
            assert any(keyword in error_msg for keyword in ['no columns', 'empty', 'parse', 'dataframe']), \
                f"Unexpected error for empty file: {e}"
        
        # Either empty result or expected error is acceptable
        assert True  # Test passes either way
    
    @staticmethod
    def test_header_only_file():
        """Test file with only headers, no data rows."""
        content = "Col1\tCol2\tCol3"
        
        reader = PandasCSVReader(delimiter='\t')
        file_obj = io.StringIO(content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 0
        assert reader.get_headers() == ['Col1', 'Col2', 'Col3']
    @staticmethod
    def test_empty_string_delimiter_fallback():
        """Test that empty string delimiter falls back to comma."""
        csv_content = "Name,Age\nJohn,30"
        
        # This should fallback to comma, not fail
        reader = PandasCSVReader(delimiter='')
        file_obj = io.StringIO(csv_content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'
    
    @staticmethod
    def test_invalid_delimiter_type():
        """Test that invalid delimiter type (not string) is handled."""
        csv_content = "Name,Age\nJohn,30"
        
        # Pass an integer as delimiter - should fallback to comma
        reader = PandasCSVReader(delimiter=123)
        file_obj = io.StringIO(csv_content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'
    
    @staticmethod
    def test_binary_file_object():
        """Test delimiter detection with binary file object."""
        csv_content = b"Name\tAge\tCity\nJohn\t30\tNYC"
        
        reader = PandasCSVReader()
        file_obj = io.BytesIO(csv_content)
        
        # Auto-detection should work with binary file objects
        delimiter = reader._detect_delimiter(file_obj, encoding='utf-8')
        
        assert delimiter == '\t', f"Expected tab delimiter, got {repr(delimiter)}"
    
    @staticmethod
    def test_lines_with_only_whitespace():
        """Test delimiter detection when file has lines with only whitespace."""
        csv_content = "Name,Age\n   \nJohn,30\n\n"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        # Should still detect comma despite whitespace-only lines
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == ',', f"Expected comma delimiter, got {repr(delimiter)}"
    
    @staticmethod
    def test_very_long_line():
        """Test delimiter detection with very long lines (>10000 chars)."""
        # Create a very long CSV line
        long_line = ','.join([f'Field{i}' for i in range(1000)])
        csv_content = f"{long_line}\n{','.join(['Value'] * 1000)}"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(csv_content)
        
        delimiter = reader._detect_delimiter(file_obj)
        
        assert delimiter == ',', f"Expected comma delimiter for long line, got {repr(delimiter)}"



class TestBackwardCompatibility:
    """Test that existing CSV functionality still works."""
    
    @staticmethod
    def test_existing_csv_without_delimiter_param():
        """Test that existing code without delimiter param still works."""
        content = "Name,Age\nJohn,30"
        
        reader = PandasCSVReader()
        file_obj = io.StringIO(content)
        
        rows = list(reader.read_csv(file_obj=file_obj))
        
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John'
    
    @staticmethod
    def test_existing_encoding_detection_still_works():
        """Test that encoding detection works alongside delimiter detection."""
        content = "Name,City\nJohn,NYC"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            reader = PandasCSVReader()
            encoding = reader._detect_encoding(temp_path)
            
            assert encoding in ['utf-8', 'utf-8-sig', 'ascii']
        finally:
            os.unlink(temp_path)


def main():
    """Main test runner."""
    print("\n" + "="*70)
    print("CSV Delimiter Support Test Suite")
    print("="*70)
    
    runner = TestRunner()
    
    # List of test classes to run
    test_classes = [
        TestDelimiterDetection,
        TestExplicitDelimiterParameter,
        TestTabDelimitedFiles,
        TestVisionDataScenario,
        TestEdgeCases,
        TestBackwardCompatibility
    ]
    
    # Run all test classes
    for test_class in test_classes:
        runner.run_test_class(test_class)
    
    # Print summary
    success = runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()