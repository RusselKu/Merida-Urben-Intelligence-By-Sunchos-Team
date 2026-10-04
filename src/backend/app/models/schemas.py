from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class WeightsType(str, Enum):
    QUEEN = "queen"
    ROOK = "rook"
    KNN = "knn"


class KPIVariableInfo(BaseModel):
    name: str = Field(..., description="Column variable name in spatial dataset")
    label: str = Field(..., description="Human-readable title")
    category: str = Field(..., description="Category: Demographics, Economic, Safety")
    description: str = Field(..., description="Detailed description of the metric")
    unit: str = Field(..., description="Measurement unit (e.g. hab/km2, %, count)")


class KPIListResponse(BaseModel):
    total: int
    variables: List[KPIVariableInfo]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    database_connected: bool
    data_source: str
    total_agebs: int


# --- Global Moran's I Schemas ---

class GlobalMoranRequest(BaseModel):
    variable: str = Field(
        default="densidad_poblacion_km2",
        description="Target variable for Global Moran's I analysis"
    )
    weights_type: WeightsType = Field(
        default=WeightsType.QUEEN,
        description="Spatial weights matrix construct (queen, rook, knn)"
    )
    k_neighbors: int = Field(default=4, ge=1, le=20, description="K neighbors if weights_type is knn")
    permutations: int = Field(default=999, ge=99, le=9999, description="Permutations for p-value estimation")


class GlobalMoranResponse(BaseModel):
    variable: str
    observations_count: int
    moran_i: float = Field(..., description="Global Moran's I statistic [-1 to 1]")
    expected_i: float = Field(..., description="Expected value E[I] under spatial randomness")
    z_score: float = Field(..., description="Z-score statistic")
    p_value_norm: float = Field(..., description="p-value based on normal distribution assumption")
    p_value_sim: float = Field(..., description="Pseudo p-value from monte carlo permutations")
    is_statistically_significant: bool = Field(..., description="True if p_value_sim <= 0.05")
    interpretation: str = Field(..., description="Clustered, Dispersed, or Random spatial pattern")


# --- Local Moran's I / LISA Schemas ---

class LocalMoranItem(BaseModel):
    cvegeo: str
    nom_asentamiento: Optional[str] = None
    observed_value: float
    local_i: float
    z_score: float
    p_value: float
    quadrant_code: int = Field(..., description="1: High-High, 2: Low-High, 3: Low-Low, 4: High-Low")
    cluster_type: str = Field(..., description="High-High, Low-Low, High-Low, Low-High, Not Significant")


class LocalMoranRequest(BaseModel):
    variable: str = Field(
        default="densidad_poblacion_km2",
        description="Target variable for Local Moran's I (LISA)"
    )
    weights_type: WeightsType = Field(
        default=WeightsType.QUEEN,
        description="Spatial weights matrix construct"
    )
    k_neighbors: int = Field(default=4, ge=1, le=20)
    alpha: float = Field(default=0.05, ge=0.001, le=0.2, description="Significance threshold alpha")
    permutations: int = Field(default=999, ge=99, le=9999)
    include_geojson: bool = Field(default=False, description="Whether to attach full GeoJSON with LISA properties")


class LocalMoranResponse(BaseModel):
    variable: str
    alpha: float
    total_observations: int
    cluster_counts: Dict[str, int] = Field(
        ...,
        description="Summary count per cluster type: High-High, Low-Low, High-Low, Low-High, Not Significant"
    )
    results: List[LocalMoranItem]
    geojson: Optional[Dict[str, Any]] = None


# --- Bivariate Moran's I Schemas ---

class BivariateMoranRequest(BaseModel):
    variable_x: str = Field(
        default="densidad_poblacion_km2",
        description="Primary variable X (e.g. Population Density)"
    )
    variable_y: str = Field(
        default="densidad_negocios_km2",
        description="Secondary spatial lag variable Y (e.g. Business Density)"
    )
    weights_type: WeightsType = Field(default=WeightsType.QUEEN)
    k_neighbors: int = Field(default=4, ge=1, le=20)
    alpha: float = Field(default=0.05, ge=0.001, le=0.2)
    permutations: int = Field(default=999, ge=99, le=9999)
    include_geojson: bool = Field(default=False)


class BivariateMoranResponse(BaseModel):
    variable_x: str
    variable_y: str
    total_observations: int
    global_bivariate_i: float
    z_score: float
    p_value_sim: float
    is_statistically_significant: bool
    interpretation: str
    cluster_counts: Dict[str, int]
    results: List[LocalMoranItem]
    geojson: Optional[Dict[str, Any]] = None
