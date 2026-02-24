"""
PDF generation utilities using xhtml2pdf
"""
import io
import math
import base64
from datetime import datetime, timedelta
from typing import List, Optional
import os
import httpx
import qrcode
from PIL import Image, ImageDraw

from xhtml2pdf import pisa

from models import MeasureData, ElementData

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def _load_logo_base64(filename: str) -> Optional[str]:
    """Load a logo image from assets dir and return as base64 data URI"""
    try:
        filepath = os.path.join(ASSETS_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"Error loading logo {filename}: {e}")
    return None


def excel_date_to_datetime(excel_date: float) -> Optional[datetime]:
    """Convert Excel date to Python datetime"""
    if not excel_date:
        return None
    try:
        base_date = datetime(1899, 12, 30)
        return base_date + timedelta(days=excel_date)
    except:
        return None


async def download_image_as_base64(url: str) -> Optional[str]:
    """Download image from URL and return as base64 data URI"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get('content-type', 'image/jpeg')
            b64 = base64.b64encode(response.content).decode('utf-8')
            return f"data:{content_type};base64,{b64}"
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None


def generate_qr_code_base64(data: str) -> str:
    """Generate QR code as base64 data URI"""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64}"


def _lat_lon_to_tile(lat: float, lon: float, zoom: int):
    """Convert lat/lon to tile coordinates"""
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def _draw_pin_marker(draw: ImageDraw, cx: int, cy: int, color=(239, 68, 68), size=32):
    """Draw a pin marker at the given pixel coordinates"""
    # Pin body (teardrop shape using ellipse + polygon)
    pin_top = cy - size
    pin_bottom = cy
    pin_w = size // 2
    
    # Draw shadow
    shadow_offset = 2
    draw.ellipse(
        [cx - pin_w + shadow_offset, pin_top + shadow_offset, 
         cx + pin_w + shadow_offset, pin_top + size * 2 // 3 + shadow_offset],
        fill=(0, 0, 0, 60)
    )
    
    # Draw pin body (circle top)
    draw.ellipse(
        [cx - pin_w, pin_top, cx + pin_w, pin_top + size * 2 // 3],
        fill=color, outline=(255, 255, 255), width=2
    )
    
    # Draw pin point (triangle)
    draw.polygon(
        [(cx - pin_w // 2, pin_top + size // 3),
         (cx, pin_bottom),
         (cx + pin_w // 2, pin_top + size // 3)],
        fill=color
    )
    
    # Draw white circle inside
    inner_r = size // 5
    draw.ellipse(
        [cx - inner_r, pin_top + size // 6, cx + inner_r, pin_top + size // 6 + inner_r * 2],
        fill=(255, 255, 255, 230)
    )
    
    # Draw colored dot inside the white circle
    dot_r = size // 8
    draw.ellipse(
        [cx - dot_r, pin_top + size // 6 + (inner_r - dot_r),
         cx + dot_r, pin_top + size // 6 + (inner_r + dot_r)],
        fill=color
    )


async def generate_static_map_base64(lat: float, lon: float, zoom: int = 17, 
                                       width: int = 400, height: int = 400,
                                       pin_color=(239, 68, 68)) -> Optional[str]:
    """Generate a static map image with a pin marker using OSM tiles + Pillow"""
    try:
        tile_size = 256
        
        # Calculate center tile coordinates
        center_x, center_y = _lat_lon_to_tile(lat, lon, zoom)
        
        # Calculate how many tiles we need
        tiles_x = math.ceil(width / tile_size) + 1
        tiles_y = math.ceil(height / tile_size) + 1
        
        # Starting tile indices
        start_tile_x = int(center_x) - tiles_x // 2
        start_tile_y = int(center_y) - tiles_y // 2
        
        # Create the composite image
        composite_w = tiles_x * tile_size
        composite_h = tiles_y * tile_size
        composite = Image.new('RGBA', (composite_w, composite_h), (240, 240, 240, 255))
        
        # Download tiles
        async with httpx.AsyncClient(timeout=15.0) as client:
            for tx in range(tiles_x):
                for ty in range(tiles_y):
                    tile_x = start_tile_x + tx
                    tile_y = start_tile_y + ty
                    
                    # Wrap tile coordinates
                    n = 2 ** zoom
                    tile_x = tile_x % n
                    if tile_y < 0 or tile_y >= n:
                        continue
                    
                    url = f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"
                    try:
                        resp = await client.get(url, headers={
                            "User-Agent": "PowerScan/1.0 (PDF Report Generator)"
                        })
                        if resp.status_code == 200:
                            tile_img = Image.open(io.BytesIO(resp.content)).convert('RGBA')
                            composite.paste(tile_img, (tx * tile_size, ty * tile_size))
                    except:
                        pass  # Skip failed tiles, background will show
        
        # Calculate pixel position of the center point within the composite
        pixel_x = int((center_x - start_tile_x) * tile_size)
        pixel_y = int((center_y - start_tile_y) * tile_size)
        
        # Crop to desired size, centered on the target point
        left = pixel_x - width // 2
        top = pixel_y - height // 2
        right = left + width
        bottom = top + height
        
        cropped = composite.crop((left, top, right, bottom))
        
        # Draw pin marker at center
        draw = ImageDraw.Draw(cropped, 'RGBA')
        _draw_pin_marker(draw, width // 2, height // 2, color=pin_color, size=36)
        
        # Convert to PNG base64
        img_buffer = io.BytesIO()
        cropped.save(img_buffer, format='PNG', quality=90)
        img_buffer.seek(0)
        b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"Error generating static map: {e}")
        return None



# PDF translations for all supported languages
PDF_TRANSLATIONS = {
    "pt": {
        "report_title": "Relatório de Inspeção Termográfica",
        "measure": "Medida",
        "detected_feeders": "Alimentadores Detectados",
        "date_time": "Data e Hora",
        "address": "Endereço",
        "inspection_name": "Nome Inspeção",
        "feeder": "Alimentador",
        "coordinates": "Coordenadas",
        "temperature": "Temperatura",
        "relative_humidity": "Umidade Relativa",
        "load": "Carregamento",
        "wind": "Vento",
        "op_number": "Número Operativo",
        "element": "Elemento",
        "method": "Método",
        "calculated": "Calculada",
        "action": "Ação",
        "no_elements": "Sem dados de elementos",
    },
    "en": {
        "report_title": "Thermographic Inspection Report",
        "measure": "Measure",
        "detected_feeders": "Detected Feeders",
        "date_time": "Date & Time",
        "address": "Address",
        "inspection_name": "Inspection Name",
        "feeder": "Feeder",
        "coordinates": "Coordinates",
        "temperature": "Temperature",
        "relative_humidity": "Relative Humidity",
        "load": "Load",
        "wind": "Wind",
        "op_number": "Operative Number",
        "element": "Element",
        "method": "Method",
        "calculated": "Calculated",
        "action": "Action",
        "no_elements": "No elements data",
    },
    "es": {
        "report_title": "Informe de Inspección Termográfica",
        "measure": "Medida",
        "detected_feeders": "Alimentadores Detectados",
        "date_time": "Fecha y Hora",
        "address": "Dirección",
        "inspection_name": "Nombre de Inspección",
        "feeder": "Alimentador",
        "coordinates": "Coordenadas",
        "temperature": "Temperatura",
        "relative_humidity": "Humedad Relativa",
        "load": "Carga",
        "wind": "Viento",
        "op_number": "Número Operativo",
        "element": "Elemento",
        "method": "Método",
        "calculated": "Calculada",
        "action": "Acción",
        "no_elements": "Sin datos de elementos",
    },
}


def generate_html_report(
    measure: MeasureData, 
    elements: List[ElementData], 
    thermal_img_b64: Optional[str], 
    optical_img_b64: Optional[str],
    map_img_b64: Optional[str], 
    qr_code_b64: Optional[str],
    client_logo_b64: Optional[str] = None,
    language: str = "pt"
) -> str:
    """Generate HTML for the PDF report matching the exact design"""
    
    # Get translations for the requested language (fallback to Portuguese)
    t = PDF_TRANSLATIONS.get(language, PDF_TRANSLATIONS["pt"])
    
    # Load PowerScan logo (always used on right side)
    powerscan_logo_b64 = _load_logo_base64("powerscan_logo.png")
    
    # Right side: always PowerScan logo (fixed)
    powerscan_logo_img = f'<img src="{powerscan_logo_b64}" class="logo-img-right" />' if powerscan_logo_b64 else '<span style="font-size:14pt;font-weight:bold;color:#7C3AED;">⚡PowerScan</span>'
    
    # Left side: client company logo if available, otherwise PowerScan logo
    if client_logo_b64:
        left_logo_img = f'<img src="{client_logo_b64}" class="logo-img-left" />'
    elif powerscan_logo_b64:
        left_logo_img = f'<img src="{powerscan_logo_b64}" class="logo-img-left" />'
    else:
        left_logo_img = '<span style="font-size:14pt;font-weight:bold;color:#7C3AED;">⚡PowerScan</span>'
    
    
    # Format date
    date_str = "-"
    if measure.data_criacao:
        dt = excel_date_to_datetime(measure.data_criacao)
        if dt:
            date_str = dt.strftime("%d/%m/%Y %H:%M:%S")
    
    # Format coordinates
    coords = "-"
    if measure.latitude and measure.longitude:
        coords = f"{measure.latitude}, {measure.longitude}"
    
    # Format temperature
    temp = f"{measure.temp1_c:.1f}°C" if measure.temp1_c else "-"
    
    # Format humidity
    humidity = f"{measure.umidade_relativa:.2f}%" if measure.umidade_relativa else "-"
    
    # Format wind
    wind = f"{measure.vel_do_ar_na_inspecao_ms}m/s" if measure.vel_do_ar_na_inspecao_ms else "-"
    
    # Format load
    load = f"{measure.carregamento:.0f}%" if measure.carregamento else "100%"
    
    # Build elements table rows
    elements_rows = ""
    for elem in elements:
        # Determine action color based on content
        action_class = "action-green" if elem.acao and elem.acao != "-" else ""
        elements_rows += f"""
        <tr>
            <td>{elem.numero_operativo or 'N/A'}</td>
            <td>{elem.elemento or '-'}</td>
            <td>{elem.temperatura or '-'}</td>
            <td class="method">{elem.metodo or '-'}</td>
            <td>{elem.calculada or '-'}</td>
            <td class="{action_class}">{elem.acao or '-'}</td>
        </tr>
        """
    
    # Default placeholder images if not available
    thermal_img = f'<img src="{thermal_img_b64}" />' if thermal_img_b64 else '<div class="placeholder thermal"></div>'
    optical_img = f'<img src="{optical_img_b64}" />' if optical_img_b64 else '<div class="placeholder optical"></div>'
    map_img = f'<img src="{map_img_b64}" />' if map_img_b64 else '<div class="placeholder map">Map unavailable</div>'
    qr_img = f'<img src="{qr_code_b64}" />' if qr_code_b64 else '<div class="placeholder">QR Code</div>'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 12mm 15mm;
            }}
            
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            
            body {{
                font-family: Arial, Helvetica, sans-serif;
                font-size: 9pt;
                color: #333;
                line-height: 1.3;
            }}
            
            .page {{
                page-break-after: always;
            }}
            
            .page:last-child {{
                page-break-after: avoid;
            }}
            
            /* Header Table Layout */
            .header-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 8px;
            }}
            
            .header-table td {{
                vertical-align: middle;
                padding: 5px 0;
            }}
            
            .logo-img-left {{
                height: 40px;
                width: auto;
            }}
            
            .logo-img-right {{
                height: 40px;
                width: auto;
            }}
            
            .header-title {{
                font-size: 14pt;
                font-weight: normal;
                color: #333;
                text-align: center;
            }}
            
            .logo-right-cell {{
                text-align: right;
            }}
            
            /* Info Section using Tables */
            .info-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 8px;
            }}
            
            .info-table td {{
                vertical-align: top;
                padding: 3px 5px 3px 0;
            }}
            
            .info-label {{
                font-weight: bold;
                font-size: 9pt;
                color: #333;
                margin-bottom: 2px;
            }}
            
            .info-value {{
                font-size: 9pt;
                color: #555;
            }}
            
            .info-value.link {{
                color: #2563EB;
                text-decoration: underline;
                font-size: 8pt;
            }}
            
            /* Images Section */
            .images-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            
            .images-table td {{
                width: 50%;
                padding: 0 5px;
                vertical-align: top;
            }}
            
            .images-table td:first-child {{
                padding-left: 0;
            }}
            
            .images-table td:last-child {{
                padding-right: 0;
            }}
            
            .images-table img {{
                width: 100%;
                max-height: 200px;
                height: auto;
                object-fit: contain;
                border: 1px solid #e5e7eb;
                background: #f9f9f9;
            }}
            
            .placeholder {{
                width: 100%;
                height: 180px;
                background: #f0f0f0;
                border: 1px solid #e5e7eb;
            }}
            
            .placeholder.thermal {{
                background: linear-gradient(to right, #1e3a8a, #7c3aed, #dc2626, #fbbf24);
            }}
            
            .placeholder.optical {{
                background: #87CEEB;
            }}
            
            /* Elements Table */
            .elements-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            
            .elements-table th {{
                font-weight: bold;
                font-size: 8pt;
                text-align: left;
                padding: 8px 5px;
                border-bottom: 1px solid #ccc;
                color: #333;
            }}
            
            .elements-table td {{
                font-size: 8pt;
                padding: 6px 5px;
                border-bottom: 1px solid #eee;
                color: #555;
            }}
            
            .elements-table td.method {{
                color: #2563EB;
            }}
            
            .elements-table td.action-green {{
                color: #16a34a;
            }}
            
            /* Page 2 */
            .page2-content {{
                margin-top: 60px;
            }}
            
            .page2-table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            .page2-table td {{
                width: 50%;
                vertical-align: middle;
                padding: 10px 20px;
            }}
            
            .page2-table img {{
                max-width: 100%;
                height: auto;
            }}
            
            .map-cell {{
                text-align: center;
            }}
            
            .map-cell img {{
                max-width: 280px;
                border: 1px solid #e5e7eb;
            }}
            
            .qr-cell {{
                text-align: center;
            }}
            
            .qr-cell img {{
                max-width: 250px;
            }}
        </style>
    </head>
    <body>
        <!-- Page 1 -->
        <div class="page">
            <!-- Header -->
            <table class="header-table">
                <tr>
                    <td style="width: 20%;">
                        {left_logo_img}
                    </td>
                    <td style="width: 60%;">
                        <div class="header-title">{t['report_title']}</div>
                    </td>
                    <td style="width: 20%;" class="logo-right-cell">
                        {powerscan_logo_img}
                    </td>
                </tr>
            </table>
            
            <!-- Info Row 1: Medida, Alimentadores Detectados, Data e Hora -->
            <table class="info-table">
                <tr>
                    <td style="width: 30%;">
                        <div class="info-label">{t['measure']}</div>
                        <div class="info-value link">{measure.id_unico}</div>
                    </td>
                    <td style="width: 40%;">
                        <div class="info-label">{t['detected_feeders']}</div>
                        <div class="info-value">{measure.alimentador or '-'}</div>
                    </td>
                    <td style="width: 30%;">
                        <div class="info-label">{t['date_time']}</div>
                        <div class="info-value">{date_str}</div>
                    </td>
                </tr>
            </table>
            
            <!-- Info Row 2: Endereço, Nome Inspeção, Alimentador -->
            <table class="info-table">
                <tr>
                    <td style="width: 40%;">
                        <div class="info-label">{t['address']}</div>
                        <div class="info-value">{measure.localizacao or '-'}</div>
                    </td>
                    <td style="width: 30%;">
                        <div class="info-label">{t['inspection_name']}</div>
                        <div class="info-value">{measure.nome_inspecao or '-'}</div>
                    </td>
                    <td style="width: 30%;">
                        <div class="info-label">{t['feeder']}</div>
                        <div class="info-value">{measure.alimentador or '-'}</div>
                    </td>
                </tr>
            </table>
            
            <!-- Info Row 3: Coordenadas, Temperatura, Umidade, Carregamento, Vento -->
            <table class="info-table">
                <tr>
                    <td style="width: 25%;">
                        <div class="info-label">{t['coordinates']}</div>
                        <div class="info-value">{coords}</div>
                    </td>
                    <td style="width: 15%;">
                        <div class="info-label">{t['temperature']}</div>
                        <div class="info-value">{temp}</div>
                    </td>
                    <td style="width: 20%;">
                        <div class="info-label">{t['relative_humidity']}</div>
                        <div class="info-value">{humidity}</div>
                    </td>
                    <td style="width: 20%;">
                        <div class="info-label">{t['load']}</div>
                        <div class="info-value">{load}</div>
                    </td>
                    <td style="width: 20%;">
                        <div class="info-label">{t['wind']}</div>
                        <div class="info-value">{wind}</div>
                    </td>
                </tr>
            </table>
            
            <!-- Images -->
            <table class="images-table">
                <tr>
                    <td>{thermal_img}</td>
                    <td>{optical_img}</td>
                </tr>
            </table>
            
            <!-- Elements Table -->
            <table class="elements-table">
                <thead>
                    <tr>
                        <th>{t['op_number']}</th>
                        <th>{t['element']}</th>
                        <th>{t['temperature']}</th>
                        <th>{t['method']}</th>
                        <th>{t['calculated']}</th>
                        <th>{t['action']}</th>
                    </tr>
                </thead>
                <tbody>
                    {elements_rows if elements_rows else f'<tr><td colspan="6" style="text-align:center;color:#999;">{t["no_elements"]}</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <!-- Page 2 -->
        <div class="page">
            <!-- Header -->
            <table class="header-table">
                <tr>
                    <td style="width: 20%;">
                        {left_logo_img}
                    </td>
                    <td style="width: 60%;">
                        <div class="header-title">{t['report_title']}</div>
                    </td>
                    <td style="width: 20%;" class="logo-right-cell">
                        {powerscan_logo_img}
                    </td>
                </tr>
            </table>
            
            <div class="page2-content">
                <table class="page2-table">
                    <tr>
                        <td class="map-cell">
                            {map_img}
                        </td>
                        <td class="qr-cell">
                            {qr_img}
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def html_to_pdf(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using xhtml2pdf"""
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)
    if pisa_status.err:
        raise Exception("PDF generation failed")
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


async def generate_pdf(
    measure: MeasureData,
    elements: List[ElementData],
    thermal_image_url: Optional[str] = None,
    optical_image_url: Optional[str] = None,
    client_company_logo_url: Optional[str] = None,
    language: str = "pt"
) -> bytes:
    """
    Generate a complete PDF report for a measure.
    
    Args:
        measure: The measure data
        elements: List of element data for the table
        thermal_image_url: URL to the thermal image
        optical_image_url: URL to the optical image
        client_company_logo_url: URL to the client company logo
        language: Language code for PDF labels (en, es, pt)
    
    Returns:
        PDF file as bytes
    """
    # Download images as base64
    thermal_img_b64 = await download_image_as_base64(thermal_image_url) if thermal_image_url else None
    optical_img_b64 = await download_image_as_base64(optical_image_url) if optical_image_url else None
    
    # Download client company logo if available
    client_logo_b64 = await download_image_as_base64(client_company_logo_url) if client_company_logo_url else None
    
    # Generate map image with pin marker
    map_img_b64 = None
    if measure.latitude and measure.longitude:
        pin_color = (239, 68, 68) if measure.temp1_c else (59, 130, 246)
        map_img_b64 = await generate_static_map_base64(
            measure.latitude, measure.longitude, pin_color=pin_color
        )
    
    # Generate QR code - links to Google Maps at the exact coordinates
    if measure.latitude and measure.longitude:
        qr_data = f"https://www.google.com/maps?q={measure.latitude},{measure.longitude}"
    else:
        # Fallback to PowerScan app link if no coordinates
        qr_data = f"https://powerscan.app/measure/{measure.id_unico}"
    qr_code_b64 = generate_qr_code_base64(qr_data)
    
    # Generate HTML
    html_content = generate_html_report(
        measure, elements,
        thermal_img_b64, optical_img_b64,
        map_img_b64, qr_code_b64,
        client_logo_b64,
        language
    )
    
    # Convert to PDF
    return html_to_pdf(html_content)
