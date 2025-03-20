from fastapi import FastAPI
from app.api.employees import router as employee_router
from app.api.reports import router as report_router
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.models.database_postgres import Base, engine

# Create all tables (if they don't exist)
Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully!")
# Initialize FastAPI app
app = FastAPI(title="Employee Report Analysis API")

# Include routers
app.include_router(employee_router)
app.include_router(report_router)

# Root endpoint
@app.get("/")
def home():
    return {"message": "Welcome to the Employee Report Analysis API"}
