// Shared ApexCharts configuration so every chart in the dashboard looks like one system
// and matches the dark glass theme defined in src/index.css.

export const COLORS = {
  text: '#f9fafb',
  muted: '#9ca3af',
  grid: 'rgba(255, 255, 255, 0.06)',
  cyan: '#06b6d4',
  blue: '#3b82f6',
  indigo: '#818cf8',
  amber: '#f59e0b',
  pink: '#f472b6',
  emerald: '#34d399',
  slate: '#64748b',
};

// Categorical palette, in a fixed order (series 1 is always cyan, etc.)
export const SERIES_PALETTE = [COLORS.cyan, COLORS.indigo, COLORS.amber, COLORS.pink, COLORS.emerald, COLORS.slate];

// Colors for SCIAN macro-categories (see map_scian_category in src/etl/transform.py)
export const MACRO_COLORS = {
  Comercio: COLORS.cyan,
  Servicios: COLORS.indigo,
  Industria: COLORS.amber,
  Otro: COLORS.slate,
};

export const baseOptions = (overrides = {}) => ({
  chart: {
    background: 'transparent',
    foreColor: COLORS.muted,
    fontFamily: "'Plus Jakarta Sans', sans-serif",
    toolbar: { show: false },
    animations: { enabled: true, speed: 400 },
    ...overrides.chart,
  },
  theme: { mode: 'dark' },
  grid: { borderColor: COLORS.grid, strokeDashArray: 3 },
  dataLabels: { enabled: false },
  legend: { labels: { colors: COLORS.muted }, fontSize: '12px' },
  tooltip: { theme: 'dark' },
  ...Object.fromEntries(Object.entries(overrides).filter(([k]) => k !== 'chart')),
});

export const fmtInt = (v) => (v == null ? '—' : Math.round(v).toLocaleString('en-US'));
export const fmtDec = (v, d = 1) =>
  v == null || Number.isNaN(v)
    ? '—'
    : Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtCompact = (v) =>
  v == null ? '—' : Number(v).toLocaleString('en-US', { notation: 'compact', maximumFractionDigits: 1 });
export const fmtP = (p) => (p == null ? '—' : p < 0.001 ? '< 0.001' : p.toFixed(3));
