"""
Input Validation Module - Sanitization and Validation Utilities.

Provides:
- File upload validation
- Path sanitization
- Content type validation
- Size limits
- SQL injection prevention
- XSS prevention
"""

import os
import re
import hashlib
import magic  # python-magic for content type detection
from typing import Optional, List, Set
from fastapi import HTTPException, status, UploadFile
from pydantic import validator
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Maximum file sizes (in bytes)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB default
MAX_CHUNK_SIZE = 10 * 1024 * 1024   # 10MB per chunk
MAX_FILENAME_LENGTH = 255

# Allowed content types
ALLOWED_CONTENT_TYPES: Set[str] = {
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    
    # Text
    'text/plain',
    'text/csv',
    'text/html',
    'text/markdown',
    'application/json',
    'application/xml',
    'text/xml',
    
    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
    
    # Archives
    'application/zip',
    'application/gzip',
    'application/x-tar',
    
    # Data
    'application/octet-stream',  # Generic binary
}

# Dangerous file extensions that should be blocked
DANGEROUS_EXTENSIONS: Set[str] = {
    '.exe', '.dll', '.bat', '.cmd', '.sh', '.ps1', '.vbs', '.js',
    '.jar', '.msi', '.scr', '.com', '.pif', '.application', '.gadget',
    '.msp', '.hta', '.cpl', '.msc', '.wsf', '.lnk', '.inf', '.reg',
}

# Characters not allowed in filenames
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\s|^)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)(\s|$)",
    r"(--)|(;)|(\/\*)",
    r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+",
    r"'.*?(\bOR\b|\bAND\b).*?'",
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
]


# ============================================================================
# FILE VALIDATION
# ============================================================================

def validate_file_size(size: int, max_size: int = MAX_FILE_SIZE) -> None:
    """Validate file size is within limits."""
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({size} bytes) exceeds maximum allowed ({max_size} bytes)"
        )


def validate_filename(filename: str) -> str:
    """
    Validate and sanitize filename.
    
    Returns sanitized filename or raises HTTPException.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Check length
    if len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Filename too long (max {MAX_FILENAME_LENGTH} characters)"
        )
    
    # Remove path components (prevent path traversal)
    filename = os.path.basename(filename)
    
    # Remove invalid characters
    filename = INVALID_FILENAME_CHARS.sub('_', filename)
    
    # Check for dangerous extensions
    ext = os.path.splitext(filename)[1].lower()
    if ext in DANGEROUS_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not allowed for security reasons"
        )
    
    # Prevent hidden files (starting with .)
    if filename.startswith('.'):
        filename = '_' + filename[1:]
    
    # Ensure filename is not empty after sanitization
    if not filename or filename == '_':
        filename = 'unnamed_file'
    
    return filename


def validate_content_type(content_type: str, filename: str = None) -> str:
    """
    Validate content type is allowed.
    
    Returns validated content type or raises HTTPException.
    """
    if not content_type:
        content_type = 'application/octet-stream'
    
    # Normalize content type (remove parameters like charset)
    content_type = content_type.split(';')[0].strip().lower()
    
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Check if it's a text type we should allow
        if content_type.startswith('text/'):
            return content_type
        
        logger.warning(f"Blocked content type: {content_type} for file: {filename}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Content type '{content_type}' is not allowed"
        )
    
    return content_type


async def validate_upload_file(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE,
    allowed_types: Optional[Set[str]] = None
) -> UploadFile:
    """
    Comprehensive file upload validation.
    
    Validates:
    - Filename
    - Content type
    - File size
    - Actual content (magic bytes)
    """
    # Validate filename
    file.filename = validate_filename(file.filename)
    
    # Validate declared content type
    allowed = allowed_types or ALLOWED_CONTENT_TYPES
    file.content_type = validate_content_type(file.content_type, file.filename)
    
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Content type '{file.content_type}' is not allowed"
        )
    
    # Read file to check size and actual content type
    content = await file.read()
    
    # Check size
    validate_file_size(len(content), max_size)
    
    # Verify actual content type matches declared type (prevent spoofing)
    # Note: This requires python-magic library
    try:
        actual_type = magic.from_buffer(content, mime=True)
        
        # Allow some flexibility for text files
        if actual_type != file.content_type:
            if not (actual_type.startswith('text/') and file.content_type.startswith('text/')):
                logger.warning(
                    f"Content type mismatch: declared={file.content_type}, actual={actual_type}"
                )
                # For security, we could reject here, but for now just log
    except Exception as e:
        logger.warning(f"Could not verify content type: {e}")
    
    # Reset file position for subsequent reads
    await file.seek(0)
    
    return file


# ============================================================================
# PATH VALIDATION
# ============================================================================

def sanitize_path(path: str) -> str:
    """
    Sanitize a file path to prevent traversal attacks.
    
    Removes:
    - Parent directory references (..)
    - Absolute paths
    - Null bytes
    """
    if not path:
        return ''
    
    # Remove null bytes
    path = path.replace('\x00', '')
    
    # Normalize the path
    path = os.path.normpath(path)
    
    # Remove leading slashes and drive letters
    path = path.lstrip('/\\')
    if len(path) > 1 and path[1] == ':':
        path = path[2:].lstrip('/\\')
    
    # Split and filter out parent directory references
    parts = path.split(os.sep)
    safe_parts = [p for p in parts if p and p != '..' and p != '.']
    
    return os.sep.join(safe_parts)


def validate_resource_id(resource_id: str, resource_type: str = "resource") -> str:
    """
    Validate a resource ID (UUID format).
    
    Prevents SQL injection in ID parameters.
    """
    if not resource_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{resource_type} ID is required"
        )
    
    # UUID format: 8-4-4-4-12 hex characters
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    if not uuid_pattern.match(resource_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {resource_type} ID format"
        )
    
    return resource_id.lower()


# ============================================================================
# STRING SANITIZATION
# ============================================================================

def sanitize_string(
    value: str,
    max_length: int = 1000,
    allow_html: bool = False,
    field_name: str = "input"
) -> str:
    """
    Sanitize a string input.
    
    Removes:
    - SQL injection patterns
    - XSS patterns (if allow_html is False)
    - Control characters
    """
    if not value:
        return ''
    
    # Truncate to max length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Remove null bytes and control characters
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    
    # Check for SQL injection
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"SQL injection attempt detected in {field_name}: {value[:100]}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid characters detected in {field_name}"
            )
    
    # Check for XSS (if HTML not allowed)
    if not allow_html:
        for pattern in XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS attempt detected in {field_name}: {value[:100]}")
                # Remove the dangerous content instead of rejecting
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    return value.strip()


def sanitize_search_query(query: str) -> str:
    """
    Sanitize a search query.
    
    Escapes special characters that could be used for injection.
    """
    if not query:
        return ''
    
    # Limit length
    query = query[:500]
    
    # Remove potentially dangerous characters
    query = re.sub(r'[;\'\"\\]', '', query)
    
    # Escape wildcards if needed
    # query = query.replace('%', '\\%').replace('_', '\\_')
    
    return query.strip()


# ============================================================================
# VALIDATORS FOR PYDANTIC MODELS
# ============================================================================

def validate_email_format(email: str) -> str:
    """Validate email format."""
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    if not email_pattern.match(email):
        raise ValueError('Invalid email format')
    return email.lower()


def validate_password_strength(password: str) -> str:
    """Validate password meets security requirements."""
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters')
    if len(password) > 128:
        raise ValueError('Password must be less than 128 characters')
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        raise ValueError('Password must contain at least one digit')
    return password


def validate_slug(slug: str) -> str:
    """Validate URL-safe slug format."""
    slug_pattern = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    if not slug_pattern.match(slug):
        raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
    if len(slug) > 100:
        raise ValueError('Slug must be less than 100 characters')
    return slug


# ============================================================================
# HASH UTILITIES
# ============================================================================

def compute_file_hash(content: bytes, algorithm: str = 'sha256') -> str:
    """Compute hash of file content."""
    hasher = hashlib.new(algorithm)
    hasher.update(content)
    return hasher.hexdigest()


def compute_content_checksum(content: bytes) -> str:
    """Compute MD5 checksum for content verification."""
    return hashlib.md5(content).hexdigest()
