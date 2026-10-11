from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.db.database import get_database
from app.api.employees import router as employee_router
from app.api.reports import router as report_router
from app.api.analyses import router as analyses_router
from app.api.visualizations import router as visualizations_router
from app.api.tasks import router as tasks_router
from app.api.imports import router as imports_router 
from app.api.sync_routes import router as sync_router 

from app.core import settings
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables (if they don't exist) when the server starts, not on import
    get_database().create_tables()
    logger.info("Database tables created successfully!")
    yield


# Initialize FastAPI app
app = FastAPI(title="Employee Report Analysis API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,  # CORS_ALLOW_ORIGINS; "*" by default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(employee_router)
app.include_router(report_router)
app.include_router(analyses_router)
app.include_router(visualizations_router)
app.include_router(tasks_router)
app.include_router(imports_router)
app.include_router(sync_router)  

# Root endpoint
@app.get("/")
def home():
    return {"message": "Welcome to the Employee Report Analysis API"}
