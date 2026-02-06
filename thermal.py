"""
Thermal image processing utilities
"""
import tempfile
import os
import numpy as np
from PIL import Image as PILImage


def estimate_temperature_from_image(
    image_path: str,
    min_temp: float = 20.0,
    max_temp: float = 45.0
) -> np.ndarray:
    """
    Estimate relative temperature from image brightness.
    NOT real temperature - this is a visual approximation.
    
    Args:
        image_path: Path to the thermal image
        min_temp: Minimum temperature in the scale
        max_temp: Maximum temperature in the scale
    
    Returns:
        2D numpy array of estimated temperatures
    """
    img = PILImage.open(image_path).convert("L")  # grayscale
    gray = np.array(img).astype(np.float32)

    norm = (gray - gray.min()) / (gray.max() - gray.min() + 1e-6)
    thermal = min_temp + norm * (max_temp - min_temp)

    return thermal


async def process_thermal_upload(content: bytes) -> dict:
    """
    Process uploaded thermal image and return temperature data.
    
    Args:
        content: Raw bytes of the uploaded image
    
    Returns:
        Dictionary with thermal data
    """
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        thermal_np = estimate_temperature_from_image(tmp_path)
        h, w = thermal_np.shape

        return {
            "mode": "estimated",
            "warning": "Temperatures are relative, not absolute",
            "width": w,
            "height": h,
            "minTemp": round(float(np.min(thermal_np)), 2),
            "maxTemp": round(float(np.max(thermal_np)), 2),
            "temperatures": thermal_np.flatten().tolist()
        }

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
