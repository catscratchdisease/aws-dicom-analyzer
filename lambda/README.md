# Lambda Functions

This directory contains the three Lambda functions that power the image analysis backend.

## Functions Overview

### Lambda 1: Generate Upload URL (`lambda1-generate-upload-url/`)
**Purpose:** Generates presigned S3 URLs for secure direct browser uploads

**Trigger:** API Gateway POST /request-upload

**Environment Variables:**
- `UPLOAD_BUCKET` - S3 bucket name for uploads
- `TABLE_NAME` - DynamoDB table name (ImageAnalysisResults)

**Permissions Required:**
- `s3:PutObject` on upload bucket
- `dynamodb:PutItem` on table

**Response:**
```json
{
  "uploadUrl": "https://s3.amazonaws.com/...",
  "jobId": "uuid"
}
```

---

### Lambda 2: Process Image (`lambda2-process-image/`)
**Purpose:** Processes uploaded images with AWS Rekognition, converts DICOM files

**Trigger:** S3 PUT event on upload bucket

**Environment Variables:**
- `TABLE_NAME` - DynamoDB table name (ImageAnalysisResults)

**Permissions Required:**
- `s3:GetObject` on upload bucket
- `s3:PutObject` on upload bucket (for converted images)
- `rekognition:DetectLabels`
- `dynamodb:UpdateItem` on table

**Dependencies:** Requires pydicom Lambda layer

**Timeout:** 300 seconds (5 minutes)

**Memory:** 1024 MB

---

### Lambda 3: Get Results (`lambda3-get-results/`)
**Purpose:** Retrieves processing results from DynamoDB

**Trigger:** API Gateway GET /get-results?jobId=xxx

**Environment Variables:**
- `TABLE_NAME` - DynamoDB table name (ImageAnalysisResults)

**Permissions Required:**
- `dynamodb:GetItem` on table

**Response:**
```json
{
  "status": "complete",
  "results": { ... },
  "imageUrl": "https://...",
  "error": null
}
```

## Deployment

### Package Function

```bash
cd lambda/lambda1-generate-upload-url
zip function.zip lambda_function.py
```

### Create Function

```bash
aws lambda create-function \
    --function-name generateUploadUrl \
    --runtime python3.12 \
    --role arn:aws:iam::ACCOUNT-ID:role/ImageAnalyzerLambdaRole \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 128 \
    --environment Variables="{UPLOAD_BUCKET=my-bucket,TABLE_NAME=ImageAnalysisResults}"
```

### Update Function Code

```bash
zip function.zip lambda_function.py

aws lambda update-function-code \
    --function-name generateUploadUrl \
    --zip-file fileb://function.zip
```

### Update Configuration

```bash
aws lambda update-function-configuration \
    --function-name processImage \
    --timeout 300 \
    --memory-size 1024 \
    --environment Variables="{TABLE_NAME=ImageAnalysisResults}"
```

## Testing Locally

### Lambda 1
```python
python3 -c "
from lambda_function import lambda_handler
import json

event = {
    'body': json.dumps({
        'fileName': 'test.jpg',
        'fileType': 'image/jpeg'
    })
}

result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
"
```

### Lambda 3
```python
python3 -c "
from lambda_function import lambda_handler
import json

event = {
    'queryStringParameters': {
        'jobId': 'test-job-id'
    }
}

result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
"
```

## Monitoring

### View Logs
```bash
# Stream logs
aws logs tail /aws/lambda/processImage --follow

# View specific time range
aws logs tail /aws/lambda/processImage \
    --since 1h \
    --format short
```

### Check Metrics
```bash
# Invocations
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=processImage \
    --start-time 2025-10-14T00:00:00Z \
    --end-time 2025-10-14T23:59:59Z \
    --period 3600 \
    --statistics Sum

# Errors
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=processImage \
    --start-time 2025-10-14T00:00:00Z \
    --end-time 2025-10-14T23:59:59Z \
    --period 3600 \
    --statistics Sum
```

## Common Issues

### Lambda 1: Upload URL Generation Fails
- Check S3 bucket exists and Lambda has permissions
- Verify environment variables are set correctly
- Check CloudWatch logs for specific errors

### Lambda 2: DICOM Processing Fails
- Ensure Lambda layer is attached
- Check timeout is sufficient (5 minutes recommended)
- Verify memory is adequate (1024 MB minimum)
- Check DICOM file is not corrupted

### Lambda 3: Results Not Found
- Verify job actually exists in DynamoDB
- Check Lambda 2 completed successfully
- Ensure TABLE_NAME environment variable is correct

## Performance Optimization

### Cold Start Reduction
- Keep memory at 1024 MB or higher
- Use provisioned concurrency for critical functions
- Minimize dependencies

### Cost Optimization
- Right-size memory allocation
- Use appropriate timeout values
- Enable Lambda function URLs if don't need API Gateway features

## Security Best Practices

1. **Least Privilege IAM**: Only grant necessary permissions
2. **Environment Variables**: Never commit secrets to git
3. **VPC**: Consider VPC if accessing private resources
4. **Encryption**: Enable encryption at rest for environment variables