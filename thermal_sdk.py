"""
Thermal SDK API - FLIR thermal image processing using flirimageextractor
Extracts real thermal data from FLIR JPEG images.
"""
import os
import tempfile

import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from flirimageextractor import FlirImageExtractor
from typing import Optional

router = APIRouter()


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    min_temp: Optional[float] = Query(None, description="Optional minimum temperature clamp"),
    max_temp: Optional[float] = Query(None, description="Optional maximum temperature clamp"),
):
    """
    Upload a FLIR thermal JPEG image and extract real temperature data.
    Returns temperature array + dimensions for overlay on the original image.
    """
    # 1. Basic validation
    if not file.filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Invalid file type (expected JPEG)")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    # 2. Save to temp file (cross-platform)
    temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
    try:
        with os.fdopen(temp_fd, "wb") as f:
            f.write(contents)

        # 3. Extract thermal data using FLIR SDK
        flir = FlirImageExtractor()
        try:
            flir.process_image(flir_img_file=temp_path)
            thermal_np = flir.get_thermal_np()  # 2D NumPy array of temperatures
        except Exception:
            raise HTTPException(status_code=400, detail="Thermal data extraction failed")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    # 4. Apply min/max temperature clamping if provided
    if min_temp is not None:
        thermal_np = np.clip(thermal_np, a_min=min_temp, a_max=None)
    if max_temp is not None:
        thermal_np = np.clip(thermal_np, a_min=None, a_max=max_temp)

    h, w = thermal_np.shape

    # 5. Return thermal data (frontend uses original image URL for display)
    return JSONResponse(content={
        "mode": "flir_sdk",
        "warning": None,
        "width": w,
        "height": h,
        "minTemp": round(float(np.min(thermal_np)), 2),
        "maxTemp": round(float(np.max(thermal_np)), 2),
        "temperatures": thermal_np.flatten().tolist(),
    })
