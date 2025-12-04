"""
File reader for dataset import
Supports CSV, JSONL, XLSX, XLS, and ZIP formats with automatic encoding detection
"""
import csv
import json
import io
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Iterator, List
from codecs import BOM_UTF8, BOM_UTF16_BE, BOM_UTF16_LE

# Try to import chardet, but make it optional
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

# Try to import pandas for Excel support
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Try to import zipfile (standard library)
import zipfile


class FileReader:
    """Unified file reader interface"""
    
    def __init__(self, file_path: str, format: str):
        self.file_path = Path(file_path)
        self.format = format.lower()
        self.file_handle = None
        self.reader = None
        self.cursor = 0
        self.fields = []  # For CSV/Excel: column names
        self.data_rows = []  # For Excel: cached rows
        self.temp_dir = None  # For ZIP: temporary extraction directory
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if self.format not in ['csv', 'jsonl', 'xlsx', 'xls', 'zip']:
            raise ValueError(f"Unsupported format: {format}. Supported: csv, jsonl, xlsx, xls, zip")
        
        # Check dependencies
        if self.format in ['xlsx', 'xls'] and not HAS_PANDAS:
            raise ValueError(f"pandas is required for {format} format support")
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def open(self):
        if self.format == 'csv':
            self._init_csv_reader()
        elif self.format == 'jsonl':
            self._init_jsonl_reader()
        elif self.format in ['xlsx', 'xls']:
            self._init_excel_reader()
        elif self.format == 'zip':
            self._init_zip_reader()
    
    def _init_csv_reader(self):
        # Read file with encoding detection
        raw_bytes = self.file_path.read_bytes()
        encoding = self._detect_encoding(raw_bytes)
        
        # Remove BOM if present
        if raw_bytes.startswith(BOM_UTF8):
            raw_bytes = raw_bytes[len(BOM_UTF8):]
        elif raw_bytes.startswith(BOM_UTF16_BE) or raw_bytes.startswith(BOM_UTF16_LE):
            # UTF-16 BOM will be handled by the decoder
            pass
        
        # Decode content
        content = raw_bytes.decode(encoding)
        self.file_handle = io.StringIO(content)
        self.file_handle.seek(0)
        self.reader = csv.reader(self.file_handle)
        
        # Read header row
        try:
            self.fields = next(self.reader)
            self.cursor = 1  # Header is line 1
        except StopIteration:
            raise ValueError("CSV file is empty")
    
    def _init_jsonl_reader(self):
        # Read file with encoding detection
        raw_bytes = self.file_path.read_bytes()
        encoding = self._detect_encoding(raw_bytes)
        
        # Remove BOM if present
        if raw_bytes.startswith(BOM_UTF8):
            raw_bytes = raw_bytes[len(BOM_UTF8):]
        elif raw_bytes.startswith(BOM_UTF16_BE) or raw_bytes.startswith(BOM_UTF16_LE):
            # UTF-16 BOM will be handled by the decoder
            pass
        
        # Decode content
        content = raw_bytes.decode(encoding)
        self.file_handle = io.StringIO(content)
        self.file_handle.seek(0)
        self.cursor = 0
    
    def _init_excel_reader(self):
        if not HAS_PANDAS:
            raise ValueError("pandas is required for Excel format support")
        
        try:
            # Read Excel file, first sheet only
            df = pd.read_excel(self.file_path, sheet_name=0, header=0)
            
            # Get column names
            self.fields = [str(col) for col in df.columns.tolist()]
            
            # Convert DataFrame to list of dictionaries
            self.data_rows = df.to_dict('records')
            self.cursor = 0  # Will be incremented when reading
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {str(e)}")
    
    def _init_zip_reader(self):
        try:
            # Create temporary directory for extraction
            self.temp_dir = Path(tempfile.mkdtemp())
            
            # Extract ZIP file
            with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # Find CSV file (prefer index.csv, otherwise first .csv file)
            csv_files = list(self.temp_dir.rglob('index.csv'))
            if not csv_files:
                csv_files = list(self.temp_dir.rglob('*.csv'))
            
            if not csv_files:
                raise ValueError("No CSV file found in ZIP archive")
            
            # Use the first CSV file found
            csv_path = csv_files[0]
            
            # Initialize CSV reader with the extracted file
            original_path = self.file_path
            self.file_path = csv_path
            self.format = 'csv'
            self._init_csv_reader()
            # Restore original path for reference
            self.file_path = original_path
            
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file")
        except Exception as e:
            raise ValueError(f"Failed to read ZIP file: {str(e)}")
    
    def _detect_encoding(self, raw_bytes: bytes) -> str:
        # Try UTF-8 first (most common)
        try:
            raw_bytes.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass
        
        # Try GB18030 (common in China)
        try:
            raw_bytes.decode('gb18030')
            return 'gb18030'
        except UnicodeDecodeError:
            pass
        
        # Try GBK
        try:
            raw_bytes.decode('gbk')
            return 'gbk'
        except UnicodeDecodeError:
            pass
        
        # Use chardet as fallback if available
        if HAS_CHARDET:
            try:
                result = chardet.detect(raw_bytes)
                if result and result.get('confidence', 0) > 0.7:
                    return result['encoding']
            except Exception:
                pass
        
        # Default to UTF-8 with errors='replace'
        return 'utf-8'
    
    def next(self) -> Optional[Dict[str, Any]]:
        if self.format in ['xlsx', 'xls']:
            if not self.data_rows:
                self.open()
            return self._next_excel()
        elif self.format == 'zip':
            # ZIP is handled as CSV after extraction
            if not self.file_handle:
                self.open()
            return self._next_csv()
        else:
            if not self.file_handle:
                self.open()
            
            if self.format == 'csv':
                return self._next_csv()
            elif self.format == 'jsonl':
                return self._next_jsonl()
        
        return None
    
    def _next_csv(self) -> Optional[Dict[str, Any]]:
        try:
            row = next(self.reader)
            self.cursor += 1
            
            # Create dictionary from row
            if len(row) != len(self.fields):
                raise ValueError(
                    f"Row {self.cursor} has {len(row)} columns, expected {len(self.fields)}"
                )
            
            return dict(zip(self.fields, row))
        except StopIteration:
            return None
    
    def _next_jsonl(self) -> Optional[Dict[str, Any]]:
        line = self.file_handle.readline()
        if not line:
            return None
        
        line = line.strip()
        if not line:
            # Skip empty lines
            return self._next_jsonl()
        
        try:
            self.cursor += 1
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON at line {self.cursor}: {e}")
    
    def _next_excel(self) -> Optional[Dict[str, Any]]:
        if self.cursor >= len(self.data_rows):
            return None
        
        row = self.data_rows[self.cursor]
        self.cursor += 1
        
        # Convert values to strings and handle None
        result = {}
        for key, value in row.items():
            if value is None:
                result[str(key)] = ""
            elif pd.isna(value):
                result[str(key)] = ""
            else:
                result[str(key)] = str(value)
        
        return result
    
    def seek_to_line(self, line_number: int):
        """
        Seek to specific line number (for resuming)
        
        Args:
            line_number: Line number to seek to (1-based for CSV/Excel, 0-based for JSONL)
        """
        if self.format in ['xlsx', 'xls']:
            # Excel: line_number is 1-based (1 = first data row, 0 = before start)
            if line_number < 1:
                self.cursor = 0
            else:
                # Excel data_rows already excludes header, so line_number 1 = index 0
                self.cursor = line_number - 1
                if self.cursor > len(self.data_rows):
                    self.cursor = len(self.data_rows)
        elif self.format == 'zip':
            # ZIP is handled as CSV after extraction
            if not self.file_handle:
                self.open()
            # CSV: line_number includes header, so we need to skip header + (line_number - 1) rows
            self.file_handle.seek(0)
            self._init_csv_reader()
            for _ in range(line_number - 1):
                try:
                    next(self.reader)
                    self.cursor += 1
                except StopIteration:
                    break
        elif self.format == 'csv':
            if not self.file_handle:
                self.open()
            # CSV: line_number includes header, so we need to skip header + (line_number - 1) rows
            self.file_handle.seek(0)
            self._init_csv_reader()
            for _ in range(line_number - 1):
                try:
                    next(self.reader)
                    self.cursor += 1
                except StopIteration:
                    break
        elif self.format == 'jsonl':
            if not self.file_handle:
                self.open()
            # JSONL: seek to line_number (0-based)
            self.file_handle.seek(0)
            self.cursor = 0
            for _ in range(line_number):
                line = self.file_handle.readline()
                if not line:
                    break
                self.cursor += 1
    
    def get_cursor(self) -> int:
        return self.cursor
    
    def get_fields(self) -> list:
        return self.fields.copy() if self.fields else []
    
    def close(self):
        """Close file handle and clean up temporary files"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
        
        # Clean up temporary directory for ZIP files
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
            self.temp_dir = None
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return self
    
    def __next__(self) -> Dict[str, Any]:
        item = self.next()
        if item is None:
            raise StopIteration
        return item

