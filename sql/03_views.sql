-- =============================================================================
-- MERIDA URBAN INTELLIGENCE - ANALYTICAL VIEWS FOR REQUIRED KPIS
-- =============================================================================

-- Consolidated Territorial KPI View by AGEB
CREATE OR REPLACE VIEW v_kpis_territoriales AS
WITH metricas_negocios AS (
    SELECT 
        fn.cvegeo,
        COUNT(fn.fact_negocio_id) AS total_negocios,
        COUNT(CASE WHEN dae.categoria_macro = 'Comercio' THEN 1 END) AS total_comercios,
        COUNT(CASE WHEN dae.categoria_macro = 'Servicios' THEN 1 END) AS total_servicios
    FROM fact_negocios fn
    LEFT JOIN dim_actividad_economica dae ON fn.scian_id = dae.scian_id
    GROUP BY fn.cvegeo
),
actividad_dominante AS (
    SELECT DISTINCT ON (fn.cvegeo)
        fn.cvegeo,
        dae.sector_nombre AS sector_dominante,
        COUNT(*) AS conteo_sector
    FROM fact_negocios fn
    JOIN dim_actividad_economica dae ON fn.scian_id = dae.scian_id
    GROUP BY fn.cvegeo, dae.sector_nombre
    ORDER BY fn.cvegeo, COUNT(*) DESC
),
metricas_crimen AS (
    SELECT 
        fc.cvegeo,
        COUNT(fc.fact_crimen_id) AS total_delitos
    FROM fact_crimen fc
    GROUP BY fc.cvegeo
)
SELECT 
    g.cvegeo,
    g.nom_asentamiento,
    g.area_km2,
    
    -- Demographic KPIs
    COALESCE(fd.poblacion_total, 0) AS poblacion_total,
    ROUND(COALESCE(fd.poblacion_total, 0) / NULLIF(g.area_km2, 0), 2) AS densidad_poblacion_km2,
    ROUND((COALESCE(fd.poblacion_pea, 0)::NUMERIC / NULLIF((fd.poblacion_total - fd.poblacion_0_14), 0)) * 100, 2) AS tasa_pea_porcentaje,
    COALESCE(fd.poblacion_0_14, 0) AS poblacion_0_14,
    COALESCE(fd.poblacion_15_64, 0) AS poblacion_15_64,
    COALESCE(fd.poblacion_65_mas, 0) AS poblacion_65_mas,
    
    -- Economic KPIs
    COALESCE(mn.total_negocios, 0) AS total_negocios,
    ROUND(COALESCE(mn.total_negocios, 0) / NULLIF(g.area_km2, 0), 2) AS densidad_negocios_km2,
    ROUND((COALESCE(mn.total_negocios, 0)::NUMERIC / NULLIF(fd.poblacion_total, 0)) * 1000, 2) AS negocios_por_mil_hab,
    ROUND(COALESCE(mn.total_comercios, 0) / NULLIF(g.area_km2, 0), 2) AS densidad_comercio_km2,
    ROUND(COALESCE(mn.total_servicios, 0) / NULLIF(g.area_km2, 0), 2) AS densidad_servicios_km2,
    COALESCE(ad.sector_dominante, 'No recorded activity') AS actividad_economica_dominante,
    
    -- Public Safety KPIs
    COALESCE(mc.total_delitos, 0) AS total_delitos,
    ROUND((COALESCE(mc.total_delitos, 0)::NUMERIC / NULLIF(fd.poblacion_total, 0)) * 1000, 2) AS tasa_delictiva_por_mil_hab,
    ROUND(COALESCE(mc.total_delitos, 0)::NUMERIC / NULLIF(mn.total_negocios, 0), 3) AS ratio_delito_por_negocio,
    
    -- Spatial Geometry
    g.geom_4326

FROM dim_geografia g
LEFT JOIN fact_demografia fd ON g.cvegeo = fd.cvegeo
LEFT JOIN metricas_negocios mn ON g.cvegeo = mn.cvegeo
LEFT JOIN actividad_dominante ad ON g.cvegeo = ad.cvegeo
LEFT JOIN metricas_crimen mc ON g.cvegeo = mc.cvegeo;
