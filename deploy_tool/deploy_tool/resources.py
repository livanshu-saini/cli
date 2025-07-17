"""
Helper module for listing resources.
"""
import click
from .aws import get_aws_session
from .config import load_state

def get_resources_summary():
    """Get a summary of all resources created by deploy-tool.
    
    Returns:
        dict: Summary of resources
    """
    session = get_aws_session()
    if not session:
        return None
    
    state = load_state()
    resources = state.get('resources', [])
    
    summary = {
        's3_buckets': [],
        'cloudfront_distributions': [],
        'other_resources': []
    }
    
    for resource in resources:
        if resource['type'] == 's3_bucket':
            # Get additional details from AWS
            try:
                s3 = session.client('s3')
                region = session.region_name
                
                # Check if bucket exists
                try:
                    s3.head_bucket(Bucket=resource['name'])
                    status = "active"
                    website_url = f"http://{resource['name']}.s3-website.{region}.amazonaws.com"
                except Exception:
                    status = "not found"
                    website_url = "N/A"
                
                summary['s3_buckets'].append({
                    'name': resource['name'],
                    'status': status,
                    'website_url': website_url
                })
            except Exception as e:
                summary['s3_buckets'].append({
                    'name': resource['name'],
                    'status': f"error: {str(e)}",
                    'website_url': "N/A"
                })
        elif resource['type'] == 'cloudfront_distribution':
            summary['cloudfront_distributions'].append(resource)
        else:
            summary['other_resources'].append(resource)
    
    return summary

def display_resources():
    """Display all resources created by deploy-tool."""
    summary = get_resources_summary()
    if not summary:
        click.echo("No resources found or cannot connect to AWS.")
        return
    
    # Display S3 buckets
    if summary['s3_buckets']:
        click.echo("\nS3 Buckets:")
        for bucket in summary['s3_buckets']:
            click.echo(f"  - {bucket['name']} ({bucket['status']})")
            if bucket['website_url'] != "N/A":
                click.echo(f"    URL: {bucket['website_url']}")
    
    # Display CloudFront distributions
    if summary['cloudfront_distributions']:
        click.echo("\nCloudFront Distributions:")
        for dist in summary['cloudfront_distributions']:
            click.echo(f"  - {dist['name']}")
    
    # Display other resources
    if summary['other_resources']:
        click.echo("\nOther Resources:")
        for res in summary['other_resources']:
            click.echo(f"  - {res['type']}: {res['name']}")
