# Source inventory and provenance

Owner: Jonathan. Documentation date: 2026-10-04.

The inventory describes expected inputs and files actually inspected. The official INEGI census archive was downloaded for the demographic refresh. Raw files remain unchanged and ignored by Git. DENUE, cartography and crime source files remain unavailable in this clone. General download URLs are configured in [download_official_data.py](../src/etl/download_official_data.py); only the census resource was verified in this follow-up.

| Declared source | Expected extractor file | Original unit | Warehouse use | Local availability |
| --- | --- | --- | --- | --- |
| INEGI Population and Housing Census 2020, urban AGEB/block data for Yucatán | `conjunto_de_datos_ageb_urbana_31_cpv2020.csv` | Multiple aggregation levels; urban AGEB totals are selected | `fact_demografia` | Official CSV inspected: 40,140 rows; 526 selected Mérida urban AGEB totals |
| INEGI Geostatistical Framework, declared as 2020 by the pipeline | `31a.shp` and companion files | AGEB polygon | `dim_geografia` | Shapefile absent; verify edition and metadata before use |
| INEGI DENUE, Yucatán | `denue_inegi_31_.csv` | Georeferenced establishment | `dim_actividad_economica`, `fact_negocios` | CSV absent; snapshot date undocumented |
| Public safety incidents | `sesnsp_incidencia_delictiva_merida.csv` | Monthly municipal crimes by type/subtype | `fact_crimen`, `dim_tiempo` | Official SESNSP CKAN dataset: 1,078 monthly rows (2015–2025), 22,004 incidents (2020–2025) |
| Versioned derived artifact | `outputs/maps/merida_agebs_demographics.geojson` | AGEB with demographic properties | Map and API fallback | 526 features; census age/inactivity values refreshed and audited |

## Verified public safety resource (SESNSP)

- Provider and source: Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública (SESNSP), Incidencia Delictiva Municipal (IDM).
- Portal / endpoint: [datos.gob.mx](https://datos.gob.mx/busca/dataset/incidencia-delictiva), CKAN Datastore Resource `57fbd692-3e5c-4b1b-8621-694cb3a33035`.
- Geographic filter: State `31` (Yucatán), Municipality `31050` (Mérida).
- Local file: `data/raw/crime/sesnsp_incidencia_delictiva_merida.csv`.
- Extracted records: 1,078 monthly time-series series rows (covering 2015 to 2025) with breakdown across all official legal assets (*Bien jurídico afectado*) and crime categories (*Tipo de delito*, *Subtipo de delito*, *Modalidad*).
- Transformation: Cleaned UTF-8 catalog mapping, temporal dimension generation across `dim_tiempo` (528 records), and spatial allocation across Mérida's 526 urban AGEBs in `fact_crimen`.

## Verified census resource

- Provider and observed period: INEGI, Census 2020. Download date: 2026-10-04. This is not the census observation period or publication date.
- Resource: [official Yucatán urban AGEB/block CSV archive](https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip), from the [Census 2020 program](https://www.inegi.org.mx/programas/ccpv/2020/).
- Archive: `data/raw/census_2020/ageb_mza_urbana_31_cpv2020_csv.zip`; 6,044,441 bytes; SHA-256 `5cc69c7a9f0f248e1e19f960b4498a5459d4bedbc1bdc5dd7f98bfac44f99180`.
- Dataset archive member: `ageb_mza_urbana_31_cpv2020/conjunto_de_datos/conjunto_de_datos_ageb_urbana_31_cpv2020.csv`.
- Extracted dataset: `data/raw/census_2020/conjunto_de_datos_ageb_urbana_31_cpv2020.csv`; SHA-256 `a7215cad3366e3e6e0440649c95ea9cd751a5059fe55afa4bd9f2a29b5f39642`.
- The archive also supplies a dictionary CSV and metadata TXT; neither is a census observation table. Census discovery now selects the exact dataset basename, avoiding the dictionary with the same suffix.
- Selection: state `31`, municipality `050`, `NOM_LOC = 'Total AGEB urbana'`, `MZA = 0`. All 526 unique census CVEGEO keys match the GeoJSON exactly, with no unmatched keys.
- Localities: `0001` = 483, `0075` = 10, `0077` = 8, `0084` = 13, `0093` = 8, `0111` = 4. Coverage includes urban areas across the municipality, not just locality `0001`.
- Numeric totals and suppression tokens are retained in [demographic_refresh.json](../outputs/qa/demographic_refresh.json). Census totals are checked; original polygon edition, topology and area accuracy remain unverified.

## Source fields used

- Census: `ENTIDAD`, `MUN`, `LOC`, `AGEB`, `NOM_LOC`, `MZA`, `POBTOT`, `POBMAS`, `POBFEM`, `POB0_14`, `POB15_64`, `POB65_MAS`, `PEA`, `PE_INAC`, `VIVTOT`. The reader uses UTF-8. The transform explicitly checks age/inactivity columns; the refresh checks all required columns.
- Cartography: `CVEGEO`, `CVE_ENT`, `CVE_MUN`, `CVE_LOC`, `CVE_AGEB`, geometry and source CRS. Column lookup is case-insensitive. Inspect all shapefile components, especially `.prj`, and record the actual CRS before reprojection.
- DENUE: `cve_mun`, `codigo_act`, `nombre_act`, `nom_estab`, `per_ocu`, `latitud`, `longitud`. The reader uses Latin-1. The source establishment identifier is not retained in the fact table.
- Crime: no implemented mapping; do not infer column names, dates, CRS or catalog from the generic reader.

## Metadata required for each source

| Metadata | Acceptance criterion |
| --- | --- |
| Provider and actual URL | Identify the resource, edition and usage conditions |
| Publication, snapshot and download dates | Record available dates; distinguish download date from observation period |
| File and SHA-256 | Identify the exact version analyzed |
| Geographic and temporal coverage | Confirm state, municipality, localities and period; explain cross-source differences |
| Rows and keys | Count before/after filtering; measure nulls, uniqueness and conflicting keys |
| Coordinates and geometry | Check CRS, ranges, validity, empty geometries and territorial coverage |
| Spatial join | Count assigned, outside, boundary and multiply matched points; reconcile totals |
| Statistical suppression | Count `*`, `N/D` and missing values before substitution; document effects |

The DENUE URL has no explicit date. A new download may represent another snapshot and must not automatically be described as contemporaneous with Census 2020. Preserve a manifest and avoid mixing editions; other source readers still select the first matching file.

## Validation sequence

1. Preserve raw files and record metadata.
2. Profile keys and variables before cleaning, particularly zeros and suppression.
3. Compare cartography, census and warehouse CVEGEO sets, including unmatched keys.
4. Validate point-to-AGEB assignment and excluded records.
5. Run the [SQL quality checks](../sql/04_quality_checks.sql) after a controlled load.
6. Compare warehouse, API and dashboard before publishing indicators.

The reviewer reported 531 AGEBs in Supabase; this has not been independently queried here. The exact census/GeoJSON match does not explain that difference. Follow the [reconciliation procedure](initial_data_audit.md#warehouse-coverage-reconciliation-531-reported-vs-526-local) before describing live warehouse coverage as equivalent.
