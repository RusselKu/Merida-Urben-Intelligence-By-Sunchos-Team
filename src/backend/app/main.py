import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health, spatial

# Setup logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("merida_backend")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    ## Mérida Urban Intelligence - Spatial Autocorrelation & Analytics Engine API
    
    This backend API provides high-performance spatial statistical analysis for the city of Mérida, Yucatán, Mexico.
    Powered by **PySAL (libpysal, esda)** and **PostGIS / GeoPandas**.
    
    ### Key Features:
    * **Global Moran's I**: Measures overall spatial clustering vs dispersion across 526 urban AGEBs.
    * **Local Moran's I (LISA)**: Detects High-High (Hotspots), Low-Low (Coldspots), and Spatial Outliers per AGEB.
    * **Bivariate Moran's I**: Computes spatial cross-correlation (e.g. Crime vs Business Density).
    * **MapLibre-Ready GeoJSON**: Exports enriched spatial polygons directly to React frontend.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = settings.ALLOWED_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 Routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(spatial.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "title": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "spatial_endpoints": f"{settings.API_V1_STR}/spatial/kpis"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
