"""
Main package for deploy-tool.
This module ensures imports work properly.
"""

from .cli import cli
from .config import (
    save_config, load_config, save_state, load_state,
    validate_aws_credentials, ensure_config_dir
)
from .aws import (
    get_aws_session, create_s3_bucket, delete_s3_bucket,
    verify_aws_credentials
)
from .github import clone_repository, detect_framework, build_project
from .resources import display_resources, get_resources_summary

__all__ = [
    'cli',
    'save_config', 'load_config',
    'save_state', 'load_state',
    'validate_aws_credentials', 'ensure_config_dir',
    'get_aws_session', 'create_s3_bucket', 'delete_s3_bucket',
    'verify_aws_credentials',
    'clone_repository', 'detect_framework', 'build_project',
    'display_resources', 'get_resources_summary'
]
