"""
FLIR Thermal Image API
Extracts temperature data from radiometric FLIR JPG images.
"""

import os
import tempfile
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="FLIR Thermal Image API",
    description="Extract temperature data from radiometric FLIR images",
    version="1.0.0"
)

# Enable CORS (safe for frontend usage)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "flir-thermal-api"
    }


@app.post("/api/thermal")
async def extract_thermal_data(file: UploadFile = File(...)):
    """
    Extract temperature data from a FLIR radiometric JPG image.
    """
    if not file.filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(
            status_code=400,
            detail="Only JPG/JPEG files are supported"
        )

    try:
        import flirimageextractor

        content = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            flir = flirimageextractor.FlirImageExtractor(palettes=[])
            flir.process_image(tmp_path)

            thermal_np = flir.get_thermal_np()

            if thermal_np is None:
                raise HTTPException(
                    status_code=400,
                    detail="Image is not a radiometric FLIR image"
                )

            height, width = thermal_np.shape
            min_temp = float(np.min(thermal_np))
            max_temp = float(np.max(thermal_np))

            return JSONResponse(content={
                "width": width,
                "height": height,
                "minTemp": round(min_temp, 2),
                "maxTemp": round(max_temp, 2),
                "temperatures": thermal_np.flatten().tolist()
            })

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="flirimageextractor not installed"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image: {str(e)}"
        )


@app.get("/api/demo")
async def demo_data():
    """
    Generates synthetic thermal data for frontend testing.
    """
    width = 320
    height = 240

    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)

    center_x, center_y = 0.6, 0.4
    distance = np.sqrt((xx - center_x) ** 2 + (yy - center_y) ** 2)

    min_temp = 20.0
    max_temp = 45.0

    thermal = max_temp - (distance * (max_temp - min_temp) * 1.5)
    thermal = np.clip(thermal, min_temp, max_temp)

    noise = np.random.normal(0, 0.5, (height, width))
    thermal = np.clip(thermal + noise, min_temp, max_temp)

    return JSONResponse(content={
        "width": width,
        "height": height,
        "minTemp": round(float(np.min(thermal)), 2),
        "maxTemp": round(float(np.max(thermal)), 2),
        "temperatures": thermal.flatten().tolist()
    })
