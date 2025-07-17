"""
Configuration management for deploy-tool.
Handles secure storage and validation of AWS credentials.
"""
import os
import json
import click
from pathlib import Path
import base64
import getpass
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configuration paths
CONFIG_DIR = Path.home() / ".deploy-tool"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CONFIG_DIR / "state.json"
KEY_FILE = CONFIG_DIR / ".keyfile"

# Required configuration fields
REQUIRED_CONFIG = ['aws_access_key_id', 'aws_secret_access_key', 'region_name']

# AWS region validation regex
AWS_REGION_PATTERN = r'^[a-z]{2}-[a-z]+-\d{1}$'  # e.g. us-east-1, eu-west-2

def ensure_config_dir():
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(exist_ok=True)
    
def _get_encryption_key():
    """Get or create an encryption key for securing credentials.
    
    Returns:
        bytes: The encryption key
    """
    # If key already exists, load it
    if KEY_FILE.exists():
        with open(KEY_FILE, 'rb') as f:
            key_data = f.read()
        return key_data
    
    # Generate a new key
    ensure_config_dir()
    
    # Get machine-specific info for salt
    username = getpass.getuser()
    hostname = os.uname().nodename
    salt = f"{username}@{hostname}".encode()
    
    # Generate key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
    
    # Save key
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    
    # Set restrictive permissions
    KEY_FILE.chmod(0o600)
    
    return key

def _encrypt_value(value):
    """Encrypt a sensitive value.
    
    Args:
        value (str): Value to encrypt
        
    Returns:
        str: Encrypted value as a base64-encoded string
    """
    if not value:
        return value
        
    key = _get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def _decrypt_value(encrypted_value):
    """Decrypt a sensitive value.
    
    Args:
        encrypted_value (str): Encrypted value as a base64-encoded string
        
    Returns:
        str: Decrypted value
    """
    if not encrypted_value:
        return encrypted_value
    
    try:
        key = _get_encryption_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(base64.urlsafe_b64decode(encrypted_value.encode()))
        return decrypted.decode()
    except Exception as e:
        click.echo(f"Error decrypting value: {e}", err=True)
        return None

def validate_aws_credentials(config):
    """Validate AWS credentials in the configuration.
    
    Args:
        config (dict): Configuration dictionary
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check for required fields
    for field in REQUIRED_CONFIG:
        if field not in config:
            return False, f"Missing required configuration: {field}"
    
    # Validate AWS access key ID format (basic check)
    access_key = config.get('aws_access_key_id')
    if not access_key or len(access_key) != 20:
        return False, "Invalid AWS Access Key ID format"
    
    # Validate AWS secret access key format (basic check)
    secret_key = config.get('aws_secret_access_key')
    if not secret_key or len(secret_key) != 40:
        return False, "Invalid AWS Secret Access Key format"
    
    # Validate region format
    region = config.get('region_name')
    if not region or not re.match(AWS_REGION_PATTERN, region):
        return False, f"Invalid AWS region format: {region}"
    
    return True, None

def save_config(config):
    """Save the configuration to file with sensitive data encrypted.
    
    Args:
        config (dict): Configuration dictionary
    """
    ensure_config_dir()
    
    # Validate configuration
    is_valid, error = validate_aws_credentials(config)
    if not is_valid:
        click.echo(f"Invalid configuration: {error}", err=True)
        return False
    
    # Create a copy to avoid modifying the original
    config_copy = config.copy()
    
    # Encrypt sensitive fields
    config_copy['aws_access_key_id'] = _encrypt_value(config['aws_access_key_id'])
    config_copy['aws_secret_access_key'] = _encrypt_value(config['aws_secret_access_key'])
    
    # Save to file
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_copy, f, indent=2)
    
    # Set restrictive permissions
    CONFIG_FILE.chmod(0o600)
    
    return True

def load_config():
    """Load the configuration from file and decrypt sensitive data.
    
    Returns:
        dict: Configuration dictionary or None if not found/invalid
    """
    if not CONFIG_FILE.exists():
        click.echo("No configuration found. Please run 'deploy-tool init' first.", err=True)
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Decrypt sensitive fields
        if 'aws_access_key_id' in config:
            config['aws_access_key_id'] = _decrypt_value(config['aws_access_key_id'])
            
        if 'aws_secret_access_key' in config:
            config['aws_secret_access_key'] = _decrypt_value(config['aws_secret_access_key'])
        
        return config
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
