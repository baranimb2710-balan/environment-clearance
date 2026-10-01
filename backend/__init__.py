"""
VYRO Backend Package.
Centralizes the multi-agent AI review pipeline, deterministic scoring engine,
statutory rules, document processing, database layer, and FastAPI REST API.
"""
import os
import sys

# Ensure backend directory is in sys.path for internal relative/absolute imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from . import models
from . import db
from . import ec_rules
from . import scoring
from . import extract
from . import review
from . import report
from . import services
from . import api

__all__ = [
    "models",
    "db",
    "ec_rules",
    "scoring",
    "extract",
    "review",
    "report",
    "services",
    "api"
]
