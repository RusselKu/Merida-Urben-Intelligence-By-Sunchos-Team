import React, { useMemo, useState } from 'react';
import useAnalyticsSummary from './useAnalyticsSummary';
import KpiSummaryCards from './KpiSummaryCards';
import AgeDistributionChart from './AgeDistributionChart';
import SectorBreakdownChart from './SectorBreakdownChart';
import CorrelationHeatmap from './CorrelationHeatmap';
import CorrelationScatter from './CorrelationScatter';
import { CrimeByCategoryChart, CrimeTimeHeatmap, CrimeTrendChart } from './CrimeCharts';
import './charts.css';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'economy', label: 'Economy' },
  { id: 'safety', label: 'Safety' },
  { id: 'correlation', label: 'Correlation' },
];

/**
 * Analytics panel for the dashboard. Self-contained: it loads its own data feed.
 *
 * Props (both optional, for syncing with the MapLibre map):
 *   selectedCvegeo  – AGEB clicked on the map; Overview then shows that AGEB's KPIs.
 *   onSelectAgeb    – called with a cvegeo when the user clicks a point in a scatter plot.
 */
export default function AnalyticsPanel({ selectedCvegeo = null, onSelectAgeb }) {
  const { data, loading, error } = useAnalyticsSummary();
  const [tab, setTab] = useState('overview');

  const ageb = useMemo(
    () => (selectedCvegeo && data ? data.agebs?.find((a) => a.cvegeo === selectedCvegeo) || null : null),
    [data, selectedCvegeo],
  );

  if (loading) return <div className="analytics-panel analytics-panel--status">Loading analytics…</div>;
  if (error)
    return (
      <div className="analytics-panel analytics-panel--status">
        Could not load the analytics feed ({error.message}). Run notebooks/02_kpi_correlation_analysis.ipynb against
        the warehouse to generate public/data/analytics_summary.json.
      </div>
    );

  return (
    <div className="analytics-panel">
      <nav className="analytics-tabs">
        {TABS.map((t) => (
          <button key={t.id} type="button" className={tab === t.id ? 'is-active' : ''} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      {tab === 'overview' && (
        <>
          {ageb && <p className="analytics-context">Showing AGEB {ageb.cvegeo}</p>}
          <KpiSummaryCards summary={data} ageb={ageb} />
          <AgeDistributionChart summary={data} ageb={ageb} />
        </>
      )}
      {tab === 'economy' && <SectorBreakdownChart summary={data} />}
      {tab === 'safety' && (
        <>
          <CrimeByCategoryChart summary={data} />
          <CrimeTimeHeatmap summary={data} />
          <CrimeTrendChart summary={data} />
        </>
      )}
      {tab === 'correlation' && (
        <>
          <CorrelationScatter summary={data} onSelectAgeb={onSelectAgeb} />
          <CorrelationHeatmap summary={data} />
        </>
      )}

      <footer className="analytics-footer">
        Source: {data.source} · generated {data.generated_at?.slice(0, 10)}
      </footer>
    </div>
  );
}
