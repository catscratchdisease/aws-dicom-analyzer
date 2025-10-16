# Lambda Layers

This directory contains scripts and configuration for building Lambda layers with dependencies for DICOM processing and ML inference.

## Available Layers

### 1. DICOM Processing Layer (pydicom-layer)
- **pydicom** (2.4.4) - DICOM file parsing and manipulation
- **Pillow** (10.3.0) - Image processing
- **numpy** (1.26.4) - Numerical operations
- **pylibjpeg** - JPEG decompression support
- **pylibjpeg-libjpeg** - JPEG baseline decoder
- **pylibjpeg-openjpeg** - JPEG 2000 decoder

### 2. TensorFlow Layer (tensorflow-layer)
- **TensorFlow** (2.15.0) - Deep learning framework
- Includes Keras for model loading and inference

## Building the Layers

### Prerequisites
- Docker installed and running
- Bash shell (Mac/Linux) or Git Bash (Windows)
- AWS CLI configured

### Build DICOM Layer

```bash
./build-layer-script.sh
```

This will:
1. Use Docker to install packages for Linux/Lambda environment
2. Create a `python/` directory with all dependencies
3. Package everything into `dicom-layer.zip` (~65-80 MB)
4. Clean up temporary files

### Build TensorFlow Layer

```bash
./build-tensorflow-layer.sh
```

This will:
1. Use Docker to install TensorFlow for Linux/Lambda environment
2. Create a `python/` directory with TensorFlow and dependencies
3. Remove unnecessary files (tests, cache) to reduce size
4. Package everything into `tensorflow-layer.zip` (~300-400 MB)
5. Clean up temporary files

**Note**: TensorFlow layer is large and may take 10-15 minutes to build.

## Deploying the Layers

### Deploy DICOM Layer

```bash
# Upload to S3
aws s3 cp dicom-layer.zip s3://YOUR-BUCKET/layers/

# Create Lambda layer
aws lambda publish-layer-version \
    --layer-name pydicom-layer \
    --description "PyDICOM, Pillow, and NumPy for DICOM processing" \
    --content S3Bucket=YOUR-BUCKET,S3Key=layers/dicom-layer.zip \
    --compatible-runtimes python3.12 \
    --compatible-architectures x86_64
```

### Deploy TensorFlow Layer

```bash
# Upload to S3 (required due to size)
aws s3 cp tensorflow-layer.zip s3://YOUR-BUCKET/layers/

# Create Lambda layer
aws lambda publish-layer-version \
    --layer-name tensorflow-layer \
    --description "TensorFlow 2.15.0 for ML inference" \
    --content S3Bucket=YOUR-BUCKET,S3Key=layers/tensorflow-layer.zip \
    --compatible-runtimes python3.12 \
    --compatible-architectures x86_64
```

## Attaching Layers to Lambda Function

### Attach Both Layers (Recommended)

```bash
# Get layer ARNs from previous command outputs
PYDICOM_LAYER="arn:aws:lambda:REGION:ACCOUNT:layer:pydicom-layer:VERSION"
TENSORFLOW_LAYER="arn:aws:lambda:REGION:ACCOUNT:layer:tensorflow-layer:VERSION"

# Attach both layers to processImage function
aws lambda update-function-configuration \
    --function-name processImage \
    --layers $PYDICOM_LAYER $TENSORFLOW_LAYER

# Increase memory and timeout for TensorFlow inference
aws lambda update-function-configuration \
    --function-name processImage \
    --memory-size 2048 \
    --timeout 300
```

### Attach Only DICOM Layer

```bash
aws lambda update-function-configuration \
    --function-name processImage \
    --layers arn:aws:lambda:REGION:ACCOUNT:layer:pydicom-layer:VERSION
```

## Troubleshooting

### Docker Not Found
Install Docker Desktop:
- **Mac**: https://docs.docker.com/desktop/install/mac-install/
- **Windows**: https://docs.docker.com/desktop/install/windows-install/
- **Linux**: https://docs.docker.com/desktop/install/linux-install/

### Permission Denied
Make the script executable:
```bash
chmod +x build-layer.sh
```

### Layer Too Large
The layer might exceed Lambda's limits. Consider:
1. Using a Lambda container image instead
2. Removing unnecessary dependencies
3. Using external compression tools

### Architecture Mismatch
If Lambda function is ARM64, rebuild with:
```bash
docker run --rm \
    --platform linux/arm64 \
    -v $(pwd):/var/task \
    -w /var/task \
    --entrypoint /bin/bash \
    public.ecr.aws/lambda/python:3.12-arm64 \
    -c "pip install --target python pydicom pillow numpy pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg"
```

## Updating Dependencies

To update package versions, modify the `build-layer.sh` script:

```bash
# Change this line:
pip install --target python pydicom==2.4.4 pillow==10.3.0 numpy==1.26.4 ...

# To:
pip install --target python pydicom==NEW_VERSION pillow==NEW_VERSION ...
```

## Testing the Layers

### Test DICOM Layer

Create a test Lambda function:

```python
import json

def lambda_handler(event, context):
    try:
        import pydicom
        import PIL
        import numpy

        return {
            'statusCode': 200,
            'body': json.dumps({
                'pydicom': pydicom.__version__,
                'pillow': PIL.__version__,
                'numpy': numpy.__version__
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### Test TensorFlow Layer

```python
import json

def lambda_handler(event, context):
    try:
        import tensorflow as tf

        return {
            'statusCode': 200,
            'body': json.dumps({
                'tensorflow': tf.__version__,
                'keras': tf.keras.__version__
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

Attach the layers and test to verify all packages load correctly.

## Using TensorFlow with Your Keras Model

To use the trained model (`models/20250713_ett_model_30epochs_resnet_cropped.keras`) in Lambda:

1. Upload the model to S3:
```bash
aws s3 cp models/20250713_ett_model_30epochs_resnet_cropped.keras s3://YOUR-BUCKET/models/
```

2. Modify Lambda2 to download and use the model (see integration guide below)

3. Ensure Lambda has sufficient memory (2048+ MB) and timeout (300s)

For detailed integration instructions, see the integration guide in the docs folder.