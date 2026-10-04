# KPI Formulas, Source Variables & Data Audit

**Owner:** Bianca — Data Analysis & Visualizations
**Phase:** 1 (Data & Geographic Assessment) → used in Phase 3 (Analytics)
**Unit of analysis:** Urban AGEB of Mérida (`dim_geografia.cvegeo`, n = 526)

This document fixes the mathematical definition of every required KPI, the original
source variable it comes from, and the warehouse column that stores it. All KPIs are
computed **from the warehouse** (`v_kpis_territoriales` in `sql/03_views.sql`), never
from raw files, as the project specification requires.

---

## 1. Notation

For each AGEB *i*:

| Symbol | Meaning | Warehouse column | Original source variable |
| :--- | :--- | :--- | :--- |
| $P_i$ | Total population | `fact_demografia.poblacion_total` | Census 2020 `POBTOT` |
| $P^{0-14}_i$ | Population aged 0–14 | `fact_demografia.poblacion_0_14` | Census 2020 `POB0_14` |
| $P^{15-64}_i$ | Population aged 15–64 | `fact_demografia.poblacion_15_64` | Census 2020 `POB15_64` |
| $P^{65+}_i$ | Population aged 65+ | `fact_demografia.poblacion_65_mas` | Census 2020 `POB65_MAS` |
| $EA_i$ | Economically active population (12+) | `fact_demografia.poblacion_pea` | Census 2020 `PEA` |
| $EI_i$ | Economically inactive population (12+) | `fact_demografia.poblacion_pnea` | Census 2020 `PE_INAC` |
| $A_i$ | Polygon area in km² (computed in EPSG:6372) | `dim_geografia.area_km2` | INEGI Marco Geoestadístico 2020 (`31a.shp`) |
| $B_i$ | DENUE establishments inside the AGEB | `COUNT(fact_negocios)` | DENUE `id`, `latitud`, `longitud` |
| $B^{com}_i$ | Retail/trade establishments | `fact_negocios` ⋈ `dim_actividad_economica.categoria_macro = 'Comercio'` | DENUE `codigo_act` (SCIAN) |
| $B^{ser}_i$ | Service establishments | `... categoria_macro = 'Servicios'` | DENUE `codigo_act` (SCIAN) |
| $C_i$ | Georeferenced crime incidents inside the AGEB | `COUNT(fact_crimen)` | Crime dataset lat/lon, type, date |

Census variable names were verified against the official INEGI descriptor
*Principales resultados por AGEB y manzana urbana, CPV 2020* (`fd_agebmza_urbana_cpv2020.pdf`).

---

## 2. KPI definitions

| # | Category | KPI | Formula | Unit | View column |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | Demographic | Total Population | $P_i$ | residents | `poblacion_total` |
| 2 | Demographic | Population Density | $P_i / A_i$ | residents / km² | `densidad_poblacion_km2` |
| 3 | Demographic | Economically Active Population Rate | $\dfrac{EA_i}{EA_i + EI_i} \times 100$ | % of population 12+ with known status | `tasa_pea_porcentaje` |
| 4 | Demographic | Population by Age Group | $P^{g}_i$ and share $P^{g}_i / P_i \times 100$, $g \in \{0\text{–}14, 15\text{–}64, 65+\}$ | residents, % | `poblacion_0_14`, `poblacion_15_64`, `poblacion_65_mas` |
| 5 | Economic | Total Businesses | $B_i$ | establishments | `total_negocios` |
| 6 | Economic | Business Density | $B_i / A_i$ | establishments / km² | `densidad_negocios_km2` |
| 7 | Economic | Businesses per 1,000 Residents | $B_i / P_i \times 1000$ | establishments / 1k residents | `negocios_por_mil_hab` |
| 8 | Economic | Retail Density | $B^{com}_i / A_i$ | establishments / km² | `densidad_comercio_km2` |
| 9 | Economic | Service Density | $B^{ser}_i / A_i$ | establishments / km² | `densidad_servicios_km2` |
| 10 | Economic | Dominant Economic Activity | $\arg\max_s \; B_{i,s}$ over SCIAN sectors *s* | category | `actividad_economica_dominante` |
| 11 | Public safety | Total Crime Incidents | $C_i$ | incidents | `total_delitos` |
| 12 | Public safety | Crime Rate | $C_i / P_i \times 1000$ | incidents / 1k residents | `tasa_delictiva_por_mil_hab` |
| 13 | Public safety | Incidents by Type and Time | $C_{i,k,t}$ = incidents of category *k* in time bucket *t* | incidents | `fact_crimen.categoria_delito` × `dim_tiempo` / `periodo_dia` |
| 14 | Public safety | Crime relative to Business Activity | $C_i / B_i \times 100$ | incidents per 100 establishments | `ratio_delito_por_negocio` × 100 |

### Additional indicators (proposed, justified)

| KPI | Formula | Why |
| :--- | :--- | :--- |
| Dependency ratio | $(P^{0-14}_i + P^{65+}_i) / P^{15-64}_i \times 100$ | Summarises age structure in one number; useful to correlate with economic density. |
| Elderly share | $P^{65+}_i / P_i \times 100$ | Mérida has an ageing city centre; tests whether older areas concentrate services. |
| Housing density | $\text{VIVTOT}_i / A_i$ | Separates built-up residential intensity from population counts. |

### Rules for edge cases

* **Division by zero.** When the denominator is 0 (e.g. $P_i = 0$ or $B_i = 0$) the KPI is `NULL`, not 0. The view already uses `NULLIF(..., 0)`.
* **Small populations.** Per-capita rates (KPIs 7 and 12) are unstable when $P_i$ is very small: an AGEB with 7 residents and 20 shops gives 2,857 shops per 1,000 residents. For **correlation and spatial statistics** we only use AGEBs with $P_i \ge 100$. Maps can still show all AGEBs, flagged.
* **Crime-to-business scale.** The view stores $C_i / B_i$; we report it **per 100 establishments** so values are readable.
* **Dominant activity** ties are broken by the first sector returned by `DISTINCT ON`; this is acceptable because ties are rare once counts exceed ~10.

---

## 3. SCIAN macro-categories used for Retail and Service density

Defined in `src/etl/transform.py → map_scian_category()`:

| Macro category | SCIAN 2-digit sectors |
| :--- | :--- |
| Comercio (Retail/Trade) | 43 (wholesale), 46 (retail), 47 |
| Servicios (Services) | 51, 52, 53, 54, 55, 56, 61, 62, 71, 72, 81 |
| Industria | 11, 21, 22, 23, 31–33 |
| Otro | 48–49 (transport), 93 (government) and anything else |

> **Inconsistency to resolve:** README §5 describes Retail as *SCIAN 46–47* and Services as
> *SCIAN 54–81*, while the ETL includes wholesale (43) in Comercio and 51–53 in Servicios.
> We keep the ETL definition (it is what is in the warehouse) and README should be aligned.

---

## 4. Data audit findings (Census 2020 layer, 526 AGEBs)

Audited from the loaded warehouse rows (`fact_demografia`) and `outputs/maps/merida_agebs_demographics.geojson`.

| # | Finding | Evidence | Impact | Status |
| :-: | :--- | :--- | :--- | :--- |
| 1 | **Age groups and inactive population were mapped to non-existent census columns** (`P_15A64`, `P_65YMAS`, `P_0A14`, `PNEA`). The fallback assigned the full population to 0–14. | 526/526 AGEBs have `poblacion_0_14 = poblacion_total`; `poblacion_15_64`, `poblacion_65_mas`, `poblacion_pnea` are 0 in 100% of rows. | KPI 3 is `NULL` everywhere (denominator 0) and KPI 4 is wrong. | Fixed in `fix/bianca-census-age-columns` (uses `POB0_14`, `POB15_64`, `POB65_MAS`, `PE_INAC`). **ETL must be re-run and Supabase reloaded.** |
| 2 | EAP rate base was `poblacion_total − poblacion_0_14`. INEGI defines PEA over population **12+**, not 15+. | Census descriptor. | Rate would be biased upward. | Fixed in the same branch: base = `PEA + PE_INAC`. |
| 3 | Statistical suppression (`*`) is converted to 0. | Male + female ≠ total in 4 AGEBs (max gap 24). | Small undercount in tiny AGEBs. | Documented assumption; acceptable at AGEB level. |
| 4 | 6 AGEBs have 0 residents and 32 have fewer than 100. | `poblacion_total` distribution. | Per-capita KPIs undefined or extreme. | Handled by the $P_i \ge 100$ rule above. |
| 5 | Polygon area ranges from 0.012 km² to 6.55 km² (median 0.41). | `area_km2`. | Densities of very small polygons are noisy (MAUP). | Report medians and use Spearman, which is robust to outliers. |
| 6 | Total population in the warehouse is **957,399**, while the dashboard card shows 887,632. | `SUM(poblacion_total)`. | Inconsistent number on the frontend. | Frontend card should read from the warehouse. |
| 7 | No crime dataset has been loaded yet (`fact_crimen` is empty). | `load_raw_crime()` finds no file. | KPIs 11–14 and crime correlations cannot be computed. | Notebook and charts already support crime and skip it gracefully until loaded. |
| 8 | `dim_actividad_economica.sector_nombre` stores the 6-digit SCIAN **class** name (e.g. *Salones y clínicas de belleza*), not the 2-digit sector name. | `sql/02_load_scian.sql`. | KPI 10 in the view returns the dominant *class*, which is very granular. | Notebook and charts also report the dominant **2-digit sector** from `sector_codigo`; recommend adding a `sector_nombre_2d` column. |

---

## 5. Correlation analysis plan (Phase 3)

At least three relationships are required. All are computed on AGEBs with $P_i \ge 100$, using
**Spearman's ρ as the primary test** (densities are strongly right-skewed and contain outliers)
and Pearson's *r* on `log1p` values as a secondary check.

| # | Relationship | Hypothesis |
| :-: | :--- | :--- |
| H1 | Population density ↔ Business density | Denser residential areas host more establishments (positive). |
| H2 | EAP rate ↔ Businesses per 1,000 residents | Areas with higher labour participation have more economic activity per resident. |
| H3 | Elderly share (65+) ↔ Service density | Older, consolidated neighbourhoods (centro) concentrate services. |
| H4 | Business density ↔ Crime rate | Commercial concentration attracts property crime (requires crime layer). |
| H5 | Retail density ↔ Crime-to-business ratio | Tests whether retail-heavy areas have more crime *per establishment*, not only more crime. |

Correlation is association only; it does not imply causation, and the values ignore spatial
autocorrelation (see Moran's I in the spatial analytics module for that).

Implementation: `notebooks/02_kpi_correlation_analysis.ipynb`.
