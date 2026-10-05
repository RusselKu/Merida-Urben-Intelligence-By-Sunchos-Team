from pathlib import Path
from datetime import datetime, timezone
import json
import tempfile
import zipfile

import geopandas as gpd
import pandas as pd


FRONTEND_DIR = Path(__file__).resolve().parents[1]

AGEB_GEOJSON = (
    FRONTEND_DIR
    / "public"
    / "data"
    / "merida_agebs_demographics.geojson"
)

# Busca el ZIP tanto en Escritorio como Desktop.
ZIP_CANDIDATES = [
    Path.home() / "Escritorio" / "31_yucatan.zip",
    Path.home() / "Desktop" / "31_yucatan.zip",
]

OUTPUT_JSON = (
    FRONTEND_DIR
    / "src"
    / "data"
    / "ageb_reference_areas.json"
)

MERIDA_MUNICIPALITY = "050"

# CRS métrico usado por el proyecto.
METRIC_CRS = "EPSG:6372"

# Ignoramos contactos mínimos de borde.
MIN_COVERAGE_PCT = 1.0

INVALID_NAMES = {
    "",
    "NINGUNO",
    "SIN NOMBRE",
    "NO APLICA",
    "N/A",
    "NONE",
}


def clean_text(value):
    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def is_valid_name(value):
    name = clean_text(value)
    return bool(name) and name.upper() not in INVALID_NAMES


def find_zip():
    for path in ZIP_CANDIDATES:
        if path.exists():
            return path

    raise FileNotFoundError(
        "No se encontró 31_yucatan.zip en Escritorio ni Desktop."
    )


def main():
    print("=== Mérida AGEB Reference Area Builder ===")
    print()

    dcah_zip = find_zip()

    if not AGEB_GEOJSON.exists():
        raise FileNotFoundError(
            f"No se encontró el GeoJSON:\n{AGEB_GEOJSON}"
        )

    print(f"AGEB source: {AGEB_GEOJSON}")
    print(f"DCAH source: {dcah_zip}")
    print()

    # --------------------------------------------------
    # 1. Cargar AGEB
    # --------------------------------------------------

    agebs = gpd.read_file(AGEB_GEOJSON)

    # Normalizar nombres de columnas.
    agebs.columns = [
        str(col).lower()
        for col in agebs.columns
    ]

    if "cvegeo" not in agebs.columns:
        raise ValueError(
            "El GeoJSON no contiene la columna 'cvegeo'."
        )

    agebs["cvegeo"] = agebs["cvegeo"].astype(str)

    agebs = agebs[
        agebs.geometry.notna()
        & ~agebs.geometry.is_empty
    ].copy()

    print(f"AGEB polygons loaded: {len(agebs):,}")

    agebs_metric = agebs.to_crs(METRIC_CRS)

    agebs_metric["ageb_area_m2"] = (
        agebs_metric.geometry.area
    )

    # --------------------------------------------------
    # 2. Abrir DCAH INEGI
    # --------------------------------------------------

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        with zipfile.ZipFile(dcah_zip, "r") as zf:
            zf.extractall(tmp_path)

        shapefiles = list(
            tmp_path.rglob("*.shp")
        )

        if not shapefiles:
            raise FileNotFoundError(
                "El ZIP no contiene ningún archivo .shp"
            )

        # Preferimos 31as.shp si existe.
        shapefile = next(
            (
                path
                for path in shapefiles
                if path.name.lower() == "31as.shp"
            ),
            shapefiles[0],
        )

        print(f"Shapefile detected: {shapefile.name}")

        settlements = gpd.read_file(shapefile)

    # Normalizar nombres de columnas.
    settlements.columns = [
        str(col).lower()
        for col in settlements.columns
    ]

    required = {
        "cvegeo",
        "cve_mun",
        "nom_asen",
        "tipo",
        "geometry",
    }

    missing = required - set(settlements.columns)

    if missing:
        raise ValueError(
            "Faltan columnas DCAH: "
            + ", ".join(sorted(missing))
        )

    # --------------------------------------------------
    # 3. Filtrar municipio Mérida
    # --------------------------------------------------

    settlements["cve_mun"] = (
        settlements["cve_mun"]
        .astype(str)
        .str.zfill(3)
    )

    settlements = settlements[
        settlements["cve_mun"]
        == MERIDA_MUNICIPALITY
    ].copy()

    settlements = settlements[
        settlements.geometry.notna()
        & ~settlements.geometry.is_empty
    ].copy()

    print(
        f"Mérida settlements loaded: "
        f"{len(settlements):,}"
    )

    settlements["nom_asen"] = (
        settlements["nom_asen"]
        .apply(clean_text)
    )

    settlements["tipo"] = (
        settlements["tipo"]
        .apply(clean_text)
    )

    if "cp" not in settlements.columns:
        settlements["cp"] = ""

    settlements["cp"] = (
        settlements["cp"]
        .apply(clean_text)
    )

    settlements = settlements.to_crs(
        METRIC_CRS
    )

    # --------------------------------------------------
    # 4. Intersección espacial
    # --------------------------------------------------

    print()
    print("Calculating spatial intersections...")

    ageb_layer = agebs_metric[
        [
            "cvegeo",
            "ageb_area_m2",
            "geometry",
        ]
    ].copy()

    settlement_layer = settlements[
        [
            "cvegeo",
            "nom_asen",
            "tipo",
            "cp",
            "geometry",
        ]
    ].copy()

    settlement_layer = (
        settlement_layer.rename(
            columns={
                "cvegeo": "settlement_cvegeo"
            }
        )
    )

    intersections = gpd.overlay(
        ageb_layer,
        settlement_layer,
        how="intersection",
        keep_geom_type=False,
    )

    if intersections.empty:
        raise RuntimeError(
            "No se encontraron intersecciones."
        )

    intersections["intersection_area_m2"] = (
        intersections.geometry.area
    )

    intersections = intersections[
        intersections["intersection_area_m2"] > 0
    ].copy()

    intersections["coverage_pct"] = (
        intersections["intersection_area_m2"]
        / intersections["ageb_area_m2"]
        * 100
    )

    # --------------------------------------------------
    # 5. Crear catálogo AGEB -> asentamiento
    # --------------------------------------------------

    result = {}
    matched = 0

    for cvegeo in agebs_metric["cvegeo"]:
        rows = intersections[
            intersections["cvegeo"] == cvegeo
        ].copy()

        rows = rows[
            rows["nom_asen"].apply(
                is_valid_name
            )
        ].copy()

        if rows.empty:
            result[cvegeo] = {
                "primary_name": None,
                "primary_type": None,
                "primary_cp": None,
                "coverage_pct": None,
                "intersections": [],
            }
            continue

        grouped = (
            rows.groupby(
                [
                    "settlement_cvegeo",
                    "nom_asen",
                    "tipo",
                    "cp",
                ],
                dropna=False,
                as_index=False,
            )
            .agg(
                intersection_area_m2=(
                    "intersection_area_m2",
                    "sum",
                ),
                ageb_area_m2=(
                    "ageb_area_m2",
                    "first",
                ),
            )
        )

        grouped["coverage_pct"] = (
            grouped["intersection_area_m2"]
            / grouped["ageb_area_m2"]
            * 100
        )

        grouped = grouped.sort_values(
            "coverage_pct",
            ascending=False,
        )

        primary = grouped.iloc[0]

        matched += 1

        relevant = grouped[
            grouped["coverage_pct"]
            >= MIN_COVERAGE_PCT
        ]

        reference_areas = []

        for _, row in relevant.iterrows():
            reference_areas.append(
                {
                    "name": clean_text(
                        row["nom_asen"]
                    ),
                    "type": clean_text(
                        row["tipo"]
                    ),
                    "postal_code": (
                        clean_text(row["cp"])
                        or None
                    ),
                    "coverage_pct": round(
                        float(
                            row["coverage_pct"]
                        ),
                        2,
                    ),
                }
            )

        result[cvegeo] = {
            "primary_name": clean_text(
                primary["nom_asen"]
            ),
            "primary_type": clean_text(
                primary["tipo"]
            ),
            "primary_cp": (
                clean_text(primary["cp"])
                or None
            ),
            "coverage_pct": round(
                float(
                    primary["coverage_pct"]
                ),
                2,
            ),
            "intersections": reference_areas,
        }

    # --------------------------------------------------
    # 6. Exportar JSON
    # --------------------------------------------------

    unmatched = len(agebs_metric) - matched

    payload = {
        "metadata": {
            "source": (
                "INEGI - Delimitación de Colonias "
                "y otros Asentamientos Humanos 2025"
            ),
            "state": "Yucatán",
            "municipality": "Mérida",
            "municipality_code": (
                MERIDA_MUNICIPALITY
            ),
            "ageb_count": int(
                len(agebs_metric)
            ),
            "matched_agebs": int(matched),
            "unmatched_agebs": int(unmatched),
            "settlements_considered": int(
                len(settlements)
            ),
            "generated_at": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
        },
        "agebs": result,
    }

    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # --------------------------------------------------
    # 7. Resumen QA
    # --------------------------------------------------

    print()
    print("=== Results ===")
    print(
        f"AGEBs processed: {len(agebs_metric):,}"
    )
    print(
        f"Matched AGEBs:   {matched:,}"
    )
    print(
        f"Unmatched AGEBs: {unmatched:,}"
    )
    print()
    print(
        f"Generated: {OUTPUT_JSON}"
    )

    example = result.get(
        "3105000010440"
    )

    print()
    print(
        "Example AGEB 3105000010440:"
    )

    print(
        json.dumps(
            example,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
