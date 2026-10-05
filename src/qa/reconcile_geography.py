"""Compare local AGEB keys with an explicit warehouse CSV export; no credentials.

Export SELECT cvegeo FROM dim_geografia ORDER BY cvegeo from Supabase using
an account with visibility of all rows, then pass that CSV with --warehouse-csv.
"""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re

from src.qa.audit_local_data import DEFAULT_INPUT


def reconcile(geojson_path, warehouse_path):
    local_bytes = geojson_path.read_bytes()
    warehouse_bytes = warehouse_path.read_bytes()
    dataset = json.loads(local_bytes.decode("utf-8-sig"))
    if not isinstance(dataset, dict) or dataset.get("type") != "FeatureCollection":
        raise ValueError("Expected a local FeatureCollection.")
    local = [feature["properties"]["cvegeo"] for feature in dataset["features"]]
    reader = csv.DictReader(io.StringIO(warehouse_bytes.decode("utf-8-sig")))
    if "cvegeo" not in (reader.fieldnames or []):
        raise ValueError("Warehouse CSV needs a cvegeo header.")
    remote = [row["cvegeo"].strip() for row in reader]
    if not local or not remote:
        raise ValueError("Both inputs must contain AGEB keys.")
    for name, keys in (("GeoJSON", local), ("warehouse", remote)):
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate CVEGEO in {name}.")
        if any(re.fullmatch(r"[0-9]{9}[0-9A-Z]{4}", key) is None for key in keys):
            raise ValueError(f"Invalid CVEGEO in {name}.")
    return {
        "local_sha256": hashlib.sha256(local_bytes).hexdigest(),
        "warehouse_csv_sha256": hashlib.sha256(warehouse_bytes).hexdigest(),
        "local_count": len(local), "warehouse_count": len(remote),
        "matched_count": len(set(local) & set(remote)),
        "local_only_keys": sorted(set(local) - set(remote)),
        "warehouse_only_keys": sorted(set(remote) - set(local)),
        "local_locality_counts": dict(sorted(Counter(key[:9] for key in local).items())),
        "warehouse_locality_counts": dict(sorted(Counter(key[:9] for key in remote).items())),
        "limitations": [
            "CSV comparison only; does not validate geometry or demographic values.",
            "Export visibility may be restricted by RLS; record export date and permissions.",
            "Count differences alone do not prove a subset relationship or identify boundary editions.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse-csv", type=Path, required=True)
    parser.add_argument("--local", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output and args.output.resolve() in {args.local.resolve(), args.warehouse_csv.resolve()}:
            raise ValueError("Output must differ from both source files.")
        report = reconcile(args.local, args.warehouse_csv)
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Reconciliation could not run: {exc}\n")


if __name__ == "__main__":
    main()
