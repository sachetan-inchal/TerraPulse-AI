const path = require('path');
const { marked } = require(path.resolve('frontend/node_modules/marked'));

marked.setOptions({ breaks: true, gfm: true });

function normalizeMarkdownTables(md) {
  if (!md || typeof md !== 'string') return md;

  const lines = md.split('\n');
  const result = [];
  let inTable = false;
  let tableCols = 0;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];
    const trimmed = line.trim();

    // Check if line looks like a table delimiter: e.g. |---|---| or |:---|:---| or |--|--|' or |---|---|`
    const isDelimiter = /^\|?(\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?['"`\s]*$/.test(trimmed) && trimmed.includes('-');

    if (isDelimiter) {
      // Clean up delimiter: remove any trailing garbage, quotes, backticks
      let cleanDelim = trimmed.replace(/['"`\s]+$/, '').trim();
      if (!cleanDelim.startsWith('|')) cleanDelim = '| ' + cleanDelim;
      if (!cleanDelim.endsWith('|')) cleanDelim = cleanDelim + ' |';

      // Count delimiter columns
      tableCols = (cleanDelim.match(/-+/g) || []).length;

      // If the preceding line is the header, ensure it is properly formatted and preceded by a blank line
      if (result.length > 0) {
        let prev = result[result.length - 1].trim();
        if (prev.startsWith('|')) {
          if (!prev.endsWith('|')) prev = prev + ' |';
          result[result.length - 1] = prev;
        }
        // Ensure empty line before table header if not already present
        if (result.length > 1 && result[result.length - 2].trim() !== '') {
          result.splice(result.length - 1, 0, '');
        }
      }

      result.push(cleanDelim);
      inTable = true;
      continue;
    }

    // Check if line is a table row (starts with |)
    if (trimmed.startsWith('|')) {
      let cleanRow = trimmed;
      // Ensure closing pipe
      if (!cleanRow.endsWith('|')) {
        cleanRow = cleanRow + ' |';
      }

      if (inTable && tableCols > 0) {
        // Count cells: | a | b | has 2 cells, 3 pipes
        const pipeCount = (cleanRow.match(/\|/g) || []).length;
        const cellCount = pipeCount - 1;

        if (cellCount < tableCols) {
          // Missing column separators, pad with empty cells e.g. | Cell 1 |
          const missing = tableCols - cellCount;
          cleanRow = cleanRow.slice(0, -1) + ' |'.repeat(missing);
        }
      }

      result.push(cleanRow);
      continue;
    }

    // Line does not start with |
    if (inTable) {
      inTable = false;
      tableCols = 0;
      if (trimmed !== '') {
        result.push('');
      }
    }
    result.push(line);
  }

  return result.join('\n');
}

const rawText = `Summary of findings:
| Category | Key Points |
|----------|------------|'
| Physical & Chemical Characteristics | Complex mixture of solid particles and liquid droplets (diameter ≤ 2.5 µm). Composed of elemental carbon, organic carbon compounds, sulfates, nitrates, trace metals, and bound water. |
| Major Anthropogenic Sources | Fossil‑fuel combustion in vehicle engines (especially diesel), coal‑ or gas‑fired thermal power generation, industrial manufacturing and metallurgical smelting, biomass and agricultural waste burning, residential wood, charcoal, and trash combustion. |
| Natural Sources | Wildfires and forest fires, dust storms and soil deflation, volcanic eruptions, sea‑spray aerosols. |
| Atmospheric Transport | Residence time ranges from days to weeks; can undergo long‑range transboundary transport spanning hundreds to thousands of kilometres due to low gravitational settling velocity. |
| Environmental & Ecosystem Impacts | Haze formation and reduced atmospheric visibility; acidification of surface waters when deposition contains sulfates and nitrates; nutrient depletion/soil alteration; radiative forcing (light absorption by black carbon – warming; scattering by sulfates – cooling). |
| Exposure Pathways | Inhalation deep into the respiratory tract, penetrating alveolar membranes directly into systemic circulation.
| Health Effects (see scientific consensus)
| Short‑term | Eye, nose, and throat irritation; coughing, wheezing, shortness of breath; aggravation of asthma and chronic bronchitis; acute cardiac events in vulnerable populations.
| Long‑term | Chronic obstructive pulmonary disease (COPD); ischemic heart disease, myocardial infarction, and stroke; reduced lung function development in children; lung cancer (classified as Group 1 carcinogen by IARC).
| Susceptible Groups | Elderly individuals; children and infants; people with pre‑existing cardiopulmonary disease; outdoor workers and economically marginalized populations.
| Medical Disclaimer | This information is provided for scientific and risk‑context only; it is not intended as medical diagnosis or individual clinical advice. |
| Guideline Limits | WHO annual limit: 5 µg/m³; WHO 24‑hour limit: 15 µg/m³ (99th percentile, 3–4 exceedance days/year); EPA NAQA  (annual): 9.0 µg/m³; EPA NAQA  (24‑hour): 35 µg/m³; CPCB (India) NAQ  (annual): 40 µg/m³; CPCB (India) NAQ  (24‑hour): 60 µg/m³.
| Scientific Consensus | • No safe threshold of PM2.5 exposure has been identified; adverse health impacts occur even below guideline levels.
| • PM2.5 penetration into systemic vasculature induces systemic inflammation and endothelial dysfunction.
| Uncertainties | Relative differential toxicity of specific chemical constituent fractions (e.g., secondary organics vs polycyclic aromatic hydrocarbons vs transition metals).
| • Synergistic toxicity interactions between co‑pollutant mixtures.
| Is Known Pollutant? | Yes (is_known_pollutant = true).
And that is all.`;

const out = marked.parse(normalizeMarkdownTables(rawText));
console.log(out);
