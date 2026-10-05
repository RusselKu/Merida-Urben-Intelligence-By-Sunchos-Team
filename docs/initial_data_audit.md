# Auditoría inicial de datos y reproducción

Responsable: Jonathan. Revisión local: 2026-10-04.

## Alcance y evidencia

Se revisó el código y el archivo GeoJSON versionado en la rama `feature/jonathan-data-dictionary`, basada en `develop`, commit `bee3f9cd621160b9b7d1c2e7b448109f7bb28485`. No se conectó a Supabase, no se descargaron fuentes y no se ejecutó el ETL. No se certifican las cifras de una base remota ni la cobertura completa de Mérida.

- Archivo: [merida_agebs_demographics.geojson](../outputs/maps/merida_agebs_demographics.geojson).
- SHA-256: `21013fd890b423dead5153c94bdac6d5c10f5a378a76a610e67fbd6589d0b967`.
- Evidencia calculada: [local_data_audit.json](../outputs/qa/local_data_audit.json).
- Herramienta reproducible: [audit_local_data.py](../src/qa/audit_local_data.py), solo biblioteca estándar de Python.

Ejecutar desde la raíz del repo:

```bash
python -m src.qa.audit_local_data --output outputs/qa/local_data_audit.json
```

El comando genera el perfil sin modificar el GeoJSON. Para usarlo como comprobación, añadir `--check`: devuelve código 1 si detecta hallazgos de error; con el archivo actual ese resultado es esperado. Un código 0 no acredita que las fuentes estén completas ni que las geometrías sean topológicamente correctas.

La herramienta se comprobó contra el archivo versionado y ejemplos sintéticos con datos coherentes, claves inválidas, claves repetidas, conteos negativos y colección vacía. Se verificaron sus códigos de salida, la reproducción exacta del JSON y el rechazo de una salida que sobrescribiera el archivo de entrada. También se comprobó que el diccionario incluye las 50 columnas de las seis tablas del DDL y que los enlaces locales de los documentos nuevos resuelven.

## Resultados observados en el archivo local

| Control | Resultado | Interpretación |
| --- | --- | --- |
| Features y claves | 526 features, sin CVEGEO repetidos o con formato inesperado | Pasa el control local de formato `31050` + localidad + AGEB; no prueba cobertura completa |
| Campos demográficos | 526 filas con los nueve conteos numéricos; sin nulos ni negativos en ellos | Los ceros imputados pueden ocultar faltantes en las fuentes |
| Población total | 957,399 | Suma de este archivo; pendiente de reconciliar con fuente y warehouse |
| AGEB sin habitantes | 6 | Las tasas por población no tienen denominador válido |
| AGEB con población menor de 100 | 32, incluidas las 6 con cero | Revisar estabilidad de tasas; la regla analítica de Bianca no se aplica automáticamente en la API actual |
| Grupos de edad | 526/526 con población 0–14 igual al total; 15–64 y 65+ en cero | Patrón sistemático incorrecto; incluye 6 AGEB con total cero |
| Patrón de edad en AGEB pobladas | 520/520 | Confirma que el problema no se explica por registros sin habitantes |
| Población inactiva | Cero en las 526 AGEB | Revisar mapeo y regenerar archivo desde la fuente |
| Tasa PEA derivada | Sería 100% en 516 AGEB con PEA positiva | Resultado aritmético del archivo desactualizado; no es un hallazgo socioeconómico |
| Suma por sexo frente al total | Diferencia en 4 AGEB; máximo absoluto de 24 personas | Cotejar supresión estadística y datos originales antes de corregir |
| Superficie | Mínimo 0.0122, mediana 0.40565, máximo 6.5497 km²; suma 259.8632 km² | Valores positivos; no se recalculó el área ni se comprobó el CRS |
| Geometrías declaradas | 526 Polygon | El DDL exige MultiPolygon; el archivo no demuestra validez topológica |
| Negocios y delitos | Propiedades `total_negocios` y `total_delitos` ausentes en las 526 features | Datos no disponibles en el archivo; no equivalen a cero observaciones |
| Fuentes originales | Sin archivos coincidentes en `data/raw/` para las cuatro fuentes | Perfilado de fuentes y reconciliación pendientes |

## Hallazgos y responsables propuestos

Las asignaciones siguientes siguen `TEAM_DISTRIBUTION.md`; son una guía de coordinación, no notificaciones enviadas al equipo. Jonathan registra evidencia y verifica el cierre con cada responsable.

| ID | Prioridad | Evidencia / problema | Acción y responsable propuesto | Criterio para cerrar |
| --- | --- | --- | --- | --- |
| QA-01 | Alta | El GeoJSON mantiene el patrón incorrecto de edad y PNEA | Russel, con Bianca: regenerar desde el censo usando el mapeo actual | Cotejo de variables originales, nuevo hash, perfil sin patrón sistemático y reconciliación con warehouse |
| QA-02 | Alta | El código actual ya usa `POB0_14`, `POB15_64`, `POB65_MAS`, `PE_INAC`, pero cambiar el código no actualiza archivos exportados | Russel: incluir regeneración verificable y registrar fecha/corte de carga | Archivo, tablas y API reflejan la misma versión validada |
| QA-03 | Alta | `load_dim_geografia()` y SQL exportado insertan Polygon sin conversión; DDL exige MultiPolygon | Russel: acordar conversión y completar carga | Una carga de prueba acepta los polígonos; Q07 no devuelve excepciones |
| QA-04 | Alta | `fact_negocios` no conserva ID DENUE ni restricción para distinguir recargas | Russel: definir identidad/corte e implementar carga repetible | Dos cargas del mismo corte no aumentan el conteo ni alteran KPIs |
| QA-05 | Media | Fallback de API asigna ceros a negocios/delitos ausentes y a ciertas tasas indefinidas | Rivaldo: identificar procedencia y disponibilidad de indicadores | Respuestas distinguen dato ausente, tasa indefinida y cero observado |
| QA-06 | Media | Dashboard tiene población fija 887,632 frente a suma local 957,399 y no consulta la API | Damián, con Bianca: conectar métricas y documentar cobertura | Tarjetas coinciden con el warehouse validado y explican fuente/corte |
| QA-07 | Alta para análisis de delitos | No hay fuente local ni transformación/carga de delitos en el pipeline | Equipo acuerda fuente; Russel implementa carga; Rivaldo/Bianca integran análisis | Catálogo, periodo, coordenadas e identidad documentados; carga y métricas reconciliadas |
| QA-08 | Media | Notebook inicial importaba `list_raw_files` y `spatial_join_points_to_polygons`, ausentes del ETL actual | Jonathan: actualizado a `get_real_paths`, auditoría local y `gpd.sjoin` en esta entrega; sintaxis e imports internos comprobados | Pendiente ejecutar todas las celdas con GeoPandas; el ejemplo espacial es sintético y no valida cobertura de fuentes |
| QA-09 | Media | CI instala pytest pero no ejecuta pruebas; control SQL solo enumera archivos | Russel/Rivaldo: incorporar pruebas y validación SQL efectiva | Fallos de prueba o SQL impiden pasar el workflow |
| QA-10 | Media | `sector_nombre` es nombre de clase; la vista lo presenta como actividad dominante | Russel/Bianca: acordar nivel SCIAN y nombres | Diccionario, agrupación SQL y visualización usan el mismo nivel |

El comando de arranque del README se corrige en esta entrega a `python src/backend/run.py`. El servicio Docker aún apunta a `src.backend.main:app`, módulo inexistente; la corrección y prueba de Docker quedan con Russel/Rivaldo.

## Validación pendiente en PostgreSQL/PostGIS

[04_quality_checks.sql](../sql/04_quality_checks.sql) contiene controles de cobertura, CVEGEO, integridad referencial, demografía, geometrías, ubicación de puntos, candidatos a duplicado, calendario, SCIAN y reconciliación de la vista. Se ejecuta en transacción de solo lectura con una instantánea consistente; requiere el esquema, la vista y acceso a todas las filas. RLS puede afectar lo observado.

Registrar fecha de carga, versión de fuentes, usuario/permisos y resultados de Q01–Q12. Se espera cero huérfanos, claves mal formadas, conteos negativos, geometrías inválidas y tasas incompatibles con sus denominadores. Los candidatos a duplicado y diferencias demográficas requieren revisión, no eliminación automática. Tablas vacías y fechas nulas deben registrarse como pendientes de cobertura.

El SQL se revisó contra los nombres del DDL, pero **no se ejecutó ni se validó con un motor PostgreSQL/PostGIS** en esta entrega. Las pruebas de FastAPI y el build del frontend también quedan pendientes por falta de dependencias. El informe técnico final debe usar resultados aceptados después de estos controles.
