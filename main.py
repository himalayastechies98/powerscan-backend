"""
PowerScan Backend API
- Thermal image processing
- PDF report generation
"""
import io

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional

# Import from modules
from models import MeasureData, ElementData, PDFRequest
from thermal import process_thermal_upload
from pdf_generator import generate_pdf, generate_qr_code_base64, generate_html_report, html_to_pdf
from thermal_sdk import router as thermal_sdk_router


app = FastAPI(
    title="PowerScan API",
    description="Thermal image processing and PDF report generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include thermal SDK router
app.include_router(thermal_sdk_router, prefix="/api/thermal-sdk", tags=["Thermal SDK"])


# ============ HEALTH CHECK ============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============ THERMAL PROCESSING ============

@app.post("/api/thermal")
async def extract_estimated_thermal(
    file: UploadFile = File(...),
    min_temp: Optional[float] = Query(20.0, description="Minimum temperature for scale"),
    max_temp: Optional[float] = Query(None, description="Maximum temperature for scale (from temp1_c)")
):
    """
    Process a thermal image and return estimated temperature data.
    Pass max_temp from the measure's temp1_c field for accurate scaling.
    """
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(400, "Only JPG/JPEG/PNG files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file uploaded")

    try:
        result = await process_thermal_upload(content, min_temp=min_temp, max_temp=max_temp)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(500, f"Failed to process thermal image: {str(e)}")


# ============ PDF GENERATION ============

@app.post("/api/pdf/{measure_id}")
async def generate_pdf_report(measure_id: str, request: PDFRequest):
    """Generate PDF report for a measure"""
    try:
        pdf_bytes = await generate_pdf(
            measure=request.measure_data,
            elements=request.elements or [],
            thermal_image_url=request.thermal_image_url,
            optical_image_url=request.optical_image_url,
            client_company_logo_url=request.client_company_logo_url,
            language=request.language or "pt"
        )
        
        filename = f"relatorio_medida_{measure_id[:8]}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        print(f"PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to generate PDF: {str(e)}")


@app.get("/api/pdf/test")
async def test_pdf():
    """Test endpoint to generate a sample PDF"""
    sample_measure = MeasureData(
        id_unico="b74b9584-a2a4-4d93-89c7-bf9fb8f83993",
        localizacao="Rua Santo Antônio Jardim Carolina 78890-000 Sorriso",
        latitude=-12.545363,
        longitude=-55.754127,
        temp1_c=31.3,
        data_criacao=45930.85,
        alimentador="RSI_088009_201 4237",
        nome_inspecao="2025 EMT - RSI",
        vel_do_ar_na_inspecao_ms=0.9,
        umidade_relativa=27.79,
        carregamento=100
    )
    
    sample_elements = [
        ElementData(
            numero_operativo="N/A",
            elemento="(1) Árvore",
            temperatura="-",
            metodo="Absolute",
            calculada="-Infinity °C",
            acao="Pruning"
        ),
        ElementData(
            numero_operativo="N/A",
            elemento="(2) Baixa",
            temperatura="-",
            metodo="-",
            calculada="-",
            acao="-"
        ),
        ElementData(
            numero_operativo="N/A",
            elemento="(3) 7294115",
            temperatura="-",
            metodo="-",
            calculada="-",
            acao="-"
        )
    ]
    
    # Generate QR code
    qr_code_b64 = generate_qr_code_base64(f"https://powerscan.app/measure/{sample_measure.id_unico}")
    
    # Generate HTML
    html_content = generate_html_report(
        sample_measure, sample_elements,
        None, None, None, qr_code_b64
    )
    
    # Convert to PDF
    pdf_bytes = html_to_pdf(html_content)
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=test_report.pdf"
        }
    )
