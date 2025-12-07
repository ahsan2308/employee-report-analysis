"""
CSV Processor Factory

This module provides a factory for creating the appropriate CSV processor
based on the CSV file format or explicit type specification.
"""
from typing import List, Type, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.base.base_csv_processor import BaseCSVProcessor
from app.services.csv.error_handler import ImportErrorHandler
from app.core.logger import logger

# Import all processor implementations
from app.services.csv.processors.employee_report_processor import EmployeeReportProcessor
from app.services.csv.processors.vision_data_processor import VisionDataProcessor
from app.services.csv.processors.job_description_processor import JobDescriptionProcessor


class ProcessorFactory:
    """
    Factory for creating CSV processors based on file format.
    
    Uses a registry of processor types to determine the appropriate
    processor for a given CSV file format.
    """
    
    # Registry of all available processors
    _processors = [
        EmployeeReportProcessor,
        VisionDataProcessor,
        JobDescriptionProcessor
    ]
    
    @classmethod
    def get_processor(cls, 
                    headers: List[str], 
                    db: Session, 
                    error_handler: ImportErrorHandler,
                    processor_type: Optional[str] = None) -> Tuple[BaseCSVProcessor, str]:
        """
        Get the appropriate processor for the CSV format.
        
        Args:
            headers: CSV headers from the file
            db: Database session
            error_handler: Error handler for collecting errors
            processor_type: Optional explicit processor type to use
            
        Returns:
            Tuple of (processor_instance, csv_type_string)
        """
        # If explicit type is provided, use that
        if processor_type:
            for processor_cls in cls._processors:
                if processor_cls.__name__ == processor_type:
                    logger.info(f"Using explicitly specified processor: {processor_type}")
                    csv_type = cls._get_csv_type_for_processor(processor_cls.__name__)
                    return processor_cls(db, error_handler), csv_type
            
            # If explicit type is not found, fall back to header detection
            logger.warning(f"Specified processor type '{processor_type}' not found. Falling back to header detection.")
        
        # Try each processor to find one that can handle the headers
        for processor_cls in cls._processors:
            if processor_cls.can_process(headers):
                logger.info(f"Selected processor: {processor_cls.__name__} based on CSV headers")
                csv_type = cls._get_csv_type_for_processor(processor_cls.__name__)
                return processor_cls(db, error_handler), csv_type
        
        # If no processor matches, provide helpful error with available types
        available_types = [p.__name__ for p in cls._processors]
        raise ValueError(
            f"No suitable processor found for the provided CSV format. "
            f"Available processor types: {', '.join(available_types)}. "
            f"CSV headers: {', '.join(headers)}"
        )
    
    @classmethod
    def _get_csv_type_for_processor(cls, processor_name: str) -> str:
        """Map processor class name to CSVImportType value."""
        from app.models.import_models import CSVImportType
        
        mapping = {
            "EmployeeReportProcessor": CSVImportType.EMPLOYEE_REPORT.value,
            "VisionDataProcessor": CSVImportType.VISION_DATA.value,
            "JobDescriptionProcessor": CSVImportType.JOB_DESCRIPTIONS.value
        }
        
        return mapping.get(processor_name, "unknown")
    
    @classmethod
    def register_processor(cls, processor_cls: Type[BaseCSVProcessor]) -> None:
        """
        Register a new processor type.
        
        Args:
            processor_cls: Processor class to register
        """
        if processor_cls not in cls._processors:
            cls._processors.append(processor_cls)
            logger.info(f"Registered new processor: {processor_cls.__name__}")
