from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Any
import uuid
from datetime import datetime, timezone
import pdfplumber
from openpyxl import Workbook
import aiofiles
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create temp directories
UPLOAD_DIR = ROOT_DIR / "uploads"
OUTPUT_DIR = ROOT_DIR / "outputs"
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Frontend build path
FRONTEND_DIR = ROOT_DIR.parent / "frontend" / "build"

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class PreviewResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    preview_data: List[List[Any]]
    total_rows: int
    total_pages: int

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

def extract_tables_from_pdf(pdf_path: str) -> tuple[List[List[Any]], int, int]:
    """Extract all tables from a PDF file"""
    all_rows = []
    total_pages = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        for page in pdf.pages:
            tables = page.extract_tables()
            
            if tables:
                for table in tables:
                    for row in table:
                        cleaned_row = [
                            str(cell).strip() if cell is not None else ""
                            for cell in row
                        ]
                        all_rows.append(cleaned_row)
            else:
                text = page.extract_text()
                if text:
                    lines = text.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            all_rows.append([line.strip()])
    
    return all_rows, len(all_rows), total_pages

def create_xlsx_from_data(data: List[List[Any]], output_path: str) -> None:
    """Create an XLSX file from extracted data"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Converted Data"
    
    for row_idx, row in enumerate(data, 1):
        for col_idx, cell_value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=cell_value)
    
    for column_cells in ws.columns:
        max_length = 0
        column = column_cells[0].column_letter
        for cell in column_cells:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    wb.save(output_path)

def save_record(file_id: str, data: dict):
    """Save record to JSON file"""
    file_path = DATA_DIR / f"{file_id}.json"
    with open(file_path, 'w') as f:
        json.dump(data, f)

def load_record(file_id: str) -> dict:
    """Load record from JSON file"""
    file_path = DATA_DIR / f"{file_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, 'r') as f:
        return json.load(f)

def delete_record(file_id: str):
    """Delete record JSON file"""
    file_path = DATA_DIR / f"{file_id}.json"
    if file_path.exists():
        file_path.unlink()

@api_router.get("/")
async def root():
    return {"message": "PDF to XLSX Converter API"}

@api_router.post("/upload", response_model=PreviewResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and get preview data"""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")
    
    file_id = str(uuid.uuid4())
    
    pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
    async with aiofiles.open(pdf_path, 'wb') as f:
        await f.write(content)
    
    try:
        data, total_rows, total_pages = extract_tables_from_pdf(str(pdf_path))
        
        if not data:
            raise HTTPException(status_code=400, detail="No se encontraron datos en el PDF")
        
        preview_data = data[:100]
        
        record = {
            "id": file_id,
            "original_filename": file.filename,
            "status": "ready",
            "preview_data": data,
            "total_rows": total_rows,
            "total_pages": total_pages
        }
        save_record(file_id, record)
        
        return PreviewResponse(
            id=file_id,
            original_filename=file.filename,
            status="ready",
            preview_data=preview_data,
            total_rows=total_rows,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando el PDF: {str(e)}")

@api_router.get("/preview/{file_id}", response_model=PreviewResponse)
async def get_preview(file_id: str):
    """Get preview data for a previously uploaded file"""
    
    record = load_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    preview_data = record.get('preview_data', [])[:100]
    
    return PreviewResponse(
        id=record['id'],
        original_filename=record['original_filename'],
        status=record['status'],
        preview_data=preview_data,
        total_rows=record['total_rows'],
        total_pages=record['total_pages']
    )

@api_router.get("/download/{file_id}")
async def download_xlsx(file_id: str):
    """Convert and download the XLSX file"""
    
    record = load_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    data = record.get('preview_data', [])
    if not data:
        raise HTTPException(status_code=400, detail="No hay datos para convertir")
    
    xlsx_filename = record['original_filename'].rsplit('.', 1)[0] + '.xlsx'
    xlsx_path = OUTPUT_DIR / f"{file_id}.xlsx"
    
    try:
        create_xlsx_from_data(data, str(xlsx_path))
        
        return FileResponse(
            path=str(xlsx_path),
            filename=xlsx_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logging.error(f"Error creating XLSX: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando el archivo Excel: {str(e)}")

@api_router.delete("/file/{file_id}")
async def delete_file(file_id: str):
    """Delete uploaded and converted files"""
    
    delete_record(file_id)
    
    pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
    xlsx_path = OUTPUT_DIR / f"{file_id}.xlsx"
    
    if pdf_path.exists():
        pdf_path.unlink()
    if xlsx_path.exists():
        xlsx_path.unlink()
    
    return {"message": "Archivo eliminado correctamente"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from frontend build
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend not found"}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
