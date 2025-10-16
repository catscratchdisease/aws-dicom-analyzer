#!/bin/bash

# Build Lambda Layer for TensorFlow
# Creates a Lambda layer with TensorFlow and Keras for ML inference

set -e  # Exit on error

echo "🏗️  Building Lambda Layer for TensorFlow"
echo "=========================================="

# Clean up old files
echo "Cleaning up old files..."
rm -f tensorflow-layer.zip
rm -rf python

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

echo "✅ Docker found"

# Build with Docker for Linux compatibility
echo "📦 Installing TensorFlow (this may take several minutes)..."
echo "Note: TensorFlow is large (~300MB compressed, ~900MB uncompressed)"
echo ""

docker run --rm \
    --platform linux/amd64 \
    -v $(pwd):/var/task \
    -w /var/task \
    --entrypoint /bin/bash \
    public.ecr.aws/lambda/python:3.12 \
    -c "pip install --target python tensorflow==2.18.0 --no-cache-dir"

if [ $? -ne 0 ]; then
    echo "❌ Failed to install TensorFlow"
    exit 1
fi

echo "✅ TensorFlow installed"

# Check if python directory exists
if [ ! -d "python" ]; then
    echo "❌ Error: python directory not created"
    exit 1
fi

# Remove unnecessary files to reduce size
echo "🧹 Removing unnecessary files to reduce layer size..."
cd python

# Remove tests and unnecessary files
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.so.*" -delete 2>/dev/null || true

cd ..

# Create zip file
echo "📦 Creating zip file (this may take a few minutes)..."
zip -r9 tensorflow-layer.zip python/

if [ $? -ne 0 ]; then
    echo "❌ Failed to create zip file"
    exit 1
fi

# Get zip file size
ZIP_SIZE=$(du -h tensorflow-layer.zip | cut -f1)
echo "✅ Zip file created: tensorflow-layer.zip ($ZIP_SIZE)"

# Check if size exceeds Lambda limits
ZIP_SIZE_BYTES=$(stat -f%z tensorflow-layer.zip 2>/dev/null || stat -c%s tensorflow-layer.zip 2>/dev/null)
if [ $ZIP_SIZE_BYTES -gt 262144000 ]; then
    echo "⚠️  WARNING: Layer size exceeds 250MB uncompressed limit"
    echo "   You may need to use a Lambda container image instead"
fi

# Clean up
echo "🧹 Cleaning up..."
rm -rf python

echo ""
echo "✅ TensorFlow Lambda layer built successfully!"
echo ""
echo "Next steps:"
echo ""
echo "1. Upload to S3 (required due to large size):"
echo "   aws s3 cp tensorflow-layer.zip s3://YOUR-BUCKET/layers/"
echo ""
echo "2. Create Lambda layer:"
echo "   aws lambda publish-layer-version \\"
echo "       --layer-name tensorflow-layer \\"
echo "       --description \"TensorFlow 2.18.0 for ML inference\" \\"
echo "       --content S3Bucket=YOUR-BUCKET,S3Key=layers/tensorflow-layer.zip \\"
echo "       --compatible-runtimes python3.12 \\"
echo "       --compatible-architectures x86_64"
echo ""
echo "3. Attach both layers to your Lambda function:"
echo "   aws lambda update-function-configuration \\"
echo "       --function-name processImage \\"
echo "       --layers \\"
echo "           arn:aws:lambda:REGION:ACCOUNT:layer:pydicom-layer:VERSION \\"
echo "           arn:aws:lambda:REGION:ACCOUNT:layer:tensorflow-layer:VERSION"
echo ""
echo "4. Increase Lambda memory to at least 2048 MB for TensorFlow:"
echo "   aws lambda update-function-configuration \\"
echo "       --function-name processImage \\"
echo "       --memory-size 2048 \\"
echo "       --timeout 300"
echo ""
echo "⚠️  IMPORTANT: TensorFlow layer is large. Consider using Lambda Container Images"
echo "   for better performance and easier management if size becomes an issue."
echo ""
