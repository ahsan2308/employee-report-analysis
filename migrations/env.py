from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import text  # Add this import for text function

from alembic import context

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import models so Alembic can detect changes
from app.models.base import Base
from app.models.db_models import Employee, Report, EmployeeAnalysis, QdrantMapping
from app.models.task_models import BackgroundTask  

# Import app config systems
from app.utils.env_loader import load_env_from_file
from app.core.config_provider import get_config_provider

# Load environment variables
load_env_from_file()

# Get configuration
config_provider = get_config_provider()

# This is the Alembic Config object
config = context.config

# Get database connection details from environment or config
db_user = os.getenv("DB_USER") or config_provider.get("user", "myuser", section="database")
db_password = os.getenv("DB_PASSWORD") or config_provider.get("password", "mypassword", section="database")
db_host = os.getenv("DB_HOST") or config_provider.get("host", "localhost", section="database")
db_port = os.getenv("DB_PORT") or config_provider.get("port", "5432", section="database")
db_name = os.getenv("DB_NAME") or config_provider.get("name", "employee_reports", section="database")
schema_name = os.getenv("SCHEMA_NAME", "employee_reports")

# Use SQLALchemy URL section with interpolation
section = config.config_ini_section
config.set_section_option(section, "DB_USER", db_user)
config.set_section_option(section, "DB_PASSWORD", db_password)
config.set_section_option(section, "DB_HOST", db_host)
config.set_section_option(section, "DB_PORT", db_port)
config.set_section_option(section, "DB_NAME", db_name)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set metadata object for Alembic to detect model changes
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=schema_name,  
        include_schemas=True,              
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Print connection info
        print(f"Connected to database: {connection.engine.url}")
        print(f"Creating schema if not exists: {schema_name}")
        
        # Ensure schema exists - create with a proper transaction
        with connection.begin():
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema_name}'))
        
        # Configure migration context with explicit schema settings
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema_name, 
            include_schemas=True,
            include_object=lambda obj, name, type_, reflected, compare_to: 
                obj.schema == schema_name if hasattr(obj, 'schema') else True
        )
        
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
