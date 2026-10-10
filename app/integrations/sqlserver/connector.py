"""
SQL Server Connector

Provides an interface for querying SQL Server data for sync operations.
Uses pyodbc for connection and implements generator-based batching for
memory-efficient data retrieval.
"""

from typing import Generator, Dict, Any, List, Optional, Set
import pyodbc
import os
from datetime import datetime
from contextlib import contextmanager

from app.core.logger import logger


class SQLServerConnectionError(Exception):
    """Raised when SQL Server connection fails."""
    pass


class SQLServerQueryError(Exception):
    """Raised when SQL Server query execution fails."""
    pass


class SQLServerConnector:
    """
    SQL Server connector for sync operations.
    
    Features:
    - Connection per operation (no pooling)
    - Parameterized queries for security
    - Generator-based batching for memory efficiency
    - Comprehensive error handling
    - Encrypted connection strings
    - SQL injection prevention
    - Configurable query whitelisting via environment variables
    """
    
    # Default whitelists (used as fallback if env vars not set)
    DEFAULT_ALLOWED_TABLES = {'EmployeeReports', 'VisionEmployeeData', 'EmployeeJobDescriptions', 'SupervisorFeedback'}
    DEFAULT_ALLOWED_TIMESTAMP_COLUMNS = {'LastModifiedDate', 'ModifiedDate', 'UpdatedAt'}
    DEFAULT_MAX_BATCH_SIZE = 10000
    
    # Common ODBC drivers in order of preference
    COMMON_ODBC_DRIVERS = [
        'ODBC Driver 17 for SQL Server',
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 13 for SQL Server',
        'SQL Server Native Client 11.0',
        'SQL Server'
    ]
    
    def __init__(self, 
                 server: str,
                 database: str,
                 username: str,
                 password: str,
                 port: Optional[int] = None,
                 driver: Optional[str] = None,
                 connection_timeout: int = 30,
                 query_timeout: int = 300,
                 use_encryption: bool = True,
                 allowed_tables: Optional[Set[str]] = None,
                 allowed_timestamp_columns: Optional[Set[str]] = None,
                 max_batch_size: Optional[int] = None):
        """
        Initialize SQL Server connector.
        
        Args:
            server: SQL Server instance (e.g., 'localhost\\SQLEXPRESS' or 'server.domain.com')
            database: Database name
            username: SQL Server login username
            password: SQL Server login password
            port: SQL Server port (optional, only needed for non-default configurations)
            driver: ODBC driver name (optional, will auto-detect if not provided)
            connection_timeout: Connection timeout in seconds (default: 30)
            query_timeout: Query timeout in seconds (default: 300)
            use_encryption: Whether to use SSL/TLS encryption (default: True)
            allowed_tables: Optional set of allowed table names (overrides env var)
            allowed_timestamp_columns: Optional set of allowed timestamp columns (overrides env var)
            max_batch_size: Optional maximum batch size (overrides env var)
        """
        # Validate inputs to prevent SQL injection in connection string
        self._validate_connection_params(server, database, username)
        
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        
        # Priority: 1) Explicit parameter, 2) Environment variable, 3) Auto-detect
        if driver:
            self.driver = driver
        else:
            env_driver = os.getenv('SQLSERVER_DRIVER')
            if env_driver and env_driver.lower() not in ('auto', ''):
                self.driver = env_driver
                logger.info(f"Using ODBC driver from environment: {env_driver}")
            else:
                self.driver = self._detect_odbc_driver()
        
        self.connection_timeout = connection_timeout
        self.query_timeout = query_timeout
        self.use_encryption = use_encryption
        
        # Load security configuration from environment or use provided/default values
        self.allowed_tables = self._load_allowed_tables(allowed_tables)
        self.allowed_timestamp_columns = self._load_allowed_timestamp_columns(allowed_timestamp_columns)
        self.max_batch_size = self._load_max_batch_size(max_batch_size)
        
        # Build connection string
        self.connection_string = self._build_connection_string()
        
        logger.info(f"SQL Server connector initialized for {server}/{database}")
        logger.info(f"Security config: {len(self.allowed_tables)} allowed tables, "
                   f"{len(self.allowed_timestamp_columns)} allowed timestamp columns, "
                   f"max batch size: {self.max_batch_size}")
    
    def _load_allowed_tables(self, override: Optional[Set[str]] = None) -> Set[str]:
        """
        Load allowed tables from environment variable or use override/default.
        
        Args:
            override: Optional set to override environment variable
            
        Returns:
            Set of allowed table names
        """
        if override is not None:
            logger.info(f"Using provided allowed_tables: {override}")
            return override
        
        env_value = os.getenv('SQLSERVER_ALLOWED_TABLES')
        if env_value:
            tables = {table.strip() for table in env_value.split(',') if table.strip()}
            logger.info(f"Loaded allowed_tables from environment: {tables}")
            return tables
        
        logger.warning(f"No SQLSERVER_ALLOWED_TABLES in environment, using defaults: {self.DEFAULT_ALLOWED_TABLES}")
        return self.DEFAULT_ALLOWED_TABLES.copy()
    
    def _load_allowed_timestamp_columns(self, override: Optional[Set[str]] = None) -> Set[str]:
        """
        Load allowed timestamp columns from environment variable or use override/default.
        
        Args:
            override: Optional set to override environment variable
            
        Returns:
            Set of allowed timestamp column names
        """
        if override is not None:
            logger.info(f"Using provided allowed_timestamp_columns: {override}")
            return override
        
        env_value = os.getenv('SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS')
        if env_value:
            columns = {col.strip() for col in env_value.split(',') if col.strip()}
            logger.info(f"Loaded allowed_timestamp_columns from environment: {columns}")
            return columns
        
        logger.warning(f"No SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS in environment, using defaults: {self.DEFAULT_ALLOWED_TIMESTAMP_COLUMNS}")
        return self.DEFAULT_ALLOWED_TIMESTAMP_COLUMNS.copy()
    
    def _load_max_batch_size(self, override: Optional[int] = None) -> int:
        """
        Load maximum batch size from environment variable or use override/default.
        
        Args:
            override: Optional value to override environment variable
            
        Returns:
            Maximum batch size
        """
        if override is not None:
            logger.info(f"Using provided max_batch_size: {override}")
            return override
        
        env_value = os.getenv('SQLSERVER_MAX_BATCH_SIZE')
        if env_value:
            try:
                max_size = int(env_value)
                logger.info(f"Loaded max_batch_size from environment: {max_size}")
                return max_size
            except ValueError:
                logger.warning(f"Invalid SQLSERVER_MAX_BATCH_SIZE value '{env_value}', using default: {self.DEFAULT_MAX_BATCH_SIZE}")
                return self.DEFAULT_MAX_BATCH_SIZE
        
        logger.warning(f"No SQLSERVER_MAX_BATCH_SIZE in environment, using default: {self.DEFAULT_MAX_BATCH_SIZE}")
        return self.DEFAULT_MAX_BATCH_SIZE
    
    def _validate_connection_params(self, server: str, database: str, username: str) -> None:
        """
        Validate connection parameters to prevent injection attacks.
        
        Args:
            server: SQL Server instance name
            database: Database name
            username: Username
            
        Raises:
            ValueError: If parameters contain suspicious characters
        """
        # Check for SQL injection patterns in connection parameters
        dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_', 'DROP', 'DELETE', 'INSERT', 'UPDATE']
        
        for param_name, param_value in [('server', server), ('database', database), ('username', username)]:
            if not param_value or not isinstance(param_value, str):
                raise ValueError(f"Invalid {param_name}: must be a non-empty string")
            
            # Check for dangerous SQL keywords/characters
            for dangerous in dangerous_chars:
                if dangerous.lower() in param_value.lower():
                    logger.error(f"Suspicious pattern detected in {param_name}: {dangerous}")
                    raise ValueError(f"Invalid {param_name}: contains prohibited pattern '{dangerous}'")
            
            # Ensure reasonable length (prevent buffer overflow attempts)
            if len(param_value) > 200:
                raise ValueError(f"Invalid {param_name}: exceeds maximum length of 200 characters")
    
    def _validate_table_name(self, table_name: str) -> None:
        """
        Validate table name against whitelist.
        
        Args:
            table_name: Name of the table to validate
            
        Raises:
            ValueError: If table name is not in whitelist
        """
        if table_name not in self.allowed_tables:
            logger.error(f"Attempted to query unauthorized table: {table_name}")
            raise ValueError(
                f"Table '{table_name}' is not authorized. "
                f"Allowed tables: {', '.join(sorted(self.allowed_tables))}"
            )
    
    def _validate_column_name(self, column_name: str, allowed_columns: Optional[Set[str]] = None) -> None:
        """
        Validate column name to prevent SQL injection.
        
        Args:
            column_name: Name of the column to validate (can be comma-separated for ORDER BY)
            allowed_columns: Optional set of allowed column names
            
        Raises:
            ValueError: If column name contains suspicious patterns
        """
        # Handle ORDER BY clauses with multiple columns (e.g., "RO_Form_ID, LastModifiedDate")
        columns = [col.strip() for col in column_name.split(',')]
        
        for col in columns:
            # Check for SQL injection patterns
            dangerous_patterns = [';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT', 'UPDATE', '(', ')']
            
            for pattern in dangerous_patterns:
                if pattern in col:
                    logger.error(f"Suspicious pattern in column name: {col}")
                    raise ValueError(f"Invalid column name: contains prohibited pattern '{pattern}'")
            
            # Validate against whitelist if provided
            if allowed_columns and col not in allowed_columns:
                logger.error(f"Column '{col}' not in allowed list")
                raise ValueError(
                    f"Column '{col}' is not authorized. "
                    f"Allowed columns: {', '.join(sorted(allowed_columns))}"
                )
            
            # Ensure column name follows SQL naming conventions
            if not col.replace('_', '').isalnum():
                raise ValueError(f"Invalid column name: must contain only alphanumeric characters and underscores")
    
    def _detect_odbc_driver(self) -> str:
        """
        Auto-detect available ODBC driver for SQL Server.
        
        Returns:
            Name of the first available ODBC driver
            
        Raises:
            RuntimeError: If no suitable ODBC driver is found
        """
        
        # Get list of available drivers
        available_drivers = pyodbc.drivers()
        
        logger.debug(f"Available ODBC drivers: {available_drivers}")
        
        # Check our preferred drivers in order
        for preferred_driver in SQLServerConnector.COMMON_ODBC_DRIVERS:  
            if preferred_driver in available_drivers:
                logger.info(f"Auto-detected ODBC driver: {preferred_driver}")
                return preferred_driver
        
        # If no preferred driver found, use any SQL Server driver
        for driver in available_drivers:
            if 'SQL Server' in driver:
                logger.warning(f"Using fallback ODBC driver: {driver}")
                return driver
        
        # No suitable driver found
        error_msg = (
            "No suitable ODBC driver found for SQL Server. "
            f"Available drivers: {', '.join(available_drivers)}. "
            "Please install 'ODBC Driver 17 for SQL Server' or newer."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _build_connection_string(self) -> str:
        """
        Build secure ODBC connection string with encryption.
        
        Returns:
            Connection string with security parameters
        """
        # Basic connection parameters
        conn_str = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
        )
        
        # Only add port if explicitly specified (not None)
        # For named instances like "localhost\SQLEXPRESS", port should NOT be specified
        if self.port is not None:
            conn_str += f"PORT={self.port};"
            logger.info(f"Using explicit port: {self.port}")
        
        if self.use_encryption:
            # Enable encryption and certificate validation
            conn_str += "Encrypt=yes;"
            # In production, should validate server certificate
            # For development/testing, we trust the certificate
            conn_str += "TrustServerCertificate=yes;"
        else:
            conn_str += "TrustServerCertificate=yes;"
        
        # Additional security settings
        conn_str += "ApplicationIntent=ReadOnly;"  
        
        logger.debug(f"Using ODBC driver: {self.driver}")
        
        return conn_str
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for SQL Server connections.
        
        Yields:
            pyodbc.Connection: Database connection
            
        Raises:
            SQLServerConnectionError: If connection fails
        """
        conn = None
        try:
            logger.debug(f"Connecting to SQL Server: {self.server}/{self.database}")
            conn = pyodbc.connect(
                self.connection_string,
                timeout=self.connection_timeout
            )
            conn.timeout = self.query_timeout
            logger.debug("SQL Server connection established")
            yield conn
        except pyodbc.Error as e:
            # Only wrap connection-specific errors, not query errors
            # Connection errors typically have error codes like '08001', '28000', etc.
            if conn is None:  # Connection never established
                error_msg = f"Failed to connect to SQL Server: {str(e)}"
                logger.error(error_msg)
                raise SQLServerConnectionError(error_msg) from e
            else:
                # Connection succeeded but query failed - let it bubble up as-is
                raise
        finally:
            if conn:
                conn.close()
                logger.debug("SQL Server connection closed")
    
    def test_connection(self) -> bool:
        """
        Test SQL Server connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                logger.info("SQL Server connection test successful")
                return result[0] == 1
        except Exception as e:
            logger.error(f"SQL Server connection test failed: {str(e)}")
            return False
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Get table schema (column names and types) with validation.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary mapping column names to data types
            
        Raises:
            ValueError: If table name is not authorized
            SQLServerQueryError: If schema query fails
        """
        # Validate table name against whitelist
        self._validate_table_name(table_name)
        
        query = """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Use parameterized query to prevent SQL injection
                cursor.execute(query, (table_name,))
                
                schema = {}
                for row in cursor.fetchall():
                    column_name, data_type = row
                    schema[column_name] = data_type
                
                logger.info(f"Retrieved schema for table '{table_name}': {len(schema)} columns")
                return schema
                
        except pyodbc.Error as e:
            error_msg = f"Failed to get schema for table '{table_name}': {str(e)}"
            logger.error(error_msg)
            raise SQLServerQueryError(error_msg) from e
    
    def get_record_count(self, 
                        table_name: str,
                        where_clause: Optional[str] = None,
                        params: Optional[tuple] = None) -> int:
        """
        Get record count for a table with optional filter.
        
        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause (without the WHERE keyword)
                         Must use ? placeholders for parameters
            params: Optional parameters for WHERE clause
            
        Returns:
            Number of records matching the criteria
            
        Raises:
            ValueError: If table name is not authorized or where_clause is unsafe
            SQLServerQueryError: If count query fails
        """
        # Validate table name against whitelist
        self._validate_table_name(table_name)
        
        # Validate where clause doesn't contain dangerous patterns
        if where_clause:
            dangerous_patterns = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'EXEC', 'EXECUTE', '--', '/*', '*/']
            where_upper = where_clause.upper()
            for pattern in dangerous_patterns:
                if pattern in where_upper:
                    logger.error(f"Dangerous pattern detected in WHERE clause: {pattern}")
                    raise ValueError(f"WHERE clause contains prohibited pattern: {pattern}")
            
            # Ensure parameterized queries are used (must contain ?)
            if params is None and any(op in where_clause for op in ['=', '>', '<', 'LIKE']):
                logger.warning("WHERE clause without parameters detected - potential SQL injection risk")
                raise ValueError("WHERE clause must use parameterized queries (? placeholders)")
        
        # Build query using parameterized approach
        query = f"SELECT COUNT(*) FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                count = cursor.fetchone()[0]
                logger.info(f"Record count for '{table_name}': {count}")
                return count
                
        except pyodbc.Error as e:
            error_msg = f"Failed to count records in '{table_name}': {str(e)}"
            logger.error(error_msg)
            raise SQLServerQueryError(error_msg) from e
    
    def get_records_since(self,
                         table_name: str,
                         timestamp_column: str,
                         since_timestamp: datetime,
                         batch_size: int = 1000,
                         order_by: Optional[str] = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Get records modified after a specific timestamp (incremental sync).
        
        Args:
            table_name: Name of the table (must be in whitelist)
            timestamp_column: Column name containing modification timestamp (must be in whitelist)
            since_timestamp: Get records modified after this timestamp
            batch_size: Number of records per batch (default: 1000, max: from config)
            order_by: Optional ORDER BY clause (column name only, no SQL expressions)
            
        Yields:
            Batches of records as list of dictionaries
            
        Raises:
            ValueError: If table/column not authorized or batch_size invalid
            SQLServerQueryError: If query fails
        """
        # Validate table name
        self._validate_table_name(table_name)
        
        # Validate timestamp column against configured whitelist
        self._validate_column_name(timestamp_column, self.allowed_timestamp_columns)
        
        # Validate batch size using configured maximum
        if batch_size < 1 or batch_size > self.max_batch_size:
            raise ValueError(f"Batch size must be between 1 and {self.max_batch_size}")
        
        # Validate order_by if provided
        if order_by:
            self._validate_column_name(order_by)
        
        # Use >= instead of > to handle precision mismatches
        # Build query with parameterized WHERE clause
        query = f"SELECT * FROM {table_name} WHERE {timestamp_column} >= ?"
        
        # Add ORDER BY if specified (important for consistent batching)
        if order_by:
            query += f" ORDER BY {order_by}"
        else:
            query += f" ORDER BY {timestamp_column} ASC"
        
        logger.info(f"Fetching records from '{table_name}' modified after {since_timestamp}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (since_timestamp,))
                
                # Get column names
                columns = [column[0] for column in cursor.description]
                
                total_records = 0
                while True:
                    # Fetch batch
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    
                    # Convert to list of dictionaries
                    batch = []
                    for row in rows:
                        record = dict(zip(columns, row))
                        batch.append(record)
                    
                    total_records += len(batch)
                    logger.debug(f"Fetched batch of {len(batch)} records (total: {total_records})")
                    
                    yield batch
                
                logger.info(f"Completed fetch: {total_records} total records from '{table_name}'")
                
        except pyodbc.Error as e:
            error_msg = f"Failed to fetch records from '{table_name}': {str(e)}"
            logger.error(error_msg)
            raise SQLServerQueryError(error_msg) from e
    

    def get_all_records(self,
                       table_name: str,
                       batch_size: int = 1000,
                       order_by: Optional[str] = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Get all records from a table (full sync).
        
        Args:
            table_name: Name of the table (must be in whitelist)
            batch_size: Number of records per batch (default: 1000, max: from config)
            order_by: Optional ORDER BY clause (column name only)
            
        Yields:
            Batches of records as list of dictionaries
            
        Raises:
            ValueError: If table not authorized or batch_size invalid
            SQLServerQueryError: If query fails
        """
        # Validate table name
        self._validate_table_name(table_name)
        
        # Validate batch size using configured maximum
        if batch_size < 1 or batch_size > self.max_batch_size:
            raise ValueError(f"Batch size must be between 1 and {self.max_batch_size}")
        
        # Validate order_by if provided
        if order_by:
            self._validate_column_name(order_by)
        
        # Get table schema to find actual timestamp column
        schema = self.get_table_schema(table_name)
        
        # Find which timestamp column actually exists in this table's schema
        timestamp_col = None
        for col_name in schema.keys():
            if col_name in self.allowed_timestamp_columns:
                timestamp_col = col_name
                logger.info(f"Found timestamp column '{timestamp_col}' in table '{table_name}'")
                break
        
        # Build query
        query = f"SELECT * FROM {table_name}"
        
        # Add ORDER BY based on what we found
        if order_by:
            query += f" ORDER BY {order_by}"
        elif timestamp_col:
            # Use the timestamp column we found for consistent ordering
            query += f" ORDER BY {timestamp_col}"
        else:
            # No timestamp column found, fetch without ordering
            logger.warning(f"No timestamp column found in '{table_name}' schema. Fetching without ordering.")
        
        logger.info(f"Fetching all records from '{table_name}'")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                # Get column names
                columns = [column[0] for column in cursor.description]
                
                total_records = 0
                while True:
                    # Fetch batch
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    
                    # Convert to list of dictionaries
                    batch = []
                    for row in rows:
                        record = dict(zip(columns, row))
                        batch.append(record)
                    
                    total_records += len(batch)
                    logger.debug(f"Fetched batch of {len(batch)} records (total: {total_records})")
                    
                    yield batch
                
                logger.info(f"Completed fetch: {total_records} total records from '{table_name}'")
                
        except pyodbc.Error as e:
            error_msg = f"Failed to fetch all records from '{table_name}': {str(e)}"
            logger.error(error_msg)
            raise SQLServerQueryError(error_msg) from e

    def execute_query(self,
                     sql: str,
                     params: Optional[tuple] = None,
                     fetch_all: bool = True) -> List[Dict[str, Any]]:
        """
        Execute a custom SQL query (RESTRICTED - use with caution).
        
        ⚠️ WARNING: This method is intentionally restricted and should only be used
        for specific administrative queries. All user-facing operations should use
        the dedicated methods (get_records_since, get_all_records, etc.) which have
        built-in security validation.
        
        Args:
            sql: SQL query to execute (must be SELECT only)
            params: Optional query parameters
            fetch_all: Whether to fetch all results (default: True)
            
        Returns:
            List of records as dictionaries
            
        Raises:
            ValueError: If query contains prohibited operations
            SQLServerQueryError: If query fails
        """
        # Security check: Only allow SELECT queries
        sql_upper = sql.strip().upper()
        
        if not sql_upper.startswith('SELECT'):
            logger.error(f"Attempted to execute non-SELECT query: {sql[:100]}")
            raise ValueError("Only SELECT queries are allowed through execute_query()")
        
        # Check for dangerous SQL operations
        dangerous_operations = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'EXEC', 'EXECUTE', 
                               'ALTER', 'CREATE', 'TRUNCATE', 'MERGE', 'GRANT', 'REVOKE']
        
        for operation in dangerous_operations:
            if operation in sql_upper:
                logger.error(f"Dangerous SQL operation detected: {operation}")
                raise ValueError(f"Query contains prohibited operation: {operation}")
        
        # Ensure parameterized queries if WHERE clause is present
        if 'WHERE' in sql_upper and params is None:
            logger.warning("Query with WHERE clause but no parameters - potential SQL injection risk")
            raise ValueError("Queries with WHERE clauses must use parameterized queries")
        
        logger.debug(f"Executing custom query: {sql[:100]}...")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                
                if not fetch_all:
                    return []
                
                # Get column names
                columns = [column[0] for column in cursor.description]
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                results = []
                for row in rows:
                    record = dict(zip(columns, row))
                    results.append(record)
                
                logger.info(f"Query returned {len(results)} records")
                return results
                
        except pyodbc.Error as e:
            error_msg = f"Failed to execute query: {str(e)}"
            logger.error(error_msg)
            raise SQLServerQueryError(error_msg) from e
    
    def get_max_timestamp(self,
                         table_name: str,
                         timestamp_column: str) -> Optional[datetime]:
        """
        Get the maximum timestamp from a table.
        
        Args:
            table_name: Name of the table (must be in whitelist)
            timestamp_column: Column name containing timestamps (must be in whitelist)
            
        Returns:
            Maximum timestamp or None if table is empty
            
        Raises:
            ValueError: If table/column not authorized
            SQLServerQueryError: If query fails
        """
        # Validate table and column names against configured whitelists
        self._validate_table_name(table_name)
        self._validate_column_name(timestamp_column, self.allowed_timestamp_columns)
        
        query = f"SELECT MAX({timestamp_column}) FROM {table_name}"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()[0]
                
                if result:
                    logger.info(f"Max timestamp in '{table_name}.{timestamp_column}': {result}")
                else:
                    logger.info(f"No records found in '{table_name}'")
                
                return result
                
        except pyodbc.Error as e:
            error_msg = f"Failed to get max timestamp from '{table_name}': {str(e)}"
            logger.error(error_msg)
            raise SQLServerQueryError(error_msg) from e
    
    def add_allowed_table(self, table_name: str) -> None:
        """
        Dynamically add a table to the allowed list.
        
        Args:
            table_name: Name of the table to allow
        """
        self.allowed_tables.add(table_name)
        logger.info(f"Added '{table_name}' to allowed tables. Current list: {sorted(self.allowed_tables)}")
    
    def remove_allowed_table(self, table_name: str) -> None:
        """
        Dynamically remove a table from the allowed list.
        
        Args:
            table_name: Name of the table to disallow
        """
        self.allowed_tables.discard(table_name)
        logger.info(f"Removed '{table_name}' from allowed tables. Current list: {sorted(self.allowed_tables)}")
    
    def get_allowed_tables(self) -> Set[str]:
        """Get the current set of allowed tables."""
        return self.allowed_tables.copy()
    
    def get_allowed_timestamp_columns(self) -> Set[str]:
        """Get the current set of allowed timestamp columns."""
        return self.allowed_timestamp_columns.copy()
    
    # Add properties for backward compatibility with tests that expect class attributes
    @property
    def ALLOWED_TABLES(self) -> Set[str]:
        """Get allowed tables (for backward compatibility)."""
        return self.allowed_tables
    
    @property
    def ALLOWED_TIMESTAMP_COLUMNS(self) -> Set[str]:
        """Get allowed timestamp columns (for backward compatibility)."""
        return self.allowed_timestamp_columns


def create_sqlserver_connector() -> SQLServerConnector:
    """
    Factory function to create SQL Server connector from environment variables.
    
    All security configurations (allowed tables, columns, batch sizes) are loaded
    from environment variables with sensible defaults.
    
    Returns:
        Configured SQLServerConnector instance with security defaults
    """
    import os
    
    server = os.getenv('SQLSERVER_HOST', 'localhost\\SQLEXPRESS')
    database = os.getenv('SQLSERVER_DATABASE', 'EmployeeTestDB')
    username = os.getenv('SQLSERVER_USERNAME', 'test_sync_user')
    password = os.getenv('SQLSERVER_PASSWORD', 'abc12345')
    
    # Port is optional - only use if explicitly set in environment
    port_env = os.getenv('SQLSERVER_PORT')
    port = int(port_env) if port_env else None
    
    # Enable encryption by default (can be disabled via env var for testing)
    use_encryption = os.getenv('SQLSERVER_USE_ENCRYPTION', 'true').lower() == 'true'
    
    # Log connection details (without password)
    if port:
        logger.info(f"Creating SQL Server connector: {server}:{port}/{database}")
    else:
        logger.info(f"Creating SQL Server connector: {server}/{database} (dynamic port)")
    
    return SQLServerConnector(
        server=server,
        database=database,
        username=username,
        password=password,
        port=port,  # Will be None if not specified
        use_encryption=use_encryption
        # allowed_tables, allowed_timestamp_columns, max_batch_size are loaded from env vars automatically
    )