import React from 'react';
import { fmtInt, fmtDec } from './chartTheme';

// City-wide KPI tiles computed from the warehouse (replaces hard-coded numbers).
// Pass `ageb` (one row of summary.agebs) to show the KPIs of a selected AGEB instead.
export default function KpiSummaryCards({ summary, ageb = null }) {
  if (!summary) return null;
  const c = ageb || summary.city;
  const crimeLoaded = summary.flags?.crime_layer_loaded;
  const businessLoaded = summary.flags?.business_layer_loaded;

  const tiles = [
    { label: 'Total population', value: fmtInt(c.poblacion_total), unit: 'residents', group: 'Demographic' },
    { label: 'Population density', value: fmtInt(c.densidad_poblacion_km2), unit: 'res / km²', group: 'Demographic' },
    { label: 'EAP rate', value: fmtDec(c.tasa_pea_porcentaje), unit: '% of 12+', group: 'Demographic' },
    { label: 'Businesses', value: businessLoaded ? fmtInt(c.total_negocios) : '—', unit: 'DENUE establishments', group: 'Economic' },
    { label: 'Business density', value: businessLoaded ? fmtInt(c.densidad_negocios_km2) : '—', unit: 'est / km²', group: 'Economic' },
    { label: 'Businesses per 1,000', value: businessLoaded ? fmtDec(c.negocios_por_mil_hab) : '—', unit: 'per 1k residents', group: 'Economic' },
    { label: 'Crime incidents', value: crimeLoaded ? fmtInt(c.total_delitos) : '—', unit: 'georeferenced', group: 'Public safety' },
    { label: 'Crime rate', value: crimeLoaded ? fmtDec(c.tasa_delictiva_por_mil_hab) : '—', unit: 'per 1k residents', group: 'Public safety' },
    { label: 'Crime vs business', value: crimeLoaded ? fmtDec(c.delitos_por_100_negocios) : '—', unit: 'per 100 establishments', group: 'Public safety' },
  ];

  return (
    <div className="kpi-grid">
      {tiles.map((t) => (
        <div key={t.label} className="kpi-tile">
          <span className="kpi-tile__group">{t.group}</span>
          <span className="kpi-tile__value">{t.value}</span>
          <span className="kpi-tile__label">{t.label}</span>
          <span className="kpi-tile__unit">{t.unit}</span>
        </div>
      ))}
    </div>
  );
}
