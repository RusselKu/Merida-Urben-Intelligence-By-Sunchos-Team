# Diccionario de datos del warehouse

Responsable: Jonathan — QA, perfilado y documentación técnica. Fecha de revisión: 2026-10-04.

Este documento describe el esquema implementado en [01_schema.sql](../sql/01_schema.sql), las transformaciones de [transform.py](../src/etl/transform.py) y la vista de [03_views.sql](../sql/03_views.sql). Las correspondencias con las fuentes se obtuvieron del código del repositorio; falta cotejarlas con los archivos originales, que no están presentes en este clon. El número de registros observado en un archivo local no certifica el contenido de Supabase.

## Convenciones y unidad de análisis

- Una AGEB se identifica por `cvegeo`: entidad (2 caracteres) + municipio (3) + localidad (4) + AGEB (4). Se conserva como texto, incluidos ceros iniciales y letras de la AGEB. Para Mérida se espera el prefijo `31050` y 13 caracteres; el DDL admite hasta 20 y no impone ese formato.
- PK significa clave primaria; FK, clave foránea; UQ, restricción de unicidad. `SERIAL` es un entero generado por una secuencia.
- La columna «Nulo / default» describe lo que permite PostgreSQL. Las reglas de calidad propuestas no son necesariamente restricciones implementadas.
- Las coordenadas geográficas usan orden longitud, latitud y SRID 4326. Las superficies se calculan en EPSG:6372 y se expresan en km².
- El warehouse actual conserva una fila demográfica por AGEB, sin año censal; una recarga actualiza esa fila. Negocios y delitos tienen claves internas, pero no identificadores únicos de la fuente.
- Un cero puede ser una observación real, un default o una imputación del ETL. No demuestra por sí solo ausencia de población, negocios o delitos.

## 1. `dim_geografia`

Grano: una fila por AGEB urbana. Fuente: Marco Geoestadístico leído desde `31a.shp`. El ETL filtra entidad `31` y municipio `050`; no restringe a la localidad `0001`.

| Campo | Tipo SQL | Nulo / default | Significado, procedencia y regla de calidad |
| --- | --- | --- | --- |
| `cvegeo` | VARCHAR(20), PK | No | `CVEGEO`; identificador territorial. Validar composición, longitud y unicidad. Si no existe en la fuente, el código usa el índice del dataframe, lo cual requiere revisión. |
| `cve_ent` | VARCHAR(2) | No / `'31'` | `CVE_ENT`; entidad federativa. Se espera `31`. |
| `cve_mun` | VARCHAR(3) | No / `'050'` | `CVE_MUN`; municipio. Se espera `050`. |
| `cve_loc` | VARCHAR(4) | No | `CVE_LOC`; localidad. El código usa `0001` si falta el campo. |
| `cve_ageb` | VARCHAR(4) | No | `CVE_AGEB`; componente AGEB, alfanumérico. El código usa `0000` si falta. |
| `nom_asentamiento` | VARCHAR(255) | Sí | El ETL asigna `Mérida Urbana`; no es un nombre individual de colonia. |
| `tipo_asentamiento` | VARCHAR(50) | Sí | El ETL asigna `AGEB Urbana`. |
| `area_km2` | NUMERIC(10,4) | No | Área de la geometría proyectada a EPSG:6372, dividida entre 1,000,000 y redondeada a cuatro decimales. Debe ser positiva; el DDL no incluye `CHECK`. |
| `geom_4326` | GEOMETRY(MultiPolygon,4326) | Sí | Geometría reparada con `buffer(0)` y reproyectada a WGS84. Índice GiST. El cargador directo no convierte explícitamente Polygon a MultiPolygon. |
| `geom_6372` | GEOMETRY(MultiPolygon,6372) | Sí | Geometría métrica prevista; índice GiST. El cargador directo actual no la inserta. Su ausencia no significa que el área no se haya calculado en proyección métrica. |

## 2. `dim_tiempo`

Grano: una fila por fecha. Fuente prevista: fechas de observación de negocios e incidentes. No hay una carga de calendario implementada en el pipeline principal.

| Campo | Tipo SQL | Nulo / default | Significado y regla de calidad |
| --- | --- | --- | --- |
| `tiempo_id` | SERIAL, PK | No / secuencia | Clave interna de la fecha. |
| `fecha` | DATE, UQ | No | Fecha completa; única. |
| `anio` | INT | No | Año de `fecha`. |
| `mes` | INT | No | Mes de `fecha`, de 1 a 12. |
| `mes_nombre` | VARCHAR(20) | No | Nombre del mes; acordar idioma con el equipo. |
| `dia` | INT | No | Día del mes, coherente con `fecha`. |
| `dia_semana` | VARCHAR(20) | No | Nombre del día de la semana; el esquema no utiliza un código numérico. |
| `es_fin_de_semana` | BOOLEAN | No | Verdadero para sábado y domingo. |
| `trimestre` | INT | No | Trimestre, de 1 a 4, coherente con `mes`. |

Los rangos y la coherencia entre atributos son reglas de QA; el DDL solo exige no nulos y unicidad de la fecha.

## 3. `dim_actividad_economica`

Grano implementado: una fila por código de actividad de DENUE (clase SCIAN). Fuente: columnas `codigo_act` y `nombre_act` del CSV DENUE.

| Campo | Tipo SQL | Nulo / default | Significado, procedencia y regla de calidad |
| --- | --- | --- | --- |
| `scian_id` | VARCHAR(10), PK | No | Copia textual de `codigo_act`. El identificador representa una clase, aunque el nombre de la tabla sea genérico. |
| `codigo_actividad` | VARCHAR(10) | No | `codigo_act`; código de actividad. Debe coincidir con `scian_id` en la transformación actual. |
| `sector_codigo` | VARCHAR(4) | No | Primeros dos caracteres de `codigo_act`; no confundir con la clase completa. |
| `sector_nombre` | VARCHAR(255) | No | Copia de `nombre_act`: actualmente contiene el nombre de la clase, no necesariamente el nombre del sector de dos dígitos. |
| `subsector_nombre` | VARCHAR(255) | Sí | Campo previsto; no poblado por el cargador directo. |
| `categoria_macro` | VARCHAR(50) | No | Clasificación asignada por `map_scian_category()`; no existe un `CHECK` de categorías. |

Categorías implementadas: `Comercio` = 43, 46, 47; `Servicios` = 51, 52, 53, 54, 55, 56, 61, 62, 71, 72, 81; `Industria` = 11, 21, 22, 23, 31, 32, 33; `Otro` = resto. Son las reglas del código del proyecto, no una validación independiente del catálogo oficial. El cargador usa `ON CONFLICT DO NOTHING`, por lo que no actualiza descripciones existentes.

## 4. `fact_demografia`

Grano: una fila censal por AGEB. Fuente declarada: Censo 2020, registros con municipio `050`, `NOM_LOC = 'Total AGEB urbana'` y `MZA = 0`. El filtro de entidad no es explícito en esta función; el extractor busca un archivo de Yucatán.

| Campo | Tipo SQL | Nulo / default | Significado y columna de origen |
| --- | --- | --- | --- |
| `fact_demografia_id` | SERIAL, PK | No / secuencia | Identificador interno. |
| `cvegeo` | VARCHAR(20), FK, UQ | No | Concatenación de `ENTIDAD`, `MUN`, `LOC`, `AGEB`; referencia `dim_geografia.cvegeo`. Eliminación de geografía en cascada. |
| `poblacion_total` | INT | No / 0 | Personas; `POBTOT`. |
| `poblacion_masculina` | INT | No / 0 | Personas; `POBMAS`. |
| `poblacion_femenina` | INT | No / 0 | Personas; `POBFEM`. |
| `poblacion_0_14` | INT | No / 0 | Personas de 0 a 14 años; `POB0_14`. |
| `poblacion_15_64` | INT | No / 0 | Personas de 15 a 64 años; `POB15_64`. |
| `poblacion_65_mas` | INT | No / 0 | Personas de 65 años o más; `POB65_MAS`. |
| `poblacion_pea` | INT | No / 0 | Población económicamente activa de 12 años o más; `PEA`. |
| `poblacion_pnea` | INT | No / 0 | Población económicamente inactiva de 12 años o más; `PE_INAC`. |
| `total_viviendas` | INT | No / 0 | Viviendas; `VIVTOT`. No confundir con habitantes ni asumir que son viviendas habitadas. |

El código sustituye `*`, `N/D`, `N/A`, vacíos y valores no numéricos por cero; elimina filas repetidas por `cvegeo` conservando la primera. No preserva una bandera de supresión estadística. Todos los conteos deberían ser no negativos; revisar diferencias entre población total y sumas por sexo o edad con la fuente, sin asumir automáticamente que toda diferencia es un error. La tasa PEA usa `PEA / (PEA + PE_INAC) * 100`, cuya base es población con condición de actividad conocida.

## 5. `fact_negocios`

Grano previsto: un establecimiento por observación. El esquema actual no permite distinguir recargas del mismo establecimiento ni identifica la fecha de corte de DENUE. Fuente: DENUE; asignación de AGEB mediante unión espacial `within`.

| Campo | Tipo SQL | Nulo / default | Significado, procedencia y regla de calidad |
| --- | --- | --- | --- |
| `fact_negocio_id` | SERIAL, PK | No / secuencia | Clave interna; no es el `id` de DENUE. |
| `cvegeo` | VARCHAR(20), FK | No | AGEB asignada al punto; referencia geográfica, eliminación en cascada. |
| `scian_id` | VARCHAR(10), FK | No | `codigo_act`; referencia `dim_actividad_economica.scian_id`. |
| `tiempo_id` | INT, FK | Sí | Referencia `dim_tiempo.tiempo_id`; no poblada en la carga actual. |
| `nombre_establecimiento` | VARCHAR(255) | Sí | `nom_estab`; el cargador directo trunca a 255 caracteres. |
| `estrato_personal` | VARCHAR(50) | Sí | `per_ocu`; categoría de personal ocupado, no conteo numérico exacto. El cargador directo trunca a 50 caracteres. |
| `geom_punto` | GEOMETRY(Point,4326) | Sí | `longitud`, `latitud`; índice GiST. El ETL elimina coordenadas nulas y conserva puntos estrictamente dentro de una AGEB; excluye puntos en el borde o fuera de los polígonos. |

No hay UQ sobre el establecimiento de origen ni control de recargas. Coincidencias de nombre, actividad y punto son candidatos a duplicación, no prueba suficiente para eliminar registros.

## 6. `fact_crimen`

Grano previsto: un incidente georreferenciado. La fuente, periodo, catálogo y columnas originales están pendientes de definir; existe un lector CSV, pero el pipeline principal no transforma ni carga delitos.

| Campo | Tipo SQL | Nulo / default | Significado y estado de implementación |
| --- | --- | --- | --- |
| `fact_crimen_id` | SERIAL, PK | No / secuencia | Clave interna; no preserva un identificador de incidente de la fuente. |
| `cvegeo` | VARCHAR(20), FK | No | AGEB asignada; referencia geográfica, eliminación en cascada. |
| `tiempo_id` | INT, FK | Sí | Referencia a la fecha del incidente; falta carga. |
| `categoria_delito` | VARCHAR(100) | No | Agrupación del delito; catálogo por acordar. |
| `tipo_delito` | VARCHAR(150) | No | Tipo específico del delito; catálogo por acordar. |
| `periodo_dia` | VARCHAR(50) | Sí | Franja horaria. El comentario SQL sugiere Morning, Afternoon, Evening, Night, pero no define horarios ni impone valores. |
| `geom_punto` | GEOMETRY(Point,4326) | Sí | Ubicación del incidente; índice GiST. Falta validar origen, CRS y método de asignación territorial. |

## 7. Vista `v_kpis_territoriales`

Grano: una fila por AGEB de `dim_geografia`. Une demografía y agregados de negocios y delitos. La definición completa está en [03_views.sql](../sql/03_views.sql); las fórmulas analíticas se coordinan con [kpi_formulas.md](kpi_formulas.md).

| Campo | Tipo resultante | Unidad / derivación implementada |
| --- | --- | --- |
| `cvegeo` | VARCHAR(20) | Identificador territorial. |
| `nom_asentamiento` | VARCHAR(255) | Nombre de la dimensión geográfica. |
| `area_km2` | NUMERIC(10,4) | km² de la dimensión geográfica. |
| `poblacion_total` | INT | Habitantes; cero si no existe fila demográfica. |
| `densidad_poblacion_km2` | NUMERIC | Habitantes / km²; dos decimales. |
| `tasa_pea_porcentaje` | NUMERIC | `100 * PEA / (PEA + PNEA)`; dos decimales. |
| `poblacion_0_14` | INT | Habitantes; cero si falta demografía. |
| `poblacion_15_64` | INT | Habitantes; cero si falta demografía. |
| `poblacion_65_mas` | INT | Habitantes; cero si falta demografía. |
| `total_negocios` | BIGINT | Conteo de filas de establecimientos; cero si no hay filas asociadas. |
| `densidad_negocios_km2` | NUMERIC | Establecimientos / km²; dos decimales. |
| `negocios_por_mil_hab` | NUMERIC | `1000 * negocios / población`; dos decimales. |
| `densidad_comercio_km2` | NUMERIC | Filas clasificadas Comercio / km²; dos decimales. |
| `densidad_servicios_km2` | NUMERIC | Filas clasificadas Servicios / km²; dos decimales. |
| `actividad_economica_dominante` | VARCHAR o texto | Moda de `sector_nombre`, actualmente nombre de clase; sin actividad devuelve `No recorded activity`. Los empates no tienen desempate explícito. |
| `total_delitos` | BIGINT | Conteo de filas de incidentes; cero si no hay filas asociadas. |
| `tasa_delictiva_por_mil_hab` | NUMERIC | `1000 * delitos / población`; dos decimales. |
| `ratio_delito_por_negocio` | NUMERIC | Delitos / establecimiento; tres decimales. Multiplicar por 100 solo cuando se reporte por cien establecimientos. |
| `geom_4326` | GEOMETRY(MultiPolygon,4326) | Geometría de la dimensión geográfica. |

`NULLIF` devuelve tasas nulas cuando el denominador es cero; los agregados ausentes se convierten en cero mediante `COALESCE`. Estos ceros no acreditan que se hayan cargado todas las fuentes. La vista usa `security_invoker = true`; sus resultados dependen de los permisos del usuario que consulta y de RLS.

## 8. Publicación por la API y controles pendientes

La API intenta leer esta vista y, ante ausencia o fallo de la base, usa `outputs/maps/merida_agebs_demographics.geojson`. El fallback añade ceros para negocios y delitos cuando esos campos no existen; no equivale a observar cero incidentes o establecimientos. También rellena ciertas tasas indefinidas con cero, a diferencia del SQL.

Controles previos a publicar resultados: comprobar cobertura y fecha de cada fuente, unicidad de AGEB, integridad referencial, validez/SRID de geometrías, grupos de edad y condición de actividad, duplicados de establecimientos y concordancia entre warehouse, API y dashboard. Las consultas están en [04_quality_checks.sql](../sql/04_quality_checks.sql) y la evidencia local en [initial_data_audit.md](initial_data_audit.md).
