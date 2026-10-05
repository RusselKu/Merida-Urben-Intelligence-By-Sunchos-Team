-- Jonathan: QA del warehouse. Solo lectura; requiere 01_schema.sql y 03_views.sql.
-- Ejecutar con acceso a todas las filas. RLS puede ocultar datos y alterar conteos.
-- Guardar los resultados junto con la fecha de carga y el usuario utilizado.
-- Una consulta sin filas significa que ese control no detecto excepciones;
-- no certifica fuentes completas. Nunca corregir o borrar datos automaticamente.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

-- Q01. Cobertura: tablas vacias son fuentes pendientes, no ausencia observada.
SELECT 'dim_geografia' AS tabla, COUNT(*) AS filas FROM dim_geografia
UNION ALL SELECT 'dim_tiempo', COUNT(*) FROM dim_tiempo
UNION ALL SELECT 'dim_actividad_economica', COUNT(*) FROM dim_actividad_economica
UNION ALL SELECT 'fact_demografia', COUNT(*) FROM fact_demografia
UNION ALL SELECT 'fact_negocios', COUNT(*) FROM fact_negocios
UNION ALL SELECT 'fact_crimen', COUNT(*) FROM fact_crimen;

-- Q02. Formato y composicion de CVEGEO. Los componentes AGEB pueden incluir letras.
SELECT cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb
FROM dim_geografia
WHERE cvegeo !~ '^31050[0-9]{4}[0-9A-Z]{4}$'
   OR cve_ent <> '31' OR cve_mun <> '050'
   OR cvegeo <> cve_ent || cve_mun || cve_loc || cve_ageb;

-- Q03. Cobertura geografica del censo en ambas direcciones.
SELECT 'geografia_sin_demografia' AS control, g.cvegeo
FROM dim_geografia g LEFT JOIN fact_demografia d USING (cvegeo)
WHERE d.cvegeo IS NULL
UNION ALL
SELECT 'demografia_sin_geografia', d.cvegeo
FROM fact_demografia d LEFT JOIN dim_geografia g USING (cvegeo)
WHERE g.cvegeo IS NULL;

-- Q04. Integridad referencial de todas las FK. Se espera cero por control.
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

-- Q05. Grano demografico y conteos negativos. Las FK/UQ no controlan signos.
SELECT cvegeo, COUNT(*) AS filas FROM fact_demografia
GROUP BY cvegeo HAVING COUNT(*) > 1;

SELECT cvegeo, poblacion_total, poblacion_0_14, poblacion_15_64,
       poblacion_65_mas, poblacion_pea, poblacion_pnea
FROM fact_demografia
WHERE LEAST(poblacion_total, poblacion_masculina, poblacion_femenina,
            poblacion_0_14, poblacion_15_64, poblacion_65_mas,
            poblacion_pea, poblacion_pnea, total_viviendas) < 0;

-- Q06. Coherencia demografica: revisar diferencias y supresiones con la fuente.
-- Las diferencias no autorizan reemplazar datos; puede haber edad no especificada.
SELECT cvegeo, poblacion_total,
       poblacion_total::BIGINT - poblacion_masculina - poblacion_femenina AS diferencia_sexo,
       poblacion_total::BIGINT - poblacion_0_14 - poblacion_15_64 - poblacion_65_mas AS diferencia_edad,
       poblacion_pea::BIGINT + poblacion_pnea AS base_actividad
FROM fact_demografia
WHERE poblacion_total::BIGINT <> poblacion_masculina::BIGINT + poblacion_femenina
   OR poblacion_total::BIGINT <> poblacion_0_14::BIGINT + poblacion_15_64 + poblacion_65_mas
   OR poblacion_pea::BIGINT + poblacion_pnea > poblacion_total;

-- Patron del archivo local desactualizado; debe revisarse tras regenerar/cargar.
SELECT COUNT(*) AS filas, SUM(poblacion_total::BIGINT) AS poblacion_total,
       COUNT(*) FILTER (WHERE poblacion_total > 0 AND poblacion_0_14 = poblacion_total
                         AND poblacion_15_64 = 0 AND poblacion_65_mas = 0) AS patron_edad_sospechoso,
       COUNT(*) FILTER (WHERE poblacion_pea > 0 AND poblacion_pnea = 0) AS pea_derivada_100,
       COUNT(*) FILTER (WHERE poblacion_total = 0) AS sin_poblacion,
       COUNT(*) FILTER (WHERE poblacion_total < 100) AS poblacion_menor_100_incluye_ceros
FROM fact_demografia;

-- Q07. Superficies y geometria obligatorias para analisis; geom_6372 es opcional
-- en el DDL y el cargador actual no la llena. Reportar ese faltante por separado.
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

-- Comparar el area guardada con el calculo proyectado; tolerancia de redondeo.
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

-- Q08. Ubicacion de puntos y pertenencia a su AGEB. Revisar tambien puntos nulos.
-- CASE evita predicados sobre geometria invalida; ST_Covers admite el borde.
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

-- Q09. Candidatos a duplicado. Nombre/actividad/punto iguales NO son un ID DENUE.
-- Revisar contra la fuente antes de concluir duplicacion; no eliminar por esta consulta.
SELECT cvegeo, scian_id, nombre_establecimiento, estrato_personal,
       ENCODE(ST_AsEWKB(geom_punto), 'hex') AS punto_ewkb, COUNT(*) AS coincidencias
FROM fact_negocios
GROUP BY cvegeo, scian_id, nombre_establecimiento, estrato_personal,
         ENCODE(ST_AsEWKB(geom_punto), 'hex')
HAVING COUNT(*) > 1
ORDER BY coincidencias DESC LIMIT 100;

-- Q10. Calendario y SCIAN: coherencia interna, no validacion del catalogo oficial.
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

-- Q11. Grano y reconciliacion de conteos de la vista con las tablas de origen.
-- Comparar bajo los mismos permisos y en esta misma transaccion.
SELECT (SELECT COUNT(*) FROM dim_geografia) AS agebs_dimension,
       COUNT(*) AS filas_vista, COUNT(DISTINCT cvegeo) AS claves_vista,
       COALESCE(SUM(poblacion_total::BIGINT), 0) AS poblacion_vista,
       (SELECT COALESCE(SUM(poblacion_total::BIGINT), 0) FROM fact_demografia) AS poblacion_tabla,
       COALESCE(SUM(total_negocios), 0) AS negocios_vista,
       (SELECT COUNT(*) FROM fact_negocios) AS negocios_tabla,
       COALESCE(SUM(total_delitos), 0) AS delitos_vista,
       (SELECT COUNT(*) FROM fact_crimen) AS delitos_tabla
FROM v_kpis_territoriales;

-- Q12. Tasas y denominadores. Un NULL con base cero es esperado en SQL.
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
-- Si una consulta falla y deja la transaccion abortada, ejecutar ROLLBACK.
