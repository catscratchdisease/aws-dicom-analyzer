# AWS DICOM Image Analysis System

Serverless image analysis application with DICOM support using AWS Lambda, Rekognition, S3, DynamoDB, and API Gateway.

## Features

- 🖼️ Upload regular images (JPG, PNG, GIF) and DICOM medical images
- 🤖 AI-powered object detection using AWS Rekognition
- 🏥 Client-side DICOM viewer with interactive controls
- 🔄 Automatic DICOM-to-JPEG conversion for AI analysis
- ⚡ Serverless architecture with automatic scaling
- 💾 Job tracking and result storage in DynamoDB

## Architecture

```
Frontend (S3 Static Website)
    ↓
API Gateway
    ↓
Lambda 1: Generate Upload URL → S3 Upload Bucket
    ↓ (S3 Event Trigger)
Lambda 2: Process Image → AWS Rekognition
    ↓
DynamoDB (Results Storage)
    ↑
Lambda 3: Get Results ← Frontend (Polling)
```

## Repository Structure

```
aws-dicom-analyzer/
├── README.md
├── .gitignore
├── frontend/
│   └── index.html
├── lambda/
│   ├── lambda1-generate-upload-url/
│   │   └── lambda_function.py
│   ├── lambda2-process-image/
│   │   └── lambda_function.py
│   └── lambda3-get-results/
│   │   └── lambda_function.py
├── layers/
│   ├── build-layer.sh
│   └── Dockerfile
├── infrastructure/
│   ├── setup-guide.md
│   └── iam-policies.json
└── docs/
    └── deployment.md
```

## Prerequisites

- AWS Account
- AWS CLI configured
- Python 3.12
- Docker (for building Lambda layers)

## Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/aws-dicom-analyzer.git
cd aws-dicom-analyzer
```

2. **Create AWS Resources**
   - S3 bucket for uploads
   - S3 bucket for website hosting
   - DynamoDB table
   - Lambda functions
   - API Gateway

   See [infrastructure/setup-guide.md](infrastructure/setup-guide.md) for detailed steps.

3. **Deploy Lambda Functions**
```bash
cd lambda/lambda1-generate-upload-url
zip function.zip lambda_function.py
aws lambda update-function-code --function-name generateUploadUrl --zip-file fileb://function.zip
```

4. **Build and Deploy Lambda Layer** (for DICOM support)
```bash
cd layers
./build-layer.sh
aws s3 cp dicom-layer.zip s3://YOUR-BUCKET/layers/
aws lambda publish-layer-version --layer-name pydicom-layer --content S3Bucket=YOUR-BUCKET,S3Key=layers/dicom-layer.zip --compatible-runtimes python3.12
```

5. **Deploy Frontend**
```bash
cd frontend
aws s3 cp index.html s3://YOUR-WEBSITE-BUCKET/
```

6. **Update API Endpoint**
   - Edit `frontend/index.html`
   - Replace `API_ENDPOINT` with your API Gateway URL

## Configuration

### Environment Variables (Lambda Functions)

**Lambda 1 & Lambda 2:**
- `UPLOAD_BUCKET`: S3 bucket name for uploads
- `TABLE_NAME`: DynamoDB table name

**Lambda 3:**
- `TABLE_NAME`: DynamoDB table name

### IAM Permissions

See [infrastructure/iam-policies.json](infrastructure/iam-policies.json) for required permissions.

## Usage

1. Open the S3 website URL in your browser
2. Drag and drop an image or DICOM file
3. For DICOM files: Use mouse to adjust brightness/contrast, scroll to zoom
4. View AI-detected objects when processing completes

## Development

### Testing Lambda Functions Locally

```bash
# Test Lambda 1
cd lambda/lambda1-generate-upload-url
python3 -c "from lambda_function import lambda_handler; print(lambda_handler({'body': '{\"fileName\":\"test.jpg\",\"fileType\":\"image/jpeg\"}'}, None))"
```

### Building Lambda Layer

```bash
cd layers
docker run --rm --platform linux/amd64 \
  -v $(pwd):/var/task \
  -w /var/task \
  --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.12 \
  -c "pip install --target python pydicom pillow numpy pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg"

zip -r9 dicom-layer.zip python/
```

## AWS Resources Created

- **S3 Buckets**: 2 (uploads, website)
- **DynamoDB Table**: 1 (ImageAnalysisResults)
- **Lambda Functions**: 3 (generateUploadUrl, processImage, getResults)
- **API Gateway**: 1 HTTP API
- **Lambda Layer**: 1 (pydicom + dependencies)

## Cost Estimation

- **S3**: ~$0.023/GB/month storage + $0.0004/1000 PUT requests
- **Lambda**: ~$0.20 per 1M requests + $0.0000166667 per GB-second
- **Rekognition**: ~$1.00 per 1,000 images
- **DynamoDB**: Free tier includes 25GB storage + 25 RCU/WCU
- **API Gateway**: ~$1.00 per million requests

## Troubleshooting

### DICOM Viewer Not Loading
- Check browser console for errors
- Verify CDN access to cdn.jsdelivr.net
- Try different network (CDNs may be blocked)

### Lambda Timeout
- Increase timeout to 3-5 minutes for DICOM processing
- Increase memory to 1024MB or higher

### Import Errors
- Verify Lambda layer is attached
- Check architecture match (x86_64 vs arm64)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/aws-dicom-analyzer/issues
- AWS Documentation: https://docs.aws.amazon.com/

## Acknowledgments

- AWS Rekognition for object detection
- Cornerstone.js for DICOM viewer
- pydicom for DICOM processing