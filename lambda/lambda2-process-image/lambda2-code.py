"""
Lambda Function 2: Process Image
Processes uploaded images with AWS Rekognition
Converts DICOM to JPEG if needed
"""

import json
import boto3
import os
import urllib.parse
from datetime import datetime
from decimal import Decimal
import io

rekognition = boto3.client('rekognition')
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ['TABLE_NAME']

# Import DICOM libraries
try:
    import pydicom
    from PIL import Image
    import numpy as np
    DICOM_SUPPORT = True
    print("DICOM libraries loaded successfully")
except ImportError as e:
    DICOM_SUPPORT = False
    print(f"DICOM libraries not available: {e}")

def convert_floats_to_decimals(obj):
    """Convert all floats in a nested structure to Decimals for DynamoDB"""
    if isinstance(obj, list):
        return [convert_floats_to_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj

def is_dicom_file(key):
    """Check if file is a DICOM file based on extension"""
    return key.lower().endswith('.dcm') or key.lower().endswith('.dicom')

def convert_dicom_to_jpeg(dicom_data):
    """Convert DICOM pixel data to JPEG"""
    ds = pydicom.dcmread(io.BytesIO(dicom_data))
    
    try:
        pixel_array = ds.pixel_array
    except Exception as e:
        print(f"Cannot decompress pixel data: {e}")
        raise Exception(f"DICOM decompression failed. Missing codec libraries.")
    
    print(f"DICOM pixel array shape: {pixel_array.shape}, dtype: {pixel_array.dtype}")
    
    # Normalize to 0-255 range
    pixel_array = pixel_array.astype(float)
    pixel_min = np.min(pixel_array)
    pixel_max = np.max(pixel_array)
    
    print(f"Pixel value range: {pixel_min} to {pixel_max}")
    
    if pixel_max > pixel_min:
        pixel_array = (pixel_array - pixel_min) / (pixel_max - pixel_min)
        pixel_array = (pixel_array * 255).astype(np.uint8)
    else:
        pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)
    
    # Convert to PIL Image
    if len(pixel_array.shape) == 2:
        image = Image.fromarray(pixel_array, mode='L')
        image = image.convert('RGB')
        print("Converted grayscale DICOM to RGB")
    else:
        image = Image.fromarray(pixel_array, mode='RGB')
        print("Processing RGB DICOM image")
    
    # Convert to JPEG
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=95)
    output.seek(0)
    
    jpeg_size = len(output.getvalue())
    print(f"Generated JPEG size: {jpeg_size} bytes")
    
    return output.getvalue()


def resize_and_crop_to_png_bytes(image_bytes, target_size=(1024, 1024), crop_size=(512, 512)):
    """Resize to target_size, then crop to crop_size keeping the upper half and middle horizontally.

    Returns PNG bytes suitable for classifier input.
    """
    with io.BytesIO(image_bytes) as buf:
        img = Image.open(buf).convert('RGB')

        # Resize to 1024x1024
        img = img.resize(target_size, Image.LANCZOS)

        # Calculate crop box: upper half (y=0..crop_h) and centered horizontally
        width, height = img.size
        crop_w, crop_h = crop_size
        left = (width - crop_w) // 2
        upper = 0
        right = left + crop_w
        lower = upper + crop_h

        cropped = img.crop((left, upper, right, lower))

        out = io.BytesIO()
        # Save as PNG for classifier input
        cropped.save(out, format='PNG')
        out.seek(0)
        return out.getvalue()


def run_classifier_on_png(png_bytes):
    """Simple placeholder classifier that returns 1 or 0.

    Current behavior: convert to grayscale, compute average brightness; return 1 if avg>127 else 0.
    Replace with a real model call as needed.
    """
    try:
        with io.BytesIO(png_bytes) as buf:
            img = Image.open(buf).convert('L')
            # Downscale for quick processing
            img_small = img.resize((64, 64))
            pixels = list(img_small.getdata())
            avg = sum(pixels) / len(pixels)
            return 1 if avg > 127 else 0
    except Exception as e:
        print(f"Classifier error: {e}")
        return 0

def lambda_handler(event, context):
    job_id = None
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        
        job_id = key.split('/')[1]
        
        print(f"Processing file: {key} for job: {job_id}")
        print(f"DICOM support available: {DICOM_SUPPORT}")
        
        image_url = None
        
        # Check if it's a DICOM file
        if is_dicom_file(key):
            if not DICOM_SUPPORT:
                raise Exception("DICOM processing not available. pydicom library not installed.")
            
            print("DICOM file detected - converting to JPEG for analysis")
            
            response = s3_client.get_object(Bucket=bucket, Key=key)
            dicom_data = response['Body'].read()
            print(f"Downloaded DICOM file: {len(dicom_data)} bytes")
            
            jpeg_data = convert_dicom_to_jpeg(dicom_data)
            
            converted_key = f"converted/{job_id}/converted.jpg"
            s3_client.put_object(
                Bucket=bucket,
                Key=converted_key,
                Body=jpeg_data,
                ContentType='image/jpeg'
            )
            
            print(f"Converted DICOM to JPEG and saved: {converted_key}")
            
            # Generate presigned URL for viewing
            image_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket,
                    'Key': converted_key
                },
                ExpiresIn=3600
            )
            
            rekognition_key = converted_key
        else:
            print("Processing regular image file")
            rekognition_key = key
        
        # Call Rekognition
        print(f"Analyzing with Rekognition: {rekognition_key}")
        
        response = rekognition.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': rekognition_key
                }
            },
            MaxLabels=20,
            MinConfidence=70
        )
        
        print(f"Rekognition found {len(response['Labels'])} labels")
        
        results = convert_floats_to_decimals(response)

        # Run classifier on the converted image (prefer converted JPEG if available)
        try:
            classifier_input_bytes = None
            # If we converted from DICOM we have jpeg_data; otherwise, download the object bytes from S3
            if is_dicom_file(key):
                # Use the converted JPEG we already created
                classifier_input_bytes = jpeg_data
            else:
                # Download original object bytes
                obj = s3_client.get_object(Bucket=bucket, Key=rekognition_key)
                classifier_input_bytes = obj['Body'].read()

            # Convert to PNG, resize and crop
            png_bytes = resize_and_crop_to_png_bytes(classifier_input_bytes)
            flag_value = run_classifier_on_png(png_bytes)
            print(f"Classifier returned flag: {flag_value}")
        except Exception as e:
            print(f"Classifier processing failed: {e}")
            flag_value = 0

        # Update DynamoDB with results, image URL and flag
        table = dynamodb.Table(TABLE_NAME)
        update_expression = 'SET #status = :status, #results = :results, #updatedAt = :updatedAt, #flag = :flag'
        expression_names = {
            '#status': 'status',
            '#results': 'results',
            '#updatedAt': 'updatedAt',
            '#flag': 'flag'
        }
        expression_values = {
            ':status': 'complete',
            ':results': results,
            ':updatedAt': datetime.utcnow().isoformat(),
            ':flag': Decimal(str(int(flag_value)))
        }

        # Add imageUrl if it's a DICOM
        if image_url:
            update_expression += ', #imageUrl = :imageUrl'
            expression_names['#imageUrl'] = 'imageUrl'
            expression_values[':imageUrl'] = image_url

        table.update_item(
            Key={'jobId': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values
        )
        
        print("Successfully saved results to DynamoDB")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Processing complete'})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        if job_id:
            try:
                table = dynamodb.Table(TABLE_NAME)
                table.update_item(
                    Key={'jobId': job_id},
                    UpdateExpression='SET #status = :status, #error = :error',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#error': 'error'
                    },
                    ExpressionAttributeValues={
                        ':status': 'error',
                        ':error': str(e)
                    }
                )
            except:
                pass
        
        raise e