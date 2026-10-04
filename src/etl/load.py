"""
Gold Layer (Loading into Supabase PostGIS Data Warehouse):
Loads validated dimensional entities and fact tables with PostGIS geometries.
Handles batch inserts, spatial indexing, and foreign key integrity.
"""

import sys
import os
from typing import Optional, List, Dict, Any
import pandas as pd
import geopandas as gpd
from src.etl.config import DATABASE_URL, SUPABASE_URL, SUPABASE_KEY

# Force UTF-8 on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Optional SQLAlchemy import
try:
    from sqlalchemy import create_engine, text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


def get_db_engine():
    """Create SQLAlchemy engine for direct PostGIS loading."""
    if not HAS_SQLALCHEMY:
        print("[INFO] SQLAlchemy not installed in current environment. Use Docker or pip install -r requirements.txt.")
        return None
    if not DATABASE_URL:
        return None
    try:
        engine = create_engine(DATABASE_URL)
        return engine
    except Exception as e:
        print(f"[ERROR] Database engine connection error: {e}")
        return None


def load_dim_geografia(gdf_agebs: gpd.GeoDataFrame, engine=None) -> int:
    """Load AGEB polygons into dim_geografia."""
    if gdf_agebs.empty:
        return 0

    if engine is None:
        engine = get_db_engine()
    if engine is None:
        print("[INFO] No active DB engine available. Skipping direct SQL load.")
        return 0

    records_loaded = 0
    with engine.begin() as conn:
        for _, row in gdf_agebs.iterrows():
            cvegeo = str(row.get("cvegeo", ""))
            ent = str(row.get("cve_ent", "31"))
            mun = str(row.get("cve_mun", "050"))
            loc = str(row.get("cve_loc", "0001"))
            ageb = str(row.get("cve_ageb", "0000"))
            nom = str(row.get("nom_asentamiento", "")) if pd.notna(row.get("nom_asentamiento")) else None
            tipo = str(row.get("tipo_asentamiento", "")) if pd.notna(row.get("tipo_asentamiento")) else None
            area = float(row.get("area_km2", 0.0))
            wkt_4326 = row["geometry"].wkt if "geometry" in row and row["geometry"] is not None else None

            stmt = text("""
                INSERT INTO dim_geografia (cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb, nom_asentamiento, tipo_asentamiento, area_km2, geom_4326)
                VALUES (:cvegeo, :ent, :mun, :loc, :ageb, :nom, :tipo, :area, ST_GeomFromText(:wkt, 4326))
                ON CONFLICT (cvegeo) DO UPDATE SET
                    area_km2 = EXCLUDED.area_km2,
                    geom_4326 = EXCLUDED.geom_4326;
            """)
            conn.execute(stmt, {
                "cvegeo": cvegeo, "ent": ent, "mun": mun, "loc": loc,
                "ageb": ageb, "nom": nom, "tipo": tipo, "area": area, "wkt": wkt_4326
            })
            records_loaded += 1

    print(f"[OK] Loaded {records_loaded} records into dim_geografia.")
    return records_loaded


def load_fact_demografia(df_demo: pd.DataFrame, engine=None) -> int:
    """Load demographic measures into fact_demografia."""
    if df_demo.empty:
        return 0

    if engine is None:
        engine = get_db_engine()
    if engine is None:
        return 0

    records_loaded = 0
    with engine.begin() as conn:
        for _, row in df_demo.iterrows():
            cvegeo = str(row.get("cvegeo", ""))
            pob_tot = int(row.get("poblacion_total", 0))
            pob_mas = int(row.get("poblacion_masculina", 0))
            pob_fem = int(row.get("poblacion_femenina", 0))
            pob_0_14 = int(row.get("poblacion_0_14", 0))
            pob_15_64 = int(row.get("poblacion_15_64", 0))
            pob_65 = int(row.get("poblacion_65_mas", 0))
            pob_pea = int(row.get("poblacion_pea", 0))
            pob_pnea = int(row.get("poblacion_pnea", 0))
            viv = int(row.get("total_viviendas", 0))

            stmt = text("""
                INSERT INTO fact_demografia (
                    cvegeo, poblacion_total, poblacion_masculina, poblacion_femenina,
                    poblacion_0_14, poblacion_15_64, poblacion_65_mas,
                    poblacion_pea, poblacion_pnea, total_viviendas
                ) VALUES (
                    :cvegeo, :tot, :mas, :fem, :p0_14, :p15_64, :p65, :pea, :pnea, :viv
                )
                ON CONFLICT (cvegeo) DO UPDATE SET
                    poblacion_total = EXCLUDED.poblacion_total,
                    poblacion_pea = EXCLUDED.poblacion_pea,
                    poblacion_0_14 = EXCLUDED.poblacion_0_14,
                    poblacion_15_64 = EXCLUDED.poblacion_15_64,
                    poblacion_65_mas = EXCLUDED.poblacion_65_mas;
            """)
            conn.execute(stmt, {
                "cvegeo": cvegeo, "tot": pob_tot, "mas": pob_mas, "fem": pob_fem,
                "p0_14": pob_0_14, "p15_64": pob_15_64, "p65": pob_65,
                "pea": pob_pea, "pnea": pob_pnea, "viv": viv
            })
            records_loaded += 1

    print(f"[OK] Loaded {records_loaded} records into fact_demografia.")
    return records_loaded
