# Multi-stage Dockerfile para PDFtoExc
# Construye frontend y backend en una sola imagen

# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Copy package files
COPY frontend/package.json frontend/yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy source code
COPY frontend/ .

# Build argument for backend URL
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Build the application
RUN yarn build

# ============================================
# Stage 2: Production Image
# ============================================
FROM python:3.11-slim

# Install nginx and system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Create directories for uploads and outputs
RUN mkdir -p /app/backend/uploads /app/backend/outputs

# Copy built frontend from Stage 1
COPY --from=frontend-build /app/frontend/build /var/www/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/sites-available/default

# Create startup script
RUN echo '#!/bin/bash\n\
nginx\n\
cd /app/backend && uvicorn server:app --host 0.0.0.0 --port 8001\n\
' > /start.sh && chmod +x /start.sh

# Expose ports
EXPOSE 80 8001

# Start both services
CMD ["/start.sh"]
