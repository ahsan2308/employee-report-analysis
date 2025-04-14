from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.database import get_database
from app.api.employees import router as employee_router
from app.api.reports import router as report_router
from app.api.analyses import router as analyses_router

# Create all tables (if they don't exist)
db_instance = get_database()  
db_instance.create_tables()

print("✅ Database tables created successfully!")
# Initialize FastAPI app
app = FastAPI(title="Employee Report Analysis API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(employee_router)
app.include_router(report_router)
app.include_router(analyses_router)

# Root endpoint
@app.get("/")
def home():
    return {"message": "Welcome to the Employee Report Analysis API"}
