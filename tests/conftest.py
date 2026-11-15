# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os.environ.setdefault("FIELDSHIFT_ENV", "development")
