from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
import os
from app.utils.env_loader import load_env_from_file

# Load environment variables from specific .env file
load_env_from_file()

# Get the schema name from the .env file
schema_name = os.getenv("SCHEMA_NAME", "public")

# Define the Base with the schema
Base = declarative_base(metadata=MetaData(schema=schema_name))