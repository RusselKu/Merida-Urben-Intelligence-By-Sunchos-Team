import React from 'react';
import Chart from 'react-apexcharts';
import ChartCard from './ChartCard';
import { baseOptions, COLORS, SERIES_PALETTE, fmtInt, fmtCompact } from './chartTheme';

const NOT_LOADED = 'The crime layer (fact_crimen) has not been loaded into the warehouse yet.';

// KPI "Incidents by Type and Time" — part 1: incidents by crime category.
export function CrimeByCategoryChart({ summary }) {
  const rows = summary?.crime?.by_category || [];
  const options = baseOptions({
    plotOptions: { bar: { horizontal: true, borderRadius: 3, barHeight: '65%' } },
    colors: [COLORS.pink],
    xaxis: { categories: rows.map((r) => r.category), tickAmount: 4, labels: { formatter: (v) => fmtCompact(v) } },
    yaxis: { labels: { maxWidth: 180, style: { colors: COLORS.muted } } },
    tooltip: { theme: 'dark', y: { formatter: (v) => `${fmtInt(v)} incidents` } },
  });
  return (
    <ChartCard title="Incidents by crime type" empty={rows.length === 0} emptyMessage={NOT_LOADED}>
      <Chart
        type="bar"
        height={Math.max(200, rows.length * 32 + 60)}
        series={[{ name: 'Incidents', data: rows.map((r) => r.count) }]}
        options={options}
      />
    </ChartCard>
  );
}

// KPI "Incidents by Type and Time" — part 2: time-of-day × day-of-week heatmap.
export function CrimeTimeHeatmap({ summary }) {
  const t = summary?.crime?.period_by_day;
  const empty = !t || !t.periods?.length || !t.days?.length;
  const max = empty ? 0 : Math.max(...t.values.flat());

  const series = empty
    ? []
    : t.periods
        .map((p, i) => ({ name: p, data: t.days.map((d, j) => ({ x: d.slice(0, 3), y: t.values[i][j] })) }))
        .reverse();

  const options = baseOptions({
    chart: { type: 'heatmap' },
    plotOptions: {
      heatmap: {
        radius: 3,
        enableShades: true,
        shadeIntensity: 0.6,
        colorScale: { ranges: [{ from: 0, to: max || 1, color: COLORS.pink }] },
      },
    },
    dataLabels: { enabled: true, style: { fontSize: '10px', colors: [COLORS.text] } },
    stroke: { width: 2, colors: ['#0b0f19'] },
    legend: { show: false },
    tooltip: { theme: 'dark', y: { formatter: (v) => `${fmtInt(v)} incidents` } },
  });

  return (
    <ChartCard title="When incidents happen" subtitle="Time of day × day of week" empty={empty} emptyMessage={NOT_LOADED}>
      <Chart type="heatmap" height={240} series={series} options={options} />
    </ChartCard>
  );
}

// Monthly trend by crime category (stacked area would hide small categories, so lines).
export function CrimeTrendChart({ summary }) {
  const m = summary?.crime?.monthly;
  const empty = !m || !m.periods?.length;
  const options = baseOptions({
    chart: { type: 'line', zoom: { enabled: false } },
    colors: SERIES_PALETTE,
    stroke: { width: 2, curve: 'smooth' },
    xaxis: { categories: m?.periods || [], tickAmount: 12, labels: { rotate: -45, style: { fontSize: '10px' } } },
    yaxis: { labels: { formatter: (v) => fmtInt(v) } },
    legend: { position: 'top', horizontalAlign: 'left' },
  });
  return (
    <ChartCard title="Monthly incidents by type" empty={empty} emptyMessage={NOT_LOADED}>
      <Chart type="line" height={260} series={m?.series || []} options={options} />
    </ChartCard>
  );
}
