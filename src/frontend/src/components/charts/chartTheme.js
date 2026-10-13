// Shared ApexCharts configuration so every chart in the dashboard looks like one
// system and matches the Yucatán token palette defined in src/index.css.

export const COLORS = {
  text: '#f4f1ec',
  muted: '#aba69e',
  grid: 'rgba(244, 241, 236, 0.07)',
  cyan: '#4ba3c7',   // Maya Blue
  blue: '#6b8fb8',   // cenote
  indigo: '#8fd0e3',
  amber: '#d9a441',  // henequén
  pink: '#b07aa1',   // colonial rose
  emerald: '#3fa37a',// jade
  rose: '#d4654f',   // terracotta
  slate: '#8c8780',  // limestone grey
};

// Categorical palette, in a fixed order (series 1 is always Maya Blue, etc.)
export const SERIES_PALETTE = [
  COLORS.cyan,
  COLORS.amber,
  COLORS.emerald,
  COLORS.pink,
  COLORS.rose,
  COLORS.slate,
];

// Colors for SCIAN macro-categories (see map_scian_category in src/etl/transform.py)
export const MACRO_COLORS = {
  Comercio: COLORS.cyan,
  Servicios: COLORS.amber,
  Industria: COLORS.emerald,
  Otro: COLORS.slate,
};

export const baseOptions = (overrides = {}) => ({
  chart: {
    background: 'transparent',
    foreColor: COLORS.muted,
    fontFamily: "'IBM Plex Sans', sans-serif",
    toolbar: { show: false },
    animations: { enabled: true, speed: 400 },
    ...overrides.chart,
  },
  theme: { mode: 'dark' },
  grid: { borderColor: COLORS.grid, strokeDashArray: 3 },
  stroke: { lineCap: 'round' },
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
