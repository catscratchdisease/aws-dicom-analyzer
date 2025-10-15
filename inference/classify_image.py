import tensorflow as tf
from tensorflow import keras
import numpy as np
from PIL import Image
import sys

# 1. Load the saved model
model = keras.models.load_model('../models/20250713_ett_model_30epochs_resnet_cropped.keras')

# 2. Load and preprocess the image
img = Image.open(sys.argv[1]).resize((512,512))  # adjust size as needed
img_array = np.array(img)

# If grayscale, convert to RGB by stacking channels
if img_array.ndim == 2:
    img_array = np.stack([img_array]*3, axis=-1)

# Add batch dimension
img_array = np.expand_dims(img_array, axis=0)  # shape: (1, 512, 512, 3)

# 3. Predict the class
predictions = model.predict(img_array)
predicted_class = np.argmax(predictions, axis=1)[0]

print(f"Predicted class: {predicted_class}")
