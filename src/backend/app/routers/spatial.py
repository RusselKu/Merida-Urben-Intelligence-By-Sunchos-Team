import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.core.database import load_spatial_dataset
from app.models.schemas import (
    KPIListResponse,
    GlobalMoranRequest, GlobalMoranResponse,
    LocalMoranRequest, LocalMoranResponse,
    BivariateMoranRequest, BivariateMoranResponse
)
from app.services.spatial_service import (
    get_available_kpis,
    calculate_global_moran,
    calculate_local_moran,
    calculate_bivariate_moran
)

router = APIRouter(prefix="/spatial", tags=["Spatial Autocorrelation (Moran's I)"])


@router.get("/kpis", response_model=KPIListResponse)
def list_spatial_kpis():
    """Returns the list of urban KPIs available for spatial statistical analysis."""
    return get_available_kpis()


@router.get("/geojson")
def get_spatial_geojson():
    """
    Returns the complete GeoJSON of Mérida AGEBs enriched with demographic & economic metrics.
    Can be loaded directly into MapLibre GL JS frontend.
    """
    try:
        gdf = load_spatial_dataset()
        # Drop raw heavy geometry objects if any non-jsonable types exist
        return json.loads(gdf.to_json())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate spatial GeoJSON: {str(e)}")


@router.post("/moran/global", response_model=GlobalMoranResponse)
def compute_global_moran_endpoint(request: GlobalMoranRequest):
    """
    Calculates Global Moran's I statistic for a selected territorial metric.
    Measures overall spatial clustering or dispersion across Mérida.
    """
    try:
        gdf = load_spatial_dataset()
        return calculate_global_moran(
            gdf=gdf,
            variable=request.variable,
            weights_type=request.weights_type,
            k_neighbors=request.k_neighbors,
            permutations=request.permutations
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing Global Moran's I: {str(e)}")


@router.post("/moran/local", response_model=LocalMoranResponse)
def compute_local_moran_endpoint(request: LocalMoranRequest):
    """
    Calculates Local Indicators of Spatial Association (LISA / Local Moran's I).
    Identifies High-High (Hotspots), Low-Low (Coldspots), and spatial outliers per AGEB.
    """
    try:
        gdf = load_spatial_dataset()
        return calculate_local_moran(
            gdf=gdf,
            variable=request.variable,
            weights_type=request.weights_type,
            k_neighbors=request.k_neighbors,
            alpha=request.alpha,
            permutations=request.permutations,
            include_geojson=request.include_geojson
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing Local Moran's I: {str(e)}")


@router.post("/moran/bivariate", response_model=BivariateMoranResponse)
def compute_bivariate_moran_endpoint(request: BivariateMoranRequest):
    """
    Calculates Bivariate Moran's I to analyze spatial cross-correlation.
    Example: Variable X (Delitos or Negocios) vs Spatial Lag of Variable Y (Población).
    """
    try:
        gdf = load_spatial_dataset()
        return calculate_bivariate_moran(
            gdf=gdf,
            variable_x=request.variable_x,
            variable_y=request.variable_y,
            weights_type=request.weights_type,
            k_neighbors=request.k_neighbors,
            alpha=request.alpha,
            permutations=request.permutations,
            include_geojson=request.include_geojson
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing Bivariate Moran's I: {str(e)}")


@router.get("/summary")
def get_spatial_summary():
    """
    Generates a pre-computed spatial summary report for key urban indicators in Mérida.
    """
    try:
        gdf = load_spatial_dataset()
        metrics = ["densidad_poblacion_km2", "densidad_negocios_km2", "tasa_pea_porcentaje"]
        summary = {}
        for metric in metrics:
            if metric in gdf.columns:
                try:
                    g_moran = calculate_global_moran(gdf, variable=metric, permutations=99)
                    summary[metric] = {
                        "moran_i": g_moran.moran_i,
                        "z_score": g_moran.z_score,
                        "p_value": g_moran.p_value_sim,
                        "interpretation": g_moran.interpretation
                    }
                except Exception as me:
                    summary[metric] = {"error": str(me)}
        return {"total_agebs": len(gdf), "spatial_autocorrelation_summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate spatial summary: {str(e)}")
