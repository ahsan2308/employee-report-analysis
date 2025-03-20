import os
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Detect if running inside Docker
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"

# Set database host dynamically
DB_HOST = "db" if RUNNING_IN_DOCKER else os.getenv("DB_HOST", "localhost")

# Database credentials
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")
DB_NAME = os.getenv("DB_NAME", "employee_reports")
DB_PORT = os.getenv("DB_PORT", "5432")
print(DB_HOST)
# Construct Database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create Database Engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata = MetaData(schema="employee_reports")
Base = declarative_base(metadata=metadata)
