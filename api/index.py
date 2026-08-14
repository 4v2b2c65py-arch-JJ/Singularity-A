#!/usr/bin/env python3
"""
Vercel Serverless Function - QB Protocol API
Wraps FastAPI app for Vercel deployment.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.api_server import app
