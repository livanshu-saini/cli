"""
GitHub operations for deploy-tool.
"""
import os
import shutil
import tempfile
import json
import click
import git
from pathlib import Path

def clone_repository(github_url):
    """Clone a GitHub repository to a temporary directory.
    
    Returns:
        tuple: (repo_path, repo_name) if successful, (None, None) otherwise
    """
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp(prefix="deploy-tool-")
        
        # Clone the repository
        click.echo(f"Cloning repository from {github_url}...")
        git.Repo.clone_from(github_url, temp_dir)
        
        # Get the repository name from the URL
        repo_name = github_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        return temp_dir, repo_name
    
    except Exception as e:
        click.echo(f"Error cloning repository: {e}", err=True)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None, None

def detect_framework(repo_path):
    """Detect the framework used in the repository.
    
    Returns:
        str: 'react', 'nextjs', 'angular', or 'unknown'
    """
    package_json_path = Path(repo_path) / 'package.json'
    
    if not package_json_path.exists():
        click.echo("No package.json found. Cannot determine framework.")
        return 'unknown'
    
    try:
        with open(package_json_path, 'r') as f:
            package_json = json.load(f)
        
        dependencies = {**package_json.get('dependencies', {}), **package_json.get('devDependencies', {})}
        
        if 'next' in dependencies:
            return 'nextjs'
        elif 'react' in dependencies and 'react-dom' in dependencies:
            return 'react'
        elif '@angular/core' in dependencies:
            return 'angular'
        else:
            click.echo("Could not determine framework from package.json.")
            return 'unknown'
    
    except Exception as e:
        click.echo(f"Error detecting framework: {e}", err=True)
        return 'unknown'

def build_project(repo_path, framework):
    """Build the project based on the detected framework.
    
    Returns:
        str: Path to the build directory if successful, None otherwise
    """
    current_dir = os.getcwd()
    try:
        os.chdir(repo_path)
        
        # Install dependencies
        click.echo("Installing dependencies...")
        os.system('npm install')
        
        # Build based on framework
        click.echo(f"Building {framework} project...")
        
        if framework == 'nextjs':
            os.system('npm run build && npm run export')
            build_dir = os.path.join(repo_path, 'out')
        elif framework == 'react':
            os.system('npm run build')
            build_dir = os.path.join(repo_path, 'build')
        elif framework == 'angular':
            os.system('npm run build -- --prod')
            build_dir = os.path.join(repo_path, 'dist')
        else:
            click.echo("Unknown framework. Cannot build project.")
            return None
        
        if not os.path.exists(build_dir):
            click.echo(f"Build directory not found: {build_dir}")
            return None
        
        return build_dir
    
    except Exception as e:
        click.echo(f"Error building project: {e}", err=True)
        return None
    
    finally:
        os.chdir(current_dir)
