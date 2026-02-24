# PDFtoExc - Convertidor PDF a Excel

## Despliegue en Coolify (VPS Hostinger)

### Opción 1: Docker Compose (Recomendado)

1. En Coolify, crear nuevo proyecto y seleccionar "Docker Compose"
2. Conectar el repositorio de GitHub
3. Coolify detectará el `docker-compose.yml` automáticamente
4. Configurar las variables de entorno:
   - `REACT_APP_BACKEND_URL`: https://pdftoexc.facore.cloud

5. Configurar el dominio: `pdftoexc.facore.cloud`
6. Habilitar SSL (Let's Encrypt)
7. Deploy!

### Opción 2: Servicios Separados

Si prefieres desplegar cada servicio por separado:

#### MongoDB
- Usar el servicio de MongoDB de Coolify o imagen `mongo:7`

#### Backend
1. Crear servicio desde `./backend`
2. Variables de entorno:
   ```
   MONGO_URL=mongodb://[tu-mongo-host]:27017
   DB_NAME=pdftoexc
   CORS_ORIGINS=https://pdftoexc.facore.cloud
   ```
3. Puerto: 8001

#### Frontend
1. Crear servicio desde `./frontend`
2. Build args:
   ```
   REACT_APP_BACKEND_URL=https://pdftoexc.facore.cloud
   ```
3. Puerto: 80

### Estructura de archivos Docker

```
/app
├── docker-compose.yml      # Orquestación completa
├── nginx-proxy.conf        # Config del proxy (opcional)
├── backend/
│   ├── Dockerfile          # Imagen del backend
│   ├── server.py
│   └── requirements.txt
└── frontend/
    ├── Dockerfile          # Imagen del frontend
    ├── nginx.conf          # Config nginx del frontend
    └── src/
```

### Notas importantes

- **SSL**: Coolify maneja certificados SSL automáticamente con Let's Encrypt
- **Dominio**: Asegúrate de apuntar `pdftoexc.facore.cloud` a la IP de tu VPS
- **MongoDB**: Los datos persisten en el volumen `mongodb_data`
- **Uploads**: Los archivos temporales se guardan en volúmenes Docker

### Comandos útiles

```bash
# Ver logs
docker-compose logs -f

# Reiniciar servicios
docker-compose restart

# Reconstruir
docker-compose up -d --build
```
