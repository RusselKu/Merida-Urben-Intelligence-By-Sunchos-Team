import referenceData from './ageb_reference_areas.json';

const INVALID_TYPES = new Set([
  '',
  'NINGUNO',
  'N/A',
  'NONE',
]);

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
      : rawType,

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
