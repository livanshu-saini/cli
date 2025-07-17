# deploy-tool

A CLI tool for deploying static websites from GitHub to AWS.

## Features

- Seamless AWS credentials handling using AWS credential provider chain
- Support for environment variables, AWS CLI profiles, and SSO
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
# Configure your AWS credentials using one of these methods:
# Option 1: Set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=ap-south-1

# Option 2: Configure the AWS CLI
aws configure

# Option 3: Set up AWS SSO
aws configure sso

# Then initialize the infrastructure
deploy-tool init
```

This will:
1. Verify your AWS credentials
2. Create an S3 bucket for static website hosting
3. Save the state information for future reference

### Verifying Configuration

```bash
# Verify your AWS credentials and configuration
deploy-tool verify
```

This will:
1. Test your AWS credentials using the AWS STS service
2. Display your AWS account ID and username
3. List any resources that have been created by the tool

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

## Framework-Specific Considerations

### React Applications
- Properly configured for client-side routing with S3
- All static assets will be served with correct MIME types and cache headers
- Supports Create React App and other React frameworks

### Angular Applications
- Automatically detects project structure from angular.json
- Configures S3 for proper client-side routing
- Handles Angular's build output structure

### Next.js Applications
- Supports both older (with export command) and newer Next.js versions
- Automatically configures next.config.js for static export when needed
- Note: Server-side features like API routes won't work on S3 static hosting

## AWS Credentials

This tool uses the AWS SDK's default credential provider chain, which will look for credentials in the following order:

1. Environment variables (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`)
2. Shared credential file (`~/.aws/credentials`)
3. IAM Role for Amazon EC2 or ECS task role
4. AWS SSO credentials from the AWS CLI
