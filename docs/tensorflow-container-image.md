# Using TensorFlow with Lambda Container Images

## Problem

The TensorFlow layer we built is **153 MB compressed** but **633 MB uncompressed**, which exceeds AWS Lambda's 250 MB unzipped layer size limit.

## Solution: Lambda Container Images

Instead of using layers, we'll package TensorFlow and your code into a Lambda container image. This approach:
- ✅ No size limits (up to 10 GB)
- ✅ Faster cold starts (model pre-loaded in image)
- ✅ Better dependency management
- ✅ Easier to test locally

## Option 1: Quick Container Image (Recommended)

### Step 1: Create Dockerfile

Create `lambda/lambda2-process-image/Dockerfile`:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies
RUN dnf install -y \
    libgomp \
    && dnf clean all

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Lambda function code
COPY lambda2-code.py ${LAMBDA_TASK_ROOT}/

# Copy model (optional - can load from S3 instead)
# COPY ../../models/20250713_ett_model_30epochs_resnet_cropped.keras /opt/model.keras

# Set the CMD to your handler
CMD ["lambda2-code.lambda_handler"]
```

### Step 2: Create requirements.txt

Create `lambda/lambda2-process-image/requirements.txt`:

```
tensorflow==2.18.0
pydicom==2.4.4
Pillow==10.3.0
numpy==2.0.2
pylibjpeg
pylibjpeg-libjpeg
pylibjpeg-openjpeg
```

### Step 3: Build Container Image

```bash
cd lambda/lambda2-process-image

# Build the image
docker build --platform linux/amd64 -t processimage:latest .
```

### Step 4: Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository --repository-name processimage --region us-east-1

# Get the repository URI (save this)
aws ecr describe-repositories --repository-names processimage --query 'repositories[0].repositoryUri' --output text
```

### Step 5: Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag the image (replace ACCOUNT_ID with your AWS account ID)
docker tag processimage:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/processimage:latest

# Push the image
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/processimage:latest
```

### Step 6: Update Lambda Function

```bash
# Update existing Lambda to use container image
aws lambda update-function-code \
    --function-name processImage \
    --image-uri ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/processimage:latest
```

Or create a new Lambda function:

```bash
aws lambda create-function \
    --function-name processImage \
    --package-type Image \
    --code ImageUri=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/processimage:latest \
    --role arn:aws:iam::ACCOUNT_ID:role/ImageAnalyzerLambdaRole \
    --timeout 300 \
    --memory-size 2048 \
    --environment Variables="{TABLE_NAME=ImageAnalysisResults,MODEL_BUCKET=image-analysis-bucket-chicken,MODEL_KEY=models/ett_model.keras}"
```

## Option 2: Include Model in Container (Fastest)

For the fastest cold starts, include the model in the container image:

### Modified Dockerfile

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies
RUN dnf install -y libgomp && dnf clean all

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model file into the image
COPY 20250713_ett_model_30epochs_resnet_cropped.keras /opt/model.keras

# Copy Lambda function code
COPY lambda2-code.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda2-code.lambda_handler"]
```

### Modified lambda2-code.py

Update the model loading code to use the pre-loaded model:

```python
# At the top of the file, after imports
TENSORFLOW_MODEL = None
try:
    import tensorflow as tf
    from tensorflow import keras

    # Load model from container filesystem
    model_path = '/opt/model.keras'
    if os.path.exists(model_path):
        print(f"Loading model from {model_path}")
        TENSORFLOW_MODEL = keras.models.load_model(model_path)
        print("Model loaded successfully from container")
    else:
        # Fallback to S3
        model_bucket = os.environ.get('MODEL_BUCKET')
        model_key = os.environ.get('MODEL_KEY')
        if model_bucket and model_key:
            model_path = '/tmp/model.keras'
            print(f"Downloading model from s3://{model_bucket}/{model_key}")
            s3_client.download_file(model_bucket, model_key, model_path)
            TENSORFLOW_MODEL = keras.models.load_model(model_path)
            print("Model loaded from S3")

except Exception as e:
    print(f"Failed to load TensorFlow model: {e}")
    TENSORFLOW_MODEL = None
```

### Build with Model

```bash
cd lambda/lambda2-process-image

# Copy model to build directory
cp ../../models/20250713_ett_model_30epochs_resnet_cropped.keras .

# Build
docker build --platform linux/amd64 -t processimage:latest .

# Push (same as before)
```

## Comparison: Layers vs Container Images

| Feature | Lambda Layers | Container Images |
|---------|--------------|------------------|
| TensorFlow size | ❌ Too large (633 MB) | ✅ Fits (up to 10 GB) |
| Cold start | ~5-10s | ~10-15s (first time) |
| Warm container | ~500ms | ~100-500ms |
| Model loading | Every cold start | Pre-loaded in image |
| Complexity | Low | Medium |
| Best for | Small dependencies | Large frameworks like TensorFlow |

## Testing Locally

Before deploying, test your container locally:

```bash
# Run container locally
docker run --platform linux/amd64 -p 9000:8080 processimage:latest

# In another terminal, invoke it
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{
    "Records": [{
      "s3": {
        "bucket": {"name": "image-analysis-bucket-chicken"},
        "object": {"key": "uploads/test-job-id/test.jpg"}
      }
    }]
  }'
```

## Updating the Container

When you need to update code or model:

```bash
# Rebuild
docker build --platform linux/amd64 -t processimage:latest .

# Tag with version
docker tag processimage:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/processimage:v2

# Push
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/processimage:v2

# Update Lambda
aws lambda update-function-code \
    --function-name processImage \
    --image-uri ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/processimage:v2
```

## Cost Implications

Container images are stored in ECR:
- **Storage**: ~$0.10 per GB/month
- **Image size**: ~1-2 GB (TensorFlow + model)
- **Monthly cost**: ~$0.10-$0.20
- **Lambda cost**: Same as before

## Recommended Approach

For your use case with TensorFlow and a 95 MB model:

1. ✅ **Use Container Images** (not layers)
2. ✅ **Include model in image** for fastest performance
3. ✅ **Set memory to 3008 MB** for optimal performance
4. ✅ **Keep timeout at 300s**

This will give you:
- Fast inference (~100-500ms after cold start)
- No download time for model
- Simplified deployment
- No layer size limits

## Next Steps

Would you like me to:
1. Create the Dockerfile and requirements.txt?
2. Build the container image?
3. Push to ECR and update Lambda?

Let me know and I'll help you complete the migration to container images!
