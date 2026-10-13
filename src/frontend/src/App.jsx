import React, { useState, useEffect, useRef } from 'react';
import {
  Activity,
  MapPinned,
  Search,
  X,
  Compass,
  PanelRightClose,
  PanelRightOpen,
  Building2,
  Users,
  Layers,
  MapPin,
  Sparkles,
} from 'lucide-react';
import UrbanMap from './components/map/UrbanMap';
import { AnalyticsPanel } from './components/charts';
import UrbanInsightStory from './components/insights/UrbanInsightStory';
import {
  getAgebReferenceArea,
  searchAgebReferenceAreas,
} from './data/agebReferenceAreas';
import './App.css';

export default function App() {
  const [selectedCvegeo, setSelectedCvegeo] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const searchRef = useRef(null);

  const selectedReferenceArea = getAgebReferenceArea(selectedCvegeo);

  // Handle live search
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.trim().length < 2) {
      setSearchResults([]);
      setSearchOpen(false);
      return;
    }

    const matches = searchAgebReferenceAreas(searchQuery, 8);
    setSearchResults(matches);
    setSearchOpen(matches.length > 0);
  }, [searchQuery]);

  // Click outside search suggestions
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setSearchOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectSearchResult = (cvegeo) => {
    setSelectedCvegeo(cvegeo);
    setSearchQuery('');
    setSearchOpen(false);
    if (!sidebarOpen) setSidebarOpen(true);
  };

  return (
    <div className={`app-shell ${sidebarOpen ? 'with-sidebar' : 'map-only'}`}>
      {/* Top Application Header / Command Bar */}
      <header className="app-header glass-panel">
        <div className="app-header__left">
          <div className="app-brand-badge">
            <div className="brand-logo-glow">
              <Activity size={20} className="brand-logo-icon" />
            </div>
            <div className="brand-copy">
              <div className="brand-title-row">
                <h1 className="brand-name">Mérida Urban Intelligence</h1>
                <span className="brand-version-tag">v2.4 Enterprise</span>
              </div>
              <p className="brand-subtitle">
                Geospatial Data Warehouse · INEGI Census 2020 & DENUE
              </p>
            </div>
          </div>
        </div>

        {/* Global Omni-Search */}
        <div className="app-header__center" ref={searchRef}>
          <div className="global-search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search neighborhood, colonia, or AGEB (e.g. Centro, Caucel)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => {
                if (searchResults.length > 0) setSearchOpen(true);
              }}
              className="global-search-input"
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                  setSearchOpen(false);
                }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Search Suggestions Dropdown */}
          {searchOpen && (
            <div className="search-dropdown glass-panel">
              <div className="search-dropdown__header">
                <span>Search results ({searchResults.length})</span>
              </div>
              <div className="search-dropdown__list">
                {searchResults.map((item) => (
                  <button
                    key={item.cvegeo}
                    type="button"
                    className="search-item"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSelectSearchResult(item.cvegeo);
                    }}
                  >
                    <MapPin size={16} className="search-item-pin" />
                    <div className="search-item-info">
                      <div className="search-item-title-row">
                        <strong className="search-item-name">{item.name}</strong>
                        {item.type && (
                          <span className="search-item-badge">{item.type}</span>
                        )}
                        {item.postalCode && (
                          <span className="search-item-cp">CP {item.postalCode}</span>
                        )}
                      </div>
                      <small className="search-item-sub">
                        AGEB: {item.cvegeo}
                        {item.coveragePct ? ` · Coverage: ${item.coveragePct}%` : ''}
                      </small>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Header Right Stats & Controls */}
        <div className="app-header__right">
          <div className="header-stat-pill">
            <Users size={14} className="stat-pill-icon text-cyan" />
            <div className="stat-pill-data">
              <span>Population</span>
              <strong>957,399</strong>
            </div>
          </div>

          <div className="header-stat-pill">
            <Building2 size={14} className="stat-pill-icon text-emerald" />
            <div className="stat-pill-data">
              <span>Businesses</span>
              <strong>56,614</strong>
            </div>
          </div>

          <div className="header-stat-pill">
            <Layers size={14} className="stat-pill-icon text-violet" />
            <div className="stat-pill-data">
              <span>AGEBs</span>
              <strong>526</strong>
            </div>
          </div>

          <div className="header-divider" />

          {/* Live DB Beacon */}
          <div className="header-live-indicator" title="Live connection to PostGIS Data Warehouse">
            <span className="live-beacon" />
            <span className="live-label">PostGIS Sync</span>
          </div>

          {/* Toggle Sidebar Button */}
          <button
            type="button"
            className="sidebar-toggle-btn"
            title={sidebarOpen ? 'Collapse analytics panel' : 'Expand analytics panel'}
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
          </button>
        </div>
      </header>

      {/* Main Workspace (Map + Analytics Sidebar) */}
      <div className="app-body">
        {/* Map Viewport */}
        <main className="map-viewport">
          <UrbanMap
            selectedCvegeo={selectedCvegeo}
            onSelectAgeb={(cvegeo) => {
              setSelectedCvegeo(cvegeo);
              if (!sidebarOpen) setSidebarOpen(true);
            }}
          />
        </main>

        {/* Analytics & Insights Sidebar */}
        {sidebarOpen && (
          <aside className="analytics-sidebar glass-panel">
            {/* Sidebar Header & Selected AGEB Inspector Card */}
            <div className="sidebar-top">
              <div className="sidebar-header-row">
                <div className="sidebar-heading">
                  <MapPinned size={18} className="text-cyan" />
                  <h2>Urban Analytics</h2>
                </div>
                <span className="sidebar-meta-badge">Census 2020 · DENUE</span>
              </div>

              {/* Selected AGEB Inspector Dossier */}
              {selectedCvegeo ? (
                <div className="selected-dossier">
                  <div className="selected-dossier__main">
                    <div className="selected-dossier__badges">
                      <span className="dossier-tag dossier-tag--active">
                        Selected AGEB
                      </span>
                      {selectedReferenceArea?.type && (
                        <span className="dossier-tag dossier-tag--type">
                          {selectedReferenceArea.type}
                        </span>
                      )}
                      {selectedReferenceArea?.postalCode && (
                        <span className="dossier-tag dossier-tag--cp">
                          CP {selectedReferenceArea.postalCode}
                        </span>
                      )}
                    </div>

                    <h3 className="selected-dossier__name">
                      {selectedReferenceArea?.name || 'Urban area without official denomination'}
                    </h3>

                    <div className="selected-dossier__cve">
                      <span>Geostatistical Key:</span>
                      <strong>{selectedCvegeo}</strong>
                      {selectedReferenceArea?.coveragePct && (
                        <span className="coverage-pill">
                          {selectedReferenceArea.coveragePct}% coverage
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="selected-dossier__close"
                    title="Clear selection and reset to citywide view"
                    onClick={() => setSelectedCvegeo(null)}
                  >
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <div className="city-scope-banner">
                  <Sparkles size={15} className="text-cyan" />
                  <span>
                    Citywide overview · Click any AGEB polygon on the map to inspect
                  </span>
                </div>
              )}
            </div>

            {/* Scrollable Sidebar Analytics Content */}
            <div className="sidebar-scrollable-content">
              {/* Executive AI Urban Story */}
              <UrbanInsightStory
                selectedCvegeo={selectedCvegeo}
                referenceArea={selectedReferenceArea}
              />

              {/* Tabbed Analytics Panel */}
              <AnalyticsPanel
                selectedCvegeo={selectedCvegeo}
                onSelectAgeb={(cvegeo) => {
                  setSelectedCvegeo(cvegeo);
                }}
              />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
