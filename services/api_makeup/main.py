import os
import sys
import cv2
import numpy as np
from PIL import Image
import io
import uuid

# Add virtual_makeup to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from virtual_makeup.makeup_applier_cv import MakeupApplierCV
from virtual_makeup.demo_responses import prepare_makeup_response

# Global instance to avoid reloading model
_applier = None

def get_applier():
    global _applier
    if _applier is None:
        _applier = MakeupApplierCV()
    return _applier

def apply_makeup_service(image_bytes: bytes, personal_color: str) -> bytes:
    """
    Apply makeup to the image based on personal color.
    Returns the processed image as bytes (JPEG).
    """
    applier = get_applier()
    
    # Convert bytes to numpy array (OpenCV format)
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError("Failed to decode image")

    # Prepare makeup response based on personal color
    makeup_response = prepare_makeup_response(personal_color)
    
    # Apply makeup
    # apply_makeup expects RGB for PIL or BGR for OpenCV if path is not string?
    # The apply_makeup method in MakeupApplierCV handles path or array.
    # If array, it expects RGB if it converts to BGR? 
    # Let's check makeup_applier_cv.py again.
    # It says: image = cv2.cvtColor(np.array(image_path), cv2.COLOR_RGB2BGR) if not string.
    # So if we pass a numpy array, it assumes it's RGB and converts to BGR.
    # But cv2.imdecode returns BGR.
    # So we should convert BGR to RGB before passing it, or modify how we pass it.
    
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # The apply_makeup method returns a PIL Image
    result_pil = applier.apply_makeup(image_rgb, makeup_response)
    
    # Convert PIL Image back to bytes
    img_byte_arr = io.BytesIO()
    result_pil.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()
