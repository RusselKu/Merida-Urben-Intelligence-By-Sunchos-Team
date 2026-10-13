import React from 'react';
import { fmtInt, fmtDec } from './chartTheme';
import { Users, TrendingUp, ShieldAlert, Building2, Briefcase, Activity } from 'lucide-react';

const GROUP_CONFIG = {
  Demographic: {
    color: 'cyan',
    icon: Users,
    label: 'Demographic',
  },
  Economic: {
    color: 'emerald',
    icon: Building2,
    label: 'Economic',
  },
  'Public safety': {
    color: 'rose',
    icon: ShieldAlert,
    label: 'Public Safety',
  },
};

// Absolute counts are not comparable to a citywide total — one AGEB out of 526
// is trivially ~100% below it. Only normalised metrics carry a benchmark.
const ABSOLUTE_METRICS = new Set([
  'poblacion_total',
  'total_negocios',
  'total_delitos',
]);

function getDelta(localVal, cityVal) {
  const l = Number(localVal);
  const c = Number(cityVal);
  if (!Number.isFinite(l) || !Number.isFinite(c) || c <= 0) return null;
  const pct = ((l - c) / c) * 100;
  return {
    pct: pct.toFixed(0),
    isPositive: pct > 0,
    isEqual: Math.abs(pct) < 1,
  };
}

export default function KpiSummaryCards({ summary, ageb = null }) {
  if (!summary) return null;
  const c = ageb || summary.city;
  const city = summary.city || {};
  const crimeLoaded = summary.flags?.crime_layer_loaded;
  const businessLoaded = summary.flags?.business_layer_loaded;

  const tiles = [
    {
      key: 'poblacion_total',
      label: 'Total population',
      value: fmtInt(c.poblacion_total),
      unit: 'residents',
      group: 'Demographic',
      rawLocal: c.poblacion_total,
      rawCity: city.poblacion_total,
    },
    {
      key: 'densidad_poblacion_km2',
      label: 'Population density',
      value: fmtInt(c.densidad_poblacion_km2),
      unit: 'res / km²',
      group: 'Demographic',
      rawLocal: c.densidad_poblacion_km2,
      rawCity: city.densidad_poblacion_km2,
    },
    {
      key: 'tasa_pea_porcentaje',
      label: 'EAP rate (12+)',
      value: fmtDec(c.tasa_pea_porcentaje),
      unit: '% active',
      group: 'Demographic',
      rawLocal: c.tasa_pea_porcentaje,
      rawCity: city.tasa_pea_porcentaje,
    },
    {
      key: 'total_negocios',
      label: 'Total businesses',
      value: businessLoaded ? fmtInt(c.total_negocios) : '—',
      unit: 'establishments',
      group: 'Economic',
      rawLocal: c.total_negocios,
      rawCity: city.total_negocios,
    },
    {
      key: 'densidad_negocios_km2',
      label: 'Business density',
      value: businessLoaded ? fmtInt(c.densidad_negocios_km2) : '—',
      unit: 'est / km²',
      group: 'Economic',
      rawLocal: c.densidad_negocios_km2,
      rawCity: city.densidad_negocios_km2,
    },
    {
      key: 'negocios_por_mil_hab',
      label: 'Businesses / 1k res.',
      value: businessLoaded ? fmtDec(c.negocios_por_mil_hab) : '—',
      unit: 'per 1k residents',
      group: 'Economic',
      rawLocal: c.negocios_por_mil_hab,
      rawCity: city.negocios_por_mil_hab,
    },
    {
      key: 'total_delitos',
      label: 'Crime incidents',
      value: crimeLoaded ? fmtInt(c.total_delitos) : '—',
      unit: 'georeferenced',
      group: 'Public safety',
      rawLocal: c.total_delitos,
      rawCity: city.total_delitos,
    },
    {
      key: 'tasa_delictiva_por_mil_hab',
      label: 'Crime rate / 1k',
      value: crimeLoaded ? fmtDec(c.tasa_delictiva_por_mil_hab) : '—',
      unit: 'per 1k residents',
      group: 'Public safety',
      rawLocal: c.tasa_delictiva_por_mil_hab,
      rawCity: city.tasa_delictiva_por_mil_hab,
    },
    {
      key: 'delitos_por_100_negocios',
      label: 'Crime / 100 businesses',
      value: crimeLoaded ? fmtDec(c.delitos_por_100_negocios) : '—',
      unit: 'per 100 est.',
      group: 'Public safety',
      rawLocal: c.delitos_por_100_negocios,
      rawCity: city.delitos_por_100_negocios,
    },
  ];

  return (
    <div className="kpi-grid">
      {tiles.map((t) => {
        const groupInfo = GROUP_CONFIG[t.group] || { color: 'cyan', label: t.group };
        const delta =
          ageb && !ABSOLUTE_METRICS.has(t.key)
            ? getDelta(t.rawLocal, t.rawCity)
            : null;

        return (
          <div key={t.key} className={`kpi-tile kpi-tile--${groupInfo.color} glass-panel`}>
            <div className="kpi-tile__header">
              <span className={`kpi-tile__group kpi-tile__group--${groupInfo.color}`}>
                {groupInfo.label}
              </span>
            </div>

            <div className="kpi-tile__value-row">
              <span
                className="kpi-tile__value"
                title={
                  t.value === '—'
                    ? 'Not available: this layer is not loaded in the current warehouse build'
                    : undefined
                }
              >
                {t.value}
              </span>
              {delta && !delta.isEqual && (
                <span
                  className={`kpi-delta-pill ${
                    delta.isPositive ? 'kpi-delta--pos' : 'kpi-delta--neg'
                  }`}
                  title={`${Math.abs(delta.pct)}% ${
                    delta.isPositive ? 'above' : 'below'
                  } the Mérida metropolitan average`}
                >
                  {delta.isPositive ? `+${delta.pct}%` : `${delta.pct}%`}
                </span>
              )}
            </div>
            <span className="kpi-tile__label">{t.label}</span>
            <span className="kpi-tile__unit">{t.unit}</span>
          </div>
        );
      })}
    </div>
  );
}
