"""Source-based QA remediation tests requiring only the standard library."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.qa.reconcile_geography import reconcile
from src.qa.refresh_demographic_geojson import FIELD_MAP, refresh_geojson


class DataRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.census = self.root / "census.csv"
        self.geojson = self.root / "map.geojson"
        self.warehouse = self.root / "warehouse.csv"
        self.row = {
            "ENTIDAD": "31", "MUN": "050", "LOC": "0001", "AGEB": "001A",
            "NOM_LOC": "Total AGEB urbana", "MZA": "0", "POBTOT": "100",
            "POBMAS": "40", "POBFEM": "60", "POB0_14": "20", "POB15_64": "70",
            "POB65_MAS": "10", "PEA": "50", "PE_INAC": "30", "VIVTOT": "35",
        }
        self.original = {
            "type": "FeatureCollection", "name": "fixture",
            "features": [{"type": "Feature", "properties": {
                "cvegeo": "310500001001A", "area_km2": 1.5,
                "poblacion_total": 100, "poblacion_0_14": 100,
                "poblacion_15_64": 0, "poblacion_65_mas": 0,
                "poblacion_pnea": 0, "unrelated": "preserve me",
            }, "geometry": {"type": "Polygon", "coordinates": [
                [[-89, 20], [-88, 20], [-88, 21], [-89, 20]],
            ]}}],
        }
        self.geojson.write_text(json.dumps(self.original), encoding="utf-8")
        self.write_census([self.row])

    def write_census(self, rows):
        with self.census.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_source_mapping_preserves_geometry_and_other_properties(self):
        payload, report = refresh_geojson(self.census, self.geojson)
        feature = json.loads(payload)["features"][0]
        for target, source in FIELD_MAP.items():
            self.assertEqual(feature["properties"][target], int(self.row[source]))
        self.assertEqual(feature["geometry"], self.original["features"][0]["geometry"])
        self.assertEqual(feature["properties"]["unrelated"], "preserve me")
        self.assertEqual(feature["properties"]["area_km2"], 1.5)
        self.assertEqual(report["geojson_only_keys"], [])
        self.geojson.write_bytes(payload)
        repeated, repeated_report = refresh_geojson(self.census, self.geojson)
        self.assertEqual(repeated, payload)
        self.assertEqual(repeated_report["changed_features"], 0)

    def test_suppression_is_recorded_and_unexpected_tokens_rejected(self):
        self.row["PE_INAC"] = "*"
        self.write_census([self.row])
        payload, report = refresh_geojson(self.census, self.geojson)
        self.assertEqual(json.loads(payload)["features"][0]["properties"]["poblacion_pnea"], 0)
        self.assertEqual(report["suppressed_values"]["poblacion_pnea"], [
            {"cvegeo": "310500001001A", "token": "*"},
        ])
        for invalid in ("unexpected", "-1", "1.5"):
            with self.subTest(token=invalid):
                self.row["PE_INAC"] = invalid
                self.write_census([self.row])
                with self.assertRaises(ValueError):
                    refresh_geojson(self.census, self.geojson)

    def test_duplicate_missing_columns_and_unmatched_keys_fail(self):
        self.write_census([self.row, self.row])
        with self.assertRaisesRegex(ValueError, "Duplicate census"):
            refresh_geojson(self.census, self.geojson)
        incomplete = dict(self.row)
        del incomplete["POB15_64"]
        self.write_census([incomplete])
        with self.assertRaisesRegex(ValueError, "required columns"):
            refresh_geojson(self.census, self.geojson)
        self.row["ENTIDAD"] = "30"
        self.write_census([self.row])
        with self.assertRaisesRegex(ValueError, "missing from census"):
            refresh_geojson(self.census, self.geojson)

    def test_cli_rejects_source_overwrite_and_leaves_invalid_input_unchanged(self):
        before = self.geojson.read_bytes()
        raw = self.census.read_bytes()
        result = subprocess.run([
            sys.executable, "-m", "src.qa.refresh_demographic_geojson",
            "--census", str(self.census), "--input", str(self.geojson),
            "--output", str(self.census),
        ], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.census.read_bytes(), raw)
        self.write_census([self.row, self.row])
        result = subprocess.run([
            sys.executable, "-m", "src.qa.refresh_demographic_geojson",
            "--census", str(self.census), "--input", str(self.geojson),
            "--report", str(self.root / "report.json"),
        ], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.geojson.read_bytes(), before)
        self.assertFalse((self.root / "report.json").exists())

    def test_warehouse_comparison_reports_both_sides_even_with_equal_counts(self):
        self.warehouse.write_text("cvegeo\n310500001002B\n", encoding="utf-8")
        report = reconcile(self.geojson, self.warehouse)
        self.assertEqual(report["local_count"], report["warehouse_count"])
        self.assertEqual(report["matched_count"], 0)
        self.assertEqual(report["local_only_keys"], ["310500001001A"])
        self.assertEqual(report["warehouse_only_keys"], ["310500001002B"])
        self.warehouse.write_text("cvegeo\n310500001002B\n310500001002B\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            reconcile(self.geojson, self.warehouse)
        self.warehouse.write_text("other\n310500001002B\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "cvegeo header"):
            reconcile(self.geojson, self.warehouse)


if __name__ == "__main__":
    unittest.main()
