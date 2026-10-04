import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { Activity, ShieldAlert, Building2, Users } from 'lucide-react';
import './App.css';

export default function App() {
  const mapContainer = useRef(null);
  const map = useRef(null);

  useEffect(() => {
    if (map.current) return;

    // Initialize MapLibre with CartoDB Dark Matter tiles (No API key needed)
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [-89.6237, 20.9674], // Mérida Coordinates
      zoom: 11.5,
      pitch: 30
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  return (
    <div className="app-container">
      {/* Sidebar Controls & KPI Overview */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">
            <Activity className="text-cyan-400" size={24} />
            Mérida Intelligence
          </div>
          <p className="sidebar-subtitle">Geospatial Data Warehouse & Urban Analytics</p>
        </div>

        <div className="sidebar-content">
          <div className="kpi-card">
            <div className="kpi-label">Analyzed Urban AGEBs</div>
            <div className="kpi-value">526</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Total Population (INEGI 2020)</div>
            <div className="kpi-value">887,632</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Registered Businesses (DENUE)</div>
            <div className="kpi-value">56,664</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Spatial Analysis Engine</div>
            <div className="kpi-value" style={{ fontSize: '1.1rem', color: '#38bdf8' }}>
              Global & Local Moran's I (LISA)
            </div>
          </div>
        </div>
      </aside>

      {/* MapLibre GIS Canvas */}
      <main className="map-container">
        <div ref={mapContainer} className="map-canvas" />
      </main>
    </div>
  );
}
