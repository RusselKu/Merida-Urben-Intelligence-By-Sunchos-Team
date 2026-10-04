import os
import json
import time
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon, mapping
from dotenv import load_dotenv

from src.etl.extract import load_raw_cartography, load_raw_demographics, load_raw_denue
from src.etl.transform import standardize_ageb_geometries, clean_census_demographics, process_denue

load_dotenv()
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def post_batch(table: str, data: list, conflict_key: str, chunk_size: int = 100):
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={conflict_key}"
    total = len(data)
    print(f"\n[LOAD] Uploading {total} records to '{table}' in batches of {chunk_size} (on_conflict={conflict_key})...")
    
    for i in range(0, total, chunk_size):
        chunk = data[i:i + chunk_size]
        res = requests.post(url, headers=HEADERS, json=chunk)
        if res.status_code not in (200, 201):
            print(f"ERROR on {table} batch {i}-{i+len(chunk)}: {res.status_code} - {res.text}")
            raise RuntimeError(f"Failed to insert into {table}: {res.text}")
        print(f"  -> Inserted batch {min(i + len(chunk), total)} / {total} (status: {res.status_code})")
    print(f"[OK] Completed upload to '{table}'.")

def run_etl_pipeline():
    print("=" * 60)
    print("STARTING FULL END-TO-END MERIDA DATA WAREHOUSE ETL")
    print("=" * 60)
    
    # 1. EXTRACT & TRANSFORM CARTOGRAPHY
    print("\n--- Phase 1: Cartography (dim_geografia) ---")
    gdf_agebs = standardize_ageb_geometries(load_raw_cartography())
    print(f"Standardized {len(gdf_agebs)} urban AGEBs.")
    
    geo_records = []
    for _, r in gdf_agebs.iterrows():
        geom = r['geometry']
        if geom.geom_type == 'Polygon':
            geom = MultiPolygon([geom])
        geojson = mapping(geom)
        geojson["crs"] = {"type": "name", "properties": {"name": "EPSG:4326"}}
        
        geo_records.append({
            "cvegeo": str(r['cvegeo']),
            "cve_ent": str(r['cve_ent']),
            "cve_mun": str(r['cve_mun']),
            "cve_loc": str(r['cve_loc']),
            "cve_ageb": str(r['cve_ageb']),
            "nom_asentamiento": "Merida Urbana",
            "tipo_asentamiento": "AGEB Urbana",
            "area_km2": round(float(r['area_km2']), 4),
            "geom_4326": json.dumps(geojson)
        })
    post_batch("dim_geografia", geo_records, conflict_key="cvegeo", chunk_size=50)

    # 2. EXTRACT & TRANSFORM DEMOGRAPHICS (CPV 2020 - PR #2 FIX)
    print("\n--- Phase 2: Demographics (fact_demografia) ---")
    df_demo = clean_census_demographics(load_raw_demographics())
    print(f"Cleaned {len(df_demo)} demographic AGEB rows.")
    
    demo_records = []
    for _, r in df_demo.iterrows():
        demo_records.append({
            "cvegeo": str(r['cvegeo']),
            "poblacion_total": int(r['poblacion_total']),
            "poblacion_masculina": int(r['poblacion_masculina']),
            "poblacion_femenina": int(r['poblacion_femenina']),
            "poblacion_0_14": int(r['poblacion_0_14']),
            "poblacion_15_64": int(r['poblacion_15_64']),
            "poblacion_65_mas": int(r['poblacion_65_mas']),
            "poblacion_pea": int(r['poblacion_pea']),
            "poblacion_pnea": int(r['poblacion_pnea']),
            "total_viviendas": int(r['total_viviendas'])
        })
    post_batch("fact_demografia", demo_records, conflict_key="cvegeo", chunk_size=100)

    # 3. EXTRACT & TRANSFORM SCIAN & DENUE BUSINESSES
    print("\n--- Phase 3: DENUE & SCIAN (dim_actividad_economica & fact_negocios) ---")
    df_scian, df_fact_neg = process_denue(load_raw_denue(), gdf_agebs)
    print(f"Processed {len(df_scian)} SCIAN activities and {len(df_fact_neg)} business establishments.")

    scian_records = []
    for _, r in df_scian.iterrows():
        scian_records.append({
            "scian_id": str(r['scian_id']),
            "codigo_actividad": str(r['codigo_actividad']),
            "sector_codigo": str(r['sector_codigo']),
            "sector_nombre": str(r['sector_nombre']),
            "categoria_macro": str(r['categoria_macro'])
        })
    post_batch("dim_actividad_economica", scian_records, conflict_key="scian_id", chunk_size=200)

    neg_records = []
    for _, r in df_fact_neg.iterrows():
        lat = round(float(r['latitud']), 6)
        lon = round(float(r['longitud']), 6)
        point_geojson = {
            "type": "Point",
            "coordinates": [lon, lat],
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}
        }
        neg_records.append({
            "cvegeo": str(r['cvegeo']),
            "scian_id": str(r['scian_id']),
            "nombre_establecimiento": str(r['nombre_establecimiento'])[:255] if pd.notna(r['nombre_establecimiento']) else "Establecimiento",
            "estrato_personal": str(r['estrato_personal']) if pd.notna(r['estrato_personal']) else "1 a 5 personas",
            "geom_punto": json.dumps(point_geojson)
        })
    
    # Upload fact_negocios in batches of 1000
    url_neg = f"{SUPABASE_URL}/rest/v1/fact_negocios"
    total_neg = len(neg_records)
    print(f"\n[LOAD] Uploading {total_neg} businesses to 'fact_negocios' in batches of 1000...")
    for i in range(0, total_neg, 1000):
        chunk = neg_records[i:i + 1000]
        res = requests.post(url_neg, headers=HEADERS, json=chunk)
        if res.status_code not in (200, 201):
            print(f"ERROR on fact_negocios batch {i}-{i+len(chunk)}: {res.status_code} - {res.text}")
            raise RuntimeError(f"Failed to insert into fact_negocios: {res.text}")
        print(f"  -> Inserted batch {min(i + len(chunk), total_neg)} / {total_neg} (status: {res.status_code})")
    print("[OK] Completed upload to 'fact_negocios'.")

    print("\n" + "=" * 60)
    print("ETL PIPELINE SUCCESSFULLY EXECUTED AND WAREHOUSE RELOADED!")
    print("=" * 60)

if __name__ == "__main__":
    start_time = time.time()
    run_etl_pipeline()
    print(f"Elapsed time: {time.time() - start_time:.2f} seconds")
