from fastapi import APIRouter
from app.core.config import settings
from app.core.database import check_db_connection, load_spatial_dataset
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Returns status of API, database connectivity, and dataset stats."""
    db_ok = check_db_connection()
    try:
        gdf = load_spatial_dataset()
        total_agebs = len(gdf)
        source = "PostGIS" if db_ok else "GeoJSON Fallback"
    except Exception:
        total_agebs = 0
        source = "None"

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        database_connected=db_ok,
        data_source=source,
        total_agebs=total_agebs
    )
