# Inventario inicial de fuentes

Responsable: Jonathan. Corte documental: 2026-10-04.

El inventario describe las fuentes que el código espera recibir. En este clon `data/raw/` solo contiene `.gitkeep`; no se han medido nulos, duplicados o cobertura de los CSV originales. Las direcciones de descarga están configuradas en [download_official_data.py](../src/etl/download_official_data.py); su disponibilidad y contenido no se verificaron en esta entrega.

| Fuente declarada | Archivo esperado por el extractor | Unidad original | Uso en el warehouse | Disponibilidad local |
| --- | --- | --- | --- | --- |
| INEGI Censo de Población y Vivienda 2020, AGEB/manzana urbana de Yucatán | `*ageb_urbana_31_cpv2020.csv` | Registros con distintos niveles de agregación; se seleccionan totales AGEB | `fact_demografia` | CSV ausente; existe un GeoJSON derivado con problemas de calidad |
| INEGI Marco Geoestadístico, declarado como 2020 por el pipeline | `31a.shp` y sus archivos complementarios | Polígono AGEB | `dim_geografia` | Shapefile ausente; comprobar edición y metadatos antes de usar |
| INEGI DENUE, Yucatán | `denue_inegi_31_.csv` | Establecimiento georreferenciado | `dim_actividad_economica`, `fact_negocios` | CSV ausente; fecha de corte no documentada |
| Incidentes de seguridad pública | `*crimen*.csv` o `*delito*.csv` | Incidente georreferenciado, previsto | `fact_crimen`, `dim_tiempo` | Fuente, proveedor, periodo y catálogo pendientes; sin carga en el pipeline |
| Archivo derivado versionado | `outputs/maps/merida_agebs_demographics.geojson` | AGEB con propiedades demográficas | Fallback de la API | 526 features; auditoría reproducible disponible |

## Campos de origen utilizados

- Censo: `ENTIDAD`, `MUN`, `LOC`, `AGEB`, `NOM_LOC`, `MZA`, `POBTOT`, `POBMAS`, `POBFEM`, `POB0_14`, `POB15_64`, `POB65_MAS`, `PEA`, `PE_INAC`, `VIVTOT`. El lector usa UTF-8. El código actual comprueba expresamente la presencia de las tres variables de edad y `PE_INAC`.
- Cartografía: `CVEGEO`, `CVE_ENT`, `CVE_MUN`, `CVE_LOC`, `CVE_AGEB`, geometría y CRS de origen. Los nombres se buscan sin distinguir mayúsculas. Revisar todos los componentes del shapefile, especialmente `.prj`, y registrar el CRS real antes de reproyectar.
- DENUE: `cve_mun`, `codigo_act`, `nombre_act`, `nom_estab`, `per_ocu`, `latitud`, `longitud`. El lector usa Latin-1. El identificador de establecimiento de la fuente no se conserva en la tabla de hechos.
- Delitos: aún no existe un mapeo implementado; no asumir nombres de columnas, fechas, CRS ni catálogo a partir del lector genérico.

## Metadatos que deben registrarse al recibir cada fuente

| Dato | Criterio de aceptación |
| --- | --- |
| Proveedor y URL efectiva | Identificar el recurso concreto descargado, su edición y sus condiciones de uso |
| Fecha de publicación, corte y descarga | Registrar las tres cuando estén disponibles; no confundir fecha de descarga con periodo observado |
| Archivo y SHA-256 | Permitir identificar exactamente la versión analizada |
| Cobertura geográfica y temporal | Confirmar entidad, municipio, localidades y periodo; justificar diferencias entre fuentes |
| Filas y claves | Contar antes y después de filtrar; medir nulos, unicidad y conflictos en las claves |
| Coordenadas y geometrías | Comprobar CRS, rangos, validez, geometrías vacías y cobertura territorial |
| Unión espacial | Contar asignados, fuera de polígonos, sobre bordes y con más de una correspondencia; reconciliar el total |
| Supresión estadística | Contar `*`, `N/D` y valores faltantes antes de sustituirlos; documentar su efecto |

DENUE utiliza una URL sin fecha explícita. Una nueva descarga puede pertenecer a otro corte; no describirla automáticamente como contemporánea al Censo 2020. El lector escoge el primer archivo coincidente, por lo que conviene conservar un manifiesto de la versión usada y evitar mezclar ediciones.

## Orden de validación

1. Registrar archivos originales y sus metadatos sin modificarlos.
2. Perfilar claves y variables antes de limpiar; comprobar especialmente ceros y supresiones.
3. Comparar CVEGEO de cartografía y censo: coincidencias y claves presentes en una sola fuente.
4. Verificar la asignación de puntos a AGEB y los registros descartados.
5. Ejecutar las [consultas SQL de calidad](../sql/04_quality_checks.sql) después de una carga controlada.
6. Contrastar warehouse, respuesta API y dashboard antes de publicar cifras.

La evidencia observada en el archivo local se detalla en [initial_data_audit.md](initial_data_audit.md). Hasta completar la validación de fuentes y la carga, los indicadores derivados siguen pendientes de aceptación.
