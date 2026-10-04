"""
Export real INEGI datasets (Cartography, Demographics, SCIAN) to SQL insert script.
"""

import sys
from pathlib import Path

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.etl.extract import load_raw_demographics, load_raw_denue, load_raw_cartography
from src.etl.transform import standardize_ageb_geometries, clean_census_demographics, process_denue

print("[INFO] Transforming real INEGI datasets...")

# 1. Cartography
gdf_agebs = standardize_ageb_geometries(load_raw_cartography())

# 2. Census Demographics
df_demo = clean_census_demographics(load_raw_demographics())

# 3. DENUE SCIAN & Businesses
df_scian, df_fact_neg = process_denue(load_raw_denue(), gdf_agebs)

lines = ["SET search_path TO public, extensions, topology;\n"]

# 1. SCIAN Activities
lines.append("-- 1. Load SCIAN Activities")
for _, r in df_scian.iterrows():
    s_id = str(r['scian_id']).replace("'", "''")
    cod = str(r['codigo_actividad']).replace("'", "''")
    sec_cod = str(r['sector_codigo']).replace("'", "''")
    sec_nom = str(r['sector_nombre']).replace("'", "''")
    cat = str(r['categoria_macro']).replace("'", "''")
    lines.append(f"INSERT INTO dim_actividad_economica (scian_id, codigo_actividad, sector_codigo, sector_nombre, categoria_macro) VALUES ('{s_id}', '{cod}', '{sec_cod}', '{sec_nom}', '{cat}') ON CONFLICT (scian_id) DO NOTHING;")

# 2. Dim Geografia
lines.append("\n-- 2. Load Real AGEB Polygons")
for _, r in gdf_agebs.iterrows():
    cve = str(r['cvegeo'])
    ent = str(r['cve_ent'])
    mun = str(r['cve_mun'])
    loc = str(r['cve_loc'])
    ageb = str(r['cve_ageb'])
    nom = str(r['nom_asentamiento']).replace("'", "''")
    tipo = str(r['tipo_asentamiento']).replace("'", "''")
    area = float(r['area_km2'])
    wkt = r['geometry'].wkt
    lines.append(f"INSERT INTO dim_geografia (cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb, nom_asentamiento, tipo_asentamiento, area_km2, geom_4326) VALUES ('{cve}', '{ent}', '{mun}', '{loc}', '{ageb}', '{nom}', '{tipo}', {area}, ST_GeomFromText('{wkt}', 4326)) ON CONFLICT (cvegeo) DO UPDATE SET area_km2 = EXCLUDED.area_km2, geom_4326 = EXCLUDED.geom_4326;")

# 3. Fact Demografia
lines.append("\n-- 3. Load Real Census Demographics")
for _, r in df_demo.iterrows():
    cve = str(r['cvegeo'])
    p_tot = int(r['poblacion_total'])
    p_mas = int(r['poblacion_masculina'])
    p_fem = int(r['poblacion_femenina'])
    p_0_14 = int(r['poblacion_0_14'])
    p_15_64 = int(r['poblacion_15_64'])
    p_65 = int(r['poblacion_65_mas'])
    p_pea = int(r['poblacion_pea'])
    p_pnea = int(r['poblacion_pnea'])
    viv = int(r['total_viviendas'])
    lines.append(f"INSERT INTO fact_demografia (cvegeo, poblacion_total, poblacion_masculina, poblacion_femenina, poblacion_0_14, poblacion_15_64, poblacion_65_mas, poblacion_pea, poblacion_pnea, total_viviendas) VALUES ('{cve}', {p_tot}, {p_mas}, {p_fem}, {p_0_14}, {p_15_64}, {p_65}, {p_pea}, {p_pnea}, {viv}) ON CONFLICT (cvegeo) DO UPDATE SET poblacion_total = EXCLUDED.poblacion_total, poblacion_masculina = EXCLUDED.poblacion_masculina, poblacion_femenina = EXCLUDED.poblacion_femenina, poblacion_0_14 = EXCLUDED.poblacion_0_14, poblacion_15_64 = EXCLUDED.poblacion_15_64, poblacion_65_mas = EXCLUDED.poblacion_65_mas, poblacion_pea = EXCLUDED.poblacion_pea, poblacion_pnea = EXCLUDED.poblacion_pnea, total_viviendas = EXCLUDED.total_viviendas;")

out_file = Path("sql/02_load_real_inegi_data.sql")
out_file.write_text("\n".join(lines), encoding="utf-8")
file_size_mb = out_file.stat().st_size / (1024 * 1024)
print(f"[OK] Generated {out_file.name} ({file_size_mb:.2f} MB, {len(lines)} statements)")
