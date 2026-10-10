"""
CSV Reader Component with pandas for efficient processing.
"""
from typing import List, Dict, Any, Generator, Optional, BinaryIO, Union
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
    - Support for multiple delimiters (comma, tab, pipe, etc.)
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
    
    def __init__(self, chunk_size: int = 1000, encoding: str = None, delimiter: str = None):
        """
        Initialize with optional chunk size, encoding, and delimiter.
        
        Args:
            chunk_size: Number of rows to process at once
            encoding: File encoding (if None, will be auto-detected)
            delimiter: Field delimiter character (if None, will be auto-detected)
        """
        self.chunk_size = chunk_size
        self.headers = []
        self._row_count = -1
        self._file_obj = None
        self.encoding = encoding
        self._detected_encoding = None
        self.delimiter = delimiter  # Don't default to comma here - let _detect_delimiter handle it
        self._detected_delimiter = None
    
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

    def _detect_delimiter(self, file_source: Any, encoding: str = None) -> str:
        """
        Detect the delimiter used in the file by analyzing the first few lines.
        
        Args:
            file_source: File path or object
            encoding: Encoding to use when reading the file
            
        Returns:
            Detected delimiter character (comma, tab, pipe, semicolon, etc.)
        """
        import csv
        
        # Define valid delimiters
        VALID_DELIMITERS = {',', '\t', '|', ';', ':', ' '}  # Common delimiters
        
        # If delimiter was explicitly specified (not None), validate and use it
        if self.delimiter is not None:
            # Validate delimiter is a non-empty single-character string
            if not isinstance(self.delimiter, str):
                logger.warning(f"Invalid delimiter type: {type(self.delimiter).__name__}. Expected string. Falling back to auto-detection.")
                self.delimiter = None  # Clear invalid delimiter to trigger auto-detection
            elif not self.delimiter:
                logger.warning(f"Invalid delimiter specified: empty string. Falling back to auto-detection.")
                self.delimiter = None  # Clear invalid delimiter to trigger auto-detection
            elif len(self.delimiter) > 1:
                logger.warning(f"Invalid delimiter length: '{self.delimiter}' ({len(self.delimiter)} characters). Delimiter must be a single character. Falling back to auto-detection.")
                self.delimiter = None  # Clear invalid delimiter to trigger auto-detection
            elif self.delimiter not in VALID_DELIMITERS:
                logger.warning(f"Invalid delimiter character: '{self.delimiter}'. Must be one of: comma, tab, pipe, semicolon, colon, space. Falling back to auto-detection.")
                self.delimiter = None  # Clear invalid delimiter to trigger auto-detection
            
            # If delimiter passed all checks, use it
            if self.delimiter is not None:
                logger.info(f"Using specified delimiter: {repr(self.delimiter)}")
                return self.delimiter
            
        # If we've already detected delimiter, return it
        if self._detected_delimiter:
            return self._detected_delimiter
        
        logger.info("Auto-detecting file delimiter...")
 
        try:
            # Get encoding for reading
            enc = encoding or self._detect_encoding(file_source)
            
            # Read first few lines for analysis
            sample_lines = []
            
            if isinstance(file_source, str):
                # File path
                with open(file_source, 'r', encoding=enc, errors='replace') as f:
                    sample_lines = [f.readline() for _ in range(5)]
            elif hasattr(file_source, 'read') and hasattr(file_source, 'seek'):
                # File object
                pos = file_source.tell()
                try:
                    # Reset to beginning
                    file_source.seek(0)
                    
                    # Determine if file object is binary or text
                    # Try to read a small sample to detect type
                    test_read = file_source.read(1)
                    file_source.seek(0)
                    
                    is_binary = isinstance(test_read, bytes)
                    
                    if is_binary:
                        # Binary mode - decode lines
                        for _ in range(5):
                            line = file_source.readline()
                            if not line:
                                break
                            try:
                                decoded_line = line.decode(enc, errors='replace')
                                sample_lines.append(decoded_line)
                            except (AttributeError, UnicodeDecodeError):
                                logger.warning(f"Failed to decode binary line, skipping")
                                continue
                    else:
                        # Text mode
                        for _ in range(5):
                            line = file_source.readline()
                            if not line:
                                break
                            sample_lines.append(line)
                finally:
                    # Restore position
                    file_source.seek(pos)
            
            # Use csv.Sniffer to detect delimiter
            if sample_lines:
                # Filter out empty lines
                sample_lines = [line for line in sample_lines if line.strip()]
                
                if not sample_lines:
                    logger.warning("No non-empty lines found for delimiter detection")
                    return ','
                
                sample = '\n'.join(sample_lines)
                try:
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff(sample, delimiters=',\t|;')
                    detected = dialect.delimiter
                    logger.info(f"Detected delimiter: {repr(detected)}")
                    self._detected_delimiter = detected
                    return detected
                except csv.Error:
                    # Sniffer failed, fall back to manual detection
                    logger.warning("CSV Sniffer failed, using manual delimiter detection")
                    
                    # Count occurrences of common delimiters in the first line
                    first_line = sample_lines[0] if sample_lines else ""
                    delimiters = {
                        ',': first_line.count(','),
                        '\t': first_line.count('\t'),
                        '|': first_line.count('|'),
                        ';': first_line.count(';')
                    }
                    
                    # Choose the delimiter with the most occurrences
                    detected = max(delimiters, key=delimiters.get)
                    if delimiters[detected] > 0:
                        logger.info(f"Manually detected delimiter: {repr(detected)}")
                        self._detected_delimiter = detected
                        return detected
        
        except Exception as e:
            logger.warning(f"Error detecting delimiter: {str(e)}")
        
        # Default fallback to comma
        logger.warning("Could not detect delimiter, defaulting to comma")
        return ','
        
    def _read_with_encoding_fallback(self, 
                                    file_source: Any, 
                                    encoding: Optional[str] = None,
                                    delimiter: Optional[str] = None,
                                    **kwargs) -> Union[pd.DataFrame, Generator]:
        """
        Try to read CSV with the given encoding and delimiter, falling back to common encodings if that fails.
        
        Args:
            file_source: File path or object
            encoding: Initial encoding to try
            delimiter: Delimiter to use (if None, will auto-detect)
            **kwargs: Additional arguments for pandas.read_csv
            
        Returns:
            Pandas read_csv result (DataFrame or generator)
            
        Raises:
            UnicodeDecodeError: If all encodings fail
        """
        # Start with detected or provided encoding
        encoding_to_try = encoding or self._detect_encoding(file_source)
        
        # Define valid delimiters
        VALID_DELIMITERS = {',', '\t', '|', ';', ':', ' '}
        
        # Validate and detect delimiter
        if delimiter is not None:
            # Validate delimiter type, value, and length
            if not isinstance(delimiter, str):
                logger.warning(f"Invalid delimiter type: {type(delimiter).__name__}. Expected string. Using auto-detection.")
                delimiter = None  # Fall back to auto-detection
            elif not delimiter:
                logger.warning(f"Invalid delimiter specified: empty string. Using auto-detection.")
                delimiter = None  # Fall back to auto-detection
            elif len(delimiter) > 1:
                logger.warning(f"Invalid delimiter length: '{delimiter}' ({len(delimiter)} characters). Delimiter must be a single character. Using auto-detection.")
                delimiter = None  # Fall back to auto-detection
            elif delimiter not in VALID_DELIMITERS:
                logger.warning(f"Invalid delimiter character: '{delimiter}'. Must be one of: comma, tab, pipe, semicolon, colon, space. Using auto-detection.")
                delimiter = None  # Fall back to auto-detection
        
        # Detect or use provided delimiter (after validation)
        delimiter_to_use = delimiter if delimiter is not None else self._detect_delimiter(file_source, encoding_to_try)
       
        errors = []
        
        # Try the initial encoding with the detected/provided delimiter
        try:
            logger.info(f"Reading file with encoding: {encoding_to_try}, delimiter: {repr(delimiter_to_use)}")
            return pd.read_csv(file_source, encoding=encoding_to_try, sep=delimiter_to_use, **kwargs)
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
                logger.info(f"Trying fallback encoding: {fallback_encoding} with delimiter: {repr(delimiter_to_use)}")
                
                # For file paths, we can just try again
                if isinstance(file_source, str):
                    result = pd.read_csv(file_source, encoding=fallback_encoding, sep=delimiter_to_use, **kwargs)
                    logger.info(f"Successfully read file with encoding: {fallback_encoding}")
                    self._detected_encoding = fallback_encoding
                    return result
                    
                # For file objects, we need to reset position if possible
                elif hasattr(file_source, 'seek'):
                    file_source.seek(0)
                    result = pd.read_csv(file_source, encoding=fallback_encoding, sep=delimiter_to_use, **kwargs)
                    logger.info(f"Successfully read file with encoding: {fallback_encoding}")
                    self._detected_encoding = fallback_encoding
                    return result
            except UnicodeDecodeError as e:
                errors.append((fallback_encoding, str(e)))
                logger.warning(f"Failed to read with {fallback_encoding}: {str(e)}")
        
        # If we get here, all encodings failed
        error_details = "\n".join([f"{enc}: {err}" for enc, err in errors])
        logger.error(f"Failed to read file with any encoding:\n{error_details}")
        raise UnicodeDecodeError(
            "csv_reader", 
            b"", 
            0, 
            1, 
            f"Could not decode file with any of the following encodings: {', '.join([e[0] for e in errors])}"
        )
    
    def read_csv(self, file_path: str = None, file_obj: Any = None, encoding: str = None, delimiter: str = None) -> Generator[Dict[str, Any], None, None]:
        """
        Read CSV using pandas and yield rows as dictionaries.
        
        Args:
            file_path: Path to CSV file (optional)
            file_obj: File-like object (optional)
            encoding: File encoding (optional, overrides auto-detection)
            delimiter: Field delimiter (optional, overrides auto-detection and constructor)
            
        Yields:
            Dictionary for each row with column names as keys
        """
        file_source = self._get_file_obj(file_path, file_obj)
        self._file_obj = file_source  # Save for later use
        
        # Use provided delimiter parameter first, then instance delimiter (which may be None)
        # If both are None, _detect_delimiter will handle auto-detection
        delimiter_to_use = delimiter if delimiter is not None else self.delimiter
        
        try:
            # Use encoding and delimiter fallback mechanism with chunked reading
            chunks = self._read_with_encoding_fallback(
                file_source,
                encoding=encoding or self.encoding,
                delimiter=delimiter_to_use,
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
    
    def read_dataframes(self, file_path: str = None, file_obj: Any = None, chunk_size: int = None, encoding: str = None, delimiter: str = None) -> Generator[pd.DataFrame, None, None]:
        """
        Read CSV file and yield pandas DataFrames with cleaned values (NaN → None).
        
        Args:
            file_path: Path to CSV file (optional)
            file_obj: File-like object (optional)
            chunk_size: Size of chunks to read (overrides self.chunk_size if provided)
            encoding: File encoding (optional, overrides auto-detection)
            delimiter: Field delimiter (optional, overrides auto-detection and constructor)
            
        Yields:
            Pandas DataFrame with pre-cleaned values (NaN converted to None)
        """
        file_source = self._get_file_obj(file_path, file_obj)
        self._file_obj = file_source  # Save for later use
        chunk_size = chunk_size or self.chunk_size
        
        # Use provided delimiter, or fall back to instance delimiter
        delimiter_to_use = delimiter or self.delimiter
        
        try:
            # Use encoding and delimiter fallback mechanism with chunked reading
            chunks = self._read_with_encoding_fallback(
                file_source,
                encoding=encoding or self.encoding,
                delimiter=delimiter_to_use,
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
                    logger.info(f"Detected {len(self.headers)} columns: {self.headers}")
                    
                    # Log first row for debugging
                    if len(chunk) > 0:
                        first_row = chunk.iloc[0].to_dict()
                        logger.debug(f"First row data sample: {list(first_row.items())[:3]}...")  # Log first 3 fields
                    
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
