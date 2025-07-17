"""
AWS operations for deploy-tool.
"""
import boto3
from botocore.exceptions import ClientError
import click
import json
import uuid
from .config import save_state, load_state

def get_aws_session():
    """Get an authenticated AWS session using the default credential provider chain.
    
    Uses credentials from:
    - Environment variables
    - AWS config files
    - IAM roles
    - SSO tokens
    """
    try:
        # Create a session using default credential provider chain
        # This will use credentials from environment variables, config files, 
        # instance profiles, or SSO automatically
        session = boto3.Session(region_name='ap-south-1')
        return session
    except Exception as e:
        click.echo(f"Error getting AWS session: {e}", err=True)
        return None

def get_aws_client(service_name):
    """Get an AWS client for the specified service.
    
    Args:
        service_name (str): The AWS service name (e.g., 's3', 'cloudfront')
        
    Returns:
        boto3.client: The AWS client or None if credentials are not available
    """
    session = get_aws_session()
    if not session:
        return None
        
    return session.client(service_name)

def verify_aws_credentials():
    """Verify that the AWS credentials are valid.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Get the STS client directly
        sts_client = get_aws_client('sts')
        if not sts_client:
            return False, "No AWS credentials found. Make sure you've configured AWS credentials."
        
        # Try to get caller identity
        response = sts_client.get_caller_identity()
        account_id = response.get('Account')
        username = response.get('Arn').split('/')[-1]
        return True, f"AWS credentials valid for account: {account_id} (user: {username})"
    except Exception as e:
        return False, f"AWS credentials invalid: {str(e)}"

def create_s3_bucket(bucket_name=None):
    """Create an S3 bucket for static site hosting."""
    # Generate a unique bucket name if not provided
    if not bucket_name:
        bucket_name = f"static-site-{uuid.uuid4().hex[:8]}"
    
    # Get S3 client
    s3 = get_aws_client('s3')
    if not s3:
        click.echo("Failed to get AWS S3 client. Check your AWS credentials.", err=True)
        return False
    
    try:
        # Fixed region for ap-south-1
        region = 'ap-south-1'
        
        # Create the bucket with location constraint
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
        
        # Configure for static website hosting
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'ErrorDocument': {'Key': 'error.html'},
                'IndexDocument': {'Suffix': 'index.html'}
            }
        )
        
        # Disable block public access settings for this bucket
        try:
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': False,
                    'IgnorePublicAcls': False,
                    'BlockPublicPolicy': False,
                    'RestrictPublicBuckets': False
                }
            )
            click.echo("Disabled block public access settings for the bucket")
        except ClientError as e:
            click.echo(f"Warning: Couldn't disable block public access settings: {e}", err=True)
            click.echo("You may need to disable these settings manually in the AWS console.")
        
        # Set bucket policy to allow public access
        try:
            bucket_policy = {
                'Version': '2012-10-17',
                'Statement': [{
                    'Sid': 'PublicReadGetObject',
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': ['s3:GetObject'],
                    'Resource': f'arn:aws:s3:::{bucket_name}/*'
                }]
            }
            s3.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
        except ClientError as e:
            click.echo(f"Warning: Couldn't set bucket policy: {e}", err=True)
            click.echo("You may need to manually set the bucket policy to make it public.")
        
        # Save to state even if we had warnings, as long as the bucket was created
        state = load_state()
        state['resources'].append({
            'type': 's3_bucket',
            'name': bucket_name
        })
        save_state(state)
        
        click.echo(f"Created S3 bucket: {bucket_name}")
        click.echo(f"Website URL: http://{bucket_name}.s3-website.{region}.amazonaws.com")
        click.echo("\nNote: If the bucket is not publicly accessible, you may need to:")
        click.echo("1. Go to the S3 console: https://s3.console.aws.amazon.com/")
        click.echo(f"2. Select bucket '{bucket_name}'")
        click.echo("3. Go to 'Permissions' tab")
        click.echo("4. Edit 'Block public access' settings and uncheck all options")
        click.echo("5. Under 'Bucket policy', add a policy to make the bucket public")
        
        return True
    
    except ClientError as e:
        if "BucketAlreadyExists" in str(e):
            click.echo(f"Error: Bucket name '{bucket_name}' already exists. Try again with a different name.", err=True)
        else:
            click.echo(f"Error creating S3 bucket: {e}", err=True)
        
        return False

def delete_s3_bucket(bucket_name):
    """Delete an S3 bucket."""
    # Get S3 client
    s3 = get_aws_client('s3')
    if not s3:
        click.echo("Failed to get AWS S3 client. Check your AWS credentials.", err=True)
        return False
    
    try:
        # First delete all objects
        session = get_aws_session()
        bucket = session.resource('s3').Bucket(bucket_name)
        bucket.objects.all().delete()
        
        # Then delete the bucket
        s3.delete_bucket(Bucket=bucket_name)
        
        click.echo(f"Deleted S3 bucket: {bucket_name}")
        return True
    
    except ClientError as e:
        click.echo(f"Error deleting S3 bucket: {e}", err=True)
        return False
