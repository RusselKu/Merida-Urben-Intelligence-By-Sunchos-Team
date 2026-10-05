import React, { useMemo } from 'react';
import useAnalyticsSummary from '../charts/useAnalyticsSummary';
import './UrbanInsightStory.css';

function formatNumber(value, digits = 0) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return 'No data';
  }

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
  }).format(number);
}

function safeRatio(value, benchmark) {
  const current = Number(value);
  const base = Number(benchmark);

  if (
    !Number.isFinite(current) ||
    !Number.isFinite(base) ||
    base <= 0
  ) {
    return null;
  }

  return current / base;
}

function percentDifference(value, benchmark) {
  const ratio = safeRatio(value, benchmark);

  if (ratio === null) return null;

  return (ratio - 1) * 100;
}

function ageShare(ageb, key) {
  if (!ageb) return null;

  const age0 = Number(ageb.poblacion_0_14) || 0;
  const age15 = Number(ageb.poblacion_15_64) || 0;
  const age65 = Number(ageb.poblacion_65_mas) || 0;

  const total = age0 + age15 + age65;

  if (total <= 0) return null;

  return ((Number(ageb[key]) || 0) / total) * 100;
}

function cityAgeShare(summary, groupName) {
  const groups = summary?.age_groups || [];

  const total = groups.reduce(
    (sum, group) => sum + (Number(group.value) || 0),
    0,
  );

  if (total <= 0) return null;

  const group = groups.find(
    (item) => item.group === groupName,
  );

  if (!group) return null;

  return ((Number(group.value) || 0) / total) * 100;
}

function buildCityInsights(summary) {
  if (!summary?.city) return [];

  const insights = [];

  const services = summary.macro_categories?.find(
    (item) => item.name === 'Servicios',
  );

  const commerce = summary.macro_categories?.find(
    (item) => item.name === 'Comercio',
  );

  insights.push({
    eyebrow: 'City scale',
    title: 'A city of nearly one million residents',
    text:
      `${formatNumber(summary.city.poblacion_total)} residents and ` +
      `${formatNumber(summary.city.total_negocios)} establishments ` +
      `are distributed across ${formatNumber(summary.city.agebs)} urban AGEBs.`,
  });

  if (services && commerce) {
    insights.push({
      eyebrow: 'Economic structure',
      title: 'Services and commerce dominate the urban economy',
      text:
        `Services account for ${formatNumber(services.count)} establishments, ` +
        `followed by commerce with ${formatNumber(commerce.count)}.`,
    });
  }

  const populationBusinessRelationship =
    summary.relationships?.find(
      (relationship) => relationship.id === 'H1',
    );

  if (populationBusinessRelationship) {
    const rho = Number(
      populationBusinessRelationship.spearman_rho,
    );

    if (Number.isFinite(rho)) {
      insights.push({
        eyebrow: 'City pattern',
        title: 'Population and business activity tend to co-locate',
        text:
          `Population density and business density show a ` +
          `${populationBusinessRelationship.strength || 'measurable'} ` +
          `${populationBusinessRelationship.direction || 'positive'} ` +
          `relationship (Spearman ρ = ${rho.toFixed(2)}). ` +
          `The relationship is not perfect, so some AGEBs behave very differently from the citywide pattern.`,
      });
    }
  }

  return insights.slice(0, 3);
}

function buildAgebInsights(summary, ageb, referenceArea) {
  if (!summary?.city || !ageb) return [];

  const insights = [];

  const city = summary.city;

  const businessDensityRatio = safeRatio(
    ageb.densidad_negocios_km2,
    city.densidad_negocios_km2,
  );

  const populationDensityRatio = safeRatio(
    ageb.densidad_poblacion_km2,
    city.densidad_poblacion_km2,
  );

  const businessesPerThousandRatio = safeRatio(
    ageb.negocios_por_mil_hab,
    city.negocios_por_mil_hab,
  );

  const businessDensityDifference = percentDifference(
    ageb.densidad_negocios_km2,
    city.densidad_negocios_km2,
  );

  const populationDensityDifference = percentDifference(
    ageb.densidad_poblacion_km2,
    city.densidad_poblacion_km2,
  );

  const areaName =
    referenceArea?.name ||
    `AGEB ${ageb.cvegeo}`;

  /*
   * Insight 1:
   * Compare residential intensity against economic intensity.
   */
  if (
    businessDensityRatio !== null &&
    populationDensityRatio !== null &&
    businessDensityRatio >= 2 &&
    populationDensityRatio < 0.75
  ) {
    insights.push({
      eyebrow: 'Urban function',
      title: 'Economic activity outweighs residential intensity',
      text:
        `${areaName} has ${businessDensityRatio.toFixed(1)}× the citywide ` +
        `business density, while its population density is only ` +
        `${Math.round(populationDensityRatio * 100)}% of the Mérida average. ` +
        `This AGEB behaves more like an economic activity center than a predominantly residential area.`,
    });
  } else if (
    businessDensityRatio !== null &&
    businessDensityRatio >= 2
  ) {
    insights.push({
      eyebrow: 'Economic concentration',
      title: 'Business activity is unusually concentrated here',
      text:
        `Business density is ${businessDensityRatio.toFixed(1)}× the ` +
        `Mérida average (${formatNumber(ageb.densidad_negocios_km2, 1)} ` +
        `vs ${formatNumber(city.densidad_negocios_km2, 1)} establishments/km²).`,
    });
  } else if (
    populationDensityRatio !== null &&
    populationDensityRatio >= 2
  ) {
    insights.push({
      eyebrow: 'Residential concentration',
      title: 'This is one of the more intensely populated urban areas',
      text:
        `Population density is ${populationDensityRatio.toFixed(1)}× the ` +
        `citywide average (${formatNumber(ageb.densidad_poblacion_km2)} ` +
        `vs ${formatNumber(city.densidad_poblacion_km2)} residents/km²).`,
    });
  } else if (
    populationDensityRatio !== null &&
    businessDensityRatio !== null &&
    populationDensityRatio >= 1.2 &&
    businessDensityRatio < 0.7
  ) {
    insights.push({
      eyebrow: 'Urban function',
      title: 'A more residential than commercial profile',
      text:
        `Population concentration is above the Mérida average, while ` +
        `business density is comparatively low. This suggests a stronger residential function.`,
    });
  } else {
    insights.push({
      eyebrow: 'Local profile',
      title: 'This AGEB stays relatively close to citywide intensity',
      text:
        `Population density differs from the Mérida average by ` +
        `${populationDensityDifference === null
          ? 'an unavailable amount'
          : `${Math.abs(populationDensityDifference).toFixed(0)}%`} and ` +
        `business density differs by ` +
        `${businessDensityDifference === null
          ? 'an unavailable amount'
          : `${Math.abs(businessDensityDifference).toFixed(0)}%`}.`,
    });
  }

  /*
   * Insight 2:
   * Compare age structure.
   */
  const localAge65 = ageShare(
    ageb,
    'poblacion_65_mas',
  );

  const cityAge65 = cityAgeShare(
    summary,
    '65+',
  );

  const localAge0 = ageShare(
    ageb,
    'poblacion_0_14',
  );

  const cityAge0 = cityAgeShare(
    summary,
    '0-14',
  );

  if (
    localAge65 !== null &&
    cityAge65 !== null &&
    localAge65 >= cityAge65 * 1.5
  ) {
    insights.push({
      eyebrow: 'Demographic signal',
      title: 'Older resident profile',
      text:
        `${localAge65.toFixed(1)}% of classified residents are 65+, ` +
        `compared with ${cityAge65.toFixed(1)}% citywide.`,
    });
  } else if (
    localAge0 !== null &&
    cityAge0 !== null &&
    localAge0 >= cityAge0 * 1.3
  ) {
    insights.push({
      eyebrow: 'Demographic signal',
      title: 'Younger resident profile',
      text:
        `${localAge0.toFixed(1)}% of classified residents are ages 0–14, ` +
        `above the citywide share of ${cityAge0.toFixed(1)}%.`,
    });
  } else {
    const localEap = Number(
      ageb.tasa_pea_porcentaje,
    );

    const cityEap = Number(
      city.tasa_pea_porcentaje,
    );

    if (
      Number.isFinite(localEap) &&
      Number.isFinite(cityEap) &&
      Math.abs(localEap - cityEap) >= 6
    ) {
      insights.push({
        eyebrow: 'Economic participation',
        title:
          localEap > cityEap
            ? 'Higher economic participation than the city average'
            : 'Lower economic participation than the city average',
        text:
          `The EAP rate is ${localEap.toFixed(1)}%, compared with ` +
          `${cityEap.toFixed(1)}% across Mérida.`,
      });
    }
  }

  /*
   * Insight 3:
   * Warn when a per-capita business indicator can be exaggerated
   * by a very small residential population.
   */
  const population = Number(ageb.poblacion_total);

  if (
    Number.isFinite(population) &&
    population < 500 &&
    businessesPerThousandRatio !== null &&
    businessesPerThousandRatio >= 3
  ) {
    insights.push({
      eyebrow: 'Interpret with care',
      title: 'Per-capita business intensity is amplified by a small population',
      text:
        `Only ${formatNumber(population)} residents are recorded in this AGEB. ` +
        `That small denominator makes the businesses-per-1,000-residents indicator ` +
        `especially large, so it should be interpreted together with total businesses and area.`,
    });
  }

  return insights.slice(0, 3);
}

export default function UrbanInsightStory({
  selectedCvegeo = null,
  referenceArea = null,
}) {
  const { data, loading, error } =
    useAnalyticsSummary();

  const ageb = useMemo(() => {
    if (!selectedCvegeo || !data?.agebs) {
      return null;
    }

    return (
      data.agebs.find(
        (item) =>
          String(item.cvegeo) ===
          String(selectedCvegeo),
      ) || null
    );
  }, [data, selectedCvegeo]);

  const insights = useMemo(() => {
    if (!data) return [];

    if (ageb) {
      return buildAgebInsights(
        data,
        ageb,
        referenceArea,
      );
    }

    return buildCityInsights(data);
  }, [data, ageb, referenceArea]);

  if (loading) {
    return (
      <section className="urban-story urban-story--status">
        Discovering urban patterns…
      </section>
    );
  }

  if (error || !data) {
    return null;
  }

  return (
    <section className="urban-story">
      <header className="urban-story__header">
        <span>
          {ageb
            ? 'What stands out here'
            : 'What stands out in Mérida'}
        </span>

        <h2>
          {ageb
            ? referenceArea?.name ||
              `AGEB ${ageb.cvegeo}`
            : 'Urban story'}
        </h2>
      </header>

      <div className="urban-story__items">
        {insights.map((insight, index) => (
          <article
            className="urban-story__item"
            key={`${insight.title}-${index}`}
          >
            <span className="urban-story__eyebrow">
              {insight.eyebrow}
            </span>

            <strong>
              {insight.title}
            </strong>

            <p>
              {insight.text}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
