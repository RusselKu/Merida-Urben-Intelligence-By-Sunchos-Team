import referenceData from './ageb_reference_areas.json';

const INVALID_TYPES = new Set([
  '',
  'NINGUNO',
  'N/A',
  'NONE',
]);

const SETTLEMENT_TYPE_EN = {
  COLONIA: 'Neighborhood',
  FRACCIONAMIENTO: 'Subdivision',
  BARRIO: 'District',
  PUEBLO: 'Town',
  EJIDO: 'Ejido',
  ZONA_MILITAR: 'Military Zone',
  ZONA_INDUSTRIAL: 'Industrial Zone',
  HACIENDA: 'Hacienda',
};

const INVALID_POSTAL_CODES = new Set([
  '',
  '00000',
]);

export function getAgebReferenceArea(cvegeo) {
  if (!cvegeo) return null;

  const record =
    referenceData.agebs?.[String(cvegeo)];

  if (!record?.primary_name) {
    return null;
  }

  const rawType = String(
    record.primary_type || '',
  ).trim();

  const rawPostalCode = String(
    record.primary_cp || '',
  ).trim();

  return {
    name: record.primary_name,

    type: INVALID_TYPES.has(
      rawType.toUpperCase(),
    )
      ? null
      : (SETTLEMENT_TYPE_EN[rawType.toUpperCase()] || rawType),

    postalCode:
      INVALID_POSTAL_CODES.has(rawPostalCode)
        ? null
        : rawPostalCode,

    coveragePct:
      Number.isFinite(
        Number(record.coverage_pct),
      )
        ? Number(record.coverage_pct)
        : null,

    intersections:
      Array.isArray(record.intersections)
        ? record.intersections
        : [],
  };
}

export function getReferenceAreaMetadata() {
  return referenceData.metadata;
}

export function searchAgebReferenceAreas(query, limit = 8) {
  if (!query || typeof query !== 'string') return [];
  const clean = query.trim().toLowerCase();
  if (clean.length < 2) return [];

  const results = [];
  const agebMap = referenceData.agebs || {};

  for (const [cvegeo, record] of Object.entries(agebMap)) {
    if (!record?.primary_name) continue;

    const name = record.primary_name.toLowerCase();
    const cp = String(record.primary_cp || '');
    const cve = String(cvegeo);

    if (name.includes(clean) || cve.includes(clean) || cp.includes(clean)) {
      const rawType = String(record.primary_type || '').trim();
      const rawCp = String(record.primary_cp || '').trim();

      results.push({
        cvegeo,
        name: record.primary_name,
        type: INVALID_TYPES.has(rawType.toUpperCase())
          ? null
          : (SETTLEMENT_TYPE_EN[rawType.toUpperCase()] || rawType),
        postalCode: INVALID_POSTAL_CODES.has(rawCp) ? null : rawCp,
        coveragePct: Number.isFinite(Number(record.coverage_pct))
          ? Number(record.coverage_pct)
          : null,
      });

      if (results.length >= limit) break;
    }
  }

  return results;
}

