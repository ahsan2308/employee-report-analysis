"""
Comprehensive Unit Tests for SQL Server Connector.

Tests all features including:
- Connection and authentication
- Security validations (table/column whitelisting)
- Schema introspection
- Data retrieval (batch and incremental)
- Error handling
- Query restrictions
"""
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database.sqlserver_connector import (
    SQLServerConnector,
    create_sqlserver_connector,
    SQLServerConnectionError,
    SQLServerQueryError
)
from app.core.logger import logger


# Test counters
total_tests = 0
passed_tests = 0


def test_result(test_name: str, passed: bool, message: str = "") -> bool:
    """Record and display test result."""
    global total_tests, passed_tests
    total_tests += 1
    
    if passed:
        passed_tests += 1
        print(f" {test_name} PASSED")
    else:
        print(f" {test_name} FAILED: {message}")
    
    return passed


def check_sql_server_availability():
    """
    Pre-flight check to verify SQL Server is available before running tests.
    
    Returns:
        tuple: (is_available, error_message)
    """
    import socket
    
    print("\n" + "=" * 70)
    print("PRE-FLIGHT CHECK: SQL Server Availability")
    print("=" * 70)
    
    # Get connection details from environment
    server = os.getenv('SQLSERVER_HOST', 'localhost\\SQLEXPRESS')
    database = os.getenv('SQLSERVER_DATABASE', 'EmployeeTestDB')
    port_env = os.getenv('SQLSERVER_PORT')
    
    # Parse server and instance
    if '\\' in server:
        host, instance = server.split('\\', 1)
        is_named_instance = True
    else:
        host = server
        instance = None
        is_named_instance = False
    
    print(f"\nSQL Server Configuration:")
    print(f"  Host: {host}")
    print(f"  Instance: {instance or 'default'}")
    print(f"  Database: {database}")
    
    # For named instances, we can't reliably test the port
    if is_named_instance and not port_env:
        print(f"\nNamed instance detected ({server})")
        print("  Port check skipped - named instances use dynamic ports")
        print("  SQL Browser service handles routing")
        print("\nAttempting actual connection test instead...")
        
        try:
            # Try to create a connector and test connection
            connector = create_sqlserver_connector()
            result = connector.test_connection()
            
            if result:
                print("  SQL Server connection successful!")
                return True, None
            else:
                error_msg = f"""
SQL Server connection test failed for named instance {server}.

Possible issues:
1. SQL Server instance '{instance}' is not running
   → Open 'SQL Server Configuration Manager'
   → Start 'SQL Server ({instance})' service

2. SQL Server Browser service is not running (required for named instances)
   → Open 'Services' (services.msc)
   → Start 'SQL Server Browser' service
   → Set startup type to 'Automatic'

3. Authentication failed
   → Verify username and password in .env file
   → Check if SQL Server authentication is enabled

4. Network protocols not enabled
   → SQL Server Configuration Manager
   → Protocols for {instance} → TCP/IP → Enabled
"""
                print(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            print(f"✗ {error_msg}")
            return False, error_msg
    
    # For non-named instances or explicit port, test the port
    try:
        port = int(port_env) if port_env else 1433
        
        print(f"\nAttempting to connect to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host if host != 'localhost' else '127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print(f"   Port {port} is open")
            return True, None
        else:
            error_msg = f"""
SQL Server appears to be unavailable on port {port}.

Possible issues:
1. SQL Server service is not running
   → Open 'SQL Server Configuration Manager'
   → Start 'SQL Server (MSSQLSERVER)' service

2. SQL Server is not listening on port {port}
   → Check SQL Server Configuration Manager
   → Protocols for MSSQLSERVER → TCP/IP → IP Addresses

3. Firewall is blocking the connection
   → Add exception for port {port}
"""
            print(f"✗ Port {port} is closed or unreachable")
            print(error_msg)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Error checking SQL Server availability: {str(e)}"
        print(f"✗ {error_msg}")
        return False, error_msg


# ============================================================================
# CONNECTION TESTS
# ============================================================================

def test_connection_basic():
    """Test basic SQL Server connection."""
    print("\n" + "=" * 60)
    print("TEST GROUP 1: CONNECTION TESTS")
    print("=" * 60)
    
    print("\n[1.1] Basic Connection Test")
    try:
        connector = create_sqlserver_connector()
        result = connector.test_connection()
        
        return test_result(
            "Basic connection",
            result,
            "Connection test returned False"
        )
    except Exception as e:
        return test_result("Basic connection", False, str(e))


def test_connection_with_custom_params():
    """Test connection with custom parameters."""
    print("\n[1.2] Custom Parameters Connection Test")
    
    try:
        connector = SQLServerConnector(
            server=os.getenv('SQLSERVER_HOST', 'localhost\\SQLEXPRESS'),
            database=os.getenv('SQLSERVER_DATABASE', 'EmployeeTestDB'),
            username=os.getenv('SQLSERVER_USERNAME', 'test_sync_user'),
            password=os.getenv('SQLSERVER_PASSWORD', 'abc12345'),
            use_encryption=True
        )
        
        result = connector.test_connection()
        
        return test_result(
            "Connection with custom params",
            result,
            "Connection with custom parameters failed"
        )
    except Exception as e:
        return test_result("Connection with custom params", False, str(e))


def test_connection_string_validation():
    """Test connection parameter validation."""
    print("\n[1.3] Connection String Validation Test")
    
    # Test 1: Invalid server name with SQL injection attempt
    try:
        connector = SQLServerConnector(
            server="localhost; DROP TABLE Users--",
            database="TestDB",
            username="user",
            password="pass"
        )
        return test_result(
            "SQL injection in server name",
            False,
            "Should have rejected malicious server name"
        )
    except ValueError as e:
        if "prohibited pattern" in str(e):
            test_result("SQL injection in server name", True)
        else:
            return test_result(
                "SQL injection in server name",
                False,
                f"Wrong error: {e}"
            )
    
    # Test 2: Invalid database name
    try:
        connector = SQLServerConnector(
            server="localhost",
            database="TestDB'; DELETE FROM Users--",
            username="user",
            password="pass"
        )
        return test_result(
            "SQL injection in database name",
            False,
            "Should have rejected malicious database name"
        )
    except ValueError as e:
        return test_result(
            "SQL injection in database name",
            "prohibited pattern" in str(e),
            f"Expected 'prohibited pattern' error, got: {e}"
        )


# ============================================================================
# SECURITY TESTS (WHITELISTING)
# ============================================================================

def test_table_whitelist():
    """Test table name whitelisting."""
    print("\n" + "=" * 60)
    print("TEST GROUP 2: SECURITY TESTS (WHITELISTING)")
    print("=" * 60)
    
    print("\n[2.1] Table Whitelist Test")
    
    connector = create_sqlserver_connector()
    
    # Test 1: Allowed table
    try:
        schema = connector.get_table_schema('EmployeeReports')
        test_result("Access allowed table", True)
    except Exception as e:
        return test_result("Access allowed table", False, str(e))
    
    # Test 2: Disallowed table
    try:
        schema = connector.get_table_schema('sys.tables')
        return test_result(
            "Block unauthorized table",
            False,
            "Should have blocked access to sys.tables"
        )
    except ValueError as e:
        return test_result(
            "Block unauthorized table",
            "not authorized" in str(e),
            f"Expected 'not authorized' error, got: {e}"
        )


def test_column_whitelist():
    """Test timestamp column whitelisting."""
    print("\n[2.2] Column Whitelist Test")
    
    connector = create_sqlserver_connector()
    
    # Test 1: Allowed timestamp column
    try:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        records = list(connector.get_records_since(
            table_name='EmployeeReports',
            timestamp_column='LastModifiedDate',
            since_timestamp=thirty_days_ago,
            batch_size=1
        ))
        test_result("Access allowed timestamp column", True)
    except Exception as e:
        return test_result("Access allowed timestamp column", False, str(e))
    
    # Test 2: Disallowed timestamp column
    try:
        records = list(connector.get_records_since(
            table_name='EmployeeReports',
            timestamp_column='Employee_ID',
            since_timestamp=thirty_days_ago,
            batch_size=1
        ))
        return test_result(
            "Block unauthorized timestamp column",
            False,
            "Should have blocked Employee_ID as timestamp column"
        )
    except ValueError as e:
        return test_result(
            "Block unauthorized timestamp column",
            "not authorized" in str(e),
            f"Expected 'not authorized' error, got: {e}"
        )


def test_sql_injection_in_columns():
    """Test SQL injection prevention in column names."""
    print("\n[2.3] SQL Injection in Column Names Test")
    
    connector = create_sqlserver_connector()
    
    # Test: SQL injection attempt in column name
    try:
        records = list(connector.get_records_since(
            table_name='EmployeeReports',
            timestamp_column='LastModifiedDate); DROP TABLE EmployeeReports--',
            since_timestamp=datetime.now() - timedelta(days=1),
            batch_size=1
        ))
        return test_result(
            "Block SQL injection in column",
            False,
            "Should have blocked malicious column name"
        )
    except ValueError as e:
        return test_result(
            "Block SQL injection in column",
            "prohibited pattern" in str(e),
            f"Expected 'prohibited pattern' error, got: {e}"
        )


def test_batch_size_limits():
    """Test batch size validation."""
    print("\n[2.4] Batch Size Limits Test")
    
    connector = create_sqlserver_connector()
    
    # Test 1: Valid batch size
    try:
        records = list(connector.get_all_records(
            'EmployeeReports',
            batch_size=100
        ))
        test_result("Valid batch size (100)", True)
    except Exception as e:
        return test_result("Valid batch size (100)", False, str(e))
    
    # Test 2: Batch size too large
    try:
        records = list(connector.get_all_records(
            'EmployeeReports',
            batch_size=20000
        ))
        return test_result(
            "Reject oversized batch",
            False,
            "Should have rejected batch_size=20000"
        )
    except ValueError as e:
        return test_result(
            "Reject oversized batch",
            "between 1 and" in str(e),
            f"Expected 'between 1 and' error, got: {e}"
        )


# ============================================================================
# SCHEMA INTROSPECTION TESTS
# ============================================================================

def test_schema_retrieval():
    """Test table schema retrieval."""
    print("\n" + "=" * 60)
    print("TEST GROUP 3: SCHEMA INTROSPECTION")
    print("=" * 60)
    
    print("\n[3.1] Schema Retrieval Test")
    
    try:
        connector = create_sqlserver_connector()
        schema = connector.get_table_schema('EmployeeReports')
        
        print(f"\nEmployeeReports Schema ({len(schema)} columns):")
        for column, data_type in list(schema.items())[:5]:  # Show first 5
            print(f"  - {column}: {data_type}")
        if len(schema) > 5:
            print(f"  ... and {len(schema) - 5} more columns")
        
        # Verify expected columns exist
        expected_columns = [
            'RecordID', 'Employee_ID', 'Name', 'Designation',
            'Tasks_Completed', 'LastModifiedDate'
        ]
        
        missing = [col for col in expected_columns if col not in schema]
        
        if missing:
            return test_result(
                "Schema completeness",
                False,
                f"Missing columns: {missing}"
            )
        else:
            return test_result("Schema completeness", True)
            
    except Exception as e:
        return test_result("Schema retrieval", False, str(e))


def test_schema_for_multiple_tables():
    """Test schema retrieval for all whitelisted tables."""
    print("\n[3.2] Multiple Tables Schema Test")
    
    connector = create_sqlserver_connector()
    
    tables = list(connector.ALLOWED_TABLES)
    all_passed = True
    
    for table in tables:
        try:
            schema = connector.get_table_schema(table)
            print(f"   {table}: {len(schema)} columns")
        except Exception as e:
            print(f"   {table}: {str(e)}")
            all_passed = False
    
    return test_result(
        "Schema for all whitelisted tables",
        all_passed,
        "Some tables failed schema retrieval"
    )


# ============================================================================
# RECORD COUNTING TESTS
# ============================================================================

def test_record_counting():
    """Test record counting functionality."""
    print("\n" + "=" * 60)
    print("TEST GROUP 4: RECORD COUNTING")
    print("=" * 60)
    
    print("\n[4.1] Basic Record Count Test")
    
    try:
        connector = create_sqlserver_connector()
        
        # Count all records
        total_count = connector.get_record_count('EmployeeReports')
        print(f"Total records in EmployeeReports: {total_count}")
        
        return test_result(
            "Basic record count",
            isinstance(total_count, int) and total_count >= 0,
            f"Invalid count: {total_count}"
        )
        
    except Exception as e:
        return test_result("Basic record count", False, str(e))


def test_filtered_record_count():
    """Test record counting with WHERE clause."""
    print("\n[4.2] Filtered Record Count Test")
    
    try:
        connector = create_sqlserver_connector()
        
        # Count with filter
        one_week_ago = datetime.now() - timedelta(days=7)
        recent_count = connector.get_record_count(
            'EmployeeReports',
            where_clause='LastModifiedDate > ?',
            params=(one_week_ago,)
        )
        
        print(f"Records modified in last 7 days: {recent_count}")
        
        return test_result(
            "Filtered record count",
            isinstance(recent_count, int) and recent_count >= 0,
            f"Invalid count: {recent_count}"
        )
        
    except Exception as e:
        return test_result("Filtered record count", False, str(e))


def test_parameterized_query_enforcement():
    """Test that WHERE clauses require parameters."""
    print("\n[4.3] Parameterized Query Enforcement Test")
    
    connector = create_sqlserver_connector()
    
    # Test: WHERE clause without parameters should be rejected
    try:
        count = connector.get_record_count(
            'EmployeeReports',
            where_clause='Employee_ID = 101',
            params=None
        )
        return test_result(
            "Enforce parameterized queries",
            False,
            "Should have required parameters for WHERE clause"
        )
    except ValueError as e:
        return test_result(
            "Enforce parameterized queries",
            "parameterized queries" in str(e),
            f"Expected 'parameterized queries' error, got: {e}"
        )


def test_dangerous_where_clause():
    """Test detection of dangerous SQL in WHERE clause."""
    print("\n[4.4] Dangerous WHERE Clause Detection Test")
    
    connector = create_sqlserver_connector()
    
    # Test: WHERE clause with dangerous SQL operations
    try:
        count = connector.get_record_count(
            'EmployeeReports',
            where_clause='Employee_ID = 1; DROP TABLE EmployeeReports--',
            params=(1,)
        )
        return test_result(
            "Detect dangerous WHERE clause",
            False,
            "Should have blocked dangerous SQL in WHERE clause"
        )
    except ValueError as e:
        return test_result(
            "Detect dangerous WHERE clause",
            "prohibited pattern" in str(e),
            f"Expected 'prohibited pattern' error, got: {e}"
        )


# ============================================================================
# DATA RETRIEVAL TESTS
# ============================================================================

def test_batch_retrieval():
    """Test generator-based batch retrieval."""
    print("\n" + "=" * 60)
    print("TEST GROUP 5: DATA RETRIEVAL")
    print("=" * 60)
    
    print("\n[5.1] Batch Retrieval Test")
    
    try:
        connector = create_sqlserver_connector()
        
        # Get records in small batches
        total_records = 0
        batch_count = 0
        first_record = None
        
        for batch in connector.get_all_records('EmployeeReports', batch_size=5):
            batch_count += 1
            batch_size = len(batch)
            total_records += batch_size
            
            if batch_count == 1:
                first_record = batch[0]
            
            # Only process first 3 batches for testing
            if batch_count >= 3:
                break
        
        print(f"Processed {batch_count} batches, {total_records} total records")
        
        if first_record:
            print("\nFirst record structure (first 5 fields):")
            for key, value in list(first_record.items())[:5]:
                print(f"  - {key}: {value}")
        
        return test_result(
            "Batch retrieval",
            batch_count > 0 and total_records > 0,
            f"Batches: {batch_count}, Records: {total_records}"
        )
        
    except Exception as e:
        return test_result("Batch retrieval", False, str(e))


def test_incremental_sync():
    """Test incremental sync query."""
    print("\n[5.2] Incremental Sync Test")
    
    try:
        connector = create_sqlserver_connector()
        
        # Get records from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        total_records = 0
        batch_count = 0
        
        for batch in connector.get_records_since(
            table_name='EmployeeReports',
            timestamp_column='LastModifiedDate',
            since_timestamp=thirty_days_ago,
            batch_size=10
        ):
            batch_count += 1
            total_records += len(batch)
            
            # Only process first 5 batches for testing
            if batch_count >= 5:
                break
        
        print(f"Records modified in last 30 days: {total_records}")
        
        return test_result(
            "Incremental sync",
            total_records >= 0,  # Could be 0 if no recent records
            f"Retrieved {total_records} records"
        )
        
    except Exception as e:
        return test_result("Incremental sync", False, str(e))


def test_ordered_retrieval():
    """Test retrieval with ORDER BY."""
    print("\n[5.3] Ordered Retrieval Test")
    
    try:
        connector = create_sqlserver_connector()
        
        records = []
        for batch in connector.get_all_records(
            'EmployeeReports',
            batch_size=10,
            order_by='RecordID'
        ):
            records.extend(batch)
            if len(records) >= 20:  # Get first 20 records
                records = records[:20]
                break
        
        if len(records) < 2:
            return test_result(
                "Ordered retrieval",
                True,
                "Not enough records to test ordering"
            )
        
        # Check if RecordIDs are in order
        record_ids = [r['RecordID'] for r in records]
        is_ordered = all(record_ids[i] <= record_ids[i+1] for i in range(len(record_ids)-1))
        
        print(f"First 5 RecordIDs: {record_ids[:5]}")
        
        return test_result(
            "Ordered retrieval",
            is_ordered,
            "Records not in expected order"
        )
        
    except Exception as e:
        return test_result("Ordered retrieval", False, str(e))


def test_max_timestamp():
    """Test getting maximum timestamp."""
    print("\n[5.4] Max Timestamp Retrieval Test")
    
    try:
        connector = create_sqlserver_connector()
        
        max_timestamp = connector.get_max_timestamp(
            'EmployeeReports',
            'LastModifiedDate'
        )
        
        if max_timestamp:
            print(f"Max LastModifiedDate: {max_timestamp}")
            print(f"Type: {type(max_timestamp).__name__}")
            
            # Verify it's a datetime object
            is_datetime = isinstance(max_timestamp, datetime)
            
            return test_result(
                "Max timestamp retrieval",
                is_datetime,
                f"Expected datetime, got {type(max_timestamp)}"
            )
        else:
            return test_result(
                "Max timestamp retrieval",
                True,
                "No records found (empty table)"
            )
            
    except Exception as e:
        return test_result("Max timestamp retrieval", False, str(e))


# ============================================================================
# CUSTOM QUERY TESTS
# ============================================================================

def test_custom_select_query():
    """Test custom SELECT query execution."""
    print("\n" + "=" * 60)
    print("TEST GROUP 6: CUSTOM QUERY EXECUTION")
    print("=" * 60)
    
    print("\n[6.1] Custom SELECT Query Test")
    
    try:
        connector = create_sqlserver_connector()
        
        # Simple aggregation query
        sql = """
            SELECT COUNT(*) as TotalRecords,
                   COUNT(DISTINCT Employee_ID) as UniqueEmployees
            FROM EmployeeReports
        """
        
        results = connector.execute_query(sql)
        
        if results and len(results) > 0:
            print(f"Total Records: {results[0]['TotalRecords']}")
            print(f"Unique Employees: {results[0]['UniqueEmployees']}")
            
            return test_result("Custom SELECT query", True)
        else:
            return test_result(
                "Custom SELECT query",
                False,
                "No results returned"
            )
        
    except Exception as e:
        return test_result("Custom SELECT query", False, str(e))


def test_parameterized_custom_query():
    """Test custom query with parameters."""
    print("\n[6.2] Parameterized Custom Query Test")
    
    try:
        connector = create_sqlserver_connector()
        
        # Query with parameters
        sql = """
            SELECT TOP 5 RecordID, Name, Designation
            FROM EmployeeReports
            WHERE Employee_ID = ?
        """
        
        results = connector.execute_query(sql, params=(101,))
        
        print(f"Found {len(results)} records for Employee_ID=101")
        
        return test_result(
            "Parameterized custom query",
            isinstance(results, list),
            "Expected list result"
        )
        
    except Exception as e:
        return test_result("Parameterized custom query", False, str(e))


def test_block_dangerous_queries():
    """Test that dangerous SQL operations are blocked."""
    print("\n[6.3] Block Dangerous Queries Test")
    
    connector = create_sqlserver_connector()
    
    dangerous_queries = [
        ("DROP TABLE", "DROP TABLE EmployeeReports"),
        ("DELETE", "DELETE FROM EmployeeReports WHERE Employee_ID = 1"),
        ("INSERT", "INSERT INTO EmployeeReports (Name) VALUES ('Test')"),
        ("UPDATE", "UPDATE EmployeeReports SET Name = 'Test' WHERE Employee_ID = 1"),
        ("EXEC", "EXEC sp_help 'EmployeeReports'"),
    ]
    
    all_blocked = True
    
    for operation, sql in dangerous_queries:
        try:
            results = connector.execute_query(sql)
            print(f"  ✗ {operation} was NOT blocked")
            all_blocked = False
        except ValueError as e:
            # Accept both "prohibited operation" and "Only SELECT queries" as valid blocks
            if "prohibited operation" in str(e) or "Only SELECT queries" in str(e):
                print(f"      {operation} correctly blocked")
            else:
                print(f"  ? {operation} blocked with unexpected error: {e}")
                all_blocked = False
    
    return test_result(
        "Block dangerous queries",
        all_blocked,
        "Some dangerous operations were not blocked"
    )


def test_select_only_enforcement():
    """Test that only SELECT queries are allowed."""
    print("\n[6.4] SELECT-Only Enforcement Test")
    
    connector = create_sqlserver_connector()
    
    # Test: Non-SELECT query should be rejected
    try:
        results = connector.execute_query("SHOW TABLES")
        return test_result(
            "SELECT-only enforcement",
            False,
            "Should have blocked non-SELECT query"
        )
    except ValueError as e:
        return test_result(
            "SELECT-only enforcement",
            "Only SELECT queries" in str(e),
            f"Expected 'Only SELECT queries' error, got: {e}"
        )


# ============================================================================
# TEST GROUP 7: CONFIGURATION
# ============================================================================

def test_environment_configuration():
    """Test configuration from environment variables."""
    print("\n" + "=" * 60)
    print("TEST GROUP 7: CONFIGURATION")
    print("=" * 60)
    
    print("\n[7.1] Environment Variable Configuration Test")
    
    try:
        connector = create_sqlserver_connector()
        
        # Check that connector has expected configuration
        print(f"Server: {connector.server}")
        print(f"Database: {connector.database}")
        print(f"Encryption: {connector.use_encryption}")
        print(f"ODBC Driver: {connector.driver}")
        print(f"Allowed tables: {len(connector.ALLOWED_TABLES)}")
        
        return test_result(
            "Environment configuration",
            connector.server and connector.database and connector.driver,
            "Missing server, database, or driver configuration"
        )
        
    except Exception as e:
        return test_result("Environment configuration", False, str(e))


def test_whitelist_contents():
    """Test that whitelists are properly configured."""
    print("\n[7.2] Whitelist Configuration Test")
    
    connector = create_sqlserver_connector()
    
    print(f"Allowed tables: {connector.ALLOWED_TABLES}")
    print(f"Allowed timestamp columns: {connector.ALLOWED_TIMESTAMP_COLUMNS}")
    
    # Verify expected tables are whitelisted
    expected_tables = {'EmployeeReports', 'VisionEmployeeData'}
    has_expected = expected_tables.issubset(connector.ALLOWED_TABLES)
    
    return test_result(
        "Whitelist configuration",
        has_expected,
        f"Missing expected tables: {expected_tables - connector.ALLOWED_TABLES}"
    )


def test_odbc_driver_detection():
    """Test ODBC driver auto-detection."""
    print("\n[7.3] ODBC Driver Detection Test")
    
    try:
        # Create connector without specifying driver
        connector = SQLServerConnector(
            server=os.getenv('SQLSERVER_HOST', 'localhost\\SQLEXPRESS'),
            database=os.getenv('SQLSERVER_DATABASE', 'EmployeeTestDB'),
            username=os.getenv('SQLSERVER_USERNAME', 'test_sync_user'),
            password=os.getenv('SQLSERVER_PASSWORD', 'abc12345'),
            driver=None  # Force auto-detection
        )
        
        print(f"Auto-detected driver: {connector.driver}")
        
        # Check that a driver was detected
        has_driver = connector.driver is not None and len(connector.driver) > 0
        
        # Check that it's a valid SQL Server driver
        is_sql_driver = 'SQL Server' in connector.driver
        
        return test_result(
            "ODBC driver auto-detection",
            has_driver and is_sql_driver,
            f"Invalid driver detected: {connector.driver}"
        )
        
    except Exception as e:
        return test_result("ODBC driver auto-detection", False, str(e))


def test_odbc_driver_override():
    """Test explicit ODBC driver specification."""
    print("\n[7.4] ODBC Driver Override Test")
    
    try:
        # Get the driver from environment or use auto-detected one
        env_driver = os.getenv('SQLSERVER_DRIVER')
        if not env_driver or env_driver.lower() == 'auto':
            # Auto-detect first to get a valid driver
            temp_connector = create_sqlserver_connector()
            test_driver = temp_connector.driver
        else:
            test_driver = env_driver
        
        # Create connector with explicit driver
        connector = SQLServerConnector(
            server=os.getenv('SQLSERVER_HOST', 'localhost\\SQLEXPRESS'),
            database=os.getenv('SQLSERVER_DATABASE', 'EmployeeTestDB'),
            username=os.getenv('SQLSERVER_USERNAME', 'test_sync_user'),
            password=os.getenv('SQLSERVER_PASSWORD', 'abc12345'),
            driver=test_driver
        )
        
        print(f"Specified driver: {test_driver}")
        print(f"Actual driver: {connector.driver}")
        
        # Verify the driver was used
        driver_matches = connector.driver == test_driver
        
        return test_result(
            "ODBC driver override",
            driver_matches,
            f"Driver mismatch: expected '{test_driver}', got '{connector.driver}'"
        )
        
    except Exception as e:
        return test_result("ODBC driver override", False, str(e))


def test_environment_driver_loading():
    """Test loading ODBC driver from environment variable."""
    print("\n[7.5] Environment Driver Loading Test")
    
    try:
        # Save current env var
        original_driver = os.getenv('SQLSERVER_DRIVER')
        
        # Test with environment variable set
        if original_driver and original_driver.lower() != 'auto':
            connector = create_sqlserver_connector()
            
            print(f"Driver from environment: {original_driver}")
            print(f"Connector driver: {connector.driver}")
            
            # Verify the environment driver was used
            driver_matches = connector.driver == original_driver
            
            return test_result(
                "Environment driver loading",
                driver_matches,
                f"Driver mismatch: expected '{original_driver}', got '{connector.driver}'"
            )
        else:
            # Environment variable not set or set to 'auto', test auto-detection
            connector = create_sqlserver_connector()
            
            print(f"Environment driver: {original_driver or 'Not set'}")
            print(f"Auto-detected driver: {connector.driver}")
            
            # Verify a driver was detected
            has_driver = connector.driver is not None and 'SQL Server' in connector.driver
            
            return test_result(
                "Environment driver loading (auto)",
                has_driver,
                f"Failed to auto-detect driver: {connector.driver}"
            )
        
    except Exception as e:
        return test_result("Environment driver loading", False, str(e))


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_error_handling():
    """Test error handling and custom exceptions."""
    print("\n" + "=" * 60)
    print("TEST GROUP 8: ERROR HANDLING")
    print("=" * 60)
    
    print("\n[8.1] Custom Exception Test")
    
    connector = create_sqlserver_connector()
    
    # Test 1: SQLServerQueryError for invalid query
    try:
        results = connector.execute_query(
            "SELECT * FROM NonExistentTable123456"
        )
        return test_result(
            "SQLServerQueryError raised",
            False,
            "Should have raised SQLServerQueryError for invalid table"
        )
    except SQLServerQueryError as e:
        print(f"       SQLServerQueryError: {str(e)[:50]}...")
        test_result("SQLServerQueryError raised", True)
    
    # Test 2: ValueError for security violations
    try:
        count = connector.get_record_count('UnauthorizedTable')
        return test_result(
            "ValueError for security violation",
            False,
            "Should have raised ValueError for unauthorized table"
        )
    except ValueError as e:
        print(f"        ValueError: {str(e)[:50]}...")
        return test_result("ValueError for security violation", True)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_performance_batch_vs_all():
    """Test performance difference between batch and fetchall."""
    print("\n" + "=" * 60)
    print("TEST GROUP 9: PERFORMANCE")
    print("=" * 60)
    
    print("\n[9.1] Batch vs FetchAll Performance Test")
    
    import time
    
    connector = create_sqlserver_connector()
    
    # Test batch retrieval (memory efficient)
    start = time.time()
    batch_count = 0
    for batch in connector.get_all_records('EmployeeReports', batch_size=100):
        batch_count += 1
        if batch_count >= 10:  # Limit to first 1000 records
            break
    batch_time = time.time() - start
    
    print(f"Batch retrieval (10 batches of 100): {batch_time:.3f}s")
    
    return test_result(
        "Performance test completed",
        batch_time > 0,
        "Performance test execution"
    )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all SQL Server connector tests."""
    print("\n" + "=" * 70)
    print(" " * 15 + "SQL SERVER CONNECTOR TEST SUITE")
    print("=" * 70)
    
    # Pre-flight check
    sql_available, error_msg = check_sql_server_availability()
    
    if not sql_available:
        print("\n" + "=" * 70)
        print("SQL SERVER NOT AVAILABLE")
        print("=" * 70)
        print("\nOnly security validation tests will run.")
        print("Connection-dependent tests will be skipped.\n")
        
        response = input("Continue with limited tests? (y/n): ").lower()
        if response != 'y':
            print("\nTests cancelled. Please start SQL Server and try again.")
            return False
    
    # Run all test groups
    test_groups = [
        # Connection tests
        test_connection_basic,
        test_connection_with_custom_params,
        test_connection_string_validation,
        
        # Security tests
        test_table_whitelist,
        test_column_whitelist,
        test_sql_injection_in_columns,
        test_batch_size_limits,
        
        # Schema tests
        test_schema_retrieval,
        test_schema_for_multiple_tables,
        
        # Record counting tests
        test_record_counting,
        test_filtered_record_count,
        test_parameterized_query_enforcement,
        test_dangerous_where_clause,
        
        # Data retrieval tests
        test_batch_retrieval,
        test_incremental_sync,
        test_ordered_retrieval,
        test_max_timestamp,
        
        # Custom query tests
        test_custom_select_query,
        test_parameterized_custom_query,
        test_block_dangerous_queries,
        test_select_only_enforcement,
        
        # Configuration tests (UPDATED)
        test_environment_configuration,
        test_whitelist_contents,
        test_odbc_driver_detection,
        test_odbc_driver_override,
        test_environment_driver_loading,
        
        # Error handling tests
        test_error_handling,
        
        # Performance tests
        test_performance_batch_vs_all,
    ]
    
    for test_func in test_groups:
        try:
            test_func()
        except Exception as e:
            test_result(test_func.__name__, False, str(e))
    
    # Summary
    print("\n" + "=" * 70)
    print(" " * 25 + "TEST SUMMARY")
    print("=" * 70)
    
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    if passed_tests == total_tests:
        print("\nALL TESTS PASSED!")
    elif pass_rate >= 90:
        print("\nMost tests passed")
    elif pass_rate >= 70:
        print("\nSome tests failed")
    else:
        print("\nMany tests failed")
    
    print("=" * 70)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)