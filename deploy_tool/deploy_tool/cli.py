#!/usr/bin/env python
"""
Main CLI module for deploy-tool.
"""

import click
import sys
import os
import uuid
from pathlib import Path
import shutil

from .config import save_config, load_config, load_state, create_empty_config, open_config_in_editor, create_config_template, validate_aws_credentials, AWS_SECTION, CONFIG_FILE
from .aws import create_s3_bucket, delete_s3_bucket, get_aws_session
from .github import clone_repository, detect_framework, build_project
from .resources import display_resources

@click.group()
@click.version_option()
def cli():
    """Deploy static websites from GitHub to AWS."""
    pass

@cli.command()
def verify():
    """Verify the AWS configuration."""
    click.echo("Verifying AWS configuration...")
    
    # Load and check config file
    config = load_config()
    if not config:
        click.echo("No configuration found. Please run 'deploy-tool init' first.", err=True)
        return
    
    # Check config format
    from .config import validate_aws_credentials
    is_valid, error = validate_aws_credentials(config)
    if not is_valid:
        click.echo(f"Configuration format is invalid: {error}", err=True)
        return
    
    # Check AWS credentials
    from .aws import verify_aws_credentials
    is_valid, message = verify_aws_credentials()
    if not is_valid:
        click.echo(f"AWS credentials verification failed: {message}", err=True)
        return
    
    click.echo(f"AWS configuration verified successfully: {message}")
    
    # Check for existing resources
    state = load_state()
    resources = state.get('resources', [])
    
    if resources:
        click.echo("\nExisting resources:")
        for resource in resources:
            click.echo(f"  - {resource['type']}: {resource['name']}")
    else:
        click.echo("\nNo resources have been created yet.")

@cli.command()
def list():
    """List all resources created by deploy-tool."""
    click.echo("Listing resources created by deploy-tool...")
    display_resources()


@cli.command()
def init():
    """Configure AWS and set up infrastructure."""
    click.echo("Initializing AWS infrastructure...")
    
    # Create empty config file if it doesn't exist
    template_path = create_config_template()
    created = create_empty_config()
    
    if created:
        click.echo(f"Created configuration file at: {CONFIG_FILE}")
    else:
        click.echo(f"Configuration file already exists at: {CONFIG_FILE}")
        if click.confirm("Would you like to overwrite it?"):
            # Make backup
            backup_file = str(CONFIG_FILE) + ".backup"
            shutil.copy(CONFIG_FILE, backup_file)
            click.echo(f"Backup created at: {backup_file}")
            
            # Create new config
            create_empty_config()
            click.echo(f"Created new configuration file at: {CONFIG_FILE}")
        else:
            click.echo("Using existing configuration file.")
    
    # Prompt user to edit the config file
    click.echo("\nPlease edit the configuration file and fill in your AWS credentials.")
    click.echo("Required fields:")
    click.echo("  - aws_access_key_id (20 characters)")
    click.echo("  - aws_secret_access_key (40 characters)")
    click.echo("  - region_name (e.g., us-east-1)")
    
    # Try to open the file in an editor
    if open_config_in_editor():
        click.echo("\nOpened configuration file in your default editor.")
        click.echo("Please save and close the file when you're done.")
        click.confirm("Press Enter when you've filled in the configuration file", default=True, show_default=False)
    else:
        click.echo(f"\nUnable to open the file automatically. Please edit the file at:")
        click.echo(f"{CONFIG_FILE}")
        click.confirm("Press Enter when you've filled in the configuration file", default=True, show_default=False)
    
    # Validate the configuration
    config = load_config()
    if not config:
        click.echo("Failed to load configuration. Please check the file format.", err=True)
        return
    
    is_valid, error = validate_aws_credentials(config)
    if not is_valid:
        click.echo(f"Invalid configuration: {error}", err=True)
        click.echo(f"Please edit the file at {CONFIG_FILE} and fix the issues.")
        return
    
    click.echo("AWS credentials loaded successfully!")
    
    # Create a unique S3 bucket for static website hosting
    bucket_suffix = uuid.uuid4().hex[:8]
    bucket_name = f"static-site-{bucket_suffix}"
    
    if click.confirm(f"Would you like to create an S3 bucket named '{bucket_name}' for static website hosting?"):
        if create_s3_bucket(bucket_name):
            click.echo("Infrastructure setup complete.")
        else:
            click.echo("Failed to create infrastructure. Please check your AWS credentials and permissions.", err=True)


@cli.command()
@click.argument('github_url')
def deploy(github_url):
    """Deploy a static site from GitHub to AWS.
    
    GITHUB_URL is the URL of the GitHub repository to deploy.
    """
    click.echo(f"Deploying static site from {github_url}...")
    
    # Check if AWS is configured
    session = get_aws_session()
    if not session:
        click.echo("AWS is not configured. Please run 'deploy-tool init' first.")
        return
    
    # Get state to find the bucket
    state = load_state()
    buckets = [r['name'] for r in state.get('resources', []) if r['type'] == 's3_bucket']
    
    if not buckets:
        click.echo("No S3 bucket found. Please run 'deploy-tool init' first.")
        return
    
    bucket_name = buckets[0]  # Use the first bucket
    
    # Clone the repository
    repo_path, repo_name = clone_repository(github_url)
    if not repo_path:
        return
    
    try:
        # Detect the framework
        framework = detect_framework(repo_path)
        if framework == 'unknown':
            click.echo("Could not detect a supported framework (React, Next.js, Angular).")
            return
        
        click.echo(f"Detected framework: {framework}")
        
        # Build the project
        build_dir = build_project(repo_path, framework)
        if not build_dir:
            return
        
        # Deploy to S3
        click.echo(f"Deploying to S3 bucket: {bucket_name}...")
        
        s3 = session.resource('s3')
        bucket = s3.Bucket(bucket_name)
        
        for root, _, files in os.walk(build_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, build_dir)
                
                # Determine content type
                content_type = 'text/html'
                if file.endswith('.css'):
                    content_type = 'text/css'
                elif file.endswith('.js'):
                    content_type = 'application/javascript'
                elif file.endswith('.json'):
                    content_type = 'application/json'
                elif file.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    content_type = f'image/{file.split(".")[-1]}'
                
                click.echo(f"Uploading: {relative_path}")
                bucket.upload_file(
                    local_path, 
                    relative_path,
                    ExtraArgs={'ContentType': content_type}
                )
        
        # Output the URL
        region = session.region_name
        url = f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
        
        click.echo("\nDeployment complete!")
        click.echo(f"Your site is available at: {url}")
    
    finally:
        # Clean up temp directory
        if repo_path and os.path.exists(repo_path):
            shutil.rmtree(repo_path)


@cli.command()
@click.confirmation_option(
    prompt="Are you sure you want to destroy all AWS infrastructure created by deploy-tool?")
def rollback():
    """Destroy all AWS infrastructure created by deploy-tool."""
    click.echo("Rolling back AWS infrastructure...")
    
    # Check if AWS is configured
    session = get_aws_session()
    if not session:
        click.echo("AWS is not configured. Please run 'deploy-tool init' first.")
        return
    
    # Get state
    state = load_state()
    resources = state.get('resources', [])
    
    if not resources:
        click.echo("No resources found to delete.")
        return
    
    # Delete resources
    for resource in resources:
        if resource['type'] == 's3_bucket':
            click.echo(f"Deleting S3 bucket: {resource['name']}...")
            delete_s3_bucket(resource['name'])
    
    # Clear state file
    from .config import CONFIG_DIR, STATE_FILE
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    
    click.echo("Rollback completed successfully.")


if __name__ == '__main__':
    cli()
