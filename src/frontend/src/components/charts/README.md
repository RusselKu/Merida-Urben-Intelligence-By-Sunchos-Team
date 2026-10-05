# Analytics chart components (ApexCharts)

Owner: Bianca — Data Analysis & Visualizations

Dark-theme ApexCharts components for the Mérida Urban Intelligence dashboard. They read one data
feed, `analytics_summary.json`, generated **from the PostGIS warehouse** by
`notebooks/02_kpi_correlation_analysis.ipynb` (view `v_kpis_territoriales` + fact tables).

## Quick use (for the map/layout owner)

```jsx
import { AnalyticsPanel } from './components/charts';

// inside App.jsx, e.g. in the sidebar or a right-hand drawer
<AnalyticsPanel
  selectedCvegeo={selectedCvegeo}          // AGEB clicked on the MapLibre map (optional)
  onSelectAgeb={(cvegeo) => flyToAgeb(cvegeo)} // point clicked in a scatter plot (optional)
/>
```

`AnalyticsPanel` loads its own data and has four tabs: **Overview**, **Economy**, **Safety**, **Correlation**.
Every chart is also exported on its own and takes the loaded `summary` object as a prop:

| Component | KPI(s) covered |
| :--- | :--- |
| `KpiSummaryCards` | Total population, density, EAP rate, businesses, business density, businesses per 1,000, crime incidents, crime rate, crime per 100 establishments (city or one AGEB) |
| `AgeDistributionChart` | Population by age group (donut, city or one AGEB) |
| `SectorBreakdownChart` | Dominant activity / retail vs services (top SCIAN sectors or macro-categories) |
| `CrimeByCategoryChart`, `CrimeTimeHeatmap`, `CrimeTrendChart` | Incidents by type and time |
| `CorrelationScatter` | Hypotheses H1–H5 with Spearman ρ, Holm p-value, Pearson r and n |
| `CorrelationHeatmap` | Full Spearman / Pearson matrix |

## Data feed

* Default URL: `/data/analytics_summary.json` (file in `src/frontend/public/data/`).
* Override with `VITE_ANALYTICS_URL` (e.g. the FastAPI endpoint once it serves the same payload).
* Layers that are not loaded yet (crime, businesses, valid age groups) show an empty-state message
  instead of failing; the flags live in `summary.flags`.

To refresh the numbers: set `DATABASE_URL` in `.env`, run the notebook, and commit the regenerated
`src/frontend/public/data/analytics_summary.json`.
