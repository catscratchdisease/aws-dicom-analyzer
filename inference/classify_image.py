"""Classifier wrapper for the saved Keras model.

This module exposes classify_png_bytes(png_bytes) -> int.
It lazily loads the Keras model from ../models/20250713_ett_model_30epochs_resnet_cropped.keras.

Note: TensorFlow and the model file must be available in the Lambda environment (layer or bundled).
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
    model_path = '../models/20250713_ett_model_30epochs_resnet_cropped.keras'
    _model = keras.models.load_model(model_path)
    return _model


def classify_png_bytes(png_bytes):
    """Classify an image provided as PNG bytes. Returns predicted class as int.

    Preprocessing mirrors the original script: resize to 512x512 and ensure 3 channels.
    """
    try:
        model = _load_model()
    except Exception:
        # Re-raise to let callers handle fallback
        raise

    with Image.open(io.BytesIO(png_bytes)) as img:
        img = img.resize((512, 512))
        arr = np.array(img)

        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)

        arr = np.expand_dims(arr, axis=0)

        preds = model.predict(arr)
        predicted_class = int(np.argmax(preds, axis=1)[0])
        return predicted_class

