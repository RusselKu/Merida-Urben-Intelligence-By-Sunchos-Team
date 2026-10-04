# ==========================================================
# Mérida Urban Intelligence - ETL & Processing Environment
# ==========================================================
FROM python:3.11-slim

# Install system geospatial libraries (GDAL, GEOS, PROJ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Configure Python environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and data folders
COPY . .

# Default command runs the complete ETL pipeline
CMD ["python", "-m", "src.etl.run_pipeline"]
