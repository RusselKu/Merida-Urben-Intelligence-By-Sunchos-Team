-- Jonathan: read-only warehouse QA; requires 01_schema.sql and 03_views.sql.
-- Execute with visibility of all rows. RLS can hide data and affect counts.
-- Preserve results together with load date and query user.
-- An empty result means this check found no exceptions;
-- it does not certify source completeness. Never repair/delete data automatically.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

-- Q01. Coverage: empty tables mean pending sources, not observed absence.
SELECT 'dim_geografia' AS tabla, COUNT(*) AS filas FROM dim_geografia
UNION ALL SELECT 'dim_tiempo', COUNT(*) FROM dim_tiempo
UNION ALL SELECT 'dim_actividad_economica', COUNT(*) FROM dim_actividad_economica
UNION ALL SELECT 'fact_demografia', COUNT(*) FROM fact_demografia
UNION ALL SELECT 'fact_negocios', COUNT(*) FROM fact_negocios
UNION ALL SELECT 'fact_crimen', COUNT(*) FROM fact_crimen;

-- Q02. CVEGEO format and composition. AGEB components may contain letters.
SELECT cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb
FROM dim_geografia
WHERE cvegeo !~ '^31050[0-9]{4}[0-9A-Z]{4}$'
   OR cve_ent <> '31' OR cve_mun <> '050'
   OR cvegeo <> cve_ent || cve_mun || cve_loc || cve_ageb;

-- Q03. Census/geography coverage in both directions.
SELECT 'geografia_sin_demografia' AS control, g.cvegeo
FROM dim_geografia g LEFT JOIN fact_demografia d USING (cvegeo)
WHERE d.cvegeo IS NULL
UNION ALL
SELECT 'demografia_sin_geografia', d.cvegeo
FROM fact_demografia d LEFT JOIN dim_geografia g USING (cvegeo)
WHERE g.cvegeo IS NULL;

-- Q04. Referential integrity for all FKs. Expected count: zero per check.
SELECT 'negocio_geografia' AS control, COUNT(*) AS huerfanos
FROM fact_negocios f LEFT JOIN dim_geografia g ON g.cvegeo = f.cvegeo
WHERE g.cvegeo IS NULL
UNION ALL
SELECT 'negocio_scian', COUNT(*)
FROM fact_negocios f LEFT JOIN dim_actividad_economica a ON a.scian_id = f.scian_id
WHERE a.scian_id IS NULL
UNION ALL
SELECT 'negocio_tiempo', COUNT(*)
FROM fact_negocios f LEFT JOIN dim_tiempo t ON t.tiempo_id = f.tiempo_id
WHERE f.tiempo_id IS NOT NULL AND t.tiempo_id IS NULL
UNION ALL
SELECT 'crimen_geografia', COUNT(*)
FROM fact_crimen f LEFT JOIN dim_geografia g ON g.cvegeo = f.cvegeo
WHERE g.cvegeo IS NULL
UNION ALL
SELECT 'crimen_tiempo', COUNT(*)
FROM fact_crimen f LEFT JOIN dim_tiempo t ON t.tiempo_id = f.tiempo_id
WHERE f.tiempo_id IS NOT NULL AND t.tiempo_id IS NULL;

-- Q05. Demographic grain and negative counts. FK/UQ constraints do not check signs.
SELECT cvegeo, COUNT(*) AS filas FROM fact_demografia
GROUP BY cvegeo HAVING COUNT(*) > 1;

SELECT cvegeo, poblacion_total, poblacion_0_14, poblacion_15_64,
       poblacion_65_mas, poblacion_pea, poblacion_pnea
FROM fact_demografia
WHERE LEAST(poblacion_total, poblacion_masculina, poblacion_femenina,
            poblacion_0_14, poblacion_15_64, poblacion_65_mas,
            poblacion_pea, poblacion_pnea, total_viviendas) < 0;

-- Q06. Demographic coherence: compare differences and suppression with the source.
-- Differences do not authorize replacement; unspecified age may be present.
SELECT cvegeo, poblacion_total,
       poblacion_total::BIGINT - poblacion_masculina - poblacion_femenina AS diferencia_sexo,
       poblacion_total::BIGINT - poblacion_0_14 - poblacion_15_64 - poblacion_65_mas AS diferencia_edad,
       poblacion_pea::BIGINT + poblacion_pnea AS base_actividad
FROM fact_demografia
WHERE poblacion_total::BIGINT <> poblacion_masculina::BIGINT + poblacion_femenina
   OR poblacion_total::BIGINT <> poblacion_0_14::BIGINT + poblacion_15_64 + poblacion_65_mas
   OR poblacion_pea::BIGINT + poblacion_pnea > poblacion_total;

-- Regression check for the stale artifact pattern; inspect after refresh/load.
SELECT COUNT(*) AS filas, SUM(poblacion_total::BIGINT) AS poblacion_total,
       COUNT(*) FILTER (WHERE poblacion_total > 0 AND poblacion_0_14 = poblacion_total
                         AND poblacion_15_64 = 0 AND poblacion_65_mas = 0) AS patron_edad_sospechoso,
       COUNT(*) FILTER (WHERE poblacion_pea > 0 AND poblacion_pnea = 0) AS pea_derivada_100,
       COUNT(*) FILTER (WHERE poblacion_total = 0) AS sin_poblacion,
       COUNT(*) FILTER (WHERE poblacion_total < 100) AS poblacion_menor_100_incluye_ceros
FROM fact_demografia;

-- Q07. Areas and geometry required for analysis; geom_6372 is optional
-- in the DDL and the direct loader does not populate it. Report separately.
SELECT cvegeo, area_km2, ST_SRID(geom_4326) AS srid,
       ST_GeometryType(geom_4326) AS tipo, ST_IsValidReason(geom_4326) AS validez
FROM dim_geografia
WHERE area_km2 <= 0 OR geom_4326 IS NULL OR ST_IsEmpty(geom_4326)
   OR NOT ST_IsValid(geom_4326) OR ST_SRID(geom_4326) <> 4326
   OR ST_GeometryType(geom_4326) <> 'ST_MultiPolygon';

SELECT COUNT(*) FILTER (WHERE geom_6372 IS NULL) AS sin_geometria_metrica,
       COUNT(*) FILTER (WHERE geom_6372 IS NOT NULL AND
           (ST_SRID(geom_6372) <> 6372 OR NOT ST_IsValid(geom_6372)
            OR ST_IsEmpty(geom_6372))) AS geometria_metrica_incorrecta
FROM dim_geografia;

-- Compare stored area with projected calculation, allowing rounding tolerance.
WITH areas AS (
    SELECT cvegeo, area_km2,
           CASE WHEN geom_4326 IS NOT NULL AND ST_IsValid(geom_4326)
                     AND NOT ST_IsEmpty(geom_4326) AND ST_SRID(geom_4326) = 4326
                THEN ST_Area(ST_Transform(geom_4326, 6372)) / 1000000.0
           END AS area_calculada_km2
    FROM dim_geografia
)
SELECT * FROM areas
WHERE ABS(area_km2 - area_calculada_km2) > 0.0001;

-- Q08. Point location and AGEB membership. Also inspect null points.
-- CASE avoids predicates on invalid geometry; ST_Covers includes boundaries.
WITH puntos AS (
    SELECT 'negocio' AS fuente, fact_negocio_id AS id, cvegeo, geom_punto FROM fact_negocios
    UNION ALL
    SELECT 'crimen', fact_crimen_id, cvegeo, geom_punto FROM fact_crimen
), revisiones AS (
    SELECT p.fuente, p.id, p.cvegeo,
           CASE
               WHEN p.geom_punto IS NULL THEN 'punto_nulo'
               WHEN ST_IsEmpty(p.geom_punto) OR NOT ST_IsValid(p.geom_punto) THEN 'punto_invalido'
               WHEN ST_SRID(p.geom_punto) <> 4326 THEN 'srid_incorrecto'
               WHEN ST_X(p.geom_punto) NOT BETWEEN -180 AND 180
                 OR ST_Y(p.geom_punto) NOT BETWEEN -90 AND 90 THEN 'coordenadas_fuera_de_rango'
               WHEN g.geom_4326 IS NULL OR ST_IsEmpty(g.geom_4326)
                 OR NOT ST_IsValid(g.geom_4326) THEN 'ageb_sin_geometria_valida'
               WHEN NOT ST_Covers(g.geom_4326, p.geom_punto) THEN 'fuera_de_ageb_asignada'
           END AS problema
    FROM puntos p LEFT JOIN dim_geografia g USING (cvegeo)
)
SELECT fuente, problema, COUNT(*) AS filas FROM revisiones
WHERE problema IS NOT NULL GROUP BY fuente, problema ORDER BY fuente, problema;

-- Q09. Duplicate candidates. Identical name/activity/point is NOT a DENUE ID.
-- Check the source before concluding duplication; do not delete based on this query.
SELECT cvegeo, scian_id, nombre_establecimiento, estrato_personal,
       ENCODE(ST_AsEWKB(geom_punto), 'hex') AS punto_ewkb, COUNT(*) AS coincidencias
FROM fact_negocios
GROUP BY cvegeo, scian_id, nombre_establecimiento, estrato_personal,
         ENCODE(ST_AsEWKB(geom_punto), 'hex')
HAVING COUNT(*) > 1
ORDER BY coincidencias DESC LIMIT 100;

-- Q10. Calendar and SCIAN: internal consistency, not official catalog validation.
SELECT tiempo_id, fecha FROM dim_tiempo
WHERE anio <> EXTRACT(YEAR FROM fecha)::INT
   OR mes <> EXTRACT(MONTH FROM fecha)::INT
   OR dia <> EXTRACT(DAY FROM fecha)::INT
   OR trimestre <> EXTRACT(QUARTER FROM fecha)::INT
   OR es_fin_de_semana <> (EXTRACT(ISODOW FROM fecha) IN (6, 7));

SELECT scian_id, codigo_actividad, sector_codigo, categoria_macro
FROM dim_actividad_economica
WHERE scian_id <> codigo_actividad OR sector_codigo <> LEFT(codigo_actividad, 2)
   OR categoria_macro NOT IN ('Comercio', 'Servicios', 'Industria', 'Otro');

-- Q11. View grain and count reconciliation with source tables.
-- Compare under the same permissions and within this transaction.
SELECT (SELECT COUNT(*) FROM dim_geografia) AS agebs_dimension,
       COUNT(*) AS filas_vista, COUNT(DISTINCT cvegeo) AS claves_vista,
       COALESCE(SUM(poblacion_total::BIGINT), 0) AS poblacion_vista,
       (SELECT COALESCE(SUM(poblacion_total::BIGINT), 0) FROM fact_demografia) AS poblacion_tabla,
       COALESCE(SUM(total_negocios), 0) AS negocios_vista,
       (SELECT COUNT(*) FROM fact_negocios) AS negocios_tabla,
       COALESCE(SUM(total_delitos), 0) AS delitos_vista,
       (SELECT COUNT(*) FROM fact_crimen) AS delitos_tabla
FROM v_kpis_territoriales;

-- Q12. Rates and denominators. NULL is expected for a zero denominator in SQL.
SELECT v.cvegeo, v.tasa_pea_porcentaje, v.negocios_por_mil_hab,
       v.tasa_delictiva_por_mil_hab, v.ratio_delito_por_negocio
FROM v_kpis_territoriales v
LEFT JOIN fact_demografia d USING (cvegeo)
WHERE v.tasa_pea_porcentaje NOT BETWEEN 0 AND 100
   OR (COALESCE(d.poblacion_pea::BIGINT + d.poblacion_pnea, 0) = 0
       AND v.tasa_pea_porcentaje IS NOT NULL)
   OR (v.poblacion_total = 0 AND
       (v.negocios_por_mil_hab IS NOT NULL OR v.tasa_delictiva_por_mil_hab IS NOT NULL))
   OR (v.total_negocios = 0 AND v.ratio_delito_por_negocio IS NOT NULL);

COMMIT;
-- If a query fails and aborts the transaction, execute ROLLBACK.
