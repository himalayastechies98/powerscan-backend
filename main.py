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
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    if not file.filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(400, "Only JPG/JPEG files are supported")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file uploaded")

    try:
        import flirimageextractor

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            flir = flirimageextractor.FlirImageExtractor(is_debug=False)
            flir.process_image(tmp_path)

            # Correct & version-safe access
            thermal_np = getattr(flir, "thermal_np", None)

            if thermal_np is None:
                raise HTTPException(
                    status_code=400,
                    detail="No thermal data found. Image is not a radiometric FLIR JPG."
                )

            return JSONResponse(content={
                "width": int(thermal_np.shape[1]),
                "height": int(thermal_np.shape[0]),
                "minTemp": round(float(np.min(thermal_np)), 2),
                "maxTemp": round(float(np.max(thermal_np)), 2),
                "temperatures": thermal_np.flatten().tolist()
            })

        finally:
            os.remove(tmp_path)

    except HTTPException:
        raise

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/demo")
def demo_data():
    width, height = 320, 240
    thermal = np.random.uniform(20, 45, (height, width))

    return JSONResponse(content={
        "width": width,
        "height": height,
        "minTemp": round(float(np.min(thermal)), 2),
        "maxTemp": round(float(np.max(thermal)), 2),
        "temperatures": thermal.flatten().tolist()
    })
