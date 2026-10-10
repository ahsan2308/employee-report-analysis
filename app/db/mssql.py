from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_database import BaseDatabase
from app.db.base import Base
import app.models  # noqa: F401  (registers every model on Base.metadata, so create_tables() creates them all)
import os
from app.utils.env_loader import load_env_from_file

# Load environment variables from specific .env file
load_env_from_file()

# Get the schema name from the .env file
schema_name = os.getenv("SCHEMA_NAME", "public")


class MSSQLDatabase(BaseDatabase):
    def __init__(self, db_url, schema_name=schema_name):
        self.db_url = db_url
        self.schema_name = schema_name
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Base = Base 

    def connect(self):
        return self.engine.connect()

    def create_session(self):
        return self.SessionLocal()

    def create_tables(self):
        self.Base.metadata.create_all(bind=self.engine)
