"""
AWS operations for deploy-tool.
"""
import boto3
from botocore.exceptions import ClientError
import click
import json
from .config import load_config, save_state, load_state, AWS_SECTION

def get_aws_session():
    """Get an authenticated AWS session."""
    config = load_config()
    if not config or AWS_SECTION not in config:
        return None
    
    aws_config = config[AWS_SECTION]
    
    session = boto3.Session(
        aws_access_key_id=aws_config.get('aws_access_key_id'),
        aws_secret_access_key=aws_config.get('aws_secret_access_key'),
        region_name=aws_config.get('region_name')
    )
    return session

def verify_aws_credentials():
    """Verify that the AWS credentials are valid.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    session = get_aws_session()
    if not session:
        return False, "No AWS credentials configured"
    
    try:
        # Try a simple AWS API call
        sts = session.client('sts')
        response = sts.get_caller_identity()
        account_id = response.get('Account')
        return True, f"AWS credentials valid for account: {account_id}"
    except Exception as e:
        return False, f"AWS credentials invalid: {str(e)}"

def create_s3_bucket(bucket_name):
    """Create an S3 bucket for static site hosting."""
    session = get_aws_session()
    if not session:
        return False
    
    s3 = session.client('s3')
    
    try:
        # Create the bucket
        region = session.region_name
        
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        # Configure for static website hosting
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'ErrorDocument': {'Key': 'index.html'},
                'IndexDocument': {'Key': 'index.html'}
            }
        )
        
        # Set bucket policy to allow public access
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
        
        # Save to state
        state = load_state()
        state['resources'].append({
            'type': 's3_bucket',
            'name': bucket_name
        })
        save_state(state)
        
        click.echo(f"Created S3 bucket: {bucket_name}")
        click.echo(f"Website URL: http://{bucket_name}.s3-website-{region}.amazonaws.com")
        
        return True
    
    except ClientError as e:
        click.echo(f"Error creating S3 bucket: {e}", err=True)
        return False

def delete_s3_bucket(bucket_name):
    """Delete an S3 bucket."""
    session = get_aws_session()
    if not session:
        return False
    
    s3 = session.client('s3')
    
    try:
        # First delete all objects
        bucket = session.resource('s3').Bucket(bucket_name)
        bucket.objects.all().delete()
        
        # Then delete the bucket
        s3.delete_bucket(Bucket=bucket_name)
        
        click.echo(f"Deleted S3 bucket: {bucket_name}")
        return True
    
    except ClientError as e:
        click.echo(f"Error deleting S3 bucket: {e}", err=True)
        return False
