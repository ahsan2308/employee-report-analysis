from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from app.base.base_db import BaseDatabase
# from sqlalchemy.orm import declarative_base
from app.models.base import Base
# from sqlalchemy import MetaData
from dotenv import load_dotenv
import os
# Load environment variables from .env
load_dotenv()

# Get the schema name from the .env file
schema_name = os.getenv("SCHEMA_NAME", "public")

class PostgresDatabase(BaseDatabase):
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
        """Create the tables."""
        print(f"Tables to be created: {self.Base.metadata.tables.keys()}")
        self.Base.metadata.create_all(bind=self.engine)
        print("Tables created.")