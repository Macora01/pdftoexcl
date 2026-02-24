from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
import uuid
from datetime import datetime, timezone
import pdfplumber
from openpyxl import Workbook
import aiofiles
import shutil

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'pdftoexc')]

# Create temp directories
UPLOAD_DIR = ROOT_DIR / "uploads"
OUTPUT_DIR = ROOT_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Frontend build path
FRONTEND_DIR = ROOT_DIR.parent / "frontend" / "build"

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class ConversionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str
    status: str = "pending"
    preview_data: Optional[List[List[Any]]] = None
    total_rows: int = 0
    total_pages: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PreviewResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    preview_data: List[List[Any]]
    total_rows: int
    total_pages: int

class UploadResponse(BaseModel):
    id: str
    message: str
    status: str

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
                        # Clean None values and strip whitespace
                        cleaned_row = [
                            str(cell).strip() if cell is not None else ""
                            for cell in row
                        ]
                        all_rows.append(cleaned_row)
            else:
                # If no tables, try to extract text as single column
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
    
    # Auto-adjust column widths
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

@api_router.get("/")
async def root():
    return {"message": "PDF to XLSX Converter API"}

@api_router.post("/upload", response_model=PreviewResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and get preview data"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")
    
    # Generate unique ID
    file_id = str(uuid.uuid4())
    
    # Save uploaded file
    pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
    async with aiofiles.open(pdf_path, 'wb') as f:
        await f.write(content)
    
    try:
        # Extract data from PDF
        data, total_rows, total_pages = extract_tables_from_pdf(str(pdf_path))
        
        if not data:
            raise HTTPException(status_code=400, detail="No se encontraron datos en el PDF")
        
        # Create preview (first 100 rows)
        preview_data = data[:100]
        
        # Save record to MongoDB
        record = ConversionRecord(
            id=file_id,
            original_filename=file.filename,
            status="ready",
            preview_data=data,  # Store all data for later conversion
            total_rows=total_rows,
            total_pages=total_pages
        )
        
        doc = record.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.conversions.insert_one(doc)
        
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
    
    record = await db.conversions.find_one({"id": file_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Return only first 100 rows for preview
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
    
    record = await db.conversions.find_one({"id": file_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    data = record.get('preview_data', [])
    if not data:
        raise HTTPException(status_code=400, detail="No hay datos para convertir")
    
    # Create XLSX file
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
    
    # Delete from database
    await db.conversions.delete_one({"id": file_id})
    
    # Delete files
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
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
