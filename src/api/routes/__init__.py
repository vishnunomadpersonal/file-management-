"""
API Routes Package.

Exports all route modules for the application.
"""

from . import file
from . import appointment
from . import user
from . import pipeline
from . import auth
from . import mcp
from . import model_versioning
from . import feedback

__all__ = [
    "file",
    "appointment", 
    "user",
    "pipeline",
    "auth",
    "mcp",
    "model_versioning",
    "feedback"
]