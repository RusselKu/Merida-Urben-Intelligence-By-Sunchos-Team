import { useEffect, useState } from 'react';

// Data feed produced by notebooks/02_kpi_correlation_analysis.ipynb from the PostGIS warehouse
// (view v_kpis_territoriales). When the FastAPI backend exposes the same payload, set
// VITE_ANALYTICS_URL to that endpoint and no component needs to change.
const DEFAULT_URL = '/data/analytics_summary.json';

export default function useAnalyticsSummary(url = import.meta.env.VITE_ANALYTICS_URL || DEFAULT_URL) {
  const [state, setState] = useState({ data: null, loading: true, error: null });

  useEffect(() => {
    const controller = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));

    fetch(url, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} while loading ${url}`);
        return res.json();
      })
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ data: null, loading: false, error });
      });

    return () => controller.abort();
  }, [url]);

  return state;
}
