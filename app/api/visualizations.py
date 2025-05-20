from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.database import get_database
from app.services.visualization_service import (
    get_sentiment_trends, 
    get_impact_score_trends, 
    get_sentiment_heatmap,
    get_impact_score_heatmap
)
from app.schemas.visualization_schema import SentimentTrendResponse, HeatmapResponse
from app.core.logger import logger

# Initialize Router
router = APIRouter(prefix="/visualizations", tags=["Visualizations"])

# Dependency to get database session (consistent with other API files)
def get_db():
    db_instance = get_database()
    session = db_instance.create_session()
    try:
        yield session
    finally:
        session.close()

@router.get("/sentiment-trends", response_model=SentimentTrendResponse)
def read_sentiment_trends(
    employee_id: Optional[int] = Query(None, description="Filter by specific employee ID"),
    department: Optional[str] = Query(None, description="Filter by specific department/wing"),
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    interval: str = Query("month", description="Time interval for grouping ('day', 'week', 'month', 'quarter', 'year')"),
    db: Session = Depends(get_db) 
):
    """
    Retrieve aggregated sentiment trend data for visualization.
    """
    logger.info(f"Received request for sentiment trends with interval: {interval}")
    try:
        # Validate interval
        allowed_intervals = ["day", "week", "month", "quarter", "year"]
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values are: {', '.join(allowed_intervals)}"
            )

        # Call the service function, passing the db session
        trend_data = get_sentiment_trends(
            db=db,
            employee_id=employee_id,
            department=department,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        # Check if data was returned
        if not trend_data or not trend_data.get("labels"):
             # Return empty structure instead of 404 if no data found for filters
             # This is often preferred for charting libraries
            logger.info("No sentiment trend data found for the given filters.")
            return {"labels": [], "datasets": []}

        return trend_data

    except HTTPException as he:
        # Re-raise HTTP exceptions from validation or service
        raise he
    except Exception as e:
        logger.error(f"Error generating sentiment trends: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while generating sentiment trends.")

@router.get("/impact-trends", response_model=SentimentTrendResponse)
def read_impact_trends(
    employee_id: Optional[int] = Query(None, description="Filter by specific employee ID"),
    department: Optional[str] = Query(None, description="Filter by specific department/wing"),
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    interval: str = Query("month", description="Time interval for grouping ('day', 'week', 'month', 'quarter', 'year')"),
    db: Session = Depends(get_db)
):
    """
    Retrieve aggregated impact score trend data for visualization.
    """
    logger.info(f"Received request for impact score trends with interval: {interval}")
    try:
        # Validate interval
        allowed_intervals = ["day", "week", "month", "quarter", "year"]
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values are: {', '.join(allowed_intervals)}"
            )

        # Call the service function
        trend_data = get_impact_score_trends(
            db=db,
            employee_id=employee_id,
            department=department,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        # Check if data was returned
        if not trend_data or not trend_data.get("labels"):
            logger.info("No impact score trend data found for the given filters.")
            return {"labels": [], "datasets": []}

        return trend_data

    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error generating impact trends: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while generating impact score trends.")

@router.get("/sentiment-heatmap", response_model=HeatmapResponse)
def read_sentiment_heatmap(
    dimension: str = Query("department", description="Dimension for y-axis ('department' or 'employee')"),
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    interval: str = Query("month", description="Time interval for x-axis ('day', 'week', 'month', 'quarter', 'year')"),
    db: Session = Depends(get_db)
):
    """
    Retrieve sentiment heatmap data for visualization.
    """
    logger.info(f"Received request for sentiment heatmap with dimension: {dimension}, interval: {interval}")
    try:
        # Validate interval
        allowed_intervals = ["day", "week", "month", "quarter", "year"]
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values are: {', '.join(allowed_intervals)}"
            )
            
        # Validate dimension
        allowed_dimensions = ["department", "employee"]
        if dimension not in allowed_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dimension. Allowed values are: {', '.join(allowed_dimensions)}"
            )

        # Call the service function
        heatmap_data = get_sentiment_heatmap(
            db=db,
            dimension=dimension,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        # Check if data was returned
        if not heatmap_data or not heatmap_data.get("x_labels") or not heatmap_data.get("y_labels"):
            logger.info("No sentiment heatmap data found for the given filters.")
            return {"x_labels": [], "y_labels": [], "cells": [], "metadata": {"min": 0, "max": 0, "avg": 0}}

        return heatmap_data

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error generating sentiment heatmap: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while generating sentiment heatmap.")

@router.get("/impact-heatmap", response_model=HeatmapResponse)
def read_impact_heatmap(
    dimension: str = Query("department", description="Dimension for y-axis ('department' or 'employee')"),
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    interval: str = Query("month", description="Time interval for x-axis ('day', 'week', 'month', 'quarter', 'year')"),
    db: Session = Depends(get_db)
):
    """
    Retrieve impact score heatmap data for visualization.
    """
    logger.info(f"Received request for impact heatmap with dimension: {dimension}, interval: {interval}")
    try:
        # Validate interval
        allowed_intervals = ["day", "week", "month", "quarter", "year"]
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values are: {', '.join(allowed_intervals)}"
            )
            
        # Validate dimension
        allowed_dimensions = ["department", "employee"]
        if dimension not in allowed_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dimension. Allowed values are: {', '.join(allowed_dimensions)}"
            )

        # Call the service function
        heatmap_data = get_impact_score_heatmap(
            db=db,
            dimension=dimension,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        # Check if data was returned
        if not heatmap_data or not heatmap_data.get("x_labels") or not heatmap_data.get("y_labels"):
            logger.info("No impact heatmap data found for the given filters.")
            return {"x_labels": [], "y_labels": [], "cells": [], "metadata": {"min": 0, "max": 0, "avg": 0}}

        return heatmap_data

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error generating impact heatmap: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while generating impact heatmap.")
