"""
Bronze Layer (Raw Ingestion):
Reads raw source datasets without modifying original files.
Sources:
- INEGI Censo de Población y Vivienda 2020 (Demografía)
- INEGI DENUE (Directorio Estadístico Nacional de Unidades Económicas)
- INEGI Cartografía Geoestadística (Polígonos AGEB Mérida)
- Incidencias Delictivas (Georreferenciadas con Lat/Long)
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import geopandas as gpd
from src.etl.config import DATA_RAW_DIR, CVE_ENT_YUCATAN, CVE_MUN_MERIDA


def list_raw_files() -> Dict[str, list]:
    """Scan and categorize raw data files in data/raw/."""
    files_by_category = {
        "demographic": [],
        "economic": [],
        "cartography": [],
        "crime": [],
        "other": []
    }
    
    if not DATA_RAW_DIR.exists():
        return files_by_category

    for p in DATA_RAW_DIR.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            lower_name = p.name.lower()
            if any(k in lower_name for k in ["censo", "demografia", "pob", "iter"]):
                files_by_category["demographic"].append(p)
            elif any(k in lower_name for k in ["denue", "negocio", "econom"]):
                files_by_category["economic"].append(p)
            elif any(k in lower_name for k in ["ageb", "cartografia", "shape", ".shp", ".geojson"]):
                files_by_category["cartography"].append(p)
            elif any(k in lower_name for k in ["crimen", "delito", "seguridad", "incidencia"]):
                files_by_category["crime"].append(p)
            else:
                files_by_category["other"].append(p)
                
    return files_by_category


def load_raw_demographics(file_path: Optional[Path] = None) -> pd.DataFrame:
    """Load raw INEGI Census tabular data."""
    if file_path and file_path.exists():
        if file_path.suffix == ".csv":
            return pd.read_csv(file_path, low_memory=False, encoding="utf-8")
        elif file_path.suffix in [".xls", ".xlsx"]:
            return pd.read_excel(file_path)
    return pd.DataFrame()


def load_raw_denue(file_path: Optional[Path] = None) -> pd.DataFrame:
    """Load raw DENUE economic establishments data."""
    if file_path and file_path.exists():
        if file_path.suffix == ".csv":
            return pd.read_csv(file_path, low_memory=False, encoding="latin1")
        elif file_path.suffix in [".xls", ".xlsx"]:
            return pd.read_excel(file_path)
    return pd.DataFrame()


def load_raw_cartography(file_path: Optional[Path] = None) -> gpd.GeoDataFrame:
    """Load raw official AGEB polygon shapefiles or GeoJSON."""
    if file_path and file_path.exists():
        return gpd.read_file(file_path)
    return gpd.GeoDataFrame()


def load_raw_crime(file_path: Optional[Path] = None) -> pd.DataFrame:
    """Load raw crime incident georeferenced records."""
    if file_path and file_path.exists():
        if file_path.suffix == ".csv":
            return pd.read_csv(file_path, low_memory=False, encoding="utf-8")
        elif file_path.suffix in [".xls", ".xlsx"]:
            return pd.read_excel(file_path)
    return pd.DataFrame()
