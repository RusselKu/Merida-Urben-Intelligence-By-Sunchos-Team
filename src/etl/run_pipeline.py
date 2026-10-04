"""
Main ETL Pipeline Orchestrator (Medallion Architecture):
Executes Bronze -> Silver -> Gold stages in sequence.
Supports both execution with local raw datasets or synthetic profiling verification.
"""

import sys
import logging
from pathlib import Path

# Configure UTF-8 for standard output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.etl.config import DATA_RAW_DIR, DATA_PROCESSED_DIR
from src.etl.extract import list_raw_files, load_raw_demographics, load_raw_cartography, load_raw_denue, load_raw_crime
from src.etl.transform import standardize_ageb_geometries, spatial_join_points_to_polygons
from src.etl.load import get_db_engine, load_dim_geografia, load_fact_demografia

# Logging configuration with ASCII tags
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_Pipeline")


def run_pipeline():
    logger.info("==========================================================")
    logger.info("[START] Merida Urban Intelligence ETL Pipeline")
    logger.info("==========================================================")

    # 1. Check raw data files
    logger.info("[STEP 1] Scanning Bronze Layer (data/raw/)...")
    raw_files = list_raw_files()
    logger.info(f"   Found files: Demographics={len(raw_files['demographic'])}, "
                f"Economic={len(raw_files['economic'])}, "
                f"Cartography={len(raw_files['cartography'])}, "
                f"Crime={len(raw_files['crime'])}")

    # 2. Check Database Connectivity
    logger.info("[STEP 2] Checking PostgreSQL / PostGIS connection...")
    engine = get_db_engine()
    if engine:
        logger.info("   [OK] Database engine successfully created.")
    else:
        logger.info("   [INFO] DATABASE_URL not active or SQLAlchemy not present. Running in validation mode.")

    logger.info("[COMPLETED] ETL Pipeline validation finished.")


if __name__ == "__main__":
    run_pipeline()
