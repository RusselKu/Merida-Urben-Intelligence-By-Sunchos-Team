import React, { useEffect, useMemo, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  Layers,
  Box,
  RotateCcw,
  Palette,
  ChevronDown,
  ChevronUp,
  MapPin,
  TrendingUp,
  Sliders,
  Sparkles,
  Plus,
  Minus,
} from 'lucide-react';
import { getAgebReferenceArea } from '../../data/agebReferenceAreas';
import './UrbanMap.css';

const GEOJSON_URL =
  import.meta.env.VITE_MAP_GEOJSON_URL ||
  '/data/merida_agebs_demographics.geojson';

const ANALYTICS_URL =
  import.meta.env.VITE_ANALYTICS_URL ||
  '/data/analytics_summary.json';

const PALETTES = {
  cyan: {
    id: 'cyan',
    name: 'Cyber Cyan',
    colors: ['#082f49', '#0284c7', '#06b6d4', '#818cf8', '#c084fc'],
    accent: '#06b6d4',
  },
  solar: {
    id: 'solar',
    name: 'Solar Flare',
    colors: ['#1c1917', '#991b1b', '#ea580c', '#f59e0b', '#fde047'],
    accent: '#f59e0b',
  },
  emerald: {
    id: 'emerald',
    name: 'Emerald Eco',
    colors: ['#022c22', '#065f46', '#059669', '#10b981', '#6ee7b7'],
    accent: '#10b981',
  },
  violet: {
    id: 'violet',
    name: 'Neon Violet',
    colors: ['#1e1b4b', '#4338ca', '#7c3aed', '#a855f7', '#f472b6'],
    accent: '#a855f7',
  },
};

const KPI_OPTIONS = [
  {
    key: 'densidad_poblacion_km2',
    label: 'Population density',
    shortLabel: 'Pop Density',
    unit: 'res / km²',
    category: 'Demographic',
  },
  {
    key: 'total_negocios',
    label: 'Total businesses',
    shortLabel: 'Businesses',
    unit: 'establishments',
    category: 'Economic',
  },
  {
    key: 'poblacion_total',
    label: 'Total population',
    shortLabel: 'Population',
    unit: 'residents',
    category: 'Demographic',
  },
  {
    key: 'tasa_pea_porcentaje',
    label: 'EAP rate (Economically Active)',
    shortLabel: 'EAP Rate',
    unit: '%',
    category: 'Labor',
  },
  {
    key: 'densidad_negocios_km2',
    label: 'Business density',
    shortLabel: 'Bus. Density',
    unit: 'est / km²',
    category: 'Economic',
  },
  {
    key: 'negocios_por_mil_hab',
    label: 'Businesses per 1,000 residents',
    shortLabel: 'Bus. / 1k',
    unit: 'per 1k res',
    category: 'Economic',
  },
  {
    key: 'densidad_comercio_km2',
    label: 'Retail & trade density',
    shortLabel: 'Retail',
    unit: 'est / km²',
    category: 'Sectoral',
  },
  {
    key: 'densidad_servicios_km2',
    label: 'Urban service density',
    shortLabel: 'Services',
    unit: 'est / km²',
    category: 'Sectoral',
  },
];

const KPI_LOOKUP = Object.fromEntries(
  KPI_OPTIONS.map((option) => [option.key, option]),
);

function formatNumber(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 'No data';
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
  }).format(number);
}

function percentile(sorted, p) {
  if (!sorted.length) return 0;
  const index = (sorted.length - 1) * p;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);

  if (lower === upper) return sorted[lower];
  const weight = index - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

function buildScale(geojson, metric, paletteKey = 'cyan') {
  const colors = PALETTES[paletteKey]?.colors || PALETTES.cyan.colors;
  const values = geojson.features
    .map((feature) => Number(feature.properties?.[metric]))
    .filter(Number.isFinite)
    .sort((a, b) => a - b);

  if (!values.length) {
    return [
      { value: 0, color: colors[0] },
      { value: 1, color: colors[colors.length - 1] },
    ];
  }

  const percentiles = [0, 0.25, 0.5, 0.75, 1];
  const rawStops = percentiles.map((p, index) => ({
    value: percentile(values, p),
    color: colors[index],
  }));

  const uniqueStops = [];
  rawStops.forEach((stop) => {
    const previous = uniqueStops[uniqueStops.length - 1];
    if (!previous || stop.value > previous.value) {
      uniqueStops.push(stop);
    }
  });

  if (uniqueStops.length === 1) {
    uniqueStops.push({
      value: uniqueStops[0].value + 1,
      color: colors[colors.length - 1],
    });
  }

  return uniqueStops;
}

function colorExpression(metric, scale) {
  return [
    'interpolate',
    ['linear'],
    ['to-number', ['get', metric], 0],
    ...scale.flatMap((stop) => [stop.value, stop.color]),
  ];
}

function extrusionHeightExpression(metric, maxVal) {
  const safeMax = maxVal > 0 ? maxVal : 100;
  return [
    'interpolate',
    ['linear'],
    ['to-number', ['get', metric], 0],
    0,
    40,
    safeMax,
    2600,
  ];
}

function geometryBounds(geometry) {
  const bounds = new maplibregl.LngLatBounds();
  const addCoordinates = (coordinates) => {
    if (
      Array.isArray(coordinates) &&
      coordinates.length >= 2 &&
      typeof coordinates[0] === 'number' &&
      typeof coordinates[1] === 'number'
    ) {
      bounds.extend(coordinates);
      return;
    }
    coordinates.forEach(addCoordinates);
  };
  addCoordinates(geometry.coordinates);
  return bounds;
}

export default function UrbanMap({
  selectedCvegeo = null,
  onSelectAgeb,
}) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const popup = useRef(null);
  const hoveredFeature = useRef(null);
  const selectedMetricRef = useRef('densidad_poblacion_km2');

  const [geojson, setGeojson] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState('densidad_poblacion_km2');
  const [opacity, setOpacity] = useState(0.78);
  const [is3D, setIs3D] = useState(false);
  const [paletteKey, setPaletteKey] = useState('cyan');
  const [controlsExpanded, setControlsExpanded] = useState(true);
  const [mapReady, setMapReady] = useState(false);
  const [error, setError] = useState(null);

  selectedMetricRef.current = selectedMetric;

  // Max value of selected metric for 3D extrusion scale
  const maxMetricValue = useMemo(() => {
    if (!geojson) return 100;
    const values = geojson.features
      .map((f) => Number(f.properties?.[selectedMetric]))
      .filter(Number.isFinite);
    return values.length ? Math.max(...values) : 100;
  }, [geojson, selectedMetric]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadData() {
      try {
        const [geoResponse, analyticsResponse] = await Promise.all([
          fetch(GEOJSON_URL, { signal: controller.signal }),
          fetch(ANALYTICS_URL, { signal: controller.signal }),
        ]);

        if (!geoResponse.ok) {
          throw new Error(`GeoJSON request failed: HTTP ${geoResponse.status}`);
        }
        if (!analyticsResponse.ok) {
          throw new Error(`Analytics request failed: HTTP ${analyticsResponse.status}`);
        }

        const [geometryData, analyticsData] = await Promise.all([
          geoResponse.json(),
          analyticsResponse.json(),
        ]);

        const analyticsByCvegeo = new Map(
          (analyticsData.agebs || []).map((ageb) => [
            String(ageb.cvegeo),
            ageb,
          ]),
        );

        const mergedGeojson = {
          ...geometryData,
          features: geometryData.features.map((feature) => {
            const cvegeo = String(feature.properties?.cvegeo || '');
            const metrics = analyticsByCvegeo.get(cvegeo) || {};
            return {
              ...feature,
              properties: {
                ...feature.properties,
                ...metrics,
                cvegeo,
              },
            };
          }),
        };

        setGeojson(mergedGeojson);
      } catch (loadError) {
        if (loadError.name !== 'AbortError') {
          setError(loadError);
        }
      }
    }

    loadData();
    return () => controller.abort();
  }, []);

  const scale = useMemo(() => {
    if (!geojson) return [];
    return buildScale(geojson, selectedMetric, paletteKey);
  }, [geojson, selectedMetric, paletteKey]);

  // Initialize Map
  useEffect(() => {
    if (!geojson || map.current) return;

    const initialScale = buildScale(
      geojson,
      selectedMetricRef.current,
      paletteKey,
    );

    const instance = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [-89.6237, 20.9674],
      zoom: 11.2,
      pitch: 0,
      bearing: 0,
      attributionControl: false,
    });

    map.current = instance;

    popup.current = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 14,
      className: 'custom-map-popup',
    });

    instance.on('load', () => {
      instance.addSource('merida-agebs', {
        type: 'geojson',
        data: geojson,
        promoteId: 'cvegeo',
      });

      // 2D Fill Layer
      instance.addLayer({
        id: 'ageb-fill',
        type: 'fill',
        source: 'merida-agebs',
        layout: {
          visibility: 'visible',
        },
        paint: {
          'fill-color': colorExpression(
            selectedMetricRef.current,
            initialScale,
          ),
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.96,
            opacity,
          ],
        },
      });

      // 3D Extrusion Layer
      instance.addLayer({
        id: 'ageb-extrusion',
        type: 'fill-extrusion',
        source: 'merida-agebs',
        layout: {
          visibility: 'none',
        },
        paint: {
          'fill-extrusion-color': colorExpression(
            selectedMetricRef.current,
            initialScale,
          ),
          'fill-extrusion-height': extrusionHeightExpression(
            selectedMetricRef.current,
            maxMetricValue,
          ),
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': opacity,
        },
      });

      // Outline Layer
      instance.addLayer({
        id: 'ageb-outline',
        type: 'line',
        source: 'merida-agebs',
        paint: {
          'line-color': 'rgba(148, 163, 184, 0.45)',
          'line-width': 0.7,
        },
      });

      // Selected AGEB Outline Layer
      instance.addLayer({
        id: 'ageb-selected',
        type: 'line',
        source: 'merida-agebs',
        filter: [
          '==',
          ['get', 'cvegeo'],
          selectedCvegeo || '__none__',
        ],
        paint: {
          'line-color': '#38bdf8',
          'line-width': 3.5,
          'line-blur': 0.5,
        },
      });

      // Hover handler
      const handleMouseMove = (event) => {
        const feature = event.features?.[0];
        if (!feature) return;

        instance.getCanvas().style.cursor = 'pointer';

        if (
          hoveredFeature.current &&
          hoveredFeature.current !== feature.id
        ) {
          instance.setFeatureState(
            { source: 'merida-agebs', id: hoveredFeature.current },
            { hover: false },
          );
        }

        hoveredFeature.current = feature.id;
        instance.setFeatureState(
          { source: 'merida-agebs', id: feature.id },
          { hover: true },
        );

        const metric = selectedMetricRef.current;
        const metricConfig = KPI_LOOKUP[metric] || KPI_OPTIONS[0];
        const properties = feature.properties;
        const referenceArea = getAgebReferenceArea(properties.cvegeo);

        const areaName = referenceArea?.name || 'Mérida Territory';
        const areaType = referenceArea?.type || 'Urban zone';
        const postalCode = referenceArea?.postalCode
          ? `CP ${referenceArea.postalCode}`
          : '';

        popup.current
          .setLngLat(event.lngLat)
          .setHTML(`
            <div class="hud-tooltip">
              <div class="hud-tooltip__header">
                <div class="hud-tooltip__badge-row">
                  <span class="hud-badge hud-badge--type">${areaType}</span>
                  ${postalCode ? `<span class="hud-badge hud-badge--cp">${postalCode}</span>` : ''}
                  <span class="hud-badge hud-badge--cve">AGEB ${properties.cvegeo}</span>
                </div>
                <strong class="hud-tooltip__title">${areaName}</strong>
              </div>

              <div class="hud-tooltip__highlight">
                <span class="hud-tooltip__metric-label">${metricConfig.label}</span>
                <div class="hud-tooltip__metric-val">
                  <span>${formatNumber(properties[metric])}</span>
                  <small>${metricConfig.unit}</small>
                </div>
              </div>

              <div class="hud-tooltip__grid">
                <div class="hud-tooltip__stat">
                  <span>Population</span>
                  <strong>${formatNumber(properties.poblacion_total, 0)}</strong>
                </div>
                <div class="hud-tooltip__stat">
                  <span>Businesses</span>
                  <strong>${formatNumber(properties.total_negocios, 0)}</strong>
                </div>
              </div>

              <div class="hud-tooltip__action">
                <span class="hud-tooltip__dot"></span>
                <span>Click to inspect in Analytics</span>
              </div>
            </div>
          `)
          .addTo(instance);
      };

      const handleMouseLeave = () => {
        instance.getCanvas().style.cursor = '';
        if (hoveredFeature.current !== null) {
          instance.setFeatureState(
            { source: 'merida-agebs', id: hoveredFeature.current },
            { hover: false },
          );
        }
        hoveredFeature.current = null;
        popup.current?.remove();
      };

      const handleClick = (event) => {
        const cvegeo = event.features?.[0]?.properties?.cvegeo;
        if (cvegeo) {
          onSelectAgeb?.(String(cvegeo));
        }
      };

      // Register events on both 2D and 3D layers
      ['ageb-fill', 'ageb-extrusion'].forEach((layerId) => {
        instance.on('mousemove', layerId, handleMouseMove);
        instance.on('mouseleave', layerId, handleMouseLeave);
        instance.on('click', layerId, handleClick);
      });

      setMapReady(true);
    });

    return () => {
      popup.current?.remove();
      instance.remove();
      map.current = null;
    };
  }, [geojson]);

  // Update Choropleth & Extrusion Color on metric/scale change
  useEffect(() => {
    if (!mapReady || !map.current || !scale.length) return;

    const expr = colorExpression(selectedMetric, scale);

    if (map.current.getLayer('ageb-fill')) {
      map.current.setPaintProperty('ageb-fill', 'fill-color', expr);
    }

    if (map.current.getLayer('ageb-extrusion')) {
      map.current.setPaintProperty('ageb-extrusion', 'fill-extrusion-color', expr);
      map.current.setPaintProperty(
        'ageb-extrusion',
        'fill-extrusion-height',
        extrusionHeightExpression(selectedMetric, maxMetricValue),
      );
    }
  }, [mapReady, selectedMetric, scale, maxMetricValue]);

  // Update Opacity
  useEffect(() => {
    if (!mapReady || !map.current) return;

    if (map.current.getLayer('ageb-fill')) {
      map.current.setPaintProperty('ageb-fill', 'fill-opacity', [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        Math.min(opacity + 0.18, 1),
        opacity,
      ]);
    }

    if (map.current.getLayer('ageb-extrusion')) {
      map.current.setPaintProperty('ageb-extrusion', 'fill-extrusion-opacity', opacity);
    }
  }, [mapReady, opacity]);

  // Toggle 2D vs 3D Extrusion
  useEffect(() => {
    if (!mapReady || !map.current) return;

    if (is3D) {
      if (map.current.getLayer('ageb-fill')) {
        map.current.setPaintProperty('ageb-fill', 'fill-opacity', 0.22);
      }
      if (map.current.getLayer('ageb-extrusion')) {
        map.current.setLayoutProperty('ageb-extrusion', 'visibility', 'visible');
      }
      map.current.easeTo({
        pitch: 50,
        bearing: -16,
        duration: 900,
      });
    } else {
      if (map.current.getLayer('ageb-fill')) {
        map.current.setPaintProperty('ageb-fill', 'fill-opacity', [
          'case',
          ['boolean', ['feature-state', 'hover'], false],
          Math.min(opacity + 0.18, 1),
          opacity,
        ]);
      }
      if (map.current.getLayer('ageb-extrusion')) {
        map.current.setLayoutProperty('ageb-extrusion', 'visibility', 'none');
      }
      map.current.easeTo({
        pitch: 0,
        bearing: 0,
        duration: 900,
      });
    }
  }, [mapReady, is3D, opacity]);

  // Handle selected AGEB change (highlight & fitBounds)
  useEffect(() => {
    if (!mapReady || !map.current || !map.current.getLayer('ageb-selected')) {
      return;
    }

    map.current.setFilter('ageb-selected', [
      '==',
      ['get', 'cvegeo'],
      selectedCvegeo || '__none__',
    ]);

    if (!selectedCvegeo || !geojson) return;

    const feature = geojson.features.find(
      (item) => String(item.properties?.cvegeo) === String(selectedCvegeo),
    );

    if (!feature) return;

    const bounds = geometryBounds(feature.geometry);
    if (!bounds.isEmpty()) {
      map.current.fitBounds(bounds, {
        padding: 90,
        maxZoom: 14.5,
        duration: 750,
      });
    }
  }, [mapReady, selectedCvegeo, geojson]);

  const activeMetric = KPI_LOOKUP[selectedMetric] || KPI_OPTIONS[0];

  const handleResetCamera = () => {
    if (!map.current) return;
    map.current.flyTo({
      center: [-89.6237, 20.9674],
      zoom: 11.2,
      pitch: is3D ? 48 : 0,
      bearing: is3D ? -16 : 0,
      duration: 1000,
    });
  };

  const handleZoom = (delta) => {
    if (!map.current) return;
    map.current.zoomTo(map.current.getZoom() + delta, { duration: 300 });
  };

  // Top 4 popular KPIs for quick buttons
  const quickKpis = [
    'densidad_poblacion_km2',
    'total_negocios',
    'poblacion_total',
    'tasa_pea_porcentaje',
  ];

  return (
    <div className="urban-map">
      <div ref={mapContainer} className="urban-map__canvas" />

      {/* Floating HUD Controls (Collapsible, Top Left) */}
      <section
        className={`urban-map__hud glass-panel ${controlsExpanded ? 'is-expanded' : 'is-collapsed'}`}
      >
        <div
          className="urban-map__hud-header"
          onClick={() => setControlsExpanded(!controlsExpanded)}
        >
          <div className="urban-map__hud-title">
            <Sliders size={16} className="text-cyan" />
            <span>Layers & Metrics</span>
          </div>
          <button
            type="button"
            className="hud-toggle-btn"
            title={controlsExpanded ? 'Collapse controls' : 'Expand controls'}
          >
            {controlsExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        </div>

        {controlsExpanded && (
          <div className="urban-map__hud-body">
            {/* Quick KPI Chips */}
            <div className="hud-quick-chips">
              {quickKpis.map((kpiKey) => {
                const opt = KPI_LOOKUP[kpiKey];
                const active = selectedMetric === kpiKey;
                return (
                  <button
                    key={kpiKey}
                    type="button"
                    className={`hud-chip ${active ? 'is-active' : ''}`}
                    onClick={() => setSelectedMetric(kpiKey)}
                  >
                    {opt.shortLabel}
                  </button>
                );
              })}
            </div>

            {/* Metric Select Dropdown */}
            <label className="hud-field">
              <span className="hud-field-label">
                Choropleth KPI
              </span>
              <div className="hud-select-wrap">
                <select
                  value={selectedMetric}
                  onChange={(e) => setSelectedMetric(e.target.value)}
                >
                  {KPI_OPTIONS.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label} ({option.unit})
                    </option>
                  ))}
                </select>
              </div>
            </label>

            {/* 2D / 3D Extrusion & Palette Row */}
            <div className="hud-mode-row">
              <button
                type="button"
                className={`hud-mode-btn ${is3D ? 'is-active' : ''}`}
                onClick={() => setIs3D(!is3D)}
                title="Toggle 3D isometric height extrusion"
              >
                <Box size={14} />
                <span>{is3D ? '3D Height Mode' : '2D Flat Mode'}</span>
              </button>

              <div className="hud-palette-selector">
                {Object.values(PALETTES).map((pal) => (
                  <button
                    key={pal.id}
                    type="button"
                    className={`hud-palette-dot ${paletteKey === pal.id ? 'is-selected' : ''}`}
                    style={{ backgroundColor: pal.accent }}
                    title={`Palette: ${pal.name}`}
                    onClick={() => setPaletteKey(pal.id)}
                  />
                ))}
              </div>
            </div>

            {/* Opacity Slider */}
            <div className="hud-field hud-field--slider">
              <div className="hud-slider-header">
                <span>Polygon Opacity</span>
                <span className="hud-slider-val">{Math.round(opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="0.95"
                step="0.05"
                value={opacity}
                onChange={(e) => setOpacity(Number(e.target.value))}
                className="hud-slider"
              />
            </div>

            {/* Status Info */}
            <div className="hud-footer-status">
              <span className="live-beacon" />
              <span>
                {geojson
                  ? `${geojson.features.length} urban AGEBs rendered`
                  : 'Loading geospatial cartography…'}
              </span>
            </div>
          </div>
        )}
      </section>

      {/* Floating Action Toolbar (Right Side) */}
      <div className="urban-map__toolbar glass-panel">
        <button
          type="button"
          onClick={() => handleZoom(1)}
          title="Zoom in"
          className="toolbar-btn"
        >
          <Plus size={16} />
        </button>
        <button
          type="button"
          onClick={() => handleZoom(-1)}
          title="Zoom out"
          className="toolbar-btn"
        >
          <Minus size={16} />
        </button>
        <div className="toolbar-divider" />
        <button
          type="button"
          onClick={() => setIs3D(!is3D)}
          title={is3D ? 'Switch to 2D' : 'View 3D Isometric'}
          className={`toolbar-btn ${is3D ? 'is-active' : ''}`}
        >
          <Box size={16} />
        </button>
        <button
          type="button"
          onClick={handleResetCamera}
          title="Reset view to Mérida"
          className="toolbar-btn"
        >
          <RotateCcw size={15} />
        </button>
      </div>

      {/* Bottom Horizontal Gradient Legend (Never collides with top controls) */}
      {scale.length > 0 && (
        <section className="urban-map__gradient-legend glass-panel">
          <div className="gradient-legend__header">
            <span className="gradient-legend__title">
              {activeMetric.label}
            </span>
            <span className="gradient-legend__unit">
              {activeMetric.unit}
            </span>
          </div>

          <div
            className="gradient-legend__bar"
            style={{
              background: `linear-gradient(to right, ${scale.map((s) => s.color).join(', ')})`,
            }}
          />

          <div className="gradient-legend__labels">
            <span>{formatNumber(scale[0].value, 1)}</span>
            <span>{formatNumber(scale[Math.floor(scale.length / 2)].value, 1)}</span>
            <span>{formatNumber(scale[scale.length - 1].value, 1)}</span>
          </div>
        </section>
      )}

      {error && (
        <div className="urban-map__error glass-panel">
          Failed to load geospatial data: {error.message}
        </div>
      )}
    </div>
  );
}
