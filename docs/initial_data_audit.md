# Local data audit, remediation and acceptance evidence

Owner: Jonathan. Local review: 2026-10-04.

## Scope and evidence

The initial audit inspected branch `feature/jonathan-data-dictionary`, based on `develop` commit `bee3f9cd621160b9b7d1c2e7b448109f7bb28485`. It detected stale age-group and inactive-population properties in the committed GeoJSON. This follow-up downloaded the official INEGI census and refreshed the demographic properties of the existing 526 features. It did not query Supabase, reload the warehouse, regenerate polygon boundaries, or run the complete ETL.

- Current artifact: [merida_agebs_demographics.geojson](../outputs/maps/merida_agebs_demographics.geojson), used by the map and API fallback.
- Initial local SHA-256 (CRLF checkout): `21013fd890b423dead5153c94bdac6d5c10f5a378a76a610e67fbd6589d0b967`.
- Original Git blob SHA-256 (LF): `5669b6b82bec7423c7a11574f3a45f1d96c1a3f5ae63cfaa4f6f8fbd2aa2bbff`.
- Corrected SHA-256 (LF): `a6f66cbc6433c2a6d70dca9bf4b5bb3df0b36e5e5fa366d2897edd57ed7c1b8e`.
- Current profile: [local_data_audit.json](../outputs/qa/local_data_audit.json).
- Source mapping, before/after totals and suppression evidence: [demographic_refresh.json](../outputs/qa/demographic_refresh.json).
- Source URL, hashes and selection: [data_sources.md](data_sources.md).
- Reproducible tools: [audit_local_data.py](../src/qa/audit_local_data.py), [refresh_demographic_geojson.py](../src/qa/refresh_demographic_geojson.py) and [reconcile_geography.py](../src/qa/reconcile_geography.py), all using the Python standard library.

File hashes describe the bytes inspected; Git line-ending conversion may change a checkout hash without changing GeoJSON values.

## Observed local results

| Control | Initial artifact | Corrected artifact / interpretation |
| --- | --- | --- |
| Features and CVEGEO keys | 526; no duplicates or unexpected format | Same 526 keys; exact match to selected census totals |
| Total population | 957,399 | 957,399; unchanged |
| Population aged 0–14 | 957,399 | 190,473 from `POB0_14` |
| Population aged 15–64 | 0 | 670,763 from `POB15_64` |
| Population aged 65+ | 0 | 93,599 from `POB65_MAS` |
| Economically active population | 508,151 | 508,151; unchanged |
| Economically inactive population | 0 | 294,340 from `PE_INAC` |
| Dwellings | 359,495 | 359,495; unchanged |
| Systematic age pattern in populated AGEBs | 520/520 | 0/520; local mapping error resolved |
| Derived 100% PEA rate | 516 AGEBs | 1 AGEB; review the original small-population record |
| Sex-total differences | 4 AGEBs, maximum absolute gap 24 | Same 4; original sex values are suppressed, so no fabricated correction |
| Zero / below-100 population | 6 / 32, including zeros | Unchanged; zero denominators and unstable small-area rates need handling |
| Numeric demographic fields | Nine numeric counts per feature, no negatives | Same; suppression remains zero-imputed under the current ETL policy |
| Area | Min 0.0122, median 0.40565, max 6.5497 km²; sum 259.8632 km² | Preserved; no CRS/topology/area recalculation |
| Geometry types | 526 Polygon | Preserved; valid GeoJSON type, with loader-specific MultiPolygon handling below |
| Business/crime properties | Absent on all features | Still unavailable; absence does not mean zero observations |
| Raw source availability | No source files in the initial clone | Official census present locally; other raw datasets still absent |

Only the four stale fields changed: 520 age-0–14 values, 516 age-15–64 values, 497 age-65+ values and 515 inactivity values, across 520 features. Keys, geometry, areas, feature order and all other properties are preserved.

The census source contains 40,140 rows. Filtering state `31`, municipality `050`, urban AGEB totals and `MZA = 0` gives 526 unique keys across six localities. There are no census-only or GeoJSON-only keys. This establishes the census join for the local artifact, not equivalent coverage of the remote warehouse.

Suppression counts among the matched AGEBs: male = 4, female = 4, age 0–14 = 7, age 15–64 = 4, age 65+ = 14, PEA = 4, PNEA = 5; total population and dwellings have none. The manifest retains each original token and CVEGEO. Age-group sums differ from population by 2,564 people overall; suppression and unspecified age must be considered before treating this as another mapping error.

## Reproduce the correction and audit

Download the [official census ZIP](https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip), verify the hash in the source inventory, and extract its dataset CSV into `data/raw/census_2020/`. Keep raw data unchanged.

From the repository root:

```bash
# Validate the source and join without writing files:
python -m src.qa.refresh_demographic_geojson --census data/raw/census_2020/conjunto_de_datos_ageb_urbana_31_cpv2020.csv --dry-run

# Update demographic properties and write a provenance report:
python -m src.qa.refresh_demographic_geojson --census data/raw/census_2020/conjunto_de_datos_ageb_urbana_31_cpv2020.csv

# Profile the current artifact and fail on error findings:
python -m src.qa.audit_local_data --output outputs/qa/local_data_audit.json --check
```

The audit now exits 0 with two warning categories: one derived 100% PEA rate and sex-total gaps in four AGEBs. It does not certify complete sources, topology or remote data. The refresh rejects missing columns, duplicate keys, unmatched local keys and unexpected numeric tokens before writing. Use `--output` for a separate candidate artifact. Repeating the refresh on corrected input changes zero demographic values. A new run overwrites its report; preserve the committed before/after manifest if keeping historical evidence.

## Warehouse coverage reconciliation: 531 reported vs 526 local

The reviewer reported 531 AGEBs in Supabase versus 526 in the GeoJSON. The warehouse count is reported evidence, not an independent query from this workstation. The net difference is five; counts alone cannot establish that the local set is a subset or identify which codes differ. The official census contains exactly the 526 local keys, so the source join does not explain the remote difference.

Export these read-only results from the live warehouse with access to all rows, recording export date, source edition, project and role/RLS visibility:

```sql
SELECT cvegeo FROM dim_geografia ORDER BY cvegeo;

SELECT g.cve_ent, g.cve_mun, g.cve_loc, COUNT(*) AS geography_rows,
       COUNT(d.cvegeo) AS rows_with_demographics
FROM dim_geografia g
LEFT JOIN fact_demografia d USING (cvegeo)
GROUP BY g.cve_ent, g.cve_mun, g.cve_loc
ORDER BY g.cve_ent, g.cve_mun, g.cve_loc;
```

Save the first result as a CSV with a `cvegeo` header, then compare exact key sets:

```bash
python -m src.qa.reconcile_geography --warehouse-csv data/raw/warehouse_geography.csv --output outputs/qa/geography_reconciliation.json
```

The tool records both input hashes, counts, matched keys, keys exclusive to either side and locality counts. Review each unmatched key against polygon edition, census coverage and demographic availability; do not delete or fabricate AGEBs to force equal counts. Include the accepted reconciliation results in the PDF report. Until the export is available, this item remains open.

## Findings and proposed owners

Assignments follow `TEAM_DISTRIBUTION.md` and are coordination guidance; no team messages were sent. Jonathan records evidence and verifies acceptance with each owner.

| ID | Priority | Current evidence / issue | Action and proposed owner | Closure criterion |
| --- | --- | --- | --- | --- |
| QA-01 | High | Local age/PNEA properties refreshed from the official census; warehouse agreement remains unverified | Jonathan: completed local repair; Russel/Bianca: compare warehouse and consumers | Source mapping/hash recorded, local error pattern absent, accepted warehouse/API/map agreement |
| QA-02 | High | Transform uses correct census fields; generated artifacts required regeneration | Local refresh completed; Russel: record warehouse source snapshot and load date | Files, warehouse and API use the same accepted version |
| QA-03 | High for unverified load paths | REST `load_full_warehouse.py` already converts Polygon to MultiPolygon; `src/etl/load.py` and exported SQL do not explicitly convert | Russel: document the active load path and validate alternatives; Jonathan: reconcile coverage | Active path accepts geometry, Q07 has no exceptions, 531/526 key difference explained |
| QA-04 | High | `fact_negocios` lacks DENUE identity and repeated-load safeguards | Russel: define source identity/snapshot and repeatable loads | Repeating a snapshot does not increase counts or alter KPIs |
| QA-05 | Medium | API fallback substitutes zeros for unavailable business/crime fields and some undefined rates | Rivaldo: expose indicator provenance/availability | Responses distinguish absent data, undefined rates and observed zero |
| QA-06 | Medium | Dashboard population is fixed at 887,632 versus local total 957,399; metrics are not API-driven | Damián/Bianca: connect metrics and explain coverage | Cards match accepted warehouse results and document source/snapshot |
| QA-07 | High for crime analysis | No local crime source or transformation/load exists in the pipeline | Team: agree on source; Russel: load; Rivaldo/Bianca: integrate analysis | Catalog, period, coordinates and identity documented; counts reconciled |
| QA-08 | Medium | Notebook imports were updated to `get_real_paths`, local audit and `gpd.sjoin` | Jonathan: syntax/internal imports checked; full GeoPandas execution pending | All cells execute with dependencies; synthetic join is not source-coverage validation |
| QA-09 | Medium | CI now runs the five QA regression tests and the artifact audit; pytest/backend coverage and real SQL execution remain pending | Russel/Rivaldo: extend test coverage and execute SQL | QA regressions fail CI; backend/SQL failures must also block workflow success |
| QA-10 | Medium | `sector_nombre` holds a class name and the view uses it as dominant activity | Russel/Bianca: agree on SCIAN level and labels | Dictionary, grouping and visualization use the same level |

The README now uses `python src/backend/run.py`. Docker still points at the nonexistent `src.backend.main:app`; correction/testing remain with Russel/Rivaldo.

## PostgreSQL/PostGIS validation status

[04_quality_checks.sql](../sql/04_quality_checks.sql) has 17 SELECT queries grouped Q01–Q12 for coverage, CVEGEO, FKs, demographics, geometry, point location, duplicate candidates, calendar, SCIAN, view reconciliation and rate denominators. It uses a read-only repeatable-read transaction. RLS may restrict observed rows.

The reviewer reported that all 17 queries execute without errors on PostgreSQL 16 + PostGIS 3 against the project schema. This is a schema/syntax smoke check, **not execution against live Supabase data**. The initial age/PNEA findings were also reproduced by the reviewer before the local repair. These are reviewer-reported results; this workstation has not executed PostgreSQL/PostGIS checks.

After loading, retain Q01–Q12 outputs, source versions, load date and query permissions. Expected exception counts are zero for orphan keys, malformed codes, negative counts, invalid geometry and rates incompatible with denominators. Duplicate candidates and demographic differences require source review, not automatic deletion. Empty tables and null dates are coverage limitations.

Local checks cover the source join, artifact preservation, repeatability, validation failures, current audit, source-discovery behavior, dictionary completeness and documentation links. Five standard-library regression tests pass with `python -m unittest discover -s tests -v`; CI now runs them and the committed-artifact audit. FastAPI tests, the complete GeoPandas notebook and frontend build remain unexecuted here because project dependencies are unavailable. The final PDF should clearly distinguish local verification, reviewer schema checks and pending live warehouse results.
