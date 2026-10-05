"""
Download Official SESNSP Crime Incident Data for Mérida, Yucatán.
Source: Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública (SESNSP)
Portal: Datos Abiertos gob.mx (https://datos.gob.mx)
Dataset: Incidencia Delictiva Municipal (IDM)
"""

import json
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path
import pandas as pd

# Reconfigure console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.etl.config import DATA_RAW_DIR, CVE_MUN_MERIDA

# CKAN Resource ID for SESNSP Incidencia Delictiva Municipal on datos.gob.mx
RESOURCE_ID = "57fbd692-3e5c-4b1b-8621-694cb3a33035"
CKAN_DATASTORE_URL = "https://datos.gob.mx/api/3/action/datastore_search"


def download_official_merida_crime() -> Path:
    """Download official SESNSP crime dataset for Mérida (Cve 31050) from datos.gob.mx."""
    crime_dir = DATA_RAW_DIR / "crime"
    crime_dir.mkdir(parents=True, exist_ok=True)
    out_file = crime_dir / "sesnsp_incidencia_delictiva_merida.csv"

    print(f"\n[DOWNLOAD] Querying official SESNSP open data API for Mérida (31050)...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    filters = {"Cve. Municipio": 31050}
    params = urllib.parse.urlencode({
        "resource_id": RESOURCE_ID,
        "filters": json.dumps(filters),
        "limit": 5000
    })
    url = f"{CKAN_DATASTORE_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        data = json.loads(resp.read().decode("utf-8"))
        records = data.get("result", {}).get("records", [])

        if not records:
            raise ValueError("No records returned from SESNSP CKAN datastore.")

        df = pd.DataFrame(records)
        df.to_csv(out_file, index=False, encoding="utf-8")
        print(f"[OK] Downloaded {len(df):,} official crime series rows for Mérida to {out_file.name}")
        return out_file

    except Exception as e:
        print(f"[ERROR] Failed downloading SESNSP data: {e}")
        raise e


if __name__ == "__main__":
    download_official_merida_crime()
