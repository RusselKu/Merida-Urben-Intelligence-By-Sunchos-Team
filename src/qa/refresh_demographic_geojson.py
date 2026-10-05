"""Refresh existing AGEB properties from an explicit official census CSV.

Uses only the standard library. Geometry, feature order and other properties
are preserved. Suppressed values become zero to match the existing ETL; their
source tokens and keys are retained in the provenance report.
"""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re

from src.qa.audit_local_data import BASE_DIR, DEFAULT_INPUT


SOURCE_URL = (
    "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/"
    "datosabiertos/ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip"
)
FIELD_MAP = {
    "poblacion_total": "POBTOT",
    "poblacion_masculina": "POBMAS",
    "poblacion_femenina": "POBFEM",
    "poblacion_0_14": "POB0_14",
    "poblacion_15_64": "POB15_64",
    "poblacion_65_mas": "POB65_MAS",
    "poblacion_pea": "PEA",
    "poblacion_pnea": "PE_INAC",
    "total_viviendas": "VIVTOT",
}
SUPPRESSED_TOKENS = {"*", "N/D", "N/A", ""}


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def refresh_geojson(census_path, geojson_path):
    """Validate the complete join before returning refreshed data and evidence."""
    census_bytes = census_path.read_bytes()
    original_bytes = geojson_path.read_bytes()
    dataset = json.loads(original_bytes.decode("utf-8-sig"))
    if not isinstance(dataset, dict) or dataset.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    features = dataset.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("The FeatureCollection must contain features.")
    reader = csv.DictReader(io.StringIO(census_bytes.decode("utf-8-sig")))
    required = {"ENTIDAD", "MUN", "LOC", "AGEB", "NOM_LOC", "MZA"} | set(FIELD_MAP.values())
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Census is missing required columns: {sorted(missing)}")
    census = {}
    suppressed = {field: [] for field in FIELD_MAP}
    raw_rows = 0
    for row in reader:
        raw_rows += 1
        if not (row["ENTIDAD"].strip().zfill(2) == "31"
                and row["MUN"].strip().zfill(3) == "050"
                and row["NOM_LOC"].strip() == "Total AGEB urbana"
                and row["MZA"].strip().zfill(3) == "000"):
            continue
        key = "".join(row[col].strip().zfill(width) for col, width in
                      (("ENTIDAD", 2), ("MUN", 3), ("LOC", 4), ("AGEB", 4)))
        if re.fullmatch(r"31050[0-9]{4}[0-9A-Z]{4}", key) is None:
            raise ValueError(f"Invalid census CVEGEO: {key}")
        if key in census:
            raise ValueError(f"Duplicate census CVEGEO: {key}")
        values = {}
        for field, source in FIELD_MAP.items():
            token = row[source].strip()
            if token in SUPPRESSED_TOKENS:
                values[field] = 0
                suppressed[field].append({"cvegeo": key, "token": token})
            elif re.fullmatch(r"[0-9]+", token):
                values[field] = int(token)
            else:
                raise ValueError(f"Unexpected count {source}={token!r} at {key}")
        census[key] = values
    keys = []
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Each item must be a GeoJSON Feature.")
        properties = feature.get("properties")
        if not isinstance(properties, dict) or not isinstance(properties.get("cvegeo"), str):
            raise ValueError("Each feature needs a text CVEGEO property.")
        keys.append(properties["cvegeo"])
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate CVEGEO in the GeoJSON.")
    codes = set(keys)
    missing_keys = sorted(codes - census.keys())
    if missing_keys:
        raise ValueError(f"GeoJSON keys missing from census: {missing_keys}")
    changed_fields = Counter()
    changed_features = 0
    before = Counter()
    after = Counter()
    for feature, key in zip(features, keys):
        properties = feature["properties"]
        changed = False
        for field, value in census[key].items():
            old = properties.get(field)
            if isinstance(old, int) and not isinstance(old, bool):
                before[field] += old
            after[field] += value
            if old != value or type(old) is not int:
                changed_fields[field] += 1
                changed = True
            properties[field] = value
        changed_features += changed
    # Keep one feature per line so a large map remains reviewable in Git.
    def encode(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)

    lines = ["{"]
    lines.extend(f"{encode(key)}: {encode(value)}," for key, value in dataset.items()
                 if key != "features")
    lines.append('"features": [')
    lines.append(",\n".join(encode(feature) for feature in features))
    lines.extend(["]", "}"])
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    report = {
        "source_url": SOURCE_URL,
        "census_file": census_path.name,
        "census_sha256": sha256(census_bytes),
        "input_sha256": sha256(original_bytes),
        "output_sha256": sha256(payload),
        "raw_census_rows": raw_rows,
        "selected_census_agebs": len(census),
        "geojson_agebs": len(keys),
        "census_only_keys": sorted(census.keys() - set(keys)),
        "geojson_only_keys": missing_keys,
        "changed_features": changed_features,
        "changed_fields": dict(changed_fields),
        "totals_before": dict(before),
        "totals_after": dict(after),
        "field_mapping": FIELD_MAP,
        "suppressed_values": {field: [item for item in items if item["cvegeo"] in codes]
                              for field, items in suppressed.items()},
        "locality_counts": dict(sorted(Counter(key[5:9] for key in keys).items())),
        "limitations": [
            "No Supabase access; remote geography coverage is not reconciled.",
            "Existing geometries and areas are preserved, not revalidated.",
            "Suppressed values become zero to match current ETL; zero is not always observed absence.",
            "INEGI broad age totals need not sum to population because of suppression or unspecified age.",
        ],
    }
    return payload, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, help="Defaults to updating the input file.")
    parser.add_argument("--report", type=Path, default=BASE_DIR / "outputs/qa/demographic_refresh.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print evidence without writing files.")
    args = parser.parse_args()
    output = args.output or args.input
    try:
        if args.census.resolve() in {output.resolve(), args.report.resolve()}:
            raise ValueError("Output/report must not overwrite the census source.")
        if args.report.resolve() in {args.input.resolve(), output.resolve()}:
            raise ValueError("Report must differ from input/output GeoJSON.")
        payload, report = refresh_geojson(args.census, args.input)
        if args.dry_run:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(payload)
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Refreshed {report['geojson_agebs']} AGEBs; changed {report['changed_features']} features.")
            print(f"Provenance: {args.report}")
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Refresh could not run: {exc}\n")


if __name__ == "__main__":
    main()
