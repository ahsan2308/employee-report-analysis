from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
from dotenv import load_dotenv
import os
# Load environment variables from .env
load_dotenv()

# Get the schema name from the .env file
schema_name = os.getenv("SCHEMA_NAME", "public")

# Define the Base with the schema
Base = declarative_base(metadata=MetaData(schema=schema_name))