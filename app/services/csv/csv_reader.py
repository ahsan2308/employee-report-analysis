"""
CSV Reader Component with pandas for efficient processing.
"""
from typing import List, Dict, Any, Generator, Optional, BinaryIO, TextIO, Union, Tuple
import pandas as pd
import io
from abc import ABC, abstractmethod
import chardet
import os

from app.core.logger import logger


class BaseCSVReader(ABC):
    """Abstract base class for CSV readers."""
    
    @abstractmethod
    def read_csv(self, file_path: str = None, file_obj: Any = None) -> Generator[Dict[str, Any], None, None]:
        """Read CSV and yield rows as dictionaries."""
        pass
        
    @abstractmethod
    def get_total_rows(self) -> int:
        """Get the total number of rows in the CSV file."""
        pass
        
    @abstractmethod
    def get_headers(self) -> List[str]:
        """Get the headers from the CSV file."""
        pass
        
    @abstractmethod
    def validate_headers(self, required_headers: List[str]) -> List[str]:
        """Validate that required headers are present and return missing ones."""
        pass


class PandasCSVReader(BaseCSVReader):
    """
    Enhanced CSV reader using pandas for efficient processing.
    
    Features:
    - Handles large files with chunked processing
    - Automatic data type inference
    - Robust encoding and dialect detection
    - Memory-efficient iteration
    """
    
    # Common encodings to try as fallbacks
    COMMON_ENCODINGS = [
        'utf-8-sig',  # UTF-8 with BOM (common in Windows)
        'utf-8',      # Standard UTF-8
        'windows-1252', # Common in Excel/Windows
        'iso-8859-1',   # Latin-1
        'cp1251',       # Cyrillic
        'utf-16'        # Sometimes used for Unicode
    ]
    
    def __init__(self, chunk_size: int = 1000, encoding: str = None):
        """
        Initialize with optional chunk size and encoding.
        
        Args:
            chunk_size: Number of rows to process at once
            encoding: File encoding (if None, will be auto-detected)
        """
        self.chunk_size = chunk_size
        self.headers = []
        self._row_count = -1
        self._file_obj = None
        self.encoding = encoding
        self._detected_encoding = None
        
    def _get_file_obj(self, file_path: str = None, file_obj: Any = None) -> Any:
        """Get a file object from either a path or file object."""
        if file_obj is not None:
            if isinstance(file_obj, (bytes, BinaryIO)):
                if hasattr(file_obj, 'read'):
                    return file_obj
                return io.BytesIO(file_obj)
            return file_obj
            
        elif file_path is not None:
            return file_path
            
        raise ValueError("Either file_path or file_obj must be provided")
    
    def _count_total_rows(self, file_obj: Any) -> int:
        """Count actual data rows in file (excluding header, empty rows, and comments)."""
        try:
            # For file paths, leverage our existing _read_with_encoding_fallback method
            # which already handles encoding detection and fallback mechanisms
            if isinstance(file_obj, str):
                # Use the same parameters we're already using in read_dataframes for consistency
                df_reader = self._read_with_encoding_fallback(
                    file_obj,
                    encoding=self.encoding,
                    dtype=str,
                    na_values=[''],
                    keep_default_na=False,
                    chunksize=10000,  # Use larger chunks for faster counting
                    iterator=True
                )
                
                # Count rows across all chunks
                if hasattr(df_reader, '__iter__'):  # It's a chunked reader
                    total_rows = sum(len(chunk) for chunk in df_reader)
                    logger.debug(f"Counted {total_rows} actual data rows in CSV file")
                    return total_rows
                else:  # It's a single DataFrame (for small files)
                    return len(df_reader)
            
            # For file objects, need to preserve position
            else:
                # Save current position
                pos = file_obj.tell()
                try:
                    # Reset to beginning
                    file_obj.seek(0)
                    
                    # Use our existing method with the same parameters as elsewhere
                    df_reader = self._read_with_encoding_fallback(
                        file_obj,
                        encoding=self.encoding,
                        dtype=str,
                        na_values=[''],
                        keep_default_na=False,
                        chunksize=10000,
                        iterator=True
                    )
                    
                    # Count rows across all chunks
                    if hasattr(df_reader, '__iter__'):
                        return sum(len(chunk) for chunk in df_reader)
                    else:
                        return len(df_reader)
                finally:
                    # Always restore position even if error occurs
                    file_obj.seek(pos)
                
        except Exception as e:
            # Log the error and fall back to the original simple line counting
            logger.warning(f"Error counting rows with pandas: {str(e)}. Falling back to simple counting.")
            
            if isinstance(file_obj, str):
                try:
                    with open(file_obj, 'r', errors='replace') as f:
                        # Subtract 1 for header row
                        return max(0, sum(1 for _ in f) - 1)
                except Exception as inner_e:
                    logger.error(f"Error during fallback line counting: {str(inner_e)}")
                    return 0
            else:
                # For file objects, preserve position during counting
                pos = file_obj.tell()
                try:
                    file_obj.seek(0)
                    # Count lines but subtract header
                    return max(0, sum(1 for _ in file_obj) - 1)
                except Exception as inner_e:
                    logger.error(f"Error during fallback line counting: {str(inner_e)}")
                    return 0
                finally:
                    file_obj.seek(pos)
    
    def _detect_encoding(self, file_path: str = None, file_obj: Any = None) -> str:
        """
        Detect file encoding using chardet or file analysis.
        
        Args:
            file_path: Path to CSV file (optional)
            file_obj: File-like object (optional)
            
        Returns:
            Detected encoding name
        """
        # If encoding was specified in constructor, use that
        if self.encoding:
            logger.info(f"Using specified encoding: {self.encoding}")
            return self.encoding
            
        # If we've already detected encoding, return it
        if self._detected_encoding:
            return self._detected_encoding
        
        logger.info("Auto-detecting file encoding...")
        
        # For file paths
        if isinstance(file_path, str) and os.path.exists(file_path):
            # Read the first few KB to detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read(min(4096, os.path.getsize(file_path)))
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")
            self._detected_encoding = encoding
            return encoding
            
        # For file objects
        elif file_obj:
            if hasattr(file_obj, 'read') and hasattr(file_obj, 'seek'):
                pos = file_obj.tell()
                try:
                    raw_data = file_obj.read(4096)
                    # Convert to bytes if it's a string
                    if isinstance(raw_data, str):
                        raw_data = raw_data.encode('utf-8')
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']
                    confidence = result['confidence']
                    logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")
                    self._detected_encoding = encoding
                    return encoding
                finally:
                    # Reset position
                    file_obj.seek(pos)
        
        # Default fallback
        logger.warning("Could not detect encoding, defaulting to utf-8-sig")
        return 'utf-8-sig'

    def _read_with_encoding_fallback(self, 
                                    file_source: Any, 
                                    encoding: Optional[str] = None, 
                                    **kwargs) -> Union[pd.DataFrame, Generator]:
        """
        Try to read CSV with the given encoding, falling back to common encodings if that fails.
        
        Args:
            file_source: File path or object
            encoding: Initial encoding to try
            **kwargs: Additional arguments for pandas.read_csv
            
        Returns:
            Pandas read_csv result (DataFrame or generator)
            
        Raises:
            UnicodeDecodeError: If all encodings fail
        """
        # Start with detected or provided encoding
        encoding_to_try = encoding or self._detect_encoding(file_source)
        errors = []
        
        # Try the initial encoding
        try:
            logger.info(f"Reading CSV with encoding: {encoding_to_try}")
            return pd.read_csv(file_source, encoding=encoding_to_try, **kwargs)
        except UnicodeDecodeError as e:
            # Store the error details
            errors.append((encoding_to_try, str(e)))
            logger.warning(f"Failed to read with {encoding_to_try}: {str(e)}")
        
        # If initial encoding failed, try the common ones
        for fallback_encoding in self.COMMON_ENCODINGS:
            # Skip the one we already tried
            if fallback_encoding == encoding_to_try:
                continue
                
            try:
                logger.info(f"Trying fallback encoding: {fallback_encoding}")
                
                # For file paths, we can just try again
                if isinstance(file_source, str):
                    result = pd.read_csv(file_source, encoding=fallback_encoding, **kwargs)
                    logger.info(f"Successfully read file with encoding: {fallback_encoding}")
                    self._detected_encoding = fallback_encoding
                    return result
                    
                # For file objects, we need to reset position if possible
                elif hasattr(file_source, 'seek'):
                    file_source.seek(0)
                    result = pd.read_csv(file_source, encoding=fallback_encoding, **kwargs)
                    logger.info(f"Successfully read file with encoding: {fallback_encoding}")
                    self._detected_encoding = fallback_encoding
                    return result
            except UnicodeDecodeError as e:
                errors.append((fallback_encoding, str(e)))
                logger.warning(f"Failed to read with {fallback_encoding}: {str(e)}")
        
        # If we get here, all encodings failed
        error_details = "\n".join([f"{enc}: {err}" for enc, err in errors])
        logger.error(f"Failed to read CSV file with any encoding:\n{error_details}")
        raise UnicodeDecodeError(
            "csv_reader", 
            b"", 
            0, 
            1, 
            f"Could not decode file with any of the following encodings: {', '.join([e[0] for e in errors])}"
        )
    
    def read_csv(self, file_path: str = None, file_obj: Any = None, encoding: str = None) -> Generator[Dict[str, Any], None, None]:
        """
        Read CSV using pandas and yield rows as dictionaries.
        
        Args:
            file_path: Path to CSV file (optional)
            file_obj: File-like object (optional)
            encoding: File encoding (optional, overrides auto-detection)
            
        Yields:
            Dictionary for each row with column names as keys
        """
        file_source = self._get_file_obj(file_path, file_obj)
        self._file_obj = file_source  # Save for later use
        
        try:
            # Use encoding fallback mechanism with chunked reading
            chunks = self._read_with_encoding_fallback(
                file_source,
                encoding=encoding or self.encoding,
                dtype=str,  # Read all columns as strings initially
                na_values=[''],  # Treat empty strings as NaN
                keep_default_na=False,  # Don't add default NA values
                chunksize=self.chunk_size,  # Process in chunks
                low_memory=True,  # Enable low memory mode
                engine='c'  # Use C engine for speed
            )
            
            # For each chunk, it processes rows
            for chunk in chunks:
                # Store headers from first chunk
                if not self.headers:
                    self.headers = chunk.columns.tolist()
                
                # Process each row and yield dictionaries
                for _, row in chunk.iterrows():
                    # Clean data: Convert NaN to None
                    row_dict = row.to_dict()
                    yield {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
        
        finally:
            # Close file if it's a path we opened
            if isinstance(file_path, str) and hasattr(self._file_obj, 'close'):
                self._file_obj.close()
    
    def read_dataframes(self, file_path: str = None, file_obj: Any = None, chunk_size: int = None, encoding: str = None) -> Generator[pd.DataFrame, None, None]:
        """
        Read CSV file and yield pandas DataFrames with cleaned values (NaN → None).
        
        Args:
            file_path: Path to CSV file (optional)
            file_obj: File-like object (optional)
            chunk_size: Size of chunks to read (overrides self.chunk_size if provided)
            encoding: File encoding (optional, overrides auto-detection)
            
        Yields:
            Pandas DataFrame with pre-cleaned values (NaN converted to None)
        """
        file_source = self._get_file_obj(file_path, file_obj)
        self._file_obj = file_source  # Save for later use
        chunk_size = chunk_size or self.chunk_size
        
        try:
            # Use encoding fallback mechanism with chunked reading
            chunks = self._read_with_encoding_fallback(
                file_source,
                encoding=encoding or self.encoding,
                dtype=str,  # Read all columns as strings initially
                na_values=[''],  # Treat empty strings as NaN
                keep_default_na=False,  # Don't add default NA values
                chunksize=chunk_size,
                low_memory=True,
                engine='c'
            )
            
            # Store headers from first chunk
            first_chunk = True
            
            for chunk in chunks:
                if first_chunk:
                    self.headers = chunk.columns.tolist()
                    first_chunk = False
                
                # Clean the DataFrame by replacing NaN with None
                cleaned_df = chunk.copy()
                # Fill NaN with None - this affects the DataFrame in memory but doesn't change how pandas stores it
                cleaned_df = cleaned_df.where(pd.notnull(cleaned_df), None)
                
                yield cleaned_df
                
        finally:
            # Close file if it's a path we opened
            if isinstance(file_path, str) and hasattr(self._file_obj, 'close'):
                self._file_obj.close()
    
    def get_total_rows(self) -> int:
        """Get the total number of rows in the CSV file."""
        if self._row_count < 0:
            if not self._file_obj:
                raise ValueError("No file has been read yet")
            
            self._row_count = self._count_total_rows(self._file_obj)
        
        return self._row_count
    
    def get_headers(self) -> List[str]:
        """Get the headers from the CSV file."""
        return self.headers
    
    def validate_headers(self, required_headers: List[str]) -> List[str]:
        """
        Validate that required headers are present and return missing ones.
        
        Args:
            required_headers: List of headers that must be present
            
        Returns:
            List of headers that are missing
        """
        if not self.headers:
            raise ValueError("No headers available. Call read_csv first.")
        
        return [h for h in required_headers if h not in self.headers]
