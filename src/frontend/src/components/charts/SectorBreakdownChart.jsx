import React, { useState } from 'react';
import Chart from 'react-apexcharts';
import ChartCard, { Toggle } from './ChartCard';
import { baseOptions, MACRO_COLORS, COLORS, fmtInt, fmtCompact } from './chartTheme';

// Economic structure: establishments by SCIAN sector (top N) or by macro-category
// (Comercio / Servicios / Industria / Otro, the basis of retail and service density).
export default function SectorBreakdownChart({ summary, topN = 10 }) {
  const [mode, setMode] = useState('sector');
  const sectors = (summary?.sectors || []).slice(0, topN);
  const macros = summary?.macro_categories || [];
  const rows = mode === 'sector' ? sectors : macros;

  const total = rows.reduce((a, r) => a + r.count, 0);
  const options = baseOptions({
    plotOptions: { bar: { horizontal: true, borderRadius: 3, barHeight: '70%', distributed: true } },
    colors: rows.map((r) => MACRO_COLORS[mode === 'sector' ? r.macro : r.name] || COLORS.slate),
    xaxis: {
      categories: rows.map((r) => (mode === 'sector' ? `${r.name} (${r.code})` : r.name)),
      tickAmount: 4,
      labels: { formatter: (v) => fmtCompact(v) },
    },
    yaxis: { labels: { maxWidth: 190, style: { colors: COLORS.muted } } },
    legend: { show: false },
    tooltip: {
      theme: 'dark',
      y: {
        formatter: (v) => `${fmtInt(v)} establishments (${((v / (total || 1)) * 100).toFixed(1)}%)`,
        title: { formatter: () => '' },
      },
    },
  });

  return (
    <ChartCard
      title="Economic activity"
      subtitle={mode === 'sector' ? `Top ${rows.length} SCIAN sectors, colored by macro-category` : 'Establishments by macro-category'}
      actions={
        <Toggle
          value={mode}
          onChange={setMode}
          options={[
            { value: 'sector', label: 'Sector' },
            { value: 'macro', label: 'Macro' },
          ]}
        />
      }
      empty={rows.length === 0}
      emptyMessage="No DENUE establishments in the warehouse yet."
    >
      <Chart
        key={mode}
        type="bar"
        height={Math.max(220, rows.length * 30 + 60)}
        series={[{ name: 'Establishments', data: rows.map((r) => r.count) }]}
        options={options}
      />
      {mode === 'sector' && (
        <div className="chart-legend">
          {Object.entries(MACRO_COLORS).map(([name, color]) => (
            <span key={name}>
              <i style={{ background: color }} />
              {name}
            </span>
          ))}
        </div>
      )}
    </ChartCard>
  );
}
