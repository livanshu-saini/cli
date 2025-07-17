# deploy-tool

A CLI tool for deploying static websites from GitHub to AWS.

## Features

- Simple file-based AWS credential configuration
- Credential validation and verification
- Automatic detection and build support for React, Next.js, and Angular projects
- S3 static website hosting with public access
- Resource management and listing
- Easy cleanup with one-command rollback

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/deploy-tool.git
cd deploy-tool

# Install the package
pip install -e .
```

## Usage

### Initial Setup

```bash
# Configure AWS credentials and create infrastructure
deploy-tool init
```

This will:
1. Create a configuration file in `~/.deploy-tool/config.ini`
2. Open the file in your default text editor
3. Guide you to fill in your AWS credentials
4. Validate the provided configuration

### Verifying Configuration

```bash
# Verify your AWS credentials and configuration
deploy-tool verify
```

This will:
1. Check if your configuration file exists and is valid
2. Test your AWS credentials with the AWS API
3. Display the AWS account information if successful

### Listing Resources

```bash
# List all resources created by deploy-tool
deploy-tool list
```

This will show all resources managed by deploy-tool, including:
1. S3 buckets with their status and website URLs
2. Any other AWS resources created by the tool

### Deploying a Website

```bash
# Deploy a static site from GitHub
deploy-tool deploy https://github.com/username/repo
```

This will:
1. Clone the repository
2. Detect the framework (React, Next.js, or Angular)
3. Build the project
4. Upload the build to S3
5. Provide a public URL for the website

### Cleaning Up

```bash
# Remove all AWS resources created by deploy-tool
deploy-tool rollback
```

This will:
1. Delete all S3 buckets created by deploy-tool
2. Remove all state information

## Requirements

- Python 3.6+
- AWS account with valid credentials
- Git

## Dependencies

- click - For CLI interface
- boto3 - For AWS operations
- gitpython - For GitHub operations

## Configuration File Format

The configuration file is located at `~/.deploy-tool/config.ini` and has the following format:

```ini
[aws]
aws_access_key_id = YOURACCESSKEYIDHERE
aws_secret_access_key = YOURSECRETACCESSKEYHERE
region_name = us-east-1
```
