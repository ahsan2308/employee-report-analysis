# SQL Server Connector Configuration

## Environment Variables

### Connection Settings

- `SQLSERVER_HOST`: SQL Server instance (e.g., `localhost\SQLEXPRESS`)
- `SQLSERVER_PORT`: SQL Server port (default: `1433`)
- `SQLSERVER_DATABASE`: Database name (e.g., `EmployeeTestDB`)
- `SQLSERVER_USERNAME`: SQL Server login username
- `SQLSERVER_PASSWORD`: SQL Server login password

### Security Settings

- `SQLSERVER_USE_ENCRYPTION`: Enable SSL/TLS encryption (`true`/`false`, default: `true`)
- `SQLSERVER_READ_ONLY`: Force read-only connection (`true`/`false`, default: `true`)
- `SQLSERVER_CONNECTION_TIMEOUT`: Connection timeout in seconds (default: `30`)
- `SQLSERVER_QUERY_TIMEOUT`: Query timeout in seconds (default: `300`)

### Access Control (Whitelists)

- `SQLSERVER_ALLOWED_TABLES`: Comma-separated list of allowed table names
  - Example: `EmployeeReports,VisionEmployeeData,AnotherTable`
  - Default: `EmployeeReports,VisionEmployeeData`

- `SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS`: Comma-separated list of allowed timestamp column names
  - Example: `LastModifiedDate,ModifiedDate,UpdatedAt,CreatedDate`
  - Default: `LastModifiedDate,ModifiedDate,UpdatedAt`

- `SQLSERVER_MAX_BATCH_SIZE`: Maximum batch size for queries
  - Example: `5000`
  - Default: `10000`

## Adding New Tables/Columns

To allow access to a new table or timestamp column:

1. Update the `.env` file:
   ```properties
   SQLSERVER_ALLOWED_TABLES=EmployeeReports,VisionEmployeeData,NewTableName
   SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS=LastModifiedDate,ModifiedDate,UpdatedAt,NewColumnName
   ```

2. Restart the application to load the new configuration

## Dynamic Configuration (Runtime)

You can also modify allowed tables at runtime:

```python
from app.database.sqlserver_connector import create_sqlserver_connector

connector = create_sqlserver_connector()

# Add a new table dynamically
connector.add_allowed_table('NewTableName')

# Remove a table
connector.remove_allowed_table('OldTableName')

# View current configuration
print(f"Allowed tables: {connector.get_allowed_tables()}")
print(f"Allowed timestamp columns: {connector.get_allowed_timestamp_columns()}")
```

## Security Best Practices

1. **Principle of Least Privilege**: Only whitelist tables that are absolutely necessary for sync operations
2. **Regular Audits**: Periodically review the whitelist and remove tables that are no longer needed
3. **Environment-Specific**: Use different whitelists for development, staging, and production
4. **Documentation**: Keep track of why each table is whitelisted
