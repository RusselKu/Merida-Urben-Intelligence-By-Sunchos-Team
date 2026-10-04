-- =============================================================================
-- MERIDA URBAN INTELLIGENCE - DATA WAREHOUSE SCHEMA (PostgreSQL / PostGIS)
-- =============================================================================

-- 1. Enable PostGIS Spatial Extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Dimension Table: Geography (Urban AGEB Polygons of Mérida)
CREATE TABLE IF NOT EXISTS dim_geografia (
    cvegeo VARCHAR(20) PRIMARY KEY,
    cve_ent VARCHAR(2) NOT NULL DEFAULT '31',
    cve_mun VARCHAR(3) NOT NULL DEFAULT '050',
    cve_loc VARCHAR(4) NOT NULL,
    cve_ageb VARCHAR(4) NOT NULL,
    nom_asentamiento VARCHAR(255),
    tipo_asentamiento VARCHAR(50),
    area_km2 NUMERIC(10, 4) NOT NULL,
    geom_4326 GEOMETRY(MultiPolygon, 4326),
    geom_6372 GEOMETRY(MultiPolygon, 6372)
);

CREATE INDEX IF NOT EXISTS idx_dim_geografia_geom4326 ON dim_geografia USING GIST(geom_4326);
CREATE INDEX IF NOT EXISTS idx_dim_geografia_geom6372 ON dim_geografia USING GIST(geom_6372);

-- 3. Dimension Table: Date / Time
CREATE TABLE IF NOT EXISTS dim_tiempo (
    tiempo_id SERIAL PRIMARY KEY,
    fecha DATE UNIQUE NOT NULL,
    anio INT NOT NULL,
    mes INT NOT NULL,
    mes_nombre VARCHAR(20) NOT NULL,
    dia INT NOT NULL,
    dia_semana VARCHAR(20) NOT NULL,
    es_fin_de_semana BOOLEAN NOT NULL,
    trimestre INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dim_tiempo_fecha ON dim_tiempo(fecha);

-- 4. Dimension Table: Economic Activity (SCIAN Taxonomy)
CREATE TABLE IF NOT EXISTS dim_actividad_economica (
    scian_id VARCHAR(10) PRIMARY KEY,
    codigo_actividad VARCHAR(10) NOT NULL,
    sector_codigo VARCHAR(4) NOT NULL,
    sector_nombre VARCHAR(255) NOT NULL,
    subsector_nombre VARCHAR(255),
    categoria_macro VARCHAR(50) NOT NULL -- 'Comercio', 'Servicios', 'Industria', 'Otro'
);

-- 5. Fact Table: Demographics (INEGI Population & Housing Census)
CREATE TABLE IF NOT EXISTS fact_demografia (
    fact_demografia_id SERIAL PRIMARY KEY,
    cvegeo VARCHAR(20) NOT NULL REFERENCES dim_geografia(cvegeo) ON DELETE CASCADE,
    poblacion_total INT NOT NULL DEFAULT 0,
    poblacion_masculina INT NOT NULL DEFAULT 0,
    poblacion_femenina INT NOT NULL DEFAULT 0,
    poblacion_0_14 INT NOT NULL DEFAULT 0,
    poblacion_15_64 INT NOT NULL DEFAULT 0,
    poblacion_65_mas INT NOT NULL DEFAULT 0,
    poblacion_pea INT NOT NULL DEFAULT 0, -- Economically Active Population
    poblacion_pnea INT NOT NULL DEFAULT 0, -- Non-Active Population
    total_viviendas INT NOT NULL DEFAULT 0,
    CONSTRAINT uk_fact_demografia_cvegeo UNIQUE (cvegeo)
);

CREATE INDEX IF NOT EXISTS idx_fact_demografia_cvegeo ON fact_demografia(cvegeo);

-- 6. Fact Table: Business Establishments (INEGI DENUE)
CREATE TABLE IF NOT EXISTS fact_negocios (
    fact_negocio_id SERIAL PRIMARY KEY,
    cvegeo VARCHAR(20) NOT NULL REFERENCES dim_geografia(cvegeo) ON DELETE CASCADE,
    scian_id VARCHAR(10) NOT NULL REFERENCES dim_actividad_economica(scian_id),
    tiempo_id INT REFERENCES dim_tiempo(tiempo_id),
    nombre_establecimiento VARCHAR(255),
    estrato_personal VARCHAR(50),
    geom_punto GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_fact_negocios_cvegeo ON fact_negocios(cvegeo);
CREATE INDEX IF NOT EXISTS idx_fact_negocios_scian ON fact_negocios(scian_id);
CREATE INDEX IF NOT EXISTS idx_fact_negocios_geom ON fact_negocios USING GIST(geom_punto);

-- 7. Fact Table: Public Safety & Crime Incidents
CREATE TABLE IF NOT EXISTS fact_crimen (
    fact_crimen_id SERIAL PRIMARY KEY,
    cvegeo VARCHAR(20) NOT NULL REFERENCES dim_geografia(cvegeo) ON DELETE CASCADE,
    tiempo_id INT REFERENCES dim_tiempo(tiempo_id),
    categoria_delito VARCHAR(100) NOT NULL,
    tipo_delito VARCHAR(150) NOT NULL,
    periodo_dia VARCHAR(50), -- 'Morning', 'Afternoon', 'Evening', 'Night'
    geom_punto GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_fact_crimen_cvegeo ON fact_crimen(cvegeo);
CREATE INDEX IF NOT EXISTS idx_fact_crimen_categoria ON fact_crimen(categoria_delito);
CREATE INDEX IF NOT EXISTS idx_fact_crimen_geom ON fact_crimen USING GIST(geom_punto);
CREATE INDEX IF NOT EXISTS idx_fact_crimen_tiempo_id ON fact_crimen(tiempo_id);
CREATE INDEX IF NOT EXISTS idx_fact_negocios_tiempo_id ON fact_negocios(tiempo_id);

-- =============================================================================
-- 8. Row Level Security (RLS) & Access Policies
-- =============================================================================
ALTER TABLE dim_geografia ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_tiempo ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_actividad_economica ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_demografia ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_negocios ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_crimen ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read on dim_geografia" ON dim_geografia FOR SELECT TO anon, authenticated, public USING (true);
CREATE POLICY "Allow public read on dim_tiempo" ON dim_tiempo FOR SELECT TO anon, authenticated, public USING (true);
CREATE POLICY "Allow public read on dim_actividad_economica" ON dim_actividad_economica FOR SELECT TO anon, authenticated, public USING (true);
CREATE POLICY "Allow public read on fact_demografia" ON fact_demografia FOR SELECT TO anon, authenticated, public USING (true);
CREATE POLICY "Allow public read on fact_negocios" ON fact_negocios FOR SELECT TO anon, authenticated, public USING (true);
CREATE POLICY "Allow public read on fact_crimen" ON fact_crimen FOR SELECT TO anon, authenticated, public USING (true);

