"""Profile a local AGEB GeoJSON with the Python standard library only.

This does not connect to Supabase or validate topology/projection accuracy.
"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = BASE_DIR / "outputs/maps/merida_agebs_demographics.geojson"
DEMOGRAPHIC_FIELDS = (
    "poblacion_total", "poblacion_masculina", "poblacion_femenina",
    "poblacion_0_14", "poblacion_15_64", "poblacion_65_mas",
    "poblacion_pea", "poblacion_pnea", "total_viviendas",
)
REQUIRED_FIELDS = ("cvegeo", "area_km2") + DEMOGRAPHIC_FIELDS
RAW_PATTERNS = {
    "census": ("conjunto_de_datos_ageb_urbana_31_cpv2020.csv",),
    "denue": ("denue_inegi_31_.csv",),
    "cartography": ("31a.shp",),
    "crime": ("*crimen*.csv", "*delito*.csv"),
}


def is_number(value):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value)
    )


def audit_geojson(path):
    """Return observed values and explicit limits, without altering the input."""
    payload = path.read_bytes()
    dataset = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(dataset, dict) or dataset.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    features = dataset.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("The FeatureCollection must contain features.")
    rows = []
    geometry_types = Counter()
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Each item must be a GeoJSON Feature.")
        row = feature.get("properties")
        if not isinstance(row, dict):
            raise ValueError("Each feature must have a properties object.")
        rows.append(row)
        geometry = feature.get("geometry")
        geometry_types[geometry.get("type", "missing") if isinstance(geometry, dict)
                       else "missing"] += 1

    fields = sorted(set(REQUIRED_FIELDS).union(*(row.keys() for row in rows)))
    profiles = {}
    for field in fields:
        values = [row.get(field) for row in rows]
        numeric = [v for v in values if is_number(v)]
        profile = {
            "missing": sum(field not in row for row in rows),
            "null": sum(field in row and row[field] is None for row in rows),
            "numeric_count": len(numeric),
        }
        if numeric:
            profile.update({
                "sum": sum(numeric), "min": min(numeric), "max": max(numeric),
                "median": statistics.median(numeric),
                "zeros": sum(v == 0 for v in numeric),
                "negative": sum(v < 0 for v in numeric),
            })
        profiles[field] = profile

    codes = Counter(row.get("cvegeo") for row in rows
                    if isinstance(row.get("cvegeo"), str))
    complete = [row for row in rows if all(is_number(row.get(field))
                for field in DEMOGRAPHIC_FIELDS)]
    sex_gaps = [abs(row["poblacion_total"] - row["poblacion_masculina"]
                   - row["poblacion_femenina"]) for row in complete]
    checks = {
        "invalid_cvegeo": sum(
            not isinstance(row.get("cvegeo"), str)
            or re.fullmatch(r"31050[0-9]{4}[0-9A-Z]{4}", row["cvegeo"]) is None
            for row in rows
        ),
        "duplicate_cvegeo_rows": sum(count - 1 for count in codes.values()),
        "nonpositive_or_missing_area": sum(
            not is_number(row.get("area_km2")) or row["area_km2"] <= 0
            for row in rows
        ),
        "complete_demographic_rows": len(complete),
        "population_zero": sum(row["poblacion_total"] == 0 for row in complete),
        "population_below_100_including_zero": sum(
            row["poblacion_total"] < 100 for row in complete),
        "age_0_14_equals_total": sum(
            row["poblacion_0_14"] == row["poblacion_total"] for row in complete),
        "age_0_14_equals_positive_total_other_groups_zero": sum(
            row["poblacion_total"] > 0
            and row["poblacion_0_14"] == row["poblacion_total"]
            and row["poblacion_15_64"] == row["poblacion_65_mas"] == 0
            for row in complete),
        "derived_pea_rate_100_percent": sum(
            row["poblacion_pea"] > 0 and row["poblacion_pnea"] == 0
            for row in complete),
        "sex_total_mismatch": sum(gap != 0 for gap in sex_gaps),
        "max_sex_total_gap": max(sex_gaps, default=0),
        "business_field_present": sum("total_negocios" in row for row in rows),
        "crime_field_present": sum("total_delitos" in row for row in rows),
    }
    findings = []
    for name in ("invalid_cvegeo", "duplicate_cvegeo_rows",
                 "nonpositive_or_missing_area"):
        if checks[name]:
            findings.append({"severity": "error", "check": name,
                             "rows": checks[name]})
    incomplete = len(rows) - len(complete)
    if incomplete:
        findings.append({"severity": "error", "check": "incomplete_demographics",
                         "rows": incomplete})
    populated_rows = len(complete) - checks["population_zero"]
    if (populated_rows > 0
            and checks["age_0_14_equals_positive_total_other_groups_zero"] == populated_rows):
        findings.append({"severity": "error", "check": "systematic_age_mapping",
                         "rows": checks["age_0_14_equals_positive_total_other_groups_zero"]})
    for field in DEMOGRAPHIC_FIELDS:
        if profiles[field].get("negative", 0):
            findings.append({"severity": "error", "check": "negative_count",
                             "field": field, "rows": profiles[field]["negative"]})
    for name in ("derived_pea_rate_100_percent", "sex_total_mismatch"):
        if checks[name]:
            findings.append({"severity": "warning", "check": name,
                             "rows": checks[name]})
    if geometry_types.get("missing", 0):
        findings.append({"severity": "error", "check": "missing_geometry",
                         "rows": geometry_types["missing"]})

    raw_dir = BASE_DIR / "data/raw"
    inventory = {name: sorted({str(p.relative_to(BASE_DIR)).replace("\\", "/")
                              for pattern in patterns for p in raw_dir.rglob(pattern)})
                 for name, patterns in RAW_PATTERNS.items()}
    return {
        "input_file": path.name, "sha256": hashlib.sha256(payload).hexdigest(),
        "features": len(features), "geometry_types": dict(geometry_types),
        "raw_inventory": inventory, "properties": profiles,
        "checks": checks, "findings": findings,
        "limitations": [
            "Local file only; no Supabase query.",
            "No validation of geometry topology, coordinate bounds or CRS accuracy.",
            "Missing business/crime fields do not mean zero observations.",
            "A 100% PEA rate or a sex total gap requires source review, not automatic correction.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true", help="Exit 1 on error findings.")
    args = parser.parse_args()
    try:
        report = audit_geojson(args.input)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Audit could not run: {exc}\n")
    serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        if args.output.resolve() == args.input.resolve():
            parser.exit(2, "Output must differ from the input dataset.\n")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Audited {report['features']} AGEBs; report: {args.output}")
        print(f"Findings: {len(report['findings'])}; Supabase not queried.")
    else:
        print(serialized, end="")
    return int(args.check and any(f["severity"] == "error" for f in report["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
