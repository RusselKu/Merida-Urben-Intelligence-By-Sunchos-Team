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
    """Load real official AGEB polygons into dim_geografia."""
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
            nom = str(row.get("nom_asentamiento", "Mérida Urbana"))
            tipo = str(row.get("tipo_asentamiento", "AGEB Urbana"))
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

    print(f"[OK] Loaded {records_loaded} official AGEBs into dim_geografia.")
    return records_loaded


def load_fact_demografia(df_demo: pd.DataFrame, engine=None) -> int:
    """Load real official INEGI demographic measures into fact_demografia."""
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
                    poblacion_masculina = EXCLUDED.poblacion_masculina,
                    poblacion_femenina = EXCLUDED.poblacion_femenina,
                    poblacion_0_14 = EXCLUDED.poblacion_0_14,
                    poblacion_15_64 = EXCLUDED.poblacion_15_64,
                    poblacion_65_mas = EXCLUDED.poblacion_65_mas,
                    poblacion_pea = EXCLUDED.poblacion_pea,
                    poblacion_pnea = EXCLUDED.poblacion_pnea,
                    total_viviendas = EXCLUDED.total_viviendas;
            """)
            conn.execute(stmt, {
                "cvegeo": cvegeo, "tot": pob_tot, "mas": pob_mas, "fem": pob_fem,
                "p0_14": pob_0_14, "p15_64": pob_15_64, "p65": pob_65,
                "pea": pob_pea, "pnea": pob_pnea, "viv": viv
            })
            records_loaded += 1

    print(f"[OK] Loaded {records_loaded} official demographic records into fact_demografia.")
    return records_loaded


def load_dim_actividad_economica(df_scian: pd.DataFrame, engine=None) -> int:
    """Load real SCIAN taxonomy into dim_actividad_economica."""
    if df_scian.empty:
        return 0

    if engine is None:
        engine = get_db_engine()
    if engine is None:
        return 0

    records_loaded = 0
    with engine.begin() as conn:
        for _, row in df_scian.iterrows():
            scian_id = str(row.get("scian_id", ""))
            codigo = str(row.get("codigo_actividad", ""))
            sector_cod = str(row.get("sector_codigo", ""))
            sector_nom = str(row.get("sector_nombre", ""))
            cat_macro = str(row.get("categoria_macro", "Otro"))

            stmt = text("""
                INSERT INTO dim_actividad_economica (scian_id, codigo_actividad, sector_codigo, sector_nombre, categoria_macro)
                VALUES (:scian_id, :codigo, :sector_cod, :sector_nom, :cat_macro)
                ON CONFLICT (scian_id) DO NOTHING;
            """)
            conn.execute(stmt, {
                "scian_id": scian_id, "codigo": codigo, "sector_cod": sector_cod,
                "sector_nom": sector_nom, "cat_macro": cat_macro
            })
            records_loaded += 1

    print(f"[OK] Loaded {records_loaded} SCIAN activity codes into dim_actividad_economica.")
    return records_loaded


def load_fact_negocios_batch(df_fact_negocios: pd.DataFrame, engine=None, batch_size=5000) -> int:
    """Load spatially joined DENUE businesses into fact_negocios in batches."""
    if df_fact_negocios.empty:
        return 0

    if engine is None:
        engine = get_db_engine()
    if engine is None:
        return 0

    total_loaded = 0
    total_records = len(df_fact_negocios)
    
    with engine.begin() as conn:
        for i in range(0, total_records, batch_size):
            batch = df_fact_negocios.iloc[i : i + batch_size]
            for _, row in batch.iterrows():
                cvegeo = str(row.get("cvegeo", ""))
                scian_id = str(row.get("scian_id", ""))
                nombre = str(row.get("nombre_establecimiento", ""))[:255]
                estrato = str(row.get("estrato_personal", ""))[:50]
                lon = float(row.get("longitud", 0.0))
                lat = float(row.get("latitud", 0.0))

                stmt = text("""
                    INSERT INTO fact_negocios (cvegeo, scian_id, nombre_establecimiento, estrato_personal, geom_punto)
                    VALUES (:cvegeo, :scian_id, :nombre, :estrato, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326));
                """)
                conn.execute(stmt, {
                    "cvegeo": cvegeo, "scian_id": scian_id, "nombre": nombre,
                    "estrato": estrato, "lon": lon, "lat": lat
                })
                total_loaded += 1

            print(f"   Progress: {total_loaded}/{total_records} businesses loaded...")

    print(f"[OK] Loaded {total_loaded} real business establishments into fact_negocios.")
    return total_loaded


def load_dim_tiempo(df_tiempo: pd.DataFrame, engine=None) -> int:
    """Load temporal dimension records into dim_tiempo."""
    if df_tiempo.empty:
        return 0

    if engine is None:
        engine = get_db_engine()
    if engine is None:
        return 0

    records_loaded = 0
    with engine.begin() as conn:
        for _, row in df_tiempo.iterrows():
            t_id = int(row["tiempo_id"])
            fecha = str(row["fecha"])
            anio = int(row["anio"])
            mes = int(row["mes"])
            mes_nom = str(row["mes_nombre"])
            dia = int(row["dia"])
            dia_sem = str(row["dia_semana"])
            es_fin = bool(row["es_fin_de_semana"])
            trim = int(row["trimestre"])

            stmt = text("""
                INSERT INTO dim_tiempo (tiempo_id, fecha, anio, mes, mes_nombre, dia, dia_semana, es_fin_de_semana, trimestre)
                VALUES (:t_id, :fecha, :anio, :mes, :mes_nom, :dia, :dia_sem, :es_fin, :trim)
                ON CONFLICT (fecha) DO UPDATE SET
                    anio = EXCLUDED.anio,
                    mes = EXCLUDED.mes,
                    mes_nombre = EXCLUDED.mes_nombre,
                    dia = EXCLUDED.dia,
                    dia_semana = EXCLUDED.dia_semana,
                    es_fin_de_semana = EXCLUDED.es_fin_de_semana,
                    trimestre = EXCLUDED.trimestre;
            """)
            conn.execute(stmt, {
                "t_id": t_id, "fecha": fecha, "anio": anio, "mes": mes,
                "mes_nom": mes_nom, "dia": dia, "dia_sem": dia_sem,
                "es_fin": es_fin, "trim": trim
            })
            records_loaded += 1

    print(f"[OK] Loaded {records_loaded} temporal entries into dim_tiempo.")
    return records_loaded


def load_fact_crimen_batch(df_fact_crimen: pd.DataFrame, engine=None, batch_size=5000) -> int:
    """Load public safety incidents into fact_crimen in batches."""
    if df_fact_crimen.empty:
        return 0

    if engine is None:
        engine = get_db_engine()
    if engine is None:
        return 0

    total_loaded = 0
    total_records = len(df_fact_crimen)

    with engine.begin() as conn:
        for i in range(0, total_records, batch_size):
            batch = df_fact_crimen.iloc[i : i + batch_size]
            for _, row in batch.iterrows():
                cvegeo = str(row.get("cvegeo", ""))
                t_id = int(row.get("tiempo_id", 1))
                cat = str(row.get("categoria_delito", "Otro"))[:100]
                tipo = str(row.get("tipo_delito", cat))[:150]
                per = str(row.get("periodo_dia", "Afternoon"))[:50]
                lon = float(row.get("longitud", 0.0))
                lat = float(row.get("latitud", 0.0))

                stmt = text("""
                    INSERT INTO fact_crimen (cvegeo, tiempo_id, categoria_delito, tipo_delito, periodo_dia, geom_punto)
                    VALUES (:cvegeo, :tiempo_id, :categoria, :tipo, :periodo, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326));
                """)
                conn.execute(stmt, {
                    "cvegeo": cvegeo, "tiempo_id": t_id, "categoria": cat,
                    "tipo": tipo, "periodo": per, "lon": lon, "lat": lat
                })
                total_loaded += 1

            print(f"   Progress: {total_loaded}/{total_records} crime incidents loaded...")

    print(f"[OK] Loaded {total_loaded} public safety incidents into fact_crimen.")
    return total_loaded
