"""
Silver Layer (Transformations & Spatial Joins):
- Standardizes CRS to EPSG:4326 (WGS84) and EPSG:6372 / EPSG:32616 (Metric).
- Resolves point-to-polygon spatial integration (DENUE & Crime -> AGEB polygons).
- Imputes / handles missing values and standardizes data types.
- Builds dimensional frames ready for loading into PostgreSQL/PostGIS.
"""

from typing import Tuple
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, MultiPolygon, Polygon
from src.etl.config import (
    CRS_WGS84,
    CRS_METRIC_MEXICO,
    CRS_UTM16N,
    CVE_ENT_YUCATAN,
    CVE_MUN_MERIDA
)


def standardize_ageb_geometries(gdf_agebs: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Standardize AGEB polygon geometries:
    - Ensure CRS is EPSG:4326
    - Calculate exact area in km² using metric projection (EPSG:6372 or EPSG:32616)
    - Ensure geometry validity (buffer(0) for topological fixes)
    """
    if gdf_agebs.empty:
        return gdf_agebs

    # Reproject to WGS84
    if gdf_agebs.crs is None:
        gdf_agebs.set_crs(CRS_WGS84, inplace=True)
    elif gdf_agebs.crs.to_string() != CRS_WGS84:
        gdf_agebs = gdf_agebs.to_crs(CRS_WGS84)

    # Standardize column names
    col_map = {c: c.lower() for c in gdf_agebs.columns}
    gdf_agebs = gdf_agebs.rename(columns=col_map)

    # Filter for Yucatán (31) and Mérida (050)
    if "cve_ent" in gdf_agebs.columns:
        gdf_agebs = gdf_agebs[gdf_agebs["cve_ent"].astype(str).str.zfill(2) == CVE_ENT_YUCATAN]
    if "cve_mun" in gdf_agebs.columns:
        gdf_agebs = gdf_agebs[gdf_agebs["cve_mun"].astype(str).str.zfill(3) == CVE_MUN_MERIDA]

    # Clean geometries
    gdf_agebs["geometry"] = gdf_agebs["geometry"].buffer(0)

    # Calculate area in km² using metric projection
    gdf_metric = gdf_agebs.to_crs(CRS_METRIC_MEXICO)
    gdf_agebs["area_km2"] = (gdf_metric.geometry.area / 1_000_000).round(4)

    # Build standard CVEGEO (13 digits: ENT(2)+MUN(3)+LOC(4)+AGEB(4))
    if "cvegeo" not in gdf_agebs.columns:
        ent = gdf_agebs.get("cve_ent", CVE_ENT_YUCATAN).astype(str).str.zfill(2)
        mun = gdf_agebs.get("cve_mun", CVE_MUN_MERIDA).astype(str).str.zfill(3)
        loc = gdf_agebs.get("cve_loc", "0001").astype(str).str.zfill(4)
        ageb = gdf_agebs.get("cve_ageb", "0000").astype(str).str.zfill(4)
        gdf_agebs["cvegeo"] = ent + mun + loc + ageb

    return gdf_agebs


def spatial_join_points_to_polygons(
    df_points: pd.DataFrame,
    gdf_polygons: gpd.GeoDataFrame,
    lat_col: str = "latitud",
    lon_col: str = "longitud",
    polygon_id_col: str = "cvegeo"
) -> gpd.GeoDataFrame:
    """
    Perform Point-in-Polygon spatial join to assign each point to its encompassing AGEB.
    """
    if df_points.empty or gdf_polygons.empty:
        return gpd.GeoDataFrame()

    # Clean coordinates
    df_valid = df_points.dropna(subset=[lat_col, lon_col]).copy()
    df_valid[lat_col] = pd.to_numeric(df_valid[lat_col], errors="coerce")
    df_valid[lon_col] = pd.to_numeric(df_valid[lon_col], errors="coerce")
    df_valid = df_valid.dropna(subset=[lat_col, lon_col])

    # Convert to GeoDataFrame
    geometry = [Point(xy) for xy in zip(df_valid[lon_col], df_valid[lat_col])]
    gdf_points = gpd.GeoDataFrame(df_valid, geometry=geometry, crs=CRS_WGS84)

    # Spatial Join
    joined = gpd.sjoin(
        gdf_points,
        gdf_polygons[[polygon_id_col, "geometry"]],
        how="inner",
        predicate="within"
    )

    if "index_right" in joined.columns:
        joined = joined.drop(columns=["index_right"])

    return joined


def map_scian_category(scian_code: str) -> str:
    """Map SCIAN code to macro category ('Comercio', 'Servicios', 'Industria', 'Otro')."""
    code_str = str(scian_code).strip()
    if not code_str:
        return "Otro"
    
    prefix2 = code_str[:2]
    if prefix2 in ["43", "46", "47"]:
        return "Comercio"
    elif prefix2 in ["51", "52", "53", "54", "55", "56", "61", "62", "71", "72", "81"]:
        return "Servicios"
    elif prefix2 in ["31", "32", "33", "23", "11", "21", "22"]:
        return "Industria"
    return "Otro"
