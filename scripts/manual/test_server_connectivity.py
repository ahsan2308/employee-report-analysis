"""
Test SQL Server connectivity for server deployment.
Run this script on the application server to verify SQL Server access.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.integrations.sqlserver.connector import create_sqlserver_connector
from app.core.logger import logger

def test_server_connectivity():
    """Test SQL Server connectivity with detailed diagnostics."""
    print("=" * 70)
    print("SQL SERVER CONNECTIVITY TEST")
    print("=" * 70)
    
    # Display configuration
    server = os.getenv('SQLSERVER_HOST', 'not set')
    database = os.getenv('SQLSERVER_DATABASE', 'not set')
    port = os.getenv('SQLSERVER_PORT', 'not set')
    
    print(f"\nConfiguration:")
    print(f"  Server: {server}")
    print(f"  Database: {database}")
    print(f"  Port: {port}")
    print(f"  Encryption: {os.getenv('SQLSERVER_USE_ENCRYPTION', 'true')}")
    
    # Test connection
    print("\nAttempting connection...")
    try:
        connector = create_sqlserver_connector()
        result = connector.test_connection()
        
        if result:
            print("SUCCESS: SQL Server connection established!")
            
            # Test query
            print("\nTesting query execution...")
            tables = connector.get_allowed_tables()
            print(f"  Allowed tables: {tables}")
            
            # Test schema retrieval for first table
            if tables:
                first_table = list(tables)[0]
                print(f"\nTesting schema retrieval for '{first_table}'...")
                schema = connector.get_table_schema(first_table)
                print(f"  Schema retrieved: {len(schema)} columns")
                
            print("\n" + "=" * 70)
            print("ALL TESTS PASSED - Server is ready for deployment!")
            print("=" * 70)
            return True
        else:
            print("FAILED: Connection test returned False")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        logger.error(f"Connection test failed: {str(e)}", exc_info=True)
        
        print("\n" + "=" * 70)
        print("TROUBLESHOOTING STEPS:")
        print("=" * 70)
        print("1. Verify SQL Server service is running")
        print("2. Check SQL Server Browser service (for named instances)")
        print("3. Verify firewall allows connections")
        print("4. Test with SQL Server Management Studio from app server")
        print("5. Verify .env file has correct credentials")
        print("6. Check SQL Server error logs")
        
        return False

if __name__ == "__main__":
    success = test_server_connectivity()
    sys.exit(0 if success else 1)
