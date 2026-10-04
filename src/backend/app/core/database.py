import logging
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("merida_backend.database")

# Database engine initialization (lazy or resilient)
engine = None
try:
    if settings.DATABASE_URL:
        # Replace postgresql:// if needed for psycopg2
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.warning(f"Database engine setup warning: {e}. Will fallback to GeoJSON file.")


def check_db_connection() -> bool:
    """Check if PostgreSQL PostGIS database is reachable and active."""
    if not engine:
        return False
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1;"))
            return result.scalar() == 1
    except Exception as e:
        logger.debug(f"DB ping failed: {e}")
        return False


def load_spatial_dataset() -> gpd.GeoDataFrame:
    """
    Loads AGEBs spatial dataset with demographical & economic metrics.
    Attempts to read from Supabase PostGIS `v_kpis_territoriales` view first.
    If database is unavailable, loads directly from local GeoJSON fallback.
    """
    # 1. Attempt DB loading via PostGIS
    if check_db_connection():
        try:
            logger.info("Fetching spatial KPIs dataset from Supabase PostGIS view `v_kpis_territoriales`...")
            query = """
                SELECT 
                    cvegeo, nom_asentamiento, area_km2,
                    poblacion_total, densidad_poblacion_km2, tasa_pea_porcentaje,
                    poblacion_0_14, poblacion_15_64, poblacion_65_mas,
                    total_negocios, densidad_negocios_km2, negocios_por_mil_hab,
                    densidad_comercio_km2, densidad_servicios_km2, actividad_economica_dominante,
                    total_delitos, tasa_delictiva_por_mil_hab, ratio_delito_por_negocio,
                    ST_AsText(geom_4326) AS wkt_geom
                FROM v_kpis_territoriales;
            """
            df = pd.read_sql_query(query, engine)
            if not df.empty and 'wkt_geom' in df.columns:
                gdf = gpd.GeoDataFrame(
                    df, 
                    geometry=gpd.GeoSeries.from_wkt(df['wkt_geom']), 
                    crs="EPSG:4326"
                )
                gdf.drop(columns=['wkt_geom'], inplace=True, errors='ignore')
                logger.info(f"Successfully loaded {len(gdf)} AGEBs from Supabase PostGIS.")
                return gdf
        except Exception as e:
            logger.warning(f"Could not load dataset from DB view: {e}. Falling back to GeoJSON.")

    # 2. Fallback to local GeoJSON file
    geojson_path = Path(settings.GEOJSON_PATH)
    if not geojson_path.is_absolute():
        geojson_path = Path(__file__).resolve().parent.parent.parent.parent.parent / settings.GEOJSON_PATH

    if geojson_path.exists():
        logger.info(f"Loading spatial dataset from local GeoJSON: {geojson_path}")
        gdf = gpd.read_file(geojson_path)
        
        # Ensure standard metrics exist or derive them if missing
        if 'densidad_poblacion_km2' not in gdf.columns and 'poblacion_total' in gdf.columns:
            gdf['densidad_poblacion_km2'] = (gdf['poblacion_total'] / gdf['area_km2'].replace(0, pd.NA)).fillna(0).round(2)
            
        if 'tasa_pea_porcentaje' not in gdf.columns and 'poblacion_pea' in gdf.columns and 'poblacion_pnea' in gdf.columns:
            total_12_plus = gdf['poblacion_pea'] + gdf['poblacion_pnea']
            gdf['tasa_pea_porcentaje'] = ((gdf['poblacion_pea'] / total_12_plus.replace(0, pd.NA)) * 100).fillna(0).round(2)
            
        if 'total_negocios' not in gdf.columns:
            gdf['total_negocios'] = 0
            gdf['densidad_negocios_km2'] = 0.0
            gdf['negocios_por_mil_hab'] = 0.0

        if 'total_delitos' not in gdf.columns:
            gdf['total_delitos'] = 0
            gdf['tasa_delictiva_por_mil_hab'] = 0.0
            gdf['ratio_delito_por_negocio'] = 0.0

        return gdf

    raise FileNotFoundError(f"Neither PostGIS database nor GeoJSON file found at {geojson_path}")
