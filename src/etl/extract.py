"""
Bronze Layer (Raw Ingestion):
Reads raw source datasets without modifying original files.
Sources:
- INEGI Population and Housing Census 2020 (Demographics - 526 Mérida Urban AGEBs)
- INEGI DENUE (56,909 Mérida Economic Establishments)
- INEGI Geo-statistical Cartography (Official 31a.shp AGEB Polygons for Mérida)
- Georeferenced Public Safety & Crime Incidents
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import geopandas as gpd
from src.etl.config import DATA_RAW_DIR, CVE_ENT_YUCATAN, CVE_MUN_MERIDA


def get_real_paths() -> Dict[str, Optional[Path]]:
    """Locate official extracted datasets in data/raw/."""
    paths = {
        "census": None,
        "denue": None,
        "cartography": None,
        "crime": None
    }
    
    # 1. Census
    # The INEGI dictionary shares the suffix; select the dataset, not metadata.
    census_candidates = sorted(DATA_RAW_DIR.rglob("conjunto_de_datos_ageb_urbana_31_cpv2020.csv"))
    if census_candidates:
        paths["census"] = census_candidates[0]
        
    # 2. DENUE
    denue_candidates = list(DATA_RAW_DIR.rglob("denue_inegi_31_.csv"))
    if denue_candidates:
        paths["denue"] = denue_candidates[0]
        
    # 3. Cartography Shapefile
    carto_candidates = list(DATA_RAW_DIR.rglob("31a.shp"))
    if carto_candidates:
        paths["cartography"] = carto_candidates[0]
        
    # 4. Crime (SESNSP / Public Safety Incidents)
    crime_candidates = (
        list(DATA_RAW_DIR.rglob("*crimen*.csv")) +
        list(DATA_RAW_DIR.rglob("*delit*.csv")) +
        list(DATA_RAW_DIR.rglob("*sesnsp*.csv")) +
        list(DATA_RAW_DIR.rglob("*crime*.csv"))
    )
    if crime_candidates:
        paths["crime"] = crime_candidates[0]
        
    return paths


def load_raw_demographics() -> pd.DataFrame:
    """Load raw INEGI Census tabular data."""
    paths = get_real_paths()
    if paths["census"] and paths["census"].exists():
        print(f"[EXTRACT] Loading real INEGI Census 2020 from: {paths['census'].name}")
        return pd.read_csv(paths["census"], low_memory=False, encoding="utf-8")
    return pd.DataFrame()


def load_raw_denue() -> pd.DataFrame:
    """Load raw DENUE economic establishments data."""
    paths = get_real_paths()
    if paths["denue"] and paths["denue"].exists():
        print(f"[EXTRACT] Loading real INEGI DENUE from: {paths['denue'].name}")
        return pd.read_csv(paths["denue"], low_memory=False, encoding="latin1")
    return pd.DataFrame()


def load_raw_cartography() -> gpd.GeoDataFrame:
    """Load raw official AGEB polygon shapefile."""
    paths = get_real_paths()
    if paths["cartography"] and paths["cartography"].exists():
        print(f"[EXTRACT] Loading real INEGI Marco Geoestadistico from: {paths['cartography'].name}")
        return gpd.read_file(paths["cartography"])
    return gpd.GeoDataFrame()


def load_raw_crime() -> pd.DataFrame:
    """Load raw crime incident georeferenced records."""
    paths = get_real_paths()
    if paths["crime"] and paths["crime"].exists():
        print(f"[EXTRACT] Loading real Crime records from: {paths['crime'].name}")
        return pd.read_csv(paths["crime"], low_memory=False, encoding="utf-8")
    return pd.DataFrame()
