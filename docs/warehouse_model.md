# Modelo dimensional implementado

Responsable: Jonathan. Revisión: 2026-10-04. Fuente: [01_schema.sql](../sql/01_schema.sql).

El modelo reúne tres dimensiones y tres tablas de hechos. El vínculo territorial común es la AGEB urbana. El siguiente diagrama muestra claves reales del DDL; los campos descriptivos completos están en el [diccionario](data_dictionary.md).

```mermaid
erDiagram
    dim_geografia ||--o| fact_demografia : "cvegeo unico"
    dim_geografia ||--o{ fact_negocios : cvegeo
    dim_geografia ||--o{ fact_crimen : cvegeo
    dim_actividad_economica ||--o{ fact_negocios : scian_id
    dim_tiempo o|--o{ fact_negocios : "tiempo_id nullable"
    dim_tiempo o|--o{ fact_crimen : "tiempo_id nullable"

    dim_geografia {
        varchar cvegeo PK
        varchar cve_ent
        varchar cve_mun
        varchar cve_loc
        varchar cve_ageb
        numeric area_km2
        geometry geom_4326
        geometry geom_6372
    }
    dim_tiempo {
        int tiempo_id PK
        date fecha UK
        int anio
        int mes
        int dia
    }
    dim_actividad_economica {
        varchar scian_id PK
        varchar codigo_actividad
        varchar sector_codigo
        varchar sector_nombre
        varchar categoria_macro
    }
    fact_demografia {
        int fact_demografia_id PK
        varchar cvegeo FK,UK
        int poblacion_total
        int poblacion_0_14
        int poblacion_15_64
        int poblacion_65_mas
        int poblacion_pea
        int poblacion_pnea
    }
    fact_negocios {
        int fact_negocio_id PK
        varchar cvegeo FK
        varchar scian_id FK
        int tiempo_id FK
        geometry geom_punto
    }
    fact_crimen {
        int fact_crimen_id PK
        varchar cvegeo FK
        int tiempo_id FK
        varchar categoria_delito
        varchar tipo_delito
        varchar periodo_dia
        geometry geom_punto
    }
```

| Tabla | Grano y cardinalidad efectiva |
| --- | --- |
| `dim_geografia` | Una AGEB; puede existir sin hechos asociados |
| `dim_tiempo` | Una fecha; una observación puede no tener fecha, porque su FK permite NULL |
| `dim_actividad_economica` | Una clase SCIAN según el código de DENUE |
| `fact_demografia` | Cero o una fila por AGEB, por UQ en `cvegeo`; sin dimensión temporal censal |
| `fact_negocios` | Una fila insertada por establecimiento; muchas por AGEB/actividad; identidad de fuente y corte aún no preservados |
| `fact_crimen` | Una fila prevista por incidente; muchas por AGEB; fuente y carga aún pendientes |

`v_kpis_territoriales` agrega negocios y delitos antes de unirlos con geografía y demografía. Esa separación evita multiplicar incidentes por establecimientos en una unión directa entre hechos. El grano final sigue siendo una AGEB; no hay filtros por fecha en esta vista.

Las FK geográficas eliminan hechos en cascada cuando se borra su AGEB. Las demás FK no declaran eliminación en cascada. Hay cuatro índices GiST: dos en geografía y uno en cada tabla de puntos (negocios y delitos). Las seis tablas tienen RLS habilitado y políticas SELECT públicas; la vista consulta con permisos del invocador.

## Decisiones pendientes antes de ampliar el modelo

1. Acordar con Russel la identidad de establecimiento DENUE y el corte temporal para evitar recargas duplicadas.
2. Definir con el equipo si demografía debe conservar varios censos; actualmente una recarga reemplaza el registro de la AGEB.
3. Acordar la fuente de delitos, identificador de incidente, fecha y catálogo antes de poblar `fact_crimen` y `dim_tiempo`.
4. Distinguir el nombre de clase SCIAN del nombre del sector de dos dígitos.
5. Documentar cambios de límites/edición de AGEB entre fuentes antes de tratarlas como unidades equivalentes.

Estas son decisiones propuestas para revisión del equipo; esta entrega no modifica el DDL.
