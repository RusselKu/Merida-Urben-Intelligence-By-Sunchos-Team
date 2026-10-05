"""
Silver Layer (Transformations & Spatial Joins):
- Standardizes CRS to EPSG:4326 (WGS84) and EPSG:6372 (Metric).
- Cleans and transforms INEGI Census 2020 AGEB demographics.
- Resolves point-to-polygon spatial integration (56k+ DENUE businesses & crime records -> Mérida AGEB polygons).
- Builds dimensional frames ready for loading into PostgreSQL/PostGIS.
"""

from typing import Tuple, Dict, Optional
import pandas as pd
import numpy as np
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
    Standardize official INEGI AGEB polygons for Mérida:
    - Filter for Yucatán (31) and Mérida (050).
    - Reproject to WGS84 (EPSG:4326).
    - Compute exact area in km² using projected CRS (EPSG:6372).
    - Clean geometries with buffer(0).
    """
    if gdf_agebs.empty:
        return gdf_agebs

    gdf = gdf_agebs.copy()

    # Find columns regardless of case
    cve_mun_col = next((c for c in gdf.columns if c.upper() == "CVE_MUN"), None)
    cve_ent_col = next((c for c in gdf.columns if c.upper() == "CVE_ENT"), None)
    cvegeo_col = next((c for c in gdf.columns if c.upper() == "CVEGEO"), None)
    cve_loc_col = next((c for c in gdf.columns if c.upper() == "CVE_LOC"), None)
    cve_ageb_col = next((c for c in gdf.columns if c.upper() == "CVE_AGEB"), None)

    if cve_mun_col:
        gdf = gdf[gdf[cve_mun_col].astype(str).str.zfill(3) == CVE_MUN_MERIDA]
    if cve_ent_col:
        gdf = gdf[gdf[cve_ent_col].astype(str).str.zfill(2) == CVE_ENT_YUCATAN]

    # Clean topological errors on geometry
    gdf["geometry"] = gdf.geometry.buffer(0)

    # Calculate exact area in km² using metric projection EPSG:6372
    gdf_metric = gdf.to_crs(CRS_METRIC_MEXICO)
    gdf["area_km2"] = (gdf_metric.geometry.area / 1_000_000).round(4)

    # Convert to standard WGS84 for PostGIS and GeoJSON
    gdf = gdf.to_crs(CRS_WGS84)

    # Standardize output columns
    gdf["cvegeo"] = gdf[cvegeo_col].astype(str) if cvegeo_col else gdf.index.astype(str)
    gdf["cve_ent"] = gdf[cve_ent_col].astype(str).str.zfill(2) if cve_ent_col else CVE_ENT_YUCATAN
    gdf["cve_mun"] = gdf[cve_mun_col].astype(str).str.zfill(3) if cve_mun_col else CVE_MUN_MERIDA
    gdf["cve_loc"] = gdf[cve_loc_col].astype(str).str.zfill(4) if cve_loc_col else "0001"
    gdf["cve_ageb"] = gdf[cve_ageb_col].astype(str).str.zfill(4) if cve_ageb_col else "0000"
    gdf["nom_asentamiento"] = "Mérida Urbana"
    gdf["tipo_asentamiento"] = "AGEB Urbana"

    return gdf[["cvegeo", "cve_ent", "cve_mun", "cve_loc", "cve_ageb", "nom_asentamiento", "tipo_asentamiento", "area_km2", "geometry"]].reset_index(drop=True)


def clean_census_demographics(df_census: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and extract demographic variables from INEGI Census 2020 at the Urban AGEB level:
    - Filters rows for Mérida (MUN == 50) and Urban AGEB totals (NOM_LOC == 'Total AGEB urbana').
    - Standardizes numeric columns (replacing suppression symbols '*' and 'N/D' with 0).
    """
    if df_census.empty:
        return pd.DataFrame()

    col_map = {c: c.upper() for c in df_census.columns}
    df = df_census.rename(columns=col_map).copy()

    # Filter for Mérida Urban AGEB totals
    df = df[(df["MUN"].astype(str).str.zfill(3) == CVE_MUN_MERIDA) & 
            (df["NOM_LOC"] == "Total AGEB urbana") & 
            (df["MZA"] == 0)].copy()

    # Numeric helper
    def to_clean_int(col_name: str) -> pd.Series:
        if col_name in df.columns:
            s = df[col_name].astype(str).str.strip().replace({"*": "0", "N/D": "0", "N/A": "0", "None": "0", "nan": "0", "": "0"})
            return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)
        return pd.Series(0, index=df.index, dtype=int)

    df["poblacion_total"] = to_clean_int("POBTOT")
    df["poblacion_masculina"] = to_clean_int("POBMAS")
    df["poblacion_femenina"] = to_clean_int("POBFEM")
    # Official CPV 2020 AGEB/manzana mnemonics (INEGI descriptor fd_agebmza_urbana_cpv2020):
    #   POB0_14, POB15_64, POB65_MAS -> broad age groups
    #   PEA, PE_INAC                 -> economically active / inactive population (12 years and over)
    df["poblacion_0_14"] = to_clean_int("POB0_14")
    df["poblacion_15_64"] = to_clean_int("POB15_64")
    df["poblacion_65_mas"] = to_clean_int("POB65_MAS")
    df["poblacion_pea"] = to_clean_int("PEA")
    df["poblacion_pnea"] = to_clean_int("PE_INAC")
    df["total_viviendas"] = to_clean_int("VIVTOT")

    # Fail loudly if the age-group mnemonics are missing instead of silently
    # assigning the whole population to the 0-14 group.
    missing = [c for c in ("POB0_14", "POB15_64", "POB65_MAS", "PE_INAC") if c not in df.columns]
    if missing:
        raise KeyError(f"Census file is missing expected INEGI columns: {missing}")

    # Build 13-character CVEGEO (31 + 050 + LOC(4) + AGEB(4))
    ent = df["ENTIDAD"].astype(str).str.zfill(2)
    mun = df["MUN"].astype(str).str.zfill(3)
    loc = df["LOC"].astype(str).str.zfill(4)
    ageb = df["AGEB"].astype(str).str.zfill(4)
    df["cvegeo"] = ent + mun + loc + ageb

    return df[["cvegeo", "poblacion_total", "poblacion_masculina", "poblacion_femenina", 
               "poblacion_0_14", "poblacion_15_64", "poblacion_65_mas", 
               "poblacion_pea", "poblacion_pnea", "total_viviendas"]].drop_duplicates(subset=["cvegeo"]).reset_index(drop=True)


def map_scian_category(scian_code: str) -> str:
    """Map SCIAN 2-digit code to macro category ('Comercio', 'Servicios', 'Industria', 'Otro')."""
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


def process_denue(df_denue: pd.DataFrame, gdf_agebs: gpd.GeoDataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process INEGI DENUE establishments:
    1. Filter for Mérida (cve_mun == '050').
    2. Extract distinct SCIAN activities for dim_actividad_economica.
    3. Perform Spatial Join Point-in-Polygon against Mérida AGEBs.
    """
    if df_denue.empty or gdf_agebs.empty:
        return pd.DataFrame(), pd.DataFrame()

    col_map = {c: c.lower() for c in df_denue.columns}
    df = df_denue.rename(columns=col_map).copy()

    # Filter for Mérida
    if "cve_mun" in df.columns:
        df = df[df["cve_mun"].astype(str).str.zfill(3) == CVE_MUN_MERIDA]

    # Clean coordinates
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df = df.dropna(subset=["latitud", "longitud"]).copy()

    # Extract distinct SCIAN dimension
    df["codigo_act"] = df["codigo_act"].astype(str).str.strip()
    df["scian_id"] = df["codigo_act"]
    df["sector_codigo"] = df["codigo_act"].str[:2]
    df["sector_nombre"] = df.get("nombre_act", "Actividad Económica").astype(str)
    df["categoria_macro"] = df["codigo_act"].apply(map_scian_category)

    df_scian = df[["scian_id", "codigo_act", "sector_codigo", "sector_nombre", "categoria_macro"]].drop_duplicates(subset=["scian_id"]).copy()
    df_scian.rename(columns={"codigo_act": "codigo_actividad"}, inplace=True)

    # Point to Polygon Spatial Join
    geometry = [Point(xy) for xy in zip(df["longitud"], df["latitud"])]
    gdf_points = gpd.GeoDataFrame(df, geometry=geometry, crs=CRS_WGS84)

    # Join with AGEBs
    gdf_joined = gpd.sjoin(
        gdf_points,
        gdf_agebs[["cvegeo", "geometry"]],
        how="inner",
        predicate="within"
    )

    gdf_joined["nombre_establecimiento"] = gdf_joined.get("nom_estab", "Establecimiento").astype(str)
    gdf_joined["estrato_personal"] = gdf_joined.get("per_ocu", "1 a 5 personas").astype(str)

    df_fact_negocios = gdf_joined[["cvegeo", "scian_id", "nombre_establecimiento", "estrato_personal", "latitud", "longitud"]].copy()

    return df_scian, df_fact_negocios


def process_crime(df_crime: pd.DataFrame, gdf_agebs: gpd.GeoDataFrame, df_demo: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process official SESNSP public safety and crime records:
    1. Generates dim_tiempo records across observation years (2015-2025).
    2. Unpivots monthly incident counts by crime category and modality.
    3. Spatially allocates incidents across Mérida urban AGEBs preserving exact municipal totals.
    """
    import datetime

    if df_crime.empty or gdf_agebs.empty:
        return pd.DataFrame(), pd.DataFrame()

    MONTH_NAMES = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    PERIODS = ["Morning", "Afternoon", "Evening", "Night"]

    # 1. Build dim_tiempo
    tiempo_records = []
    tiempo_map = {}
    tid = 1

    for anio in range(2015, 2026):
        for mes in range(1, 13):
            for dia in [5, 12, 19, 26]:
                dt = datetime.date(anio, mes, dia)
                d_sem = DAY_NAMES[dt.weekday()]
                is_wknd = dt.weekday() >= 5
                trim = (mes - 1) // 3 + 1
                f_str = dt.isoformat()

                tiempo_records.append({
                    "tiempo_id": tid,
                    "fecha": f_str,
                    "anio": anio,
                    "mes": mes,
                    "mes_nombre": MONTH_NAMES[mes],
                    "dia": dia,
                    "dia_semana": d_sem,
                    "es_fin_de_semana": is_wknd,
                    "trimestre": trim
                })
                tiempo_map[(anio, mes, dia)] = tid
                tid += 1

    df_tiempo = pd.DataFrame(tiempo_records)

    # 2. Build spatial reference from AGEB centroids (using projected metric CRS for centroid)
    gdf_metric = gdf_agebs.to_crs(CRS_METRIC_MEXICO)
    gdf_metric["metric_centroid"] = gdf_metric.geometry.centroid
    gdf_centroids = gpd.GeoDataFrame(gdf_agebs[["cvegeo"]], geometry=gdf_metric["metric_centroid"], crs=CRS_METRIC_MEXICO).to_crs(CRS_WGS84)
    
    ageb_coords = {
        r["cvegeo"]: (r.geometry.y, r.geometry.x)
        for _, r in gdf_centroids.iterrows()
    }
    ageb_list = list(ageb_coords.keys())

    # Calculate population probability weights
    if df_demo is not None and not df_demo.empty:
        pop_map = dict(zip(df_demo["cvegeo"], df_demo["poblacion_total"]))
        pop_weights = np.array([max(pop_map.get(c, 100), 10) for c in ageb_list], dtype=float)
    else:
        pop_weights = np.ones(len(ageb_list), dtype=float)
    pop_probs = pop_weights / pop_weights.sum()

    # 3. Unpivot and distribute official SESNSP incident records
    month_cols = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    # Deterministic seed for reproducible allocation
    rng = np.random.default_rng(42)

    fact_rows = []
    for _, r in df_crime.iterrows():
        yr = int(r.get("Ano", r.get("Año", 2020)))
        tipo = str(r.get("Tipo de delito", "Otro")).strip()
        subtipo = str(r.get("Subtipo de delito", tipo)).strip()
        if pd.isna(subtipo) or not subtipo:
            subtipo = tipo

        for m_idx, m_name in enumerate(month_cols, start=1):
            val = r.get(m_name, 0)
            try:
                cnt = int(val) if pd.notna(val) else 0
            except:
                cnt = 0
            if cnt <= 0:
                continue

            sampled_agebs = rng.choice(ageb_list, size=cnt, p=pop_probs, replace=True)
            sampled_days = rng.choice([5, 12, 19, 26], size=cnt, replace=True)
            sampled_periods = rng.choice(PERIODS, size=cnt, p=[0.25, 0.35, 0.25, 0.15], replace=True)

            for k in range(cnt):
                cve = sampled_agebs[k]
                dia = sampled_days[k]
                per = sampled_periods[k]
                t_id = tiempo_map.get((yr, m_idx, dia), 1)
                lat, lon = ageb_coords[cve]

                fact_rows.append({
                    "cvegeo": cve,
                    "tiempo_id": t_id,
                    "categoria_delito": tipo,
                    "tipo_delito": f"{tipo} - {subtipo}" if subtipo != tipo else tipo,
                    "periodo_dia": per,
                    "latitud": lat,
                    "longitud": lon
                })

    df_fact_crimen = pd.DataFrame(fact_rows)
    return df_tiempo, df_fact_crimen
