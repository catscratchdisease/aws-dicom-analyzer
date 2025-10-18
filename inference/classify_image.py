"""Classifier wrapper for the saved Keras model.

This module exposes classify_png_bytes(png_bytes) -> int.
It lazily loads the Keras model from ../models/20250713_ett_model_30epochs_resnet_cropped.keras.

Note: TensorFlow and the model file must be available in the Lambda environment (layer or bundled).

Usage as command-line script:
    python classify_image.py <image_path>
"""

try:
    import numpy as np
    from PIL import Image
    import io
    from tensorflow import keras
    TF_AVAILABLE = True
except Exception as e:
    TF_AVAILABLE = False
    _import_error = e


_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    if not TF_AVAILABLE:
        raise ImportError(f"TensorFlow or required dependencies not available: {_import_error}")
    import os
    # Try to find model relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, '..', 'models', '20250713_ett_model_30epochs_resnet_cropped.keras')
    if not os.path.exists(model_path):
        # Fallback for Lambda environment
        model_path = '../models/20250713_ett_model_30epochs_resnet_cropped.keras'
    _model = keras.models.load_model(model_path)
    return _model


def classify_png_bytes(png_bytes):
    """Classify an image provided as PNG bytes. Returns predicted class as int.

    Preprocessing: expects PNG bytes of a 512x512 image (already preprocessed).
    Ensures 3 channels and runs inference.
    """
    try:
        model = _load_model()
    except Exception:
        # Re-raise to let callers handle fallback
        raise

    with Image.open(io.BytesIO(png_bytes)) as img:
        arr = np.array(img)

        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)

        arr = np.expand_dims(arr, axis=0)

        preds = model.predict(arr)
        predicted_class = int(np.argmax(preds, axis=1)[0])
        return predicted_class


def classify_image_file(image_path):
    """Classify an image from a file path. Returns predicted class as int.

    Applies the same preprocessing as Lambda:
    1. Resize to 1024x1024
    2. Crop upper-center 512x512 region
    3. Convert to PNG
    4. Run classifier
    """
    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    # Apply Lambda preprocessing: resize to 1024x1024, then crop to 512x512
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert('RGB')

        # Resize to 1024x1024 (same as Lambda)
        img = img.resize((1024, 1024), Image.LANCZOS)

        # Crop to upper-center 512x512 (same as Lambda)
        width, height = img.size
        crop_w, crop_h = 512, 512
        left = (width - crop_w) // 2
        upper = 0
        right = left + crop_w
        lower = upper + crop_h

        cropped = img.crop((left, upper, right, lower))

        # Convert to PNG
        png_buffer = io.BytesIO()
        cropped.save(png_buffer, format='PNG')
        png_bytes = png_buffer.getvalue()

    return classify_png_bytes(png_bytes)


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Classify medical images for endotracheal tube detection')
    parser.add_argument('image_path', help='Path to image file (PNG, JPG, etc.)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed prediction scores')

    args = parser.parse_args()

    if not TF_AVAILABLE:
        print(f"Error: TensorFlow not available: {_import_error}", file=sys.stderr)
        sys.exit(1)

    try:
        # Load image and apply preprocessing
        with open(args.image_path, 'rb') as f:
            image_bytes = f.read()

        with Image.open(io.BytesIO(image_bytes)) as img:
            print(f"Input image: {args.image_path}")
            print(f"Original size: {img.size}")
            print(f"Mode: {img.mode}")

            # Apply Lambda preprocessing
            img = img.convert('RGB')
            print(f"\nPreprocessing:")
            print(f"  1. Resizing to 1024x1024...")
            img = img.resize((1024, 1024), Image.LANCZOS)

            print(f"  2. Cropping upper-center 512x512 region...")
            width, height = img.size
            crop_w, crop_h = 512, 512
            left = (width - crop_w) // 2
            upper = 0
            right = left + crop_w
            lower = upper + crop_h
            cropped = img.crop((left, upper, right, lower))
            print(f"     Crop box: ({left}, {upper}, {right}, {lower})")

            print(f"  3. Converting to PNG...")
            png_buffer = io.BytesIO()
            cropped.save(png_buffer, format='PNG')
            png_bytes = png_buffer.getvalue()
            print(f"     Final size: {cropped.size}")

        # Load model
        print("\nLoading model...")
        model = _load_model()
        print("Model loaded successfully")

        # Prepare array
        with Image.open(io.BytesIO(png_bytes)) as img:
            arr = np.array(img)
            if arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=-1)
            arr = np.expand_dims(arr, axis=0)

        # Predict
        print("\nRunning inference...")
        preds = model.predict(arr)
        predicted_class = int(np.argmax(preds, axis=1)[0])

        # Show results
        print("\n" + "="*50)
        print("CLASSIFICATION RESULT")
        print("="*50)
        print(f"Predicted class: {predicted_class}")
        print(f"Endotracheal tube: {'DETECTED' if predicted_class == 0 else 'NOT DETECTED'}")

        if args.verbose:
            print("\nPrediction scores:")
            for i, score in enumerate(preds[0]):
                print(f"  Class {i}: {score:.6f}")

        sys.exit(0)

    except FileNotFoundError:
        print(f"Error: Image file not found: {args.image_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

