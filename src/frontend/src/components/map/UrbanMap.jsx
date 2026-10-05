import React, { useEffect, useMemo, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './UrbanMap.css';

const GEOJSON_URL =
  import.meta.env.VITE_MAP_GEOJSON_URL ||
  '/data/merida_agebs_demographics.geojson';

const ANALYTICS_URL =
  import.meta.env.VITE_ANALYTICS_URL ||
  '/data/analytics_summary.json';

const COLORS = [
  '#164e63',
  '#0891b2',
  '#22d3ee',
  '#818cf8',
  '#c084fc',
];

const KPI_OPTIONS = [
  {
    key: 'poblacion_total',
    label: 'Total population',
    unit: 'residents',
  },
  {
    key: 'densidad_poblacion_km2',
    label: 'Population density',
    unit: 'res / km²',
  },
  {
    key: 'tasa_pea_porcentaje',
    label: 'EAP rate',
    unit: '%',
  },
  {
    key: 'total_negocios',
    label: 'Total businesses',
    unit: 'establishments',
  },
  {
    key: 'densidad_negocios_km2',
    label: 'Business density',
    unit: 'est / km²',
  },
  {
    key: 'negocios_por_mil_hab',
    label: 'Businesses per 1,000 residents',
    unit: 'per 1k',
  },
  {
    key: 'densidad_comercio_km2',
    label: 'Retail / trade density',
    unit: 'est / km²',
  },
  {
    key: 'densidad_servicios_km2',
    label: 'Service density',
    unit: 'est / km²',
  },
];

const KPI_LOOKUP = Object.fromEntries(
  KPI_OPTIONS.map((option) => [option.key, option]),
);

function formatNumber(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) return 'No data';

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
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

function buildScale(geojson, metric) {
  const values = geojson.features
    .map((feature) => Number(feature.properties?.[metric]))
    .filter(Number.isFinite)
    .sort((a, b) => a - b);

  if (!values.length) {
    return [
      { value: 0, color: COLORS[0] },
      { value: 1, color: COLORS[COLORS.length - 1] },
    ];
  }

  const percentiles = [0, 0.25, 0.5, 0.75, 1];

  const rawStops = percentiles.map((p, index) => ({
    value: percentile(values, p),
    color: COLORS[index],
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
      color: COLORS[COLORS.length - 1],
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
  const [selectedMetric, setSelectedMetric] = useState(
    'densidad_poblacion_km2',
  );
  const [opacity, setOpacity] = useState(0.72);
  const [mapReady, setMapReady] = useState(false);
  const [error, setError] = useState(null);

  selectedMetricRef.current = selectedMetric;

  useEffect(() => {
    const controller = new AbortController();

    async function loadData() {
      try {
        const [geoResponse, analyticsResponse] = await Promise.all([
          fetch(GEOJSON_URL, { signal: controller.signal }),
          fetch(ANALYTICS_URL, { signal: controller.signal }),
        ]);

        if (!geoResponse.ok) {
          throw new Error(
            `GeoJSON request failed with HTTP ${geoResponse.status}`,
          );
        }

        if (!analyticsResponse.ok) {
          throw new Error(
            `Analytics request failed with HTTP ${analyticsResponse.status}`,
          );
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
    return buildScale(geojson, selectedMetric);
  }, [geojson, selectedMetric]);

  useEffect(() => {
    if (!geojson || map.current) return;

    const initialScale = buildScale(
      geojson,
      selectedMetricRef.current,
    );

    const instance = new maplibregl.Map({
      container: mapContainer.current,
      style:
        'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [-89.6237, 20.9674],
      zoom: 11,
      pitch: 15,
    });

    map.current = instance;

    instance.addControl(
      new maplibregl.NavigationControl(),
      'top-right',
    );

    popup.current = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
    });

    instance.on('load', () => {
      instance.addSource('merida-agebs', {
        type: 'geojson',
        data: geojson,
        promoteId: 'cvegeo',
      });

      instance.addLayer({
        id: 'ageb-fill',
        type: 'fill',
        source: 'merida-agebs',
        paint: {
          'fill-color': colorExpression(
            selectedMetricRef.current,
            initialScale,
          ),
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.95,
            opacity,
          ],
        },
      });

      instance.addLayer({
        id: 'ageb-outline',
        type: 'line',
        source: 'merida-agebs',
        paint: {
          'line-color': 'rgba(226, 232, 240, 0.55)',
          'line-width': 0.6,
        },
      });

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
          'line-color': '#ffffff',
          'line-width': 3,
        },
      });

      instance.on('mousemove', 'ageb-fill', (event) => {
        const feature = event.features?.[0];

        if (!feature) return;

        instance.getCanvas().style.cursor = 'pointer';

        if (
          hoveredFeature.current &&
          hoveredFeature.current !== feature.id
        ) {
          instance.setFeatureState(
            {
              source: 'merida-agebs',
              id: hoveredFeature.current,
            },
            { hover: false },
          );
        }

        hoveredFeature.current = feature.id;

        instance.setFeatureState(
          {
            source: 'merida-agebs',
            id: feature.id,
          },
          { hover: true },
        );

        const metric = selectedMetricRef.current;
        const metricConfig = KPI_LOOKUP[metric];
        const properties = feature.properties;

        popup.current
          .setLngLat(event.lngLat)
          .setHTML(`
            <div class="map-popup">
              <strong>AGEB ${properties.cvegeo}</strong>
              <span>
                ${metricConfig.label}:
                <b>${formatNumber(properties[metric])}</b>
                ${metricConfig.unit}
              </span>
              <span>
                Population:
                <b>${formatNumber(properties.poblacion_total)}</b>
              </span>
              <span>
                Businesses:
                <b>${formatNumber(properties.total_negocios)}</b>
              </span>
              <small>Click to inspect this AGEB</small>
            </div>
          `)
          .addTo(instance);
      });

      instance.on('mouseleave', 'ageb-fill', () => {
        instance.getCanvas().style.cursor = '';

        if (hoveredFeature.current !== null) {
          instance.setFeatureState(
            {
              source: 'merida-agebs',
              id: hoveredFeature.current,
            },
            { hover: false },
          );
        }

        hoveredFeature.current = null;
        popup.current?.remove();
      });

      instance.on('click', 'ageb-fill', (event) => {
        const cvegeo =
          event.features?.[0]?.properties?.cvegeo;

        if (cvegeo) {
          onSelectAgeb?.(String(cvegeo));
        }
      });

      setMapReady(true);
    });

    return () => {
      popup.current?.remove();
      instance.remove();
      map.current = null;
    };
  }, [geojson]);

  useEffect(() => {
    if (
      !mapReady ||
      !map.current ||
      !map.current.getLayer('ageb-fill') ||
      !scale.length
    ) {
      return;
    }

    map.current.setPaintProperty(
      'ageb-fill',
      'fill-color',
      colorExpression(selectedMetric, scale),
    );
  }, [mapReady, selectedMetric, scale]);

  useEffect(() => {
    if (
      !mapReady ||
      !map.current ||
      !map.current.getLayer('ageb-fill')
    ) {
      return;
    }

    map.current.setPaintProperty(
      'ageb-fill',
      'fill-opacity',
      [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        Math.min(opacity + 0.2, 1),
        opacity,
      ],
    );
  }, [mapReady, opacity]);

  useEffect(() => {
    if (
      !mapReady ||
      !map.current ||
      !map.current.getLayer('ageb-selected')
    ) {
      return;
    }

    map.current.setFilter('ageb-selected', [
      '==',
      ['get', 'cvegeo'],
      selectedCvegeo || '__none__',
    ]);

    if (!selectedCvegeo || !geojson) return;

    const feature = geojson.features.find(
      (item) =>
        String(item.properties?.cvegeo) ===
        String(selectedCvegeo),
    );

    if (!feature) return;

    const bounds = geometryBounds(feature.geometry);

    if (!bounds.isEmpty()) {
      map.current.fitBounds(bounds, {
        padding: 80,
        maxZoom: 14,
        duration: 650,
      });
    }
  }, [mapReady, selectedCvegeo, geojson]);

  const activeMetric = KPI_LOOKUP[selectedMetric];

  return (
    <div className="urban-map">
      <div ref={mapContainer} className="urban-map__canvas" />

      <section className="urban-map__controls">
        <label>
          <span>Choropleth KPI</span>

          <select
            value={selectedMetric}
            onChange={(event) =>
              setSelectedMetric(event.target.value)
            }
          >
            {KPI_OPTIONS.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>
            Polygon opacity
            <b>{Math.round(opacity * 100)}%</b>
          </span>

          <input
            type="range"
            min="0.2"
            max="0.95"
            step="0.05"
            value={opacity}
            onChange={(event) =>
              setOpacity(Number(event.target.value))
            }
          />
        </label>

        <div className="urban-map__status">
          {geojson
            ? `${geojson.features.length} AGEB polygons loaded`
            : 'Loading AGEB polygons…'}
        </div>
      </section>

      {scale.length > 0 && (
        <section className="urban-map__legend">
          <strong>{activeMetric.label}</strong>

          <div className="urban-map__legend-scale">
            {scale.map((stop) => (
              <div key={`${stop.value}-${stop.color}`}>
                <i
                  style={{
                    backgroundColor: stop.color,
                  }}
                />
                <span>
                  {formatNumber(stop.value)}
                </span>
              </div>
            ))}
          </div>

          <small>{activeMetric.unit}</small>
        </section>
      )}

      {error && (
        <div className="urban-map__error">
          Map data could not be loaded: {error.message}
        </div>
      )}
    </div>
  );
}
