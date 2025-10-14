#!/bin/bash

# Build Lambda Layer for DICOM Processing
# Creates a Lambda layer with pydicom, pillow, numpy, and JPEG decoders

set -e  # Exit on error

echo "🏗️  Building Lambda Layer for DICOM Processing"
echo "=============================================="

# Clean up old files
echo "Cleaning up old files..."
rm -f dicom-layer.zip
rm -rf python

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

echo "✅ Docker found"

# Build with Docker for Linux compatibility
echo "📦 Installing Python packages..."
docker run --rm \
    --platform linux/amd64 \
    -v $(pwd):/var/task \
    -w /var/task \
    --entrypoint /bin/bash \
    public.ecr.aws/lambda/python:3.12 \
    -c "pip install --target python pydicom pillow numpy pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg"

if [ $? -ne 0 ]; then
    echo "❌ Failed to install packages"
    exit 1
fi

echo "✅ Packages installed"

# Check if python directory exists
if [ ! -d "python" ]; then
    echo "❌ Error: python directory not created"
    exit 1
fi

# Create zip file
echo "📦 Creating zip file..."
zip -r9 dicom-layer.zip python/

if [ $? -ne 0 ]; then
    echo "❌ Failed to create zip file"
    exit 1
fi

# Get zip file size
ZIP_SIZE=$(du -h dicom-layer.zip | cut -f1)
echo "✅ Zip file created: dicom-layer.zip ($ZIP_SIZE)"

# Clean up
echo "🧹 Cleaning up..."
rm -rf python

echo ""
echo "✅ Lambda layer built successfully!"
echo ""
echo "Next steps:"
echo "1. Upload to S3:"
echo "   aws s3 cp dicom-layer.zip s3://YOUR-BUCKET/layers/"
echo ""
echo "2. Create Lambda layer:"
echo "   aws lambda publish-layer-version \\"
echo "       --layer-name pydicom-layer \\"
echo "       --content S3Bucket=YOUR-BUCKET,S3Key=layers/dicom-layer.zip \\"
echo "       --compatible-runtimes python3.12 \\"
echo "       --compatible-architectures x86_64"
echo ""