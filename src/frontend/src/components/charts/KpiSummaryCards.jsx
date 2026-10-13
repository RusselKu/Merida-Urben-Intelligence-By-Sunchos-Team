import React from 'react';
import { fmtInt, fmtDec } from './chartTheme';
import { Users, TrendingUp, ShieldAlert, Building2, Briefcase, Activity } from 'lucide-react';

const GROUP_CONFIG = {
  Demographic: {
    color: 'cyan',
    icon: Users,
    label: 'Demográfico',
  },
  Economic: {
    color: 'emerald',
    icon: Building2,
    label: 'Económico',
  },
  'Public safety': {
    color: 'rose',
    icon: ShieldAlert,
    label: 'Seguridad',
  },
};

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
      label: 'Población total',
      value: fmtInt(c.poblacion_total),
      unit: 'habitantes',
      group: 'Demographic',
      rawLocal: c.poblacion_total,
      rawCity: city.poblacion_total,
    },
    {
      key: 'densidad_poblacion_km2',
      label: 'Densidad poblacional',
      value: fmtInt(c.densidad_poblacion_km2),
      unit: 'hab / km²',
      group: 'Demographic',
      rawLocal: c.densidad_poblacion_km2,
      rawCity: city.densidad_poblacion_km2,
    },
    {
      key: 'tasa_pea_porcentaje',
      label: 'Tasa PEA (12+)',
      value: fmtDec(c.tasa_pea_porcentaje),
      unit: '% activa',
      group: 'Demographic',
      rawLocal: c.tasa_pea_porcentaje,
      rawCity: city.tasa_pea_porcentaje,
    },
    {
      key: 'total_negocios',
      label: 'Negocios totales',
      value: businessLoaded ? fmtInt(c.total_negocios) : '—',
      unit: 'establecimientos',
      group: 'Economic',
      rawLocal: c.total_negocios,
      rawCity: city.total_negocios,
    },
    {
      key: 'densidad_negocios_km2',
      label: 'Densidad de negocios',
      value: businessLoaded ? fmtInt(c.densidad_negocios_km2) : '—',
      unit: 'est / km²',
      group: 'Economic',
      rawLocal: c.densidad_negocios_km2,
      rawCity: city.densidad_negocios_km2,
    },
    {
      key: 'negocios_por_mil_hab',
      label: 'Negocios / 1k hab.',
      value: businessLoaded ? fmtDec(c.negocios_por_mil_hab) : '—',
      unit: 'por 1,000 hab',
      group: 'Economic',
      rawLocal: c.negocios_por_mil_hab,
      rawCity: city.negocios_por_mil_hab,
    },
    {
      key: 'total_delitos',
      label: 'Incidentes delictivos',
      value: crimeLoaded ? fmtInt(c.total_delitos) : '—',
      unit: 'georreferenciados',
      group: 'Public safety',
      rawLocal: c.total_delitos,
      rawCity: city.total_delitos,
    },
    {
      key: 'tasa_delictiva_por_mil_hab',
      label: 'Tasa delictiva / 1k',
      value: crimeLoaded ? fmtDec(c.tasa_delictiva_por_mil_hab) : '—',
      unit: 'por 1,000 hab',
      group: 'Public safety',
      rawLocal: c.tasa_delictiva_por_mil_hab,
      rawCity: city.tasa_delictiva_por_mil_hab,
    },
    {
      key: 'delitos_por_100_negocios',
      label: 'Delitos / 100 negocios',
      value: crimeLoaded ? fmtDec(c.delitos_por_100_negocios) : '—',
      unit: 'por 100 est.',
      group: 'Public safety',
      rawLocal: c.delitos_por_100_negocios,
      rawCity: city.delitos_por_100_negocios,
    },
  ];

  return (
    <div className="kpi-grid">
      {tiles.map((t) => {
        const groupInfo = GROUP_CONFIG[t.group] || { color: 'cyan', label: t.group };
        const delta = ageb ? getDelta(t.rawLocal, t.rawCity) : null;

        return (
          <div key={t.key} className={`kpi-tile kpi-tile--${groupInfo.color} glass-panel`}>
            <div className="kpi-tile__header">
              <span className={`kpi-tile__group kpi-tile__group--${groupInfo.color}`}>
                {groupInfo.label}
              </span>
              {delta && !delta.isEqual && (
                <span
                  className={`kpi-delta-pill ${
                    delta.isPositive ? 'kpi-delta--pos' : 'kpi-delta--neg'
                  }`}
                  title="Comparativa relativa contra el promedio metropolitano de Mérida"
                >
                  {delta.isPositive ? `+${delta.pct}%` : `${delta.pct}%`} vs ciudad
                </span>
              )}
            </div>

            <span className="kpi-tile__value">{t.value}</span>
            <span className="kpi-tile__label">{t.label}</span>
            <span className="kpi-tile__unit">{t.unit}</span>
          </div>
        );
      })}
    </div>
  );
}
