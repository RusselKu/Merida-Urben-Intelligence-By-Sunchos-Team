import os
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root path calculation
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
FALLBACK_GEOJSON = BASE_DIR / "outputs" / "maps" / "merida_agebs_demographics.geojson"


class Settings(BaseSettings):
    """
    Application Settings for Mérida Urban Intelligence Backend.
    Reads environment variables from .env file or environment.
    """
    PROJECT_NAME: str = "Mérida Urban Intelligence API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = ["*"]
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database & Supabase connection
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        description="PostgreSQL / PostGIS connection string"
    )
    SUPABASE_URL: str = Field(default="", description="Supabase Project URL")
    SUPABASE_KEY: str = Field(default="", description="Supabase Publishable/Anon/Service Key")
    
    # Spatial data fallback path
    GEOJSON_PATH: str = str(FALLBACK_GEOJSON)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
