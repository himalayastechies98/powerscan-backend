"""
FLIR Thermal Image API
Debug-safe version for Render + Docker
"""

import os
import tempfile
import traceback
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="FLIR Thermal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/thermal")
async def extract_thermal(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(400, "Only JPG/JPEG supported")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    try:
        import flirimageextractor
        print("✅ flirimageextractor imported")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(data)
            path = tmp.name

        print("📁 Temp file:", path)

        try:
            flir = flirimageextractor.FlirImageExtractor(
                is_debug=True,
                loglevel="DEBUG"
            )

            print("🔥 Processing image...")
            flir.process_image(path)

            thermal_np = getattr(flir, "thermal_np", None)

            if thermal_np is None:
                raise HTTPException(
                    status_code=400,
                    detail="No thermal data found (NOT a radiometric FLIR image)"
                )

            print("🌡 Thermal shape:", thermal_np.shape)

            return {
                "width": int(thermal_np.shape[1]),
                "height": int(thermal_np.shape[0]),
                "minTemp": float(np.min(thermal_np)),
                "maxTemp": float(np.max(thermal_np)),
            }

        finally:
            os.remove(path)

    except HTTPException:
        raise

    except Exception as e:
        print("❌ FULL TRACEBACK BELOW")
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.get("/api/demo")
def demo():
    arr = np.random.uniform(20, 45, (240, 320))
    return {
        "width": 320,
        "height": 240,
        "minTemp": float(arr.min()),
        "maxTemp": float(arr.max()),
    }
