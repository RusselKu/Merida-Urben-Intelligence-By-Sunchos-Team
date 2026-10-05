"""
Automated Downloader for Official Public Datasets:
Downloads official datasets directly from INEGI and open government repositories:
1. INEGI Censo 2020 - AGEB Urbana Yucatán (State 31)
2. INEGI DENUE - Economic Directory Yucatán (State 31)
3. INEGI Marco Geoestadístico 2020 - Official AGEB shapefiles for Yucatán (State 31)
"""

import sys
import ssl
import zipfile
import urllib.request
from pathlib import Path
from src.etl.config import DATA_RAW_DIR

# Reconfigure console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DOWNLOADS = [
    {
        "name": "INEGI Census 2020 (AGEB Urbana Yucatán)",
        "url": "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip",
        "zip_name": "census_31_ageb.zip",
        "extract_dir": "census_2020"
    },
    {
        "name": "INEGI DENUE (Economic Establishments Yucatán)",
        "url": "https://www.inegi.org.mx/contenidos/masiva/denue/denue_31_csv.zip",
        "zip_name": "denue_31.zip",
        "extract_dir": "denue"
    },
    {
        "name": "INEGI Marco Geoestadístico (Cartography Yucatán 31)",
        "url": "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/31_yucatan.zip",
        "zip_name": "cartography_31.zip",
        "extract_dir": "cartography"
    }
]


def download_and_extract():
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for item in DOWNLOADS:
        name = item["name"]
        url = item["url"]
        zip_path = DATA_RAW_DIR / item["zip_name"]
        extract_to = DATA_RAW_DIR / item["extract_dir"]

        print(f"\n[DOWNLOAD] Starting download: {name}...")
        print(f"           Source URL: {url}")
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp, open(zip_path, "wb") as f_out:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                block_size = 65536
                
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"\r           Progress: {downloaded / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB ({pct:.1f}%)", end="")
                    else:
                        print(f"\r           Downloaded: {downloaded / (1024*1024):.2f} MB", end="")
                        
            print(f"\n[OK] Download completed: {zip_path.name}")
            
            # Extract ZIP
            print(f"[EXTRACT] Extracting {zip_path.name} to {extract_to}...")
            extract_to.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_to)
            print(f"[OK] Extracted successfully.")

        except Exception as e:
            print(f"\n[ERROR] Failed downloading {name}: {e}")

    print("\n==========================================================")
    print("[COMPLETED] INEGI raw datasets downloaded & extracted.")
    print("==========================================================")

    # SESNSP Official Crime Data
    try:
        from src.etl.download_official_crime import download_crime_data
        download_crime_data()
    except Exception as e:
        print(f"[WARN] Crime data download encountered an issue: {e}")


if __name__ == "__main__":
    download_and_extract()

