import tempfile
import numpy as np
from PIL import Image

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Thermal Estimation API",
    description="Estimate relative temperature data from any thermal-like image",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def estimate_temperature_from_image(
    image_path: str,
    min_temp: float = 20.0,
    max_temp: float = 45.0
):
    """
    Estimate relative temperature from image brightness.
    NOT real temperature.
    """
    img = Image.open(image_path).convert("L")  # grayscale
    gray = np.array(img).astype(np.float32)

    norm = (gray - gray.min()) / (gray.max() - gray.min() + 1e-6)
    thermal = min_temp + norm * (max_temp - min_temp)

    return thermal


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/thermal")
async def extract_estimated_thermal(file: UploadFile = File(...)):

    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(400, "Only JPG/JPEG/PNG files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file uploaded")

    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        thermal_np = estimate_temperature_from_image(tmp_path)

        h, w = thermal_np.shape

        return JSONResponse({
            "mode": "estimated",
            "warning": "Temperatures are relative, not absolute",
            "width": w,
            "height": h,
            "minTemp": round(float(np.min(thermal_np)), 2),
            "maxTemp": round(float(np.max(thermal_np)), 2),
            "temperatures": thermal_np.flatten().tolist()
        })

    finally:
        if tmp_path:
            try:
                import os
                os.remove(tmp_path)
            except Exception:
                pass
