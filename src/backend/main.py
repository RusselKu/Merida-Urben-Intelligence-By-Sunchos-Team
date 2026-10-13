"""
Mérida Urban Intelligence - FastAPI Application Entrypoint Proxy.
Allows launching the API directly via:
  uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
  python src/backend/main.py
"""
import os
import sys
from pathlib import Path

# Ensure src/backend is on sys.path so app.* modules resolve correctly
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        app_dir=str(_backend_dir)
    )
