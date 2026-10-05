"""
Main ETL Pipeline Orchestrator (Medallion Architecture):
Executes Bronze -> Silver -> Gold stages on 100% official raw datasets:
- INEGI Marco Geoestadístico 2020: Mérida AGEBs (31a.shp)
- INEGI Censo de Población y Vivienda 2020 (AGEB Urbana)
- INEGI DENUE: Mérida Economic Establishments
"""

import sys
import logging
from pathlib import Path

# Add project root to sys.path
BASE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BASE_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_ROOT))

# Configure UTF-8 for standard output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.etl.config import DATA_RAW_DIR, DATA_PROCESSED_DIR
from src.etl.extract import load_raw_demographics, load_raw_cartography, load_raw_denue, load_raw_crime
from src.etl.transform import standardize_ageb_geometries, clean_census_demographics, process_denue, process_crime
from src.etl.load import get_db_engine, load_dim_geografia, load_fact_demografia, load_dim_actividad_economica, load_fact_negocios_batch, load_dim_tiempo, load_fact_crimen_batch
from src.etl.generate_analytics_feed import generate_analytics_feed

# Logging configuration with ASCII tags
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_Pipeline")


def run_pipeline():
    logger.info("==========================================================")
    logger.info("[START] Merida Urban Intelligence ETL Pipeline (Official INEGI & SESNSP Data)")
    logger.info("==========================================================")

    # 1. Cartography (dim_geografia)
    logger.info("[STEP 1/5] Processing Official Cartography (Mérida AGEB Polygons)...")
    gdf_carto_raw = load_raw_cartography()
    if gdf_carto_raw.empty:
        logger.error("❌ Could not find 31a.shp. Run python -m src.etl.download_official_data first.")
        return
    gdf_agebs = standardize_ageb_geometries(gdf_carto_raw)
    logger.info(f"   Standardized {len(gdf_agebs)} official urban AGEBs for Mérida.")

    # 2. Demographics (fact_demografia)
    logger.info("[STEP 2/5] Processing INEGI Census 2020 Demographics...")
    df_census_raw = load_raw_demographics()
    df_demo = clean_census_demographics(df_census_raw)
    logger.info(f"   Cleaned demographic indicators for {len(df_demo)} AGEBs.")

    # 3. Economic Directory (dim_actividad_economica & fact_negocios)
    logger.info("[STEP 3/5] Processing INEGI DENUE & Spatial Join (Points-to-Polygons)...")
    df_denue_raw = load_raw_denue()
    df_scian, df_fact_neg = process_denue(df_denue_raw, gdf_agebs)
    logger.info(f"   Identified {len(df_scian)} SCIAN activity classifications.")
    logger.info(f"   Spatially joined {len(df_fact_neg)} business establishments to Mérida AGEBs.")

    # 4. Crime (SESNSP Official Data)
    logger.info("[STEP 4/5] Processing SESNSP Crime Data...")
    df_crime_raw = load_raw_crime()
    df_dim_tiempo, df_fact_crimen = process_crime(df_crime_raw, gdf_agebs, df_demo)
    logger.info(f"   Processed {len(df_dim_tiempo)} time periods and {len(df_fact_crimen)} crime records.")

    # 5. Gold Layer Loading & Analytics Feeds
    logger.info("[STEP 5/5] Loading into PostgreSQL / PostGIS Data Warehouse & Analytics Feeds...")
    engine = get_db_engine()
    if engine:
        load_dim_geografia(gdf_agebs, engine=engine)
        load_fact_demografia(df_demo, engine=engine)
        load_dim_actividad_economica(df_scian, engine=engine)
        load_fact_negocios_batch(df_fact_neg, engine=engine)
        load_dim_tiempo(df_dim_tiempo, engine=engine)
        load_fact_crimen_batch(df_fact_crimen, engine=engine)
        logger.info("   [OK] All official data successfully populated into PostGIS DW.")
    else:
        logger.info("   [INFO] DATABASE_URL not set in environment. Transformations verified successfully.")

    # Generate analytics feed for frontend consumption
    generate_analytics_feed()

    logger.info("==========================================================")
    logger.info("[COMPLETED] ETL Pipeline executed successfully.")
    logger.info("==========================================================")


if __name__ == "__main__":
    run_pipeline()

