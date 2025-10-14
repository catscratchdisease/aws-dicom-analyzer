# Lambda Layers

This directory contains scripts and configuration for building Lambda layers with DICOM processing dependencies.

## What's Included

The Lambda layer includes:
- **pydicom** (2.4.4) - DICOM file parsing and manipulation
- **Pillow** (10.3.0) - Image processing
- **numpy** (1.26.4) - Numerical operations
- **pylibjpeg** - JPEG decompression support
- **pylibjpeg-libjpeg** - JPEG baseline decoder
- **pylibjpeg-openjpeg** - JPEG 2000 decoder

## Building the Layer

### Prerequisites
- Docker installed and running
- Bash shell (Mac/Linux) or Git Bash (Windows)

### Build Command

```bash
./build-layer.sh
```

This will:
1. Use Docker to install packages for Linux/Lambda environment
2. Create a `python/` directory with all dependencies
3. Package everything into `dicom-layer.zip`
4. Clean up temporary files

### Output

- **dicom-layer.zip** - Lambda layer package (~65-80 MB)

## Deploying the Layer

### Option 1: Via S3 (Recommended for large files)

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

### Option 2: Direct Upload (if < 50MB)

```bash
aws lambda publish-layer-version \
    --layer-name pydicom-layer \
    --description "PyDICOM, Pillow, and NumPy for DICOM processing" \
    --zip-file fileb://dicom-layer.zip \
    --compatible-runtimes python3.12 \
    --compatible-architectures x86_64
```

## Attaching to Lambda Function

```bash
# Get layer ARN from previous command output
LAYER_ARN="arn:aws:lambda:us-east-1:ACCOUNT-ID:layer:pydicom-layer:1"

# Attach to Lambda function
aws lambda update-function-configuration \
    --function-name processImage \
    --layers $LAYER_ARN
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

## Testing the Layer

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

Attach the layer and test to verify all packages load correctly.