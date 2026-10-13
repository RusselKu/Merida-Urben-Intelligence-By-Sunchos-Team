import React, { useMemo, useState } from 'react';
import { LayoutDashboard, Building2, ShieldAlert, Network, Sparkles, MapPin } from 'lucide-react';
import useAnalyticsSummary from './useAnalyticsSummary';
import KpiSummaryCards from './KpiSummaryCards';
import AgeDistributionChart from './AgeDistributionChart';
import SectorBreakdownChart from './SectorBreakdownChart';
import CorrelationHeatmap from './CorrelationHeatmap';
import CorrelationScatter from './CorrelationScatter';
import { CrimeByCategoryChart, CrimeTimeHeatmap, CrimeTrendChart } from './CrimeCharts';
import './charts.css';

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'economy', label: 'Economy', icon: Building2 },
  { id: 'safety', label: 'Safety', icon: ShieldAlert },
  { id: 'correlation', label: 'Correlation', icon: Network },
];

/**
 * Analytics panel for the dashboard.
 * Props:
 *   selectedCvegeo  – AGEB clicked on the map; Overview then shows that AGEB's KPIs.
 *   onSelectAgeb    – called with a cvegeo when the user clicks a point in a scatter plot.
 */
export default function AnalyticsPanel({ selectedCvegeo = null, onSelectAgeb }) {
  const { data, loading, error, reload } = useAnalyticsSummary();
  const [tab, setTab] = useState('overview');

  const ageb = useMemo(
    () => (selectedCvegeo && data ? data.agebs?.find((a) => a.cvegeo === selectedCvegeo) || null : null),
    [data, selectedCvegeo],
  );

  if (loading) {
    return (
      <div className="analytics-panel analytics-panel--status glass-panel">
        <div className="loading-spinner" />
        <span>Loading analytics matrix & data warehouse…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-panel analytics-panel--status analytics-panel--error glass-panel">
        <div>
          <strong>Analytics feed unavailable</strong>
          <p>
            The map stays usable; metrics and charts return once the feed responds.
          </p>
          <button type="button" className="retry-btn" onClick={reload}>
            Try again
          </button>
          <code>{error.message}</code>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-panel">
      {/* Tab Navigation with Icons */}
      <nav className="analytics-tabs glass-panel">
        {TABS.map((t) => {
          const Icon = t.icon;
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              className={`analytics-tab-btn ${isActive ? 'is-active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              <Icon size={14} className="tab-icon" />
              <span>{t.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Tab Content */}
      <div className="analytics-tab-content">
        {tab === 'overview' && (
          <div className="tab-pane-fade">
            {ageb && (
              <div className="analytics-context-badge">
                <MapPin size={13} className="text-cyan" />
                <span>Focused on AGEB <strong>{ageb.cvegeo}</strong></span>
              </div>
            )}
            {selectedCvegeo && !ageb && (
              <div className="analytics-context-badge analytics-context-badge--warn">
                <MapPin size={13} />
                <span>
                  No warehouse record for AGEB <strong>{selectedCvegeo}</strong>.
                  Showing citywide figures.
                </span>
              </div>
            )}
            <KpiSummaryCards summary={data} ageb={ageb} />
            <AgeDistributionChart summary={data} ageb={ageb} />
          </div>
        )}

        {tab === 'economy' && (
          <div className="tab-pane-fade">
            <SectorBreakdownChart summary={data} />
          </div>
        )}

        {tab === 'safety' && (
          <div className="tab-pane-fade">
            <CrimeByCategoryChart summary={data} />
            <CrimeTimeHeatmap summary={data} />
            <CrimeTrendChart summary={data} />
          </div>
        )}

        {tab === 'correlation' && (
          <div className="tab-pane-fade">
            <CorrelationScatter summary={data} onSelectAgeb={onSelectAgeb} />
            <CorrelationHeatmap summary={data} />
          </div>
        )}
      </div>

      <footer className="analytics-footer">
        <div className="footer-meta">
          <span>Source: {data.source}</span>
          <span>·</span>
          <span>Updated: {data.generated_at?.slice(0, 10)}</span>
        </div>
      </footer>
    </div>
  );
}
