"""
State management for deploy-tool.
"""
import os
import json
import click
from pathlib import Path

# Configuration paths
CONFIG_DIR = Path.home() / ".deploy-tool"
STATE_FILE = CONFIG_DIR / "state.json"

def ensure_config_dir():
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(exist_ok=True)

def save_state(state):
    """Save the state to file."""
    ensure_config_dir()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_state():
    """Load the state from file."""
    if not STATE_FILE.exists():
        return {"resources": []}
    
    with open(STATE_FILE, 'r') as f:
        return json.load(f)
