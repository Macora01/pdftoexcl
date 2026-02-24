# PDFtoExc - Product Requirements Document

## Problema Original
Aplicación web para convertir archivos PDF a formato XLSX con paleta de colores marrón/beige específica. Será instalada en pdftoexc.facore.cloud.

## Arquitectura
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + Python
- **Database**: MongoDB (Motor async)
- **PDF Processing**: pdfplumber + openpyxl

## User Personas
- Usuarios que necesitan convertir PDFs con tablas a Excel
- Acceso libre sin autenticación requerida

## Requisitos Core (Estáticos)
- Máximo 10MB por archivo
- Un archivo a la vez
- Vista previa antes de descargar
- Paleta de colores marrón/beige obligatoria

## Implementado (Enero 2026)
- [x] Zona drag & drop para subir PDFs
- [x] Validación de tipo de archivo (solo .pdf)
- [x] Validación de tamaño (máx 10MB)
- [x] Extracción de tablas y texto de PDFs
- [x] Vista previa de datos extraídos (hasta 100 filas)
- [x] Conversión a formato XLSX con ajuste de columnas
- [x] Descarga del archivo convertido
- [x] UI responsive con paleta marrón/beige
- [x] Indicadores de progreso
- [x] Mensajes de error en español
- [x] Toast notifications con sonner

## Endpoints API
- `GET /api/` - Health check
- `POST /api/upload` - Subir PDF y obtener preview
- `GET /api/preview/{id}` - Obtener preview de archivo
- `GET /api/download/{id}` - Descargar XLSX
- `DELETE /api/file/{id}` - Eliminar archivo

## Backlog
### P0 (Crítico) - Completado
- [x] Conversión básica PDF → XLSX

### P1 (Alta prioridad)
- [ ] Mejorar extracción de tablas complejas
- [ ] Soporte para PDFs escaneados (OCR)

### P2 (Media prioridad)
- [ ] Historial de conversiones
- [ ] Múltiples hojas por archivo
- [ ] Selección de páginas específicas

## Próximas Tareas
1. Optimizar extracción de tablas con múltiples formatos
2. Agregar OCR para PDFs escaneados
3. Implementar limpieza automática de archivos temporales
