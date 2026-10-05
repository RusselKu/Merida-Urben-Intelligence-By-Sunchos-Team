import React from 'react';

// Common frame for every chart: title, optional subtitle/actions and an empty state.
export default function ChartCard({ title, subtitle, actions, empty, emptyMessage, children }) {
  return (
    <section className="chart-card">
      <header className="chart-card__header">
        <div>
          <h3 className="chart-card__title">{title}</h3>
          {subtitle && <p className="chart-card__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="chart-card__actions">{actions}</div>}
      </header>
      {empty ? <div className="chart-card__empty">{emptyMessage || 'No data available yet.'}</div> : children}
    </section>
  );
}

// Small segmented control used by several charts (e.g. Spearman / Pearson)
export function Toggle({ options, value, onChange }) {
  return (
    <div className="chart-toggle" role="group">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          className={o.value === value ? 'is-active' : ''}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
