"""
Lambda Function 1: Generate Upload URL
Generates presigned S3 URLs for direct browser uploads
"""

import json
import boto3
import uuid
import os
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET']
TABLE_NAME = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        file_name = body['fileName']
        file_type = body['fileType']
        
        # Handle DICOM files that might have empty MIME type
        if file_name.lower().endswith('.dcm') or file_name.lower().endswith('.dicom'):
            file_type = 'application/dicom'
        elif not file_type:
            file_type = 'application/octet-stream'
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create unique S3 key
        s3_key = f"uploads/{job_id}/{file_name}"
        
        print(f"Generating presigned URL for: {file_name}, type: {file_type}")
        
        # Generate presigned URL with matching Content-Type
        upload_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET,
                'Key': s3_key,
                'ContentType': file_type
            },
            ExpiresIn=3600
        )
        
        # Initialize job in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'jobId': job_id,
                'status': 'pending',
                's3Key': s3_key,
                'fileName': file_name,
                'fileType': file_type,
                'createdAt': datetime.utcnow().isoformat()
            }
        )
        
        print(f"Created job {job_id} with Content-Type: {file_type}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST'
            },
            'body': json.dumps({
                'uploadUrl': upload_url,
                'jobId': job_id
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }