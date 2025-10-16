# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS DICOM Image Analysis System - A serverless medical image analysis application that processes both regular images and DICOM medical images using AWS Lambda, Rekognition, S3, and DynamoDB.

**Core data flow:** Frontend → API Gateway → Lambda1 (presigned URL) → S3 uploads → S3 event → Lambda2 (DICOM conversion + Rekognition + classifier) → DynamoDB → Lambda3 (results retrieval) → Frontend polling

## Key Architecture Patterns

### S3 Key Layout (DO NOT CHANGE)
- **Uploads**: `uploads/{jobId}/{originalFileName}` (created by Lambda1)
- **Converted DICOM**: `converted/{jobId}/converted.jpg` (created by Lambda2)

These paths are hardcoded throughout the system. Changing them breaks downstream processing.

### DynamoDB Schema
**Table**: ImageAnalysisResults
**Primary key**: `jobId` (UUID string)

**Item structure**:
- `jobId` - UUID
- `status` - "pending" | "complete" | "error"
- `s3Key` - Original file path in S3
- `fileName` - Original filename
- `fileType` - MIME type (forced to "application/dicom" for .dcm/.dicom files)
- `results` - Rekognition response (floats converted to Decimals)
- `flag` - Classifier output (0 or 1, stored as Decimal)
- `imageUrl` - Presigned URL (DICOM files only)
- `error` - Error message (when status="error")
- `createdAt` - ISO timestamp
- `updatedAt` - ISO timestamp

**CRITICAL**: All numeric values must be converted to Decimal before writing to DynamoDB using `convert_floats_to_decimals()` in lambda2-code.py:32. Lambda3 converts them back using `convert_decimals_to_floats()`.

### API Endpoints
- **POST /request-upload** - Body: `{fileName, fileType}` → Response: `{uploadUrl, jobId}`
- **GET /get-results?jobId={id}** - Response: `{status, results, imageUrl, error, flag}`

Frontend polls every 2 seconds for max 30 attempts (60s total).

## Lambda Functions

### Lambda 1: Generate Upload URL (lambda1-code.py)
- Generates presigned PUT URLs for direct browser uploads
- Creates initial DynamoDB item with status="pending"
- Auto-detects DICOM files by .dcm/.dicom extension and forces ContentType to "application/dicom"
- Env vars: `UPLOAD_BUCKET`, `TABLE_NAME`

### Lambda 2: Process Image (lambda2-code.py)
- S3-triggered on uploads/ prefix
- Detects DICOM by file extension (.dcm/.dicom)
- For DICOM: converts to JPEG using pydicom+Pillow, stores to `converted/` prefix, generates presigned URL
- Calls Rekognition.detect_labels on JPEG (converted or original)
- Runs classifier: resizes to 1024×1024, crops upper-center 512×512, converts to PNG, runs placeholder classifier (currently brightness-based)
- Stores results, flag, and imageUrl to DynamoDB with status="complete"
- On error: updates DynamoDB with status="error" and error message
- **Timeout**: 300s (5 min), **Memory**: 1024 MB
- Env vars: `TABLE_NAME`
- **Dependencies**: Requires pydicom Lambda layer

### Lambda 3: Get Results (lambda3-code.py)
- Retrieves results from DynamoDB by jobId
- Converts Decimals back to floats for JSON response
- Env vars: `TABLE_NAME`

## Image Classifier

Lambda2 includes a classifier pipeline (lambda2-code.py:92-136):
1. Resize image to 1024×1024
2. Crop to 512×512 (upper half, horizontally centered)
3. Convert to PNG
4. Run classifier (currently placeholder that returns 1 if avg brightness > 127, else 0)

**To integrate a real ML model**: Replace `run_classifier_on_png()` function. The input is PNG bytes at 512×512. The trained Keras model is in `models/20250713_ett_model_30epochs_resnet_cropped.keras`. Reference `inference/classify_image.py` for usage pattern (TensorFlow/Keras).

## Development Commands

### Build Lambda Layer (DICOM support)
```bash
cd layers
./build-layer-script.sh
# Uploads to S3 and publishes layer
aws s3 cp dicom-layer.zip s3://YOUR-BUCKET/layers/
aws lambda publish-layer-version --layer-name pydicom-layer \
  --content S3Bucket=YOUR-BUCKET,S3Key=layers/dicom-layer.zip \
  --compatible-runtimes python3.12 --compatible-architectures x86_64
```

**Layer contents**: pydicom, Pillow, numpy, pylibjpeg, pylibjpeg-libjpeg, pylibjpeg-openjpeg

### Deploy Lambda Functions
```bash
cd lambda/lambda1-generate-upload-url
zip function.zip lambda1-code.py
aws lambda update-function-code --function-name generateUploadUrl --zip-file fileb://function.zip

cd ../lambda2-process-image
zip function.zip lambda2-code.py
aws lambda update-function-code --function-name processImage --zip-file fileb://function.zip

cd ../lambda3-get-results
zip function.zip lambda3-code.py
aws lambda update-function-code --function-name getResults --zip-file fileb://function.zip
```

**Note**: Lambda function names (generateUploadUrl, processImage, getResults) are the actual AWS function names used in deployment.

### Deploy Frontend
```bash
cd frontend
aws s3 cp index.html s3://YOUR-WEBSITE-BUCKET/
```

Update `API_ENDPOINT` in index.html with your API Gateway URL.

### Local Testing
```bash
# Lambda1
cd lambda/lambda1-generate-upload-url
python3 -c "from lambda1-code import lambda_handler; print(lambda_handler({'body': '{\"fileName\":\"test.jpg\",\"fileType\":\"image/jpeg\"}'}, None))"

# Lambda3
cd lambda/lambda3-get-results
python3 -c "from lambda3-code import lambda_handler; print(lambda_handler({'queryStringParameters': {'jobId': 'test-id'}}, None))"
```

### Test Classifier Locally
```bash
cd inference
python classify_image.py /path/to/image.png
```

## Critical Conventions

### DICOM Detection
DICOM files are detected by extension only: `.dcm` or `.dicom` (case-insensitive). Lambda1 forces ContentType to "application/dicom" regardless of what the browser sends.

### Error Handling
- Lambda2 attempts to update DynamoDB on any exception to set status="error"
- All Lambda responses include CORS headers: `Access-Control-Allow-Origin: *`
- Frontend displays error messages from DynamoDB error field

### Floating Point / Decimal Conversion
**Always** use `convert_floats_to_decimals()` before writing to DynamoDB. DynamoDB doesn't support native floats. Lambda3 uses `convert_decimals_to_floats()` before JSON serialization.

### CORS Configuration
- All Lambda responses include CORS headers
- S3 upload bucket has CORS rules (see infrastructure/s3-cors.json)
- API Gateway must have CORS enabled

## What NOT to Do

1. **Do not change S3 key prefixes** (`uploads/`, `converted/`) without updating all Lambdas and S3 event filters
2. **Do not write floats directly to DynamoDB** - always convert to Decimal
3. **Do not assume DICOM libraries are present** - Lambda2 checks `DICOM_SUPPORT` flag at runtime
4. **Do not remove CORS headers** from Lambda responses
5. **Do not change API request/response shapes** without updating frontend (see index.html lines 200-400 for polling logic)
6. **Do not commit AWS credentials or bucket names** - use environment variables

## Key Files Reference

- `frontend/index.html` - Single-file SPA with upload, polling, and DICOM viewer
- `lambda/lambda1-generate-upload-url/lambda1-code.py` - Presigned URL generation
- `lambda/lambda2-process-image/lambda2-code.py` - Image processing, DICOM conversion, Rekognition, classifier
- `lambda/lambda3-get-results/lambda3-code.py` - Results retrieval
- `layers/build-layer-script.sh` - Lambda layer build script
- `models/20250713_ett_model_30epochs_resnet_cropped.keras` - Trained classifier model
- `inference/classify_image.py` - Standalone classifier test script
- `.github/copilot-instructions.md` - Detailed architectural notes

## Environment Variables

All Lambda functions require these environment variables (set in AWS Lambda console or via CLI):

- **Lambda1 & Lambda2**: `UPLOAD_BUCKET` (S3 bucket name)
- **All Lambdas**: `TABLE_NAME` (DynamoDB table, typically "ImageAnalysisResults")

## Git LFS

Large model files are tracked with Git LFS:
```bash
git lfs track "*.keras"
```

Model file: `models/20250713_ett_model_30epochs_resnet_cropped.keras` (~95 MB)

## Common Issues

### DICOM Processing Failures
- Verify Lambda layer is attached to processImage function
- Check timeout (must be ≥300s) and memory (must be ≥1024MB)
- Lambda2 logs show "DICOM support available: True/False" - if False, layer is missing

### Classifier Integration
To replace placeholder classifier with real model in Lambda2:
1. Package TensorFlow/Keras with dependencies in a separate Lambda layer
2. Load model in Lambda2: `model = keras.models.load_model('/opt/model.keras')`
3. Replace `run_classifier_on_png()` function (line 120-136)
4. Increase Lambda memory to 2048-4096 MB for TensorFlow inference

### Frontend Polling Timeout
Default: 30 attempts × 2s = 60s total. For longer processing, increase `maxAttempts` in index.html (search for `pollForResults`).
