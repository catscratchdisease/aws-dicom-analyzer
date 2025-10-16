# TensorFlow Integration Guide

This guide explains how to integrate the TensorFlow Keras model into Lambda2 for real-time inference.

## Overview

The current Lambda2 implementation uses a placeholder classifier that returns 0 or 1 based on image brightness. This guide shows how to replace it with the actual trained Keras model (`models/20250713_ett_model_30epochs_resnet_cropped.keras`).

## Prerequisites

1. TensorFlow Lambda layer built and deployed
2. Both pydicom-layer and tensorflow-layer attached to Lambda
3. Lambda memory increased to 2048+ MB
4. Model file uploaded to S3

## Step 1: Upload Model to S3

```bash
aws s3 cp models/20250713_ett_model_30epochs_resnet_cropped.keras \
    s3://YOUR-BUCKET/models/ett_model.keras
```

## Step 2: Update Lambda Environment Variables

Add the following environment variable to Lambda2:

```bash
aws lambda update-function-configuration \
    --function-name processImage \
    --environment Variables="{
        TABLE_NAME=ImageAnalysisResults,
        MODEL_BUCKET=YOUR-BUCKET,
        MODEL_KEY=models/ett_model.keras
    }"
```

## Step 3: Modify Lambda2 Code

### Option A: Load Model on Every Invocation (Simple)

Replace the `run_classifier_on_png()` function in `lambda2-code.py`:

```python
def run_classifier_on_png(png_bytes):
    """Run TensorFlow/Keras model inference on PNG image.

    Expects 512x512 PNG image, returns predicted class (0 or 1).
    """
    try:
        import tensorflow as tf
        from tensorflow import keras
        import numpy as np

        # Download model from S3 if not cached
        model_bucket = os.environ.get('MODEL_BUCKET')
        model_key = os.environ.get('MODEL_KEY')

        if not model_bucket or not model_key:
            print("Model S3 location not configured, falling back to placeholder")
            # Fallback to brightness-based classifier
            with io.BytesIO(png_bytes) as buf:
                img = Image.open(buf).convert('L')
                img_small = img.resize((64, 64))
                pixels = list(img_small.getdata())
                avg = sum(pixels) / len(pixels)
                return 1 if avg > 127 else 0

        # Download model to /tmp
        model_path = '/tmp/model.keras'
        if not os.path.exists(model_path):
            print(f"Downloading model from s3://{model_bucket}/{model_key}")
            s3_client.download_file(model_bucket, model_key, model_path)
            print("Model downloaded successfully")

        # Load model
        model = keras.models.load_model(model_path)

        # Preprocess image
        with io.BytesIO(png_bytes) as buf:
            img = Image.open(buf).convert('RGB')
            img_array = np.array(img)

            # If image is not 512x512, resize it
            if img_array.shape[:2] != (512, 512):
                img = img.resize((512, 512))
                img_array = np.array(img)

            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)  # shape: (1, 512, 512, 3)

        # Run inference
        predictions = model.predict(img_array, verbose=0)
        predicted_class = int(np.argmax(predictions, axis=1)[0])
        confidence = float(np.max(predictions))

        print(f"Model prediction: class={predicted_class}, confidence={confidence:.3f}")

        return predicted_class

    except Exception as e:
        print(f"TensorFlow classifier error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 0
```

### Option B: Load Model Once Per Container (Optimized)

For better performance, load the model once when the Lambda container starts:

```python
import json
import boto3
import os
import urllib.parse
from datetime import datetime
from decimal import Decimal
import io

# AWS clients
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

# Import TensorFlow and load model (once per container)
TENSORFLOW_MODEL = None
try:
    import tensorflow as tf
    from tensorflow import keras

    # Download and load model on cold start
    model_bucket = os.environ.get('MODEL_BUCKET')
    model_key = os.environ.get('MODEL_KEY')

    if model_bucket and model_key:
        model_path = '/tmp/model.keras'
        print(f"Downloading model from s3://{model_bucket}/{model_key}")
        s3_client.download_file(model_bucket, model_key, model_path)
        print("Loading TensorFlow model...")
        TENSORFLOW_MODEL = keras.models.load_model(model_path)
        print(f"Model loaded successfully: {TENSORFLOW_MODEL.summary()}")
    else:
        print("MODEL_BUCKET or MODEL_KEY not set, model not loaded")

except Exception as e:
    print(f"Failed to load TensorFlow model: {e}")
    TENSORFLOW_MODEL = None


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


# ... keep all other existing functions (is_dicom_file, convert_dicom_to_jpeg, resize_and_crop_to_png_bytes) ...


def run_classifier_on_png(png_bytes):
    """Run TensorFlow/Keras model inference on PNG image.

    Uses pre-loaded model for better performance.
    """
    try:
        if TENSORFLOW_MODEL is None:
            print("TensorFlow model not loaded, using placeholder")
            # Fallback to brightness-based classifier
            with io.BytesIO(png_bytes) as buf:
                img = Image.open(buf).convert('L')
                img_small = img.resize((64, 64))
                pixels = list(img_small.getdata())
                avg = sum(pixels) / len(pixels)
                return 1 if avg > 127 else 0

        # Preprocess image
        with io.BytesIO(png_bytes) as buf:
            img = Image.open(buf).convert('RGB')
            img_array = np.array(img)

            # Ensure 512x512
            if img_array.shape[:2] != (512, 512):
                img = img.resize((512, 512))
                img_array = np.array(img)

            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)

        # Run inference
        predictions = TENSORFLOW_MODEL.predict(img_array, verbose=0)
        predicted_class = int(np.argmax(predictions, axis=1)[0])
        confidence = float(np.max(predictions))

        print(f"Model prediction: class={predicted_class}, confidence={confidence:.3f}")

        return predicted_class

    except Exception as e:
        print(f"TensorFlow classifier error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 0


# ... keep lambda_handler and all other functions unchanged ...
```

## Step 4: Deploy Updated Lambda

```bash
cd lambda/lambda2-process-image
zip function.zip lambda2-code.py
aws lambda update-function-code --function-name processImage --zip-file fileb://function.zip
```

## Step 5: Test the Integration

### Test with Sample Image

```bash
# Upload a test image through the frontend or via AWS CLI
aws s3 cp inference/00021942_009.png s3://YOUR-UPLOAD-BUCKET/uploads/test-job-id/test.png
```

### Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/processImage --follow
```

Look for:
- "Model loaded successfully"
- "Model prediction: class=X, confidence=Y.YYY"

### Verify DynamoDB

```bash
aws dynamodb get-item \
    --table-name ImageAnalysisResults \
    --key '{"jobId":{"S":"YOUR-JOB-ID"}}'
```

The `flag` attribute should contain the predicted class (0 or 1).

## Performance Considerations

### Option A vs Option B

**Option A (Load on every invocation)**:
- Pros: Simpler code
- Cons: Slower (loads model every time), higher latency (~2-5s overhead)
- Use when: Traffic is low and cold starts are common

**Option B (Load once per container)**:
- Pros: Much faster after cold start (~100-500ms inference)
- Cons: Slightly more complex, higher cold start time (~10-15s)
- Use when: Traffic is moderate to high, containers stay warm

### Memory Recommendations

- **2048 MB**: Minimum for TensorFlow
- **3008 MB**: Recommended for better performance
- **4096 MB**: Optimal for faster cold starts

### Cost Optimization

```bash
# Set memory based on your traffic
aws lambda update-function-configuration \
    --function-name processImage \
    --memory-size 3008
```

## Troubleshooting

### Model Not Loading

**Error**: "Model file not found in /tmp"

**Solution**: Verify model exists in S3 and Lambda has s3:GetObject permission

```bash
aws s3 ls s3://YOUR-BUCKET/models/
```

### Out of Memory Errors

**Error**: "Runtime exited with error: signal: killed Runtime.ExitError"

**Solution**: Increase Lambda memory

```bash
aws lambda update-function-configuration \
    --function-name processImage \
    --memory-size 3008
```

### TensorFlow Import Errors

**Error**: "No module named 'tensorflow'"

**Solution**: Verify TensorFlow layer is attached

```bash
aws lambda get-function-configuration --function-name processImage | grep Layers
```

### Slow Inference

**Symptoms**: Processing takes > 10 seconds per image

**Solutions**:
1. Use Option B (pre-load model)
2. Increase memory to 3008+ MB
3. Consider provisioned concurrency for consistent performance

### Shape Mismatch Errors

**Error**: "Input shape mismatch"

**Solution**: Verify image preprocessing matches training preprocessing. Current code expects 512×512 RGB images.

## Advanced: Using EFS for Large Models

If your model is > 100 MB or you have multiple models, consider using Amazon EFS:

1. Create EFS file system
2. Mount to Lambda function
3. Store model on EFS instead of S3
4. Load from `/mnt/efs/model.keras` instead of `/tmp/model.keras`

This eliminates download time on every cold start.

## Monitoring

### Key Metrics to Watch

1. **Duration**: Should be < 5s after cold start (< 1s with warm containers)
2. **Memory usage**: Should not exceed 80% of allocated memory
3. **Cold start rate**: If > 50%, consider provisioned concurrency
4. **Error rate**: Should be < 1%

### CloudWatch Dashboard

Create a dashboard with:
- Lambda invocations
- Lambda errors
- Lambda duration (p50, p99)
- Memory utilization

## Alternative: Lambda Container Images

For even better performance and easier management, consider using Lambda Container Images:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy model
COPY models/ett_model.keras /opt/model.keras

# Copy function code
COPY lambda2-code.py ${LAMBDA_TASK_ROOT}

CMD ["lambda2-code.lambda_handler"]
```

Benefits:
- No layer size limits
- Faster cold starts (model pre-loaded in image)
- Better dependency management

## Summary

This integration replaces the placeholder classifier with your trained Keras model. Choose Option B for better performance if you have consistent traffic, or Option A for simplicity if traffic is sporadic.

For production use, monitor performance metrics and adjust memory/timeout settings accordingly.
