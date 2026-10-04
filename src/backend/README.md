# Mérida Urban Intelligence - FastAPI Backend & Spatial Autocorrelation Engine

This directory contains the production-ready FastAPI backend for **Mérida Urban Intelligence**. It connects with Supabase PostGIS and implements spatial statistical engines using **PySAL (`libpysal`, `esda`)** and **GeoPandas**.

---

## 🏗️ Architecture & Structure

```text
src/backend/
├── app/
│   ├── main.py                  # FastAPI application entrypoint & middleware setup
│   ├── core/
│   │   ├── config.py            # Environment configuration & settings loading
│   │   └── database.py          # Supabase PostGIS connection & GeoJSON fallback loader
│   ├── models/
│   │   └── schemas.py           # Pydantic request & response schemas
│   ├── services/
│   │   └── spatial_service.py   # PySAL Spatial Autocorrelation (Moran's I Global, LISA, Bivariate)
│   └── routers/
│       ├── health.py            # Health check & DB status endpoint
│       └── spatial.py           # Spatial statistics & GeoJSON API endpoints
├── tests/
│   └── test_spatial.py          # Pytest suite verifying spatial calculations & endpoints
├── run.py                       # Uvicorn server launcher script
└── README.md                    # Backend documentation
```

---

## ⚡ Quick Start

### 1. Requirements & Dependencies
Ensure Python dependencies are installed:
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
Copy `.env.example` to `.env` in the repository root and configure your `DATABASE_URL` (Supabase PostGIS string). If database credentials are not provided, the API automatically operates using the local 526 AGEBs GeoJSON fallback dataset (`outputs/maps/merida_agebs_demographics.geojson`).

### 3. Run Development Server
```bash
python src/backend/run.py
```
Or directly with Uvicorn:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger API documentation will be available at: `http://localhost:8000/docs`

### 4. Run Test Suite
```bash
pytest src/backend/tests/ -v
```

---

## 🛰️ API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API status and root links |
| `GET` | `/api/v1/health` | Healthcheck & Supabase PostGIS connection status |
| `GET` | `/api/v1/spatial/kpis` | List all available metrics/KPIs for spatial analysis |
| `GET` | `/api/v1/spatial/geojson` | Export 526 AGEBs GeoJSON enriched with calculated KPIs for MapLibre |
| `POST` | `/api/v1/spatial/moran/global` | Compute Global Moran's $I$ (Clustering / Dispersion statistic, z-score, p-value) |
| `POST` | `/api/v1/spatial/moran/local` | Compute Local Moran's $I$ (LISA Clusters: High-High, Low-Low, Outliers) |
| `POST` | `/api/v1/spatial/moran/bivariate` | Compute Bivariate Moran's $I$ (Spatial cross-correlation X vs Y spatial lag) |
| `GET` | `/api/v1/spatial/summary` | Spatial summary report across key urban metrics |

---

## 🧮 Spatial Autocorrelation Engine Details (PySAL)

### 1. Spatial Weights Matrix ($W$)
Constructed using Queen contiguity with row standardization (`'r'`). Automatically handles island polygons (unconnected AGEBs) via KNN fallback neighbors to prevent zero-division errors.

### 2. Global Moran's $I$
Calculates global spatial autocorrelation statistic $I \in [-1, 1]$, expected value $E[I]$, analytical $z$-score, and Monte Carlo permutation pseudo-$p$-value ($999$ iterations).

### 3. Local Moran's $I$ (LISA)
Identifies spatial clusters per AGEB (quadrant classification):
* **High-High (Hotspots)**: High values surrounded by high values ($p \le 0.05$).
* **Low-Low (Coldspots)**: Low values surrounded by low values ($p \le 0.05$).
* **High-Low (Spatial Outliers)**: High values surrounded by low values.
* **Low-High (Spatial Outliers)**: Low values surrounded by high values.
* **Not Significant**: $p > \alpha$ (default $\alpha = 0.05$).

### 4. Bivariate Moran's $I$
Measures the relationship between a target variable $X$ in polygon $i$ and the average of variable $Y$ in neighboring polygons ($W Y$).
