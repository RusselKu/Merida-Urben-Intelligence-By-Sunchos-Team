import React, { useMemo, useState } from 'react';
import Chart from 'react-apexcharts';
import ChartCard, { Toggle } from './ChartCard';
import { baseOptions, COLORS } from './chartTheme';

// Short axis labels; the full label is shown in the tooltip.
const SHORT = {
  densidad_poblacion_km2: 'Pop. dens.',
  tasa_pea_porcentaje: 'EAP %',
  share_65_mas: '65+ %',
  dependency_ratio: 'Dependency',
  densidad_viviendas_km2: 'Housing dens.',
  densidad_negocios_km2: 'Business dens.',
  negocios_por_mil_hab: 'Bus./1k',
  densidad_comercio_km2: 'Retail dens.',
  densidad_servicios_km2: 'Service dens.',
  tasa_delictiva_por_mil_hab: 'Crime/1k',
  delitos_por_100_negocios: 'Crime/100 bus.',
};

// Diverging scale: blue = negative, neutral gray = none, red = positive.
const RANGES = [
  { from: -1, to: -0.5, color: '#1d4ed8', name: 'strong −' },
  { from: -0.5, to: -0.3, color: '#3b82f6', name: 'moderate −' },
  { from: -0.3, to: -0.1, color: '#93c5fd', name: 'weak −' },
  { from: -0.1, to: 0.1, color: '#374151', name: 'negligible' },
  { from: 0.1, to: 0.3, color: '#fca5a5', name: 'weak +' },
  { from: 0.3, to: 0.5, color: '#ef4444', name: 'moderate +' },
  { from: 0.5, to: 1.0001, color: '#b91c1c', name: 'strong +' },
];

export default function CorrelationHeatmap({ summary }) {
  const [method, setMethod] = useState('spearman');
  const matrix = summary?.correlation_matrix;
  const vars = matrix?.variables || [];
  const values = matrix?.[method] || [];

  const series = useMemo(
    () =>
      vars
        .map((rowVar, i) => ({
          name: SHORT[rowVar.key] || rowVar.label,
          data: vars.map((colVar, j) => ({
            x: SHORT[colVar.key] || colVar.label,
            y: values[i]?.[j] == null ? 0 : Number(values[i][j].toFixed(2)),
            full: `${rowVar.label} × ${colVar.label}`,
          })),
        }))
        .reverse(), // ApexCharts draws the first series at the bottom
    [vars, values],
  );

  const options = baseOptions({
    chart: { type: 'heatmap' },
    plotOptions: { heatmap: { radius: 2, enableShades: false, colorScale: { ranges: RANGES } } },
    dataLabels: {
      enabled: vars.length <= 7, // larger matrices: values in the tooltip only
      style: { fontSize: '10px', colors: [COLORS.text] },
      formatter: (v) => v.toFixed(2),
    },
    stroke: { width: 1, colors: ['#0b0f19'] },
    xaxis: { labels: { rotate: -45, style: { fontSize: '10px' } }, tooltip: { enabled: false } },
    yaxis: { labels: { style: { fontSize: '10px', colors: COLORS.muted } } },
    legend: { position: 'bottom', fontSize: '11px' },
    tooltip: {
      theme: 'dark',
      custom: ({ seriesIndex, dataPointIndex, w }) => {
        const p = w.config.series[seriesIndex].data[dataPointIndex];
        return `<div class="apex-tip"><b>${p.full}</b><br/>${method === 'spearman' ? 'Spearman ρ' : 'Pearson r (log)'} = ${p.y.toFixed(3)}</div>`;
      },
    },
  });

  return (
    <ChartCard
      title="Correlation matrix"
      subtitle={`AGEBs with population ≥ ${summary?.min_population_rule ?? 100}`}
      actions={
        <Toggle
          value={method}
          onChange={setMethod}
          options={[
            { value: 'spearman', label: 'Spearman' },
            { value: 'pearson_log', label: 'Pearson' },
          ]}
        />
      }
      empty={vars.length < 2}
      emptyMessage="Run notebooks/02_kpi_correlation_analysis.ipynb to generate the correlation matrix."
    >
      <Chart type="heatmap" height={Math.max(320, vars.length * 34 + 110)} series={series} options={options} />
    </ChartCard>
  );
}
