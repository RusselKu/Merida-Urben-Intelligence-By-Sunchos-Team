import json
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import geopandas as gpd
import libpysal
import esda

from app.models.schemas import (
    WeightsType, KPIVariableInfo, KPIListResponse,
    GlobalMoranResponse, LocalMoranItem, LocalMoranResponse, BivariateMoranResponse
)

logger = logging.getLogger("merida_backend.spatial_service")

# Metadata catalog of supported KPIs for spatial analysis
SUPPORTED_KPIS: Dict[str, KPIVariableInfo] = {
    "poblacion_total": KPIVariableInfo(
        name="poblacion_total",
        label="Población Total",
        category="Demographics",
        description="Población total registrada por el INEGI Censo 2020",
        unit="habitantes"
    ),
    "densidad_poblacion_km2": KPIVariableInfo(
        name="densidad_poblacion_km2",
        label="Densidad Poblacional",
        category="Demographics",
        description="Población total por kilómetro cuadrado",
        unit="hab/km²"
    ),
    "tasa_pea_porcentaje": KPIVariableInfo(
        name="tasa_pea_porcentaje",
        label="Tasa de Población Económicamente Activa (PEA)",
        category="Demographics",
        description="Porcentaje de la población de 12+ años económicamente activa",
        unit="%"
    ),
    "total_negocios": KPIVariableInfo(
        name="total_negocios",
        label="Total de Establecimientos Económicos",
        category="Economic",
        description="Conteo total de unidades económicas según INEGI DENUE",
        unit="establecimientos"
    ),
    "densidad_negocios_km2": KPIVariableInfo(
        name="densidad_negocios_km2",
        label="Densidad de Establecimientos",
        category="Economic",
        description="Número de establecimientos comerciales y servicios por km²",
        unit="est/km²"
    ),
    "negocios_por_mil_hab": KPIVariableInfo(
        name="negocios_por_mil_hab",
        label="Negocios por 1,000 Habitantes",
        category="Economic",
        description="Proporción de establecimientos por cada mil residentes",
        unit="est/1k hab"
    ),
    "densidad_comercio_km2": KPIVariableInfo(
        name="densidad_comercio_km2",
        label="Densidad Comercial",
        category="Economic",
        description="Establecimientos del sector comercio (SCIAN 43, 46-47) por km²",
        unit="est/km²"
    ),
    "densidad_servicios_km2": KPIVariableInfo(
        name="densidad_servicios_km2",
        label="Densidad de Servicios",
        category="Economic",
        description="Establecimientos del sector servicios (SCIAN 51-81) por km²",
        unit="est/km²"
    ),
    "total_delitos": KPIVariableInfo(
        name="total_delitos",
        label="Total de Incidentes Delictivos",
        category="Public Safety",
        description="Conteo de incidentes de seguridad reportados por AGEB",
        unit="incidentes"
    ),
    "tasa_delictiva_por_mil_hab": KPIVariableInfo(
        name="tasa_delictiva_por_mil_hab",
        label="Tasa Delictiva por 1,000 Habitantes",
        category="Public Safety",
        description="Tasa de delitos por cada mil habitantes",
        unit="delitos/1k hab"
    ),
    "ratio_delito_por_negocio": KPIVariableInfo(
        name="ratio_delito_por_negocio",
        label="Ratio Delito por Negocio",
        category="Public Safety",
        description="Proporción de incidentes delictivos por unidad económica",
        unit="delitos/est"
    )
}


def get_available_kpis() -> KPIListResponse:
    """Returns catalog of all available metrics for spatial autocorrelation."""
    items = list(SUPPORTED_KPIS.values())
    return KPIListResponse(total=len(items), variables=items)


def build_spatial_weights(
    gdf: gpd.GeoDataFrame, 
    weights_type: WeightsType = WeightsType.QUEEN, 
    k_neighbors: int = 4
) -> libpysal.weights.W:
    """
    Constructs and row-standardizes spatial weights matrix (W) for spatial autocorrelation.
    Handles island polygons gracefully.
    """
    try:
        if weights_type == WeightsType.ROOK:
            w = libpysal.weights.Rook.from_dataframe(gdf, use_index=False, silence_warnings=True)
        elif weights_type == WeightsType.KNN:
            w = libpysal.weights.KNN.from_dataframe(gdf, k=min(k_neighbors, len(gdf)-1), use_index=False, silence_warnings=True)
        else:
            w = libpysal.weights.Queen.from_dataframe(gdf, use_index=False, silence_warnings=True)

        # Handle zero-neighbor island polygons if using Queen or Rook
        if w.islands:
            logger.info(f"Spatial weights matrix contains {len(w.islands)} island polygon(s). Resolving islands using KNN fallback.")
            knn_fallback = libpysal.weights.KNN.from_dataframe(gdf, k=min(k_neighbors, len(gdf)-1), use_index=False, silence_warnings=True)
            for island in w.islands:
                w.neighbors[island] = knn_fallback.neighbors[island]
                w.weights[island] = knn_fallback.weights[island]

        w.transform = 'r'  # Row-standardization
        return w
    except Exception as e:
        logger.warning(f"Falling back to KNN weights matrix due to: {e}")
        w = libpysal.weights.KNN.from_dataframe(gdf, k=min(k_neighbors, len(gdf)-1), use_index=False, silence_warnings=True)
        w.transform = 'r'
        return w


def calculate_global_moran(
    gdf: gpd.GeoDataFrame,
    variable: str,
    weights_type: WeightsType = WeightsType.QUEEN,
    k_neighbors: int = 4,
    permutations: int = 999
) -> GlobalMoranResponse:
    """
    Calculates Global Moran's I spatial autocorrelation statistic.
    """
    if variable not in gdf.columns:
        raise ValueError(f"Variable '{variable}' not found in spatial dataset.")

    y = gdf[variable].fillna(0).astype(float).values
    
    # Check for zero variance
    if np.std(y) == 0:
        raise ValueError(f"Variable '{variable}' has zero variance across all observations.")

    w = build_spatial_weights(gdf, weights_type, k_neighbors)
    moran = esda.moran.Moran(y, w, transformation='r', permutations=permutations)

    is_sig = float(moran.p_sim) <= 0.05

    if is_sig and moran.I > moran.EI:
        interp = "Spatial Clustering (High values tend to be near high values, low near low)"
    elif is_sig and moran.I < moran.EI:
        interp = "Spatial Dispersion (High values tend to be near low values)"
    else:
        interp = "Random Spatial Pattern (No statistically significant spatial autocorrelation)"

    return GlobalMoranResponse(
        variable=variable,
        observations_count=len(y),
        moran_i=round(float(moran.I), 4),
        expected_i=round(float(moran.EI), 4),
        z_score=round(float(moran.z_sim), 4),
        p_value_norm=round(float(moran.p_norm), 6),
        p_value_sim=round(float(moran.p_sim), 6),
        is_statistically_significant=is_sig,
        interpretation=interp
    )


def calculate_local_moran(
    gdf: gpd.GeoDataFrame,
    variable: str,
    weights_type: WeightsType = WeightsType.QUEEN,
    k_neighbors: int = 4,
    alpha: float = 0.05,
    permutations: int = 999,
    include_geojson: bool = False
) -> LocalMoranResponse:
    """
    Calculates Local Indicators of Spatial Association (LISA / Local Moran's I).
    Identifies High-High, Low-Low, High-Low, Low-High spatial clusters & outliers.
    """
    if variable not in gdf.columns:
        raise ValueError(f"Variable '{variable}' not found in spatial dataset.")

    y = gdf[variable].fillna(0).astype(float).values
    w = build_spatial_weights(gdf, weights_type, k_neighbors)
    
    lisa = esda.moran.Moran_Local(y, w, transformation='r', permutations=permutations)

    # Quadrant mapping:
    # 1: High-High, 2: Low-High, 3: Low-Low, 4: High-Low
    quadrant_names = {
        1: "High-High",
        2: "Low-High",
        3: "Low-Low",
        4: "High-Low"
    }

    results: List[LocalMoranItem] = []
    cluster_counts = {
        "High-High": 0,
        "Low-Low": 0,
        "High-Low": 0,
        "Low-High": 0,
        "Not Significant": 0
    }

    # Attach LISA properties to GeoDataFrame copy if geojson requested
    gdf_copy = gdf.copy() if include_geojson else None

    lisa_clusters = []
    lisa_pvalues = []
    lisa_zscores = []
    lisa_is = []

    for i in range(len(gdf)):
        cvegeo = str(gdf.iloc[i]['cvegeo'])
        nom = str(gdf.iloc[i].get('nom_asentamiento', '')) if 'nom_asentamiento' in gdf.columns else None
        val = float(y[i])
        local_i = float(lisa.Is[i])
        z_sc = float(lisa.z_sim[i])
        p_val = float(lisa.p_sim[i])
        q_code = int(lisa.q[i])

        if p_val <= alpha:
            c_type = quadrant_names.get(q_code, "Not Significant")
        else:
            c_type = "Not Significant"

        cluster_counts[c_type] += 1

        results.append(LocalMoranItem(
            cvegeo=cvegeo,
            nom_asentamiento=nom,
            observed_value=round(val, 2),
            local_i=round(local_i, 4),
            z_score=round(z_sc, 4),
            p_value=round(p_val, 6),
            quadrant_code=q_code,
            cluster_type=c_type
        ))

        if include_geojson:
            lisa_clusters.append(c_type)
            lisa_pvalues.append(round(p_val, 6))
            lisa_zscores.append(round(z_sc, 4))
            lisa_is.append(round(local_i, 4))

    geojson_dict = None
    if include_geojson and gdf_copy is not None:
        gdf_copy['lisa_cluster'] = lisa_clusters
        gdf_copy['lisa_pvalue'] = lisa_pvalues
        gdf_copy['lisa_zscore'] = lisa_zscores
        gdf_copy['lisa_i'] = lisa_is
        geojson_dict = json.loads(gdf_copy.to_json())

    return LocalMoranResponse(
        variable=variable,
        alpha=alpha,
        total_observations=len(y),
        cluster_counts=cluster_counts,
        results=results,
        geojson=geojson_dict
    )


def calculate_bivariate_moran(
    gdf: gpd.GeoDataFrame,
    variable_x: str,
    variable_y: str,
    weights_type: WeightsType = WeightsType.QUEEN,
    k_neighbors: int = 4,
    alpha: float = 0.05,
    permutations: int = 999,
    include_geojson: bool = False
) -> BivariateMoranResponse:
    """
    Calculates Bivariate Moran's I (Global and Local LISA) for spatial cross-correlation between X and Y.
    """
    if variable_x not in gdf.columns:
        raise ValueError(f"Variable X '{variable_x}' not found in spatial dataset.")
    if variable_y not in gdf.columns:
        raise ValueError(f"Variable Y '{variable_y}' not found in spatial dataset.")

    x = gdf[variable_x].fillna(0).astype(float).values
    y = gdf[variable_y].fillna(0).astype(float).values

    w = build_spatial_weights(gdf, weights_type, k_neighbors)

    # Global Bivariate Moran
    moran_bv = esda.moran.Moran_BV(x, y, w, transformation='r', permutations=permutations)
    # Local Bivariate Moran
    lisa_bv = esda.moran.Moran_Local_BV(x, y, w, transformation='r', permutations=permutations)

    is_sig = float(moran_bv.p_sim) <= 0.05

    if is_sig and moran_bv.I > 0:
        interp = f"Positive Spatial Relationship: High values of {variable_x} tend to be surrounded by High values of {variable_y}."
    elif is_sig and moran_bv.I < 0:
        interp = f"Negative Spatial Relationship: High values of {variable_x} tend to be surrounded by Low values of {variable_y}."
    else:
        interp = f"No statistically significant spatial association between {variable_x} and spatial lag of {variable_y}."

    quadrant_names = {
        1: "High-High",
        2: "Low-High",
        3: "Low-Low",
        4: "High-Low"
    }

    results: List[LocalMoranItem] = []
    cluster_counts = {
        "High-High": 0,
        "Low-Low": 0,
        "High-Low": 0,
        "Low-High": 0,
        "Not Significant": 0
    }

    gdf_copy = gdf.copy() if include_geojson else None
    bv_clusters = []

    for i in range(len(gdf)):
        cvegeo = str(gdf.iloc[i]['cvegeo'])
        nom = str(gdf.iloc[i].get('nom_asentamiento', '')) if 'nom_asentamiento' in gdf.columns else None
        val_x = float(x[i])
        local_i = float(lisa_bv.Is[i])
        z_sc = float(lisa_bv.z_sim[i])
        p_val = float(lisa_bv.p_sim[i])
        q_code = int(lisa_bv.q[i])

        if p_val <= alpha:
            c_type = quadrant_names.get(q_code, "Not Significant")
        else:
            c_type = "Not Significant"

        cluster_counts[c_type] += 1

        results.append(LocalMoranItem(
            cvegeo=cvegeo,
            nom_asentamiento=nom,
            observed_value=round(val_x, 2),
            local_i=round(local_i, 4),
            z_score=round(z_sc, 4),
            p_value=round(p_val, 6),
            quadrant_code=q_code,
            cluster_type=c_type
        ))

        if include_geojson:
            bv_clusters.append(c_type)

    geojson_dict = None
    if include_geojson and gdf_copy is not None:
        gdf_copy['bivariate_cluster'] = bv_clusters
        geojson_dict = json.loads(gdf_copy.to_json())

    return BivariateMoranResponse(
        variable_x=variable_x,
        variable_y=variable_y,
        total_observations=len(x),
        global_bivariate_i=round(float(moran_bv.I), 4),
        z_score=round(float(moran_bv.z_sim), 4),
        p_value_sim=round(float(moran_bv.p_sim), 6),
        is_statistically_significant=is_sig,
        interpretation=interp,
        cluster_counts=cluster_counts,
        results=results,
        geojson=geojson_dict
    )
