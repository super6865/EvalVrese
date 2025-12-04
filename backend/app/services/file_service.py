"""
File upload service for dataset import
"""
import os
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile


def secure_filename(filename: str) -> str:
    """
    Secure filename by removing dangerous characters
    Similar to werkzeug.utils.secure_filename
    """
    # Remove path separators and other dangerous characters
    filename = re.sub(r'[^\w\s-]', '', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    return filename


class FileService:
    """Service for handling file uploads and storage"""
    
    # Supported file formats
    SUPPORTED_FORMATS = {
        'csv': ['text/csv', 'application/vnd.ms-excel'],
        'jsonl': ['application/jsonl', 'text/plain'],
        'json': ['application/json'],
        'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'],
        'xls': ['application/vnd.ms-excel', 'application/excel'],
        'zip': ['application/zip', 'application/x-zip-compressed'],
    }
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.csv', '.jsonl', '.json', '.xlsx', '.xls', '.zip'}
    
    def __init__(self, upload_dir: str = "uploads/datasets"):
        """
        Initialize file service
        
        Args:
            upload_dir: Directory to store uploaded files
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_file(self, filename: str, content_type: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file
        
        Args:
            filename: Name of the file
            content_type: MIME type of the file
            
        Returns:
            (is_valid, error_message)
        """
        if not filename:
            return False, "Filename is required"
        
        # Check file extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file format. Allowed formats: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # Check content type if provided
        if content_type:
            format_name = ext[1:]  # Remove the dot
            if format_name in self.SUPPORTED_FORMATS:
                allowed_types = self.SUPPORTED_FORMATS[format_name]
                if content_type not in allowed_types:
                    # Be lenient with content type checking
                    pass
        
        return True, None
    
    def get_file_format(self, filename: str) -> Optional[str]:
        """
        Get file format from filename
        
        Args:
            filename: Name of the file
            
        Returns:
            File format (csv, jsonl, json, xlsx, xls, zip) or None
        """
        ext = Path(filename).suffix.lower()
        if ext:
            format_name = ext[1:]  # Remove the dot
            # Normalize xls and xlsx
            if format_name in ['xlsx', 'xls']:
                return format_name
            return format_name
        return None
    
    def save_file(self, file: UploadFile, dataset_id: Optional[int] = None) -> Tuple[str, str]:
        """
        Save uploaded file to disk
        
        Args:
            file: Uploaded file object
            dataset_id: Optional dataset ID for organizing files
            
        Returns:
            (file_path, file_uri) - Relative path and URI
        """
        # Validate file
        is_valid, error = self.validate_file(file.filename, file.content_type)
        if not is_valid:
            raise ValueError(error)
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        unique_filename = f"{uuid.uuid4().hex}_{name}{ext}"
        
        # Create dataset-specific directory if dataset_id provided
        if dataset_id:
            dataset_dir = self.upload_dir / str(dataset_id)
            dataset_dir.mkdir(parents=True, exist_ok=True)
            file_path = dataset_dir / unique_filename
        else:
            file_path = self.upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)
        
        # Return absolute path and URI
        absolute_path = str(file_path.absolute())
        file_uri = f"/uploads/datasets/{dataset_id}/{unique_filename}" if dataset_id else f"/uploads/datasets/{unique_filename}"
        
        return absolute_path, file_uri
    
    def get_file_path(self, file_uri: str) -> Optional[Path]:
        """
        Get file path from URI
        
        Args:
            file_uri: File URI
            
        Returns:
            Path object or None if not found
        """
        # Remove leading slash if present
        if file_uri.startswith('/'):
            file_uri = file_uri[1:]
        
        file_path = Path(file_uri)
        if file_path.exists():
            return file_path
        return None
    
    def delete_file(self, file_uri: str) -> bool:
        """
        Delete file by URI
        
        Args:
            file_uri: File URI
            
        Returns:
            True if deleted, False otherwise
        """
        file_path = self.get_file_path(file_uri)
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception:
                return False
        return False
    
    def file_exists(self, file_uri: str) -> bool:
        """
        Check if file exists
        
        Args:
            file_uri: File URI
            
        Returns:
            True if file exists
        """
        file_path = self.get_file_path(file_uri)
        return file_path is not None and file_path.exists()
    
    def get_file_size(self, file_uri: str) -> Optional[int]:
        """
        Get file size in bytes
        
        Args:
            file_uri: File URI
            
        Returns:
            File size in bytes or None
        """
        file_path = self.get_file_path(file_uri)
        if file_path and file_path.exists():
            return file_path.stat().st_size
        return None

