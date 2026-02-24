import { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "sonner";
import { 
  FileSpreadsheet, 
  Upload, 
  Download, 
  Loader2, 
  X, 
  CheckCircle, 
  AlertCircle,
  FileText,
  Trash2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Max file size: 10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024;

function App() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewData, setPreviewData] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);

  const resetState = useCallback(() => {
    setFile(null);
    setPreviewData(null);
    setFileInfo(null);
    setUploadProgress(0);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  }, []);

  const validateAndSetFile = (selectedFile) => {
    // Check if it's a PDF
    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      toast.error("Solo se permiten archivos PDF", {
        description: "Por favor selecciona un archivo con extensión .pdf"
      });
      return;
    }

    // Check file size
    if (selectedFile.size > MAX_FILE_SIZE) {
      toast.error("Archivo demasiado grande", {
        description: "El tamaño máximo permitido es 10MB"
      });
      return;
    }

    setFile(selectedFile);
    setPreviewData(null);
    setFileInfo(null);
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  const uploadFile = async () => {
    if (!file) return;

    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(progress);
        },
      });

      setFileInfo({
        id: response.data.id,
        originalFilename: response.data.original_filename,
        status: response.data.status,
        totalRows: response.data.total_rows,
        totalPages: response.data.total_pages,
      });

      setPreviewData(response.data.preview_data);
      
      toast.success("PDF procesado correctamente", {
        description: `Se encontraron ${response.data.total_rows} filas en ${response.data.total_pages} página(s)`
      });

    } catch (error) {
      console.error('Upload error:', error);
      const message = error.response?.data?.detail || "Error al procesar el archivo";
      toast.error("Error", { description: message });
      resetState();
    } finally {
      setIsUploading(false);
    }
  };

  const downloadFile = () => {
    if (!fileInfo?.id) return;

    const downloadUrl = `${API}/download/${fileInfo.id}`;
    
    // Abrir en nueva ventana - el servidor tiene Content-Disposition: attachment
    const newWindow = window.open(downloadUrl, '_blank');
    
    if (newWindow) {
      toast.success("Descarga iniciada", {
        description: `Archivo: ${fileInfo.originalFilename.replace('.pdf', '.xlsx')}`
      });
    } else {
      // Si el popup fue bloqueado, mostrar enlace manual
      toast.error("Popup bloqueado", {
        description: "Permite popups o haz clic derecho en el botón y selecciona 'Abrir enlace en nueva pestaña'"
      });
    }
  };

  const deleteFile = async () => {
    if (fileInfo?.id) {
      try {
        await axios.delete(`${API}/file/${fileInfo.id}`);
      } catch (error) {
        console.error('Delete error:', error);
      }
    }
    resetState();
  };

  // Get column headers from first row or generate generic ones
  const getHeaders = () => {
    if (!previewData || previewData.length === 0) return [];
    const maxCols = Math.max(...previewData.map(row => row.length));
    return Array.from({ length: maxCols }, (_, i) => `Columna ${i + 1}`);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 md:p-8 bg-background">
      <Toaster 
        position="top-right" 
        toastOptions={{
          style: {
            background: '#FFFFFF',
            border: '1px solid rgba(95, 46, 10, 0.2)',
            color: '#5D4037',
          },
        }}
      />
      
      <div className="w-full max-w-4xl animate-fade-in">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <FileSpreadsheet className="w-10 h-10 text-primary" />
            <h1 className="font-heading text-4xl md:text-5xl font-bold text-foreground tracking-tight">
              PDFtoExc
            </h1>
          </div>
          <p className="font-body text-base md:text-lg text-muted-foreground max-w-xl mx-auto">
            Convierte tus archivos PDF a formato Excel de manera rápida y sencilla
          </p>
        </div>

        {/* Main Card */}
        <Card className="converter-card" data-testid="converter-card">
          <CardHeader className="pb-4">
            <CardTitle className="font-heading text-xl text-foreground flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Subir Archivo PDF
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Arrastra y suelta tu archivo PDF o haz clic para seleccionar (máximo 10MB)
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Upload Zone */}
            {!previewData && (
              <div
                data-testid="upload-zone"
                className={`upload-zone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input').click()}
              >
                <input
                  id="file-input"
                  data-testid="file-input"
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />

                {!file ? (
                  <div className="space-y-4">
                    <div className="w-16 h-16 mx-auto rounded-full bg-accent/30 flex items-center justify-center">
                      <FileText className="w-8 h-8 text-primary" />
                    </div>
                    <div>
                      <p className="text-foreground font-medium text-lg">
                        {isDragging ? "Suelta el archivo aquí" : "Arrastra tu PDF aquí"}
                      </p>
                      <p className="text-muted-foreground text-sm mt-1">
                        o haz clic para seleccionar
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="w-16 h-16 mx-auto rounded-full bg-primary/10 flex items-center justify-center">
                      <CheckCircle className="w-8 h-8 text-primary" />
                    </div>
                    <div>
                      <p className="text-foreground font-medium text-lg truncate max-w-xs mx-auto">
                        {file.name}
                      </p>
                      <p className="text-muted-foreground text-sm mt-1">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Upload Progress */}
            {isUploading && (
              <div className="space-y-3" data-testid="upload-progress">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Procesando PDF...
                  </span>
                  <span className="text-foreground font-medium">{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            )}

            {/* Action Buttons (before preview) */}
            {file && !previewData && !isUploading && (
              <div className="flex gap-3 justify-center">
                <Button
                  data-testid="upload-btn"
                  onClick={uploadFile}
                  className="btn-primary"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Procesar PDF
                </Button>
                <Button
                  data-testid="cancel-btn"
                  variant="outline"
                  onClick={resetState}
                  className="btn-secondary"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancelar
                </Button>
              </div>
            )}

            {/* File Info */}
            {fileInfo && (
              <div 
                data-testid="file-info"
                className="bg-accent/20 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <FileSpreadsheet className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium text-foreground truncate max-w-[200px] md:max-w-xs">
                      {fileInfo.originalFilename}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {fileInfo.totalRows} filas • {fileInfo.totalPages} página(s)
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="status-badge ready">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Listo
                  </span>
                </div>
              </div>
            )}

            {/* Preview Table */}
            {previewData && previewData.length > 0 && (
              <div className="space-y-3" data-testid="preview-section">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading text-lg font-semibold text-foreground">
                    Vista Previa
                  </h3>
                  <span className="text-sm text-muted-foreground">
                    Mostrando {Math.min(previewData.length, 100)} de {fileInfo?.totalRows || previewData.length} filas
                  </span>
                </div>
                
                <ScrollArea className="preview-table-wrapper" data-testid="preview-table">
                  <Table className="preview-table">
                    <TableHeader>
                      <TableRow>
                        {getHeaders().map((header, idx) => (
                          <TableHead key={idx} className="whitespace-nowrap">
                            {header}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewData.slice(0, 100).map((row, rowIdx) => (
                        <TableRow key={rowIdx}>
                          {getHeaders().map((_, colIdx) => (
                            <TableCell key={colIdx} className="whitespace-nowrap">
                              {row[colIdx] || ''}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </div>
            )}

            {/* Download Actions */}
            {previewData && (
              <div className="flex gap-3 justify-center pt-4" data-testid="download-actions">
                <Button
                  data-testid="download-btn"
                  onClick={downloadFile}
                  className="btn-primary"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Descargar Excel
                </Button>
                <Button
                  data-testid="new-file-btn"
                  variant="outline"
                  onClick={deleteFile}
                  className="btn-secondary"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Nuevo Archivo
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Footer */}
        <footer className="mt-8 text-center">
          <p className="text-sm text-muted-foreground">
            Desarrollado para <span className="font-medium text-foreground">pdftoexc.facore.cloud</span>
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
