import React from 'react';
import Chart from 'react-apexcharts';
import ChartCard from './ChartCard';
import { baseOptions, COLORS, fmtInt } from './chartTheme';

// KPI "Population by Age Group" — donut for the whole city or for a selected AGEB.
export default function AgeDistributionChart({ summary, ageb = null }) {
  const valid = summary?.flags?.age_groups_valid;
  const groups = ageb
    ? [
        { group: '0-14', value: ageb.poblacion_0_14 },
        { group: '15-64', value: ageb.poblacion_15_64 },
        { group: '65+', value: ageb.poblacion_65_mas },
      ]
    : summary?.age_groups || [];

  const series = groups.map((g) => g.value || 0);
  const total = series.reduce((a, b) => a + b, 0);

  const options = baseOptions({
    labels: groups.map((g) => `${g.group} years`),
    colors: [COLORS.cyan, COLORS.indigo, COLORS.amber],
    stroke: { width: 0 },
    legend: { position: 'bottom', labels: { colors: COLORS.muted } },
    dataLabels: { enabled: true, formatter: (pct) => `${pct.toFixed(1)}%` },
    plotOptions: {
      pie: {
        donut: {
          size: '68%',
          labels: {
            show: true,
            value: { color: COLORS.text, formatter: (v) => fmtInt(Number(v)) },
            total: { show: true, label: 'Residents', color: COLORS.muted, formatter: () => fmtInt(total) },
          },
        },
      },
    },
    tooltip: { theme: 'dark', y: { formatter: (v) => `${fmtInt(v)} residents` } },
  });

  return (
    <ChartCard
      title="Population by age group"
      subtitle={ageb ? `AGEB ${ageb.cvegeo}` : 'Mérida urban AGEBs — INEGI Census 2020'}
      empty={!valid || total === 0}
      emptyMessage="Age groups are not valid in the warehouse yet (census column mapping fix pending reload)."
    >
      <Chart type="donut" height={280} series={series} options={options} />
    </ChartCard>
  );
}
