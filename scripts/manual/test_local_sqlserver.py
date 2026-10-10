"""
Test connection to local SQL Server Express instance.
"""
import pyodbc

# Connection details (update these to match your setup)
SERVER = "localhost\\SQLEXPRESS"  
DATABASE = "EmployeeTestDB"
USERNAME = "test_sync_user"
PASSWORD = "abc12345"

def test_local_connection():
    """Test connection to local SQL Server."""
    print("=" * 60)
    print("Testing Local SQL Server Connection")
    print("=" * 60)
    
    # Build connection string
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )
    
    try:
        print(f"\n1. Attempting to connect to:")
        print(f"   Server: {SERVER}")
        print(f"   Database: {DATABASE}")
        print(f"   Username: {USERNAME}")
        print()
        
        # Try to connect
        conn = pyodbc.connect(connection_string, timeout=10)
        cursor = conn.cursor()
        
        print("Connection successful!")
        print()
        
        # Test 1: Get SQL Server version
        print("2. Checking SQL Server version...")
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"   SQL Server Version: {version.split('\\n')[0]}")
        print()
        
        # Test 2: List all tables in the database
        print("3. Listing tables in database...")
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = cursor.fetchall()
        print(f"   Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
        print()
        
        # Test 3: Count records in each table
        print("4. Counting records in tables...")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   {table_name}: {count} rows")
        print()
        
        cursor.close()
        conn.close()
        
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True
        
    except pyodbc.Error as e:
        print(f"\nConnection FAILED!")
        print(f"Error: {str(e)}")
        print()
        print("Common solutions:")
        print("1. Check that SQL Server Express is running")
        print("   - Open 'Services' (Windows + R, type services.msc)")
        print("   - Look for 'SQL Server (SQLEXPRESS)'")
        print("   - Status should be 'Running'")
        print()
        print("2. Verify the server name is correct")
        print("   - Should be: localhost\\SQLEXPRESS (with double backslash)")
        print()
        print("3. Check username and password")
        print("4. Ensure Mixed Mode authentication is enabled")
        print("5. Check if Windows Firewall is blocking port 1433")
        return False

if __name__ == "__main__":
    test_local_connection()