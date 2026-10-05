import React, { useMemo, useState } from 'react';
import Chart from 'react-apexcharts';
import ChartCard from './ChartCard';
import { baseOptions, COLORS, fmtDec, fmtP } from './chartTheme';

// Percent-type variables are plotted on a linear axis; densities and rates on log10.
const LINEAR_VARS = new Set(['tasa_pea_porcentaje', 'share_65_mas', 'dependency_ratio']);

const toAxis = (v, log) => (log ? Math.log10(v) : v);
const fromAxis = (v, log) => (log ? 10 ** v : v);

// One scatter plot per tested hypothesis (H1…H5) with its Spearman / Pearson statistics.
// `onSelectAgeb(cvegeo)` lets the map highlight the AGEB of a clicked point.
export default function CorrelationScatter({ summary, onSelectAgeb }) {
  const rels = summary?.relationships || [];
  const [selected, setSelected] = useState(0);
  const rel = rels[Math.min(selected, rels.length - 1)];

  const { series, logX, logY } = useMemo(() => {
    if (!rel) return { series: [], logX: false, logY: false };
    const lx = !LINEAR_VARS.has(rel.x) && rel.points.every((p) => p[0] > 0);
    const ly = !LINEAR_VARS.has(rel.y) && rel.points.every((p) => p[1] > 0);
    return {
      logX: lx,
      logY: ly,
      series: [
        {
          name: rel.id,
          data: rel.points.map(([x, y, cvegeo]) => ({ x: toAxis(x, lx), y: toAxis(y, ly), cvegeo })),
        },
      ],
    };
  }, [rel]);

  const options = baseOptions({
    chart: {
      type: 'scatter',
      zoom: { enabled: true, type: 'xy' },
      events: {
        dataPointSelection: (_e, _ctx, { seriesIndex, dataPointIndex, w }) => {
          const p = w.config.series[seriesIndex].data[dataPointIndex];
          if (onSelectAgeb && p) onSelectAgeb(p.cvegeo);
        },
      },
    },
    colors: [COLORS.cyan],
    markers: { size: 3.5, strokeWidth: 0, fillOpacity: 0.6, hover: { size: 6 } },
    xaxis: {
      type: 'numeric',
      tickAmount: 6,
      title: { text: rel ? `${rel.x_label}${logX ? ' (log scale)' : ''}` : '', style: { color: COLORS.muted } },
      labels: { formatter: (v) => fmtDec(fromAxis(Number(v), logX), logX ? 0 : 1) },
    },
    yaxis: {
      tickAmount: 5,
      title: { text: rel ? `${rel.y_label}${logY ? ' (log scale)' : ''}` : '', style: { color: COLORS.muted } },
      labels: { formatter: (v) => fmtDec(fromAxis(Number(v), logY), logY ? 0 : 1) },
    },
    tooltip: {
      theme: 'dark',
      custom: ({ seriesIndex, dataPointIndex, w }) => {
        const p = w.config.series[seriesIndex].data[dataPointIndex];
        return `<div class="apex-tip"><b>AGEB ${p.cvegeo}</b><br/>${rel.x_label}: ${fmtDec(fromAxis(p.x, logX), 1)}<br/>${rel.y_label}: ${fmtDec(fromAxis(p.y, logY), 1)}</div>`;
      },
    },
  });

  const picker = rels.length > 0 && (
    <select className="chart-select" value={selected} onChange={(e) => setSelected(Number(e.target.value))}>
      {rels.map((r, i) => (
        <option key={r.id} value={i}>
          {r.id}: {r.x_label} vs {r.y_label}
        </option>
      ))}
    </select>
  );

  return (
    <ChartCard
      title="Tested relationships"
      subtitle="Each point is one urban AGEB"
      actions={picker}
      empty={!rel}
      emptyMessage="Run notebooks/02_kpi_correlation_analysis.ipynb to generate the relationship tests."
    >
      {rel && (
        <>
          <div className="stat-row">
            <div><span>Spearman ρ</span><b>{fmtDec(rel.spearman_rho, 3)}</b></div>
            <div><span>p (Holm)</span><b>{fmtP(rel.spearman_p_holm)}</b></div>
            <div><span>Pearson r (log)</span><b>{fmtDec(rel.pearson_r_log, 3)}</b></div>
            <div><span>n</span><b>{rel.n}</b></div>
            <div className={rel.significant ? 'badge badge--ok' : 'badge'}>
              {rel.significant ? `${rel.strength} ${rel.direction}` : 'not significant'}
            </div>
          </div>
          <Chart key={rel.id} type="scatter" height={300} series={series} options={options} />
          <p className="chart-note">Association, not causation. Neighbouring AGEBs are not independent — see Moran's I.</p>
        </>
      )}
    </ChartCard>
  );
}
