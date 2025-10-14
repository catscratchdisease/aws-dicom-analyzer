# Infrastructure

AWS infrastructure setup and configuration files.

## Overview

This directory contains infrastructure configuration, IAM policies, and setup documentation.

## AWS Resources

### Required Resources
- **2 S3 Buckets**: Upload storage and website hosting
- **1 DynamoDB Table**: Job tracking and results
- **3 Lambda Functions**: Upload URL generation, image processing, results retrieval
- **1 Lambda Layer**: DICOM processing libraries
- **1 API Gateway**: HTTP API for frontend communication
- **1 IAM Role**: Lambda execution role

### Architecture Diagram

```
┌─────────────────┐
│   CloudFront    │ (Optional CDN)
└────────┬────────┘
         │
    ┌────▼────┐
    │   S3    │ Static Website
    │ Hosting │
    └────┬────┘
         │
         │ API Calls
         │
    ┌────▼────────┐
    │ API Gateway │
    └─┬─────────┬─┘
      │         │
      │         │
┌─────▼───┐ ┌──▼──────┐
│ Lambda1 │ │ Lambda3 │
│Generate │ │   Get   │
│  URL    │ │ Results │
└────┬────┘ └───┬─────┘
     │          │
     │          │
┌────▼──────────▼────┐
│     DynamoDB        │
│ ImageAnalysisResults│
└─────────────────────┘
     ▲          ▲
     │          │
┌────┴────┐     │
│   S3    │     │
│ Upload  │     │
│ Bucket  │     │
└────┬────┘     │
     │          │
     │ S3 Event │
     │          │
┌────▼──────────┘
│   Lambda2
│  Process
│   Image
│     +
│ Rekognition
└─────────────┘
```

## Files

- **setup-guide.md** - Complete step-by-step setup instructions
- **s3-cors.json** - CORS configuration for upload bucket
- **s3-notification.json** - S3 event notification configuration
- **website-bucket-policy.json** - Public access policy for website bucket
- **lambda-trust-policy.json** - IAM trust policy for Lambda execution role
- **iam-policies.json** - IAM policies for Lambda functions

## Quick Setup

See [setup-guide.md](setup-guide.md) for detailed instructions.

### Prerequisites
```bash
# Install AWS CLI
# Mac
brew install awscli

# Windows
choco install awscli

# Configure
aws configure
```

### Estimated Setup Time
- **Manual Setup**: 30-45 minutes
- **Automated (with scripts)**: 10-15 minutes

### Cost Estimate
- **Development/Testing**: ~$5-10/month
- **Production (1000 images/month)**: ~$20-30/month

## Configuration Files

### s3-cors.json
CORS configuration allowing browser uploads:
```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"]
    }
  ]
}
```

### s3-notification.json
S3 event configuration for triggering Lambda:
```json
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "arn:aws:lambda:REGION:ACCOUNT:function:processImage",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "prefix", "Value": "uploads/"}
          ]
        }
      }
    }
  ]
}
```

### website-bucket-policy.json
Public read access for website:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::BUCKET-NAME/*"
    }
  ]
}
```

## IAM Permissions

### Lambda Execution Role
Required policies:
- `AWSLambdaBasicExecutionRole` (AWS managed)
- `AmazonS3FullAccess` (AWS managed)
- `AmazonDynamoDBFullAccess` (AWS managed)
- `AmazonRekognitionReadOnlyAccess` (AWS managed)

### Least Privilege Custom Policy
For production, use custom policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::UPLOAD-BUCKET/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/ImageAnalysisResults"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:DetectLabels"
      ],
      "Resource": "*"
    }
  ]
}
```

## Monitoring & Alerts

### CloudWatch Alarms
Set up alarms for:
- Lambda errors
- Lambda duration > 4 minutes
- API Gateway 5xx errors
- DynamoDB throttling

Example:
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name lambda-errors-processImage \
    --alarm-description "Alert on Lambda errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value=processImage
```

### X-Ray Tracing
Enable for debugging:
```bash
aws lambda update-function-configuration \
    --function-name processImage \
    --tracing-config Mode=Active
```

## Backup & Disaster Recovery

### DynamoDB Backups
Enable point-in-time recovery:
```bash
aws dynamodb update-continuous-backups \
    --table-name ImageAnalysisResults \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### S3 Versioning
Enable on upload bucket:
```bash
aws s3api put-bucket-versioning \
    --bucket UPLOAD-BUCKET \
    --versioning-configuration Status=Enabled
```

## Security Hardening

1. **Enable S3 bucket encryption**
2. **Use VPC endpoints** for private AWS service access
3. **Implement API Gateway throttling**
4. **Add AWS WAF** for DDoS protection
5. **Enable CloudTrail** for audit logging
6. **Use Secrets Manager** for sensitive configuration

## Cleanup

To delete all resources:
```bash
# See setup-guide.md for complete cleanup script
./cleanup.sh
```

## Support

For infrastructure issues:
- AWS Support: https://console.aws.amazon.com/support
- AWS Documentation: https://docs.aws.amazon.com/
- GitHub Issues: [Your repo URL]