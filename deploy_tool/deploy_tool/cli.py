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

from .config import load_state, save_state
from .aws import create_s3_bucket, delete_s3_bucket, get_aws_session, verify_aws_credentials, get_aws_client
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
    click.echo("Verifying AWS credentials...")
    
    # Check AWS credentials
    is_valid, message = verify_aws_credentials()
    if not is_valid:
        click.echo(f"AWS credentials verification failed: {message}", err=True)
        click.echo("\nTo configure AWS credentials, use one of these methods:")
        click.echo("1. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        click.echo("2. Configure the AWS CLI with 'aws configure'")
        click.echo("3. Set up SSO with 'aws configure sso'")
        return
    
    click.echo(f"AWS credentials verified successfully: {message}")
    
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
    """Initialize AWS infrastructure."""
    click.echo("Initializing AWS infrastructure...")
    
    # Verify AWS credentials are available
    is_valid, message = verify_aws_credentials()
    if not is_valid:
        click.echo(f"AWS credentials verification failed: {message}", err=True)
        click.echo("\nPlease configure AWS credentials using one of these methods:")
        click.echo("1. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        click.echo("2. Configure the AWS CLI with 'aws configure'")
        click.echo("3. Set up SSO with 'aws configure sso'")
        return
    
    click.echo(f"AWS credentials verified successfully: {message}")
    
    # Generate a unique bucket name for the static site
    bucket_suffix = uuid.uuid4().hex[:8]
    bucket_name = f"static-site-{bucket_suffix}"
    
    if click.confirm(f"Would you like to create an S3 bucket named '{bucket_name}' for static website hosting?"):
        success = create_s3_bucket(bucket_name)
        if success:
            click.echo("Infrastructure setup complete.")
        else:
            click.echo("Failed to create infrastructure completely. Check the error messages above for details.", err=True)


@cli.command()
@click.argument('github_url')
@click.option('--debug', is_flag=True, help="Show additional debug information during deployment")
def deploy(github_url, debug):
    """Deploy a static site from GitHub to AWS.
    
    GITHUB_URL is the URL of the GitHub repository to deploy.
    """
    click.echo(f"Deploying static site from {github_url}...")
    
    # Verify AWS credentials
    is_valid, message = verify_aws_credentials()
    if not is_valid:
        click.echo(f"AWS credentials verification failed: {message}", err=True)
        click.echo("Please configure AWS credentials and run 'deploy-tool init' first.")
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
        
        # Get S3 client and resource
        session = get_aws_session()
        s3_client = get_aws_client('s3')
        s3_resource = session.resource('s3')
        bucket = s3_resource.Bucket(bucket_name)
        
        # Special handling for SPA frameworks (React, Angular, Next.js) to ensure proper routing
        if framework in ['react', 'angular', 'nextjs']:
            click.echo(f"Configuring deployment for {framework} single-page application...")
            
            # Check for index.html in the build directory and validate its content
            index_path = os.path.join(build_dir, 'index.html')
            if not os.path.exists(index_path):
                click.echo("Warning: No index.html found in build directory!", err=True)
                if debug:
                    click.echo("Build directory contents:")
                    for item in os.listdir(build_dir):
                        click.echo(f"  - {item}")
            else:
                # Check if index.html is not empty and has actual content
                with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
                    index_content = f.read()
                    
                if len(index_content) < 100:
                    click.echo("Warning: index.html seems unusually small!", err=True)
                
                if debug:
                    click.echo(f"index.html size: {len(index_content)} bytes")
                    # Check for basic elements that should be in a properly built React app
                    has_root_div = '<div id="root"' in index_content or '<div id="app"' in index_content
                    has_js_imports = '.js"' in index_content
                    click.echo(f"index.html has root div: {has_root_div}")
                    click.echo(f"index.html has JS imports: {has_js_imports}")
            
            # For React apps, check for JS files that might indicate proper build
            if framework == 'react' and debug:
                js_files = [f for f in os.listdir(build_dir) if f.endswith('.js') and os.path.isfile(os.path.join(build_dir, f))]
                click.echo(f"Found {len(js_files)} JavaScript files in build directory")
                for js_file in js_files[:5]:  # Show up to 5 files
                    click.echo(f"  - {js_file}")
            
            # Ensure proper MIME types and caching for React apps
            for root, _, files in os.walk(build_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, build_dir)
                    
                    # Determine content type with better MIME type handling
                    content_type = 'text/plain'
                    cache_control = 'max-age=86400'  # Default cache of 1 day
                    
                    if file.endswith('.html'):
                        content_type = 'text/html'
                        cache_control = 'no-cache, no-store, must-revalidate'  # Prevent caching for HTML files
                    elif file.endswith('.css'):
                        content_type = 'text/css'
                        cache_control = 'max-age=31536000'  # 1 year for static assets
                    elif file.endswith('.js'):
                        content_type = 'application/javascript'
                        cache_control = 'max-age=31536000'  # 1 year for static assets
                    elif file.endswith('.json'):
                        content_type = 'application/json'
                    elif file.endswith('.svg'):
                        content_type = 'image/svg+xml'
                    elif file.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        file_ext = file.split(".")[-1]
                        content_type = f'image/{file_ext.lower()}'
                        cache_control = 'max-age=31536000'  # 1 year for images
                    elif file.endswith(('.woff', '.woff2', '.eot', '.ttf', '.otf')):
                        file_ext = file.split(".")[-1]
                        content_type = f'font/{file_ext.lower()}'
                        cache_control = 'max-age=31536000'  # 1 year for fonts
                    
                    click.echo(f"Uploading: {relative_path} [{content_type}]")
                    bucket.upload_file(
                        local_path, 
                        relative_path,
                        ExtraArgs={
                            'ContentType': content_type,
                            'CacheControl': cache_control
                        }
                    )
        else:
            # Standard file upload for other frameworks
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
        
        # Output the URL - using ap-south-1 region
        region = 'ap-south-1'
        url = f"http://{bucket_name}.s3-website.{region}.amazonaws.com"
        
        click.echo("\nDeployment complete!")
        click.echo(f"Your site is available at: {url}")
    
    finally:
        # Clean up temp directory
        if repo_path and os.path.exists(repo_path):
            try:
                # Try normal cleanup
                shutil.rmtree(repo_path)
            except (PermissionError, OSError) as e:
                # Handle Windows file lock issues
                click.echo(f"Warning: Could not fully clean up temporary files: {e}", err=True)
                click.echo("Some temporary files may remain in your temp directory.")
                # Continue execution despite cleanup failure


@cli.command()
@click.confirmation_option(
    prompt="Are you sure you want to destroy all AWS infrastructure created by deploy-tool?")
def rollback():
    """Destroy all AWS infrastructure created by deploy-tool."""
    click.echo("Rolling back AWS infrastructure...")
    
    # Verify AWS credentials
    is_valid, message = verify_aws_credentials()
    if not is_valid:
        click.echo(f"AWS credentials verification failed: {message}", err=True)
        click.echo("Please configure AWS credentials first.")
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
    from pathlib import Path
    STATE_FILE = Path.home() / ".deploy-tool" / "state.json"
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    
    click.echo("Rollback completed successfully.")


if __name__ == '__main__':
    cli()
