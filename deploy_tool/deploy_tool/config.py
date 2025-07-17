"""
Configuration management for deploy-tool.
Handles storage and validation of AWS credentials.
"""
import os
import json
import click
from pathlib import Path
import re
import configparser
import shutil

# Configuration paths
CONFIG_DIR = Path.home() / ".deploy-tool"
CONFIG_FILE = CONFIG_DIR / "config.ini"
STATE_FILE = CONFIG_DIR / "state.json"
CONFIG_TEMPLATE_FILE = CONFIG_DIR / "config.template.ini"

# Configuration sections and keys
AWS_SECTION = 'aws'
CONFIG_KEYS = {
    AWS_SECTION: ['aws_access_key_id', 'aws_secret_access_key', 'region_name']
}

# AWS region validation regex
AWS_REGION_PATTERN = r'^[a-z]{2}-[a-z]+-\d{1}$'  # e.g. us-east-1, eu-west-2

def ensure_config_dir():
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(exist_ok=True)

def create_config_template():
    """Create a template configuration file with empty values.
    
    Returns:
        Path: The path to the template file
    """
    ensure_config_dir()
    
    config = configparser.ConfigParser()
    config[AWS_SECTION] = {
        'aws_access_key_id': '',
        'aws_secret_access_key': '',
        'region_name': 'us-east-1'  # Default region
    }
    
    with open(CONFIG_TEMPLATE_FILE, 'w') as f:
        config.write(f)
    
    # Set reasonable permissions
    CONFIG_TEMPLATE_FILE.chmod(0o600)
    
    return CONFIG_TEMPLATE_FILE

def create_empty_config():
    """Create an empty configuration file based on the template.
    
    Returns:
        bool: True if successful, False otherwise
    """
    ensure_config_dir()
    
    # Create template if it doesn't exist
    if not CONFIG_TEMPLATE_FILE.exists():
        create_config_template()
    
    # If config already exists, don't overwrite
    if CONFIG_FILE.exists():
        return False
    
    # Copy template to config file
    shutil.copy(CONFIG_TEMPLATE_FILE, CONFIG_FILE)
    
    # Set restrictive permissions
    CONFIG_FILE.chmod(0o600)
    
    return True

def open_config_in_editor():
    """Try to open the config file in the default editor.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # For Windows
        if os.name == 'nt':
            os.startfile(CONFIG_FILE)
        # For macOS
        elif os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
            os.system(f'open "{CONFIG_FILE}"')
        # For Linux
        elif os.name == 'posix':
            os.system(f'xdg-open "{CONFIG_FILE}"')
        else:
            return False
        return True
    except Exception:
        return False

def validate_aws_credentials(config_dict):
    """Validate AWS credentials in the configuration.
    
    Args:
        config_dict (dict): Configuration dictionary with AWS section
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if AWS_SECTION not in config_dict:
        return False, f"Missing AWS configuration section"
    
    aws_config = config_dict[AWS_SECTION]
    
    # Check for required fields
    for field in CONFIG_KEYS[AWS_SECTION]:
        if field not in aws_config or not aws_config[field]:
            return False, f"Missing or empty required configuration: {field}"
    
    # Validate AWS access key ID format (basic check)
    access_key = aws_config.get('aws_access_key_id')
    if not access_key or len(access_key) != 20:
        return False, "Invalid AWS Access Key ID format"
    
    # Validate AWS secret access key format (basic check)
    secret_key = aws_config.get('aws_secret_access_key')
    if not secret_key or len(secret_key) != 40:
        return False, "Invalid AWS Secret Access Key format"
    
    # Validate region format
    region = aws_config.get('region_name')
    if not region or not re.match(AWS_REGION_PATTERN, region):
        return False, f"Invalid AWS region format: {region}"
    
    return True, None

def save_config(config_dict):
    """Save the configuration to file.
    
    Args:
        config_dict (dict): Configuration dictionary with section keys
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        ensure_config_dir()
        
        # Convert dictionary to ConfigParser object
        config = configparser.ConfigParser()
        for section, values in config_dict.items():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in values.items():
                config.set(section, key, value)
        
        # Write to file
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
        
        # Set restrictive permissions
        CONFIG_FILE.chmod(0o600)
        
        return True
    except Exception as e:
        click.echo(f"Error saving configuration: {e}", err=True)
        return False

def load_config():
    """Load the configuration from file.
    
    Returns:
        dict: Configuration dictionary or None if not found/invalid
    """
    if not CONFIG_FILE.exists():
        click.echo("No configuration found. Please run 'deploy-tool init' to create one.", err=True)
        return None
    
    try:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        
        # Convert ConfigParser to dictionary
        config_dict = {}
        for section in config.sections():
            config_dict[section] = {}
            for key, value in config.items(section):
                config_dict[section][key] = value
        
        return config_dict
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        return None

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
