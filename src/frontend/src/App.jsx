import React, { useState } from 'react';
import { Activity, MapPinned, X } from 'lucide-react';
import UrbanMap from './components/map/UrbanMap';
import { AnalyticsPanel } from './components/charts';
import './App.css';

export default function App() {
  const [selectedCvegeo, setSelectedCvegeo] = useState(null);

  return (
    <div className="app-container">
      <main className="map-pane">
        <header className="map-brand">
          <div className="map-brand__title">
            <Activity size={22} />
            Mérida Urban Intelligence
          </div>

          <p>
            Geospatial Data Warehouse & Urban Analytics
          </p>
        </header>

        <UrbanMap
          selectedCvegeo={selectedCvegeo}
          onSelectAgeb={setSelectedCvegeo}
        />
      </main>

      <aside className="analytics-sidebar">
        <header className="sidebar-header">
          <div>
            <div className="sidebar-title">
              <MapPinned size={20} />
              Urban Analytics
            </div>

            <p className="sidebar-subtitle">
              INEGI Census 2020 · DENUE · PostGIS
            </p>
          </div>

          {selectedCvegeo && (
            <div className="selected-ageb">
              <div>
                <span>Selected AGEB</span>
                <strong>{selectedCvegeo}</strong>
              </div>

              <button
                type="button"
                title="Clear AGEB selection"
                onClick={() => setSelectedCvegeo(null)}
              >
                <X size={16} />
              </button>
            </div>
          )}
        </header>

        <div className="sidebar-content">
          <AnalyticsPanel
            selectedCvegeo={selectedCvegeo}
            onSelectAgeb={setSelectedCvegeo}
          />
        </div>
      </aside>
    </div>
  );
}
