"""
Lambda Function 3: Get Results
Retrieves processing results from DynamoDB
"""

import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME', 'ImageAnalysisResults')

def convert_decimals_to_floats(obj):
    """Convert Decimals back to floats for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals_to_floats(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_floats(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def lambda_handler(event, context):
    print(f"Event received: {json.dumps(event)}")
    
    try:
        # Check if queryStringParameters exists
        if 'queryStringParameters' not in event or event['queryStringParameters'] is None:
            print("ERROR: No queryStringParameters in event")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing jobId parameter'})
            }
        
        job_id = event['queryStringParameters'].get('jobId')
        
        if not job_id:
            print("ERROR: No jobId in queryStringParameters")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing jobId parameter'})
            }
        
        print(f"Getting results for job: {job_id}")
        
        # Query DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'jobId': job_id})
        
        print(f"DynamoDB response: {response}")
        
        if 'Item' not in response:
            print(f"Job {job_id} not found in DynamoDB")
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Job not found'})
            }
        
        item = response['Item']
        print(f"Found item with status: {item.get('status')}")
        
        # Convert Decimals to floats for JSON
        results = convert_decimals_to_floats(item.get('results'))
        
        # Convert flag Decimal to int if present
        flag_val = item.get('flag')
        if isinstance(flag_val, Decimal):
            flag_out = int(flag_val)
        else:
            flag_out = flag_val

        response_body = {
            'status': item['status'],
            'results': results,
            'imageUrl': item.get('imageUrl'),
            'flag': flag_out,
            'error': item.get('error')
        }
        
        print(f"Returning response with status: {item['status']}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET'
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }