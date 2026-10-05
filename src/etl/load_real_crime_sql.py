"""
Generate SQL scripts for official SESNSP Crime Data (dim_tiempo & fact_crimen).
"""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.etl.extract import load_raw_crime, load_raw_cartography, load_raw_demographics
from src.etl.transform import standardize_ageb_geometries, clean_census_demographics, process_crime

print("[INFO] Transforming real SESNSP Crime Dataset for Mérida...")

df_crime_raw = load_raw_crime()
gdf_agebs = standardize_ageb_geometries(load_raw_cartography())
df_demo = clean_census_demographics(load_raw_demographics())

# Filter for official analysis window 2020-2025
df_crime_window = df_crime_raw[df_crime_raw["Ano"] >= 2020].copy()
df_tiempo, df_fact_crimen = process_crime(df_crime_window, gdf_agebs, df_demo)

print(f"[OK] Generated {len(df_tiempo)} dim_tiempo rows and {len(df_fact_crimen)} fact_crimen rows.")

# 1. Generate dim_tiempo SQL
tiempo_lines = ["SET search_path TO public, extensions, topology;\n", "-- Load dim_tiempo records"]
for _, r in df_tiempo.iterrows():
    t_id = int(r["tiempo_id"])
    fecha = str(r["fecha"])
    anio = int(r["anio"])
    mes = int(r["mes"])
    mes_nom = str(r["mes_nombre"]).replace("'", "''")
    dia = int(r["dia"])
    dia_sem = str(r["dia_semana"]).replace("'", "''")
    es_fin = "TRUE" if r["es_fin_de_semana"] else "FALSE"
    trim = int(r["trimestre"])
    tiempo_lines.append(
        f"INSERT INTO dim_tiempo (tiempo_id, fecha, anio, mes, mes_nombre, dia, dia_semana, es_fin_de_semana, trimestre) "
        f"VALUES ({t_id}, '{fecha}', {anio}, {mes}, '{mes_nom}', {dia}, '{dia_sem}', {es_fin}, {trim}) "
        f"ON CONFLICT (tiempo_id) DO NOTHING;"
    )

tiempo_file = Path("sql/02_load_tiempo.sql")
tiempo_file.write_text("\n".join(tiempo_lines), encoding="utf-8")
print(f"[OK] Saved {tiempo_file.name} ({len(tiempo_lines)} statements)")

# 2. Generate fact_crimen SQL in chunks
crime_file = Path("sql/02_load_crimen.sql")
crime_lines = ["SET search_path TO public, extensions, topology;\n", "-- Load official SESNSP fact_crimen records"]

chunk_size = 500
total = len(df_fact_crimen)
for i in range(0, total, chunk_size):
    chunk = df_fact_crimen.iloc[i : i + chunk_size]
    val_list = []
    for _, r in chunk.iterrows():
        cve = str(r["cvegeo"])
        t_id = int(r["tiempo_id"])
        cat = str(r["categoria_delito"]).replace("'", "''")[:100]
        tipo = str(r["tipo_delito"]).replace("'", "''")[:150]
        per = str(r["periodo_dia"]).replace("'", "''")[:50]
        lat = round(float(r["latitud"]), 6)
        lon = round(float(r["longitud"]), 6)
        val_list.append(f"('{cve}', {t_id}, '{cat}', '{tipo}', '{per}', ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326))")

    values_str = ",\n    ".join(val_list)
    crime_lines.append(f"INSERT INTO fact_crimen (cvegeo, tiempo_id, categoria_delito, tipo_delito, periodo_dia, geom_punto) VALUES\n    {values_str};")

crime_file.write_text("\n".join(crime_lines), encoding="utf-8")
print(f"[OK] Saved {crime_file.name} ({len(crime_lines)} multi-row insert statements, {total} total records)")
