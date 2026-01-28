"""
FLIR Thermal Image API
Extracts temperature data from radiometric FLIR JPG images.
"""

import os
import tempfile
import traceback
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="FLIR Thermal Image API",
    description="Extract temperature data from radiometric FLIR images",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "running", "service": "flir-thermal-api"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/thermal")
async def extract_thermal_data(file: UploadFile = File(...)):
    """
    Extract temperature data from a FLIR radiometric JPG image.
    """

    if not file.filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(400, "Only JPG/JPEG files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file uploaded")

    try:
        import flirimageextractor

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            flir = flirimageextractor.FlirImageExtractor(palettes=[])
            flir.process_image(tmp_path)

            # ✅ Correct way (get_thermal_np is unreliable across versions)
            thermal_np = getattr(flir, "thermal_np", None)

            if thermal_np is None:
                raise HTTPException(
                    status_code=400,
                    detail="No thermal data found. Image is not radiometric FLIR."
                )

            height, width = thermal_np.shape

            return JSONResponse(content={
                "width": width,
                "height": height,
                "minTemp": round(float(np.min(thermal_np)), 2),
                "maxTemp": round(float(np.max(thermal_np)), 2),
                "temperatures": thermal_np.flatten().tolist()
            })

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except HTTPException:
        raise

    except Exception as e:
        # ✅ Print full traceback to Render logs
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/demo")
def demo_data():
    """
    Generates synthetic thermal data for frontend testing.
    """

    width, height = 320, 240

    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)

    distance = np.sqrt((xx - 0.6) ** 2 + (yy - 0.4) ** 2)

    min_temp, max_temp = 20.0, 45.0
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
