import warnings
warnings.filterwarnings("ignore")

import json
import asyncio
import sys
import os
from pathlib import Path

# Add backend/ to path so 'app.*' imports work
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # backend/
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import mcp.types as types
from mcp.server import Server
from app.gcp import vm, vpc, storage, gke, functions, billing, cloudsql, loadbalancer, dns

server = Server("gcp-assistant")

def _json(result):
    return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]