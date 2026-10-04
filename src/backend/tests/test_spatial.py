import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add src/backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["total_agebs"] > 0


def test_list_kpis():
    response = client.get("/api/v1/spatial/kpis")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert any(var["name"] == "densidad_poblacion_km2" for var in data["variables"])


def test_global_moran():
    payload = {
        "variable": "densidad_poblacion_km2",
        "weights_type": "queen",
        "permutations": 99
    }
    response = client.post("/api/v1/spatial/moran/global", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["variable"] == "densidad_poblacion_km2"
    assert "moran_i" in data
    assert "z_score" in data
    assert "interpretation" in data


def test_local_moran():
    payload = {
        "variable": "densidad_poblacion_km2",
        "weights_type": "queen",
        "alpha": 0.05,
        "permutations": 99,
        "include_geojson": False
    }
    response = client.post("/api/v1/spatial/moran/local", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_observations"] > 0
    assert "High-High" in data["cluster_counts"]
    assert "Low-Low" in data["cluster_counts"]
    assert len(data["results"]) == data["total_observations"]


def test_bivariate_moran():
    payload = {
        "variable_x": "densidad_poblacion_km2",
        "variable_y": "densidad_negocios_km2",
        "weights_type": "queen",
        "alpha": 0.05,
        "permutations": 99
    }
    response = client.post("/api/v1/spatial/moran/bivariate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["variable_x"] == "densidad_poblacion_km2"
    assert data["variable_y"] == "densidad_negocios_km2"
    assert "global_bivariate_i" in data


def test_spatial_summary():
    response = client.get("/api/v1/spatial/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_agebs"] > 0
    assert "densidad_poblacion_km2" in data["spatial_autocorrelation_summary"]
