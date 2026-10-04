import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env if present
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Project Paths
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUTS_MAPS_DIR = BASE_DIR / "outputs" / "maps"
OUTPUTS_FIGURES_DIR = BASE_DIR / "outputs" / "figures"

# Supabase Credentials
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Direct PostgreSQL Connection
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Coordinate Reference Systems
CRS_WGS84 = "EPSG:4326"        # Geographic Coordinates (GPS / GeoJSON / MapLibre)
CRS_METRIC_MEXICO = "EPSG:6372"  # Projected Conformal Conic (Accurate Area & Distance in Mexico)
CRS_UTM16N = "EPSG:32616"       # UTM Zone 16N (Yucatán Peninsula metric projection)

# Geographic Constraints
CVE_ENT_YUCATAN = "31"
CVE_MUN_MERIDA = "050"
