# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Compatibility shim: `uvicorn backend.main:app` (v0.4 command) still works."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.main import app  # noqa: E402,F401
