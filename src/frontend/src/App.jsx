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
  ChevronRight,
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
  const [activeResult, setActiveResult] = useState(0);
  const [mobileTab, setMobileTab] = useState('map');
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  const searchRef = useRef(null);
  const mobileSearchInputRef = useRef(null);
  const scrollRef = useRef(null);
  const dossierRef = useRef(null);

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
    setActiveResult(0);
  }, [searchQuery]);

  // A new selection replaces everything in the panel, so the panel returns to
  // the top — otherwise the dossier appears above content from the previous AGEB.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [selectedCvegeo]);

  // ...and the keyboard follows the selection into the panel, which is the only
  // route to an AGEB that does not require pointing at a polygon.
  useEffect(() => {
    if (selectedCvegeo) dossierRef.current?.focus();
  }, [selectedCvegeo]);

  // Focus mobile input when mobile search bar opens
  useEffect(() => {
    if (mobileSearchOpen) {
      setTimeout(() => mobileSearchInputRef.current?.focus(), 60);
    }
  }, [mobileSearchOpen]);

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
    setMobileSearchOpen(false);
    if (!sidebarOpen) setSidebarOpen(true);
    if (typeof window !== 'undefined' && window.innerWidth <= 860) {
      setMobileTab('map');
    }
  };

  const handleSearchKeyDown = (event) => {
    if (!searchOpen || !searchResults.length) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveResult((i) => (i + 1) % searchResults.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveResult((i) => (i - 1 + searchResults.length) % searchResults.length);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const match = searchResults[activeResult];
      if (match) handleSelectSearchResult(match.cvegeo);
    } else if (event.key === 'Escape') {
      setSearchOpen(false);
    }
  };

  return (
    <div
      className={`app-shell ${sidebarOpen ? 'with-sidebar' : 'map-only'} mobile-view-${mobileTab}${
        mobileSearchOpen ? ' mobile-search-active' : ''
      }`}
    >
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
              </div>
              <p className="brand-subtitle">
                Geospatial Data Warehouse · INEGI Census 2020 & DENUE
              </p>
            </div>
          </div>
        </div>

        {/* Global Omni-Search */}
        <div
          className={`app-header__center${mobileSearchOpen ? ' mobile-expanded' : ''}`}
          ref={searchRef}
        >
          <div className="global-search-box">
            <Search size={16} className="search-icon" />
            <input
              ref={mobileSearchInputRef}
              type="text"
              placeholder="Search neighborhood, colonia, or AGEB (e.g. Centro, Caucel)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => {
                if (searchResults.length > 0) setSearchOpen(true);
              }}
              onKeyDown={handleSearchKeyDown}
              className="global-search-input"
              role="combobox"
              aria-expanded={searchOpen}
              aria-controls="search-results"
              aria-autocomplete="list"
              aria-activedescendant={
                searchOpen && searchResults[activeResult]
                  ? `search-result-${searchResults[activeResult].cvegeo}`
                  : undefined
              }
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
            {mobileSearchOpen && (
              <button
                type="button"
                className="mobile-search-close-btn"
                title="Close search"
                onClick={() => {
                  setMobileSearchOpen(false);
                  setSearchQuery('');
                  setSearchResults([]);
                  setSearchOpen(false);
                }}
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* Search Suggestions Dropdown */}
          {searchOpen && (
            <div className="search-dropdown glass-panel">
              <div className="search-dropdown__header">
                <span>Search results ({searchResults.length})</span>
              </div>
              <div className="search-dropdown__list" id="search-results" role="listbox">
                {searchResults.map((item, index) => (
                  <button
                    key={item.cvegeo}
                    id={`search-result-${item.cvegeo}`}
                    type="button"
                    role="option"
                    aria-selected={index === activeResult}
                    className={`search-item${index === activeResult ? ' is-active' : ''}`}
                    onMouseEnter={() => setActiveResult(index)}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
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

          {/* Mobile Search Button */}
          <button
            type="button"
            className="mobile-search-btn"
            title="Search neighborhood or AGEB"
            onClick={() => {
              setMobileSearchOpen(true);
              setSearchOpen(false);
            }}
          >
            <Search size={18} />
          </button>

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

          {/* Mobile Floating AGEB Quick Card (when on map and an AGEB is selected) */}
          {selectedCvegeo && (
            <div className="mobile-ageb-sheet glass-panel">
              <div className="mobile-ageb-sheet__header">
                <div className="mobile-ageb-sheet__badges">
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
                <button
                  type="button"
                  className="mobile-ageb-sheet__close"
                  title="Deselect"
                  onClick={() => setSelectedCvegeo(null)}
                >
                  <X size={15} />
                </button>
              </div>

              <div className="mobile-ageb-sheet__body">
                <h3 className="mobile-ageb-sheet__title">
                  {selectedReferenceArea?.name || 'Urban area without official denomination'}
                </h3>
                <div className="mobile-ageb-sheet__cve">
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
                className="mobile-ageb-sheet__cta"
                onClick={() => setMobileTab('analytics')}
              >
                <Activity size={15} />
                <span>View Full Analytics</span>
                <ChevronRight size={15} />
              </button>
            </div>
          )}
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
                <div
                  className="selected-dossier"
                  ref={dossierRef}
                  tabIndex={-1}
                  aria-live="polite"
                >
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

                  <div className="selected-dossier__actions">
                    <button
                      type="button"
                      className="mobile-view-map-btn"
                      title="View on Map"
                      onClick={() => setMobileTab('map')}
                    >
                      <MapPin size={13} />
                      <span>Map</span>
                    </button>
                    <button
                      type="button"
                      className="selected-dossier__close"
                      title="Clear selection and reset to citywide view"
                      onClick={() => setSelectedCvegeo(null)}
                    >
                      <X size={16} />
                    </button>
                  </div>
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
            <div className="sidebar-scrollable-content" ref={scrollRef}>
              {/* Derived urban briefing */}
              <UrbanInsightStory
                selectedCvegeo={selectedCvegeo}
                referenceArea={selectedReferenceArea}
              />

              {/* Tabbed Analytics Panel */}
              <AnalyticsPanel
                selectedCvegeo={selectedCvegeo}
                onSelectAgeb={(cvegeo) => {
                  setSelectedCvegeo(cvegeo);
                  if (typeof window !== 'undefined' && window.innerWidth <= 860) {
                    setMobileTab('map');
                  }
                }}
              />
            </div>
          </aside>
        )}
      </div>

      {/* Mobile Bottom Navigation Bar */}
      <nav className="mobile-bottom-nav glass-panel" aria-label="Mobile Navigation">
        <button
          type="button"
          className={`mobile-nav-btn ${mobileTab === 'map' ? 'is-active' : ''}`}
          onClick={() => setMobileTab('map')}
        >
          <MapPinned size={18} />
          <span>Map</span>
        </button>

        <button
          type="button"
          className={`mobile-nav-btn ${mobileTab === 'analytics' ? 'is-active' : ''}`}
          onClick={() => setMobileTab('analytics')}
        >
          <div className="mobile-nav-icon-wrap">
            <Activity size={18} />
            {selectedCvegeo && <span className="mobile-nav-badge-dot" />}
          </div>
          <span>Analytics</span>
        </button>
      </nav>
    </div>
  );
}
