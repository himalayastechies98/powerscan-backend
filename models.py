"""
Data models for the PowerScan API
"""
from pydantic import BaseModel
from typing import Optional, List


class MeasureData(BaseModel):
    """Measure data for PDF generation"""
    id_unico: str
    inspection_id: Optional[str] = None
    registro_num: Optional[int] = None
    localizacao: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    temp1_c: Optional[float] = None
    data_criacao: Optional[float] = None  # Excel date format
    alimentador: Optional[str] = None
    inspetor: Optional[str] = None
    regional: Optional[str] = None
    severidade: Optional[str] = None
    observations: Optional[str] = None
    vel_do_ar_na_inspecao_ms: Optional[float] = None
    umidade_relativa: Optional[float] = None
    carregamento: Optional[float] = None
    nome_inspecao: Optional[str] = None


class ElementData(BaseModel):
    """Element data for the elements table"""
    numero_operativo: Optional[str] = None
    elemento: Optional[str] = None
    temperatura: Optional[str] = None
    metodo: Optional[str] = None
    calculada: Optional[str] = None
    acao: Optional[str] = None


class PDFRequest(BaseModel):
    """Request body for PDF generation"""
    measure_data: MeasureData
    thermal_image_url: Optional[str] = None
    optical_image_url: Optional[str] = None
    client_company_logo_url: Optional[str] = None
    language: Optional[str] = "pt"
    elements: Optional[List[ElementData]] = []
