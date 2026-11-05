import re

def normalize_markdown_tables(md: str) -> str:
    if not md:
        return md

    lines = md.split("\n")
    result = []
    in_table = False
    table_cols = 0

    for i, line in enumerate(lines):
        trimmed = line.strip()

        is_delimiter = bool(re.match(r"^\|?(\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?['\"`\s]*$", trimmed)) and ("-" in trimmed)

        if is_delimiter:
            clean_delim = re.sub(r"['\"`\s]+$", "", trimmed).strip()
            if not clean_delim.startswith("|"):
                clean_delim = "| " + clean_delim
            if not clean_delim.endswith("|"):
                clean_delim = clean_delim + " |"

            table_cols = len(re.findall(r"-+", clean_delim))

            if result:
                prev = result[-1].strip()
                if prev.startswith("|"):
                    if not prev.endswith("|"):
                        prev = prev + " |"
                    result[-1] = prev
                if len(result) > 1 and result[-2].strip() != "":
                    result.insert(-1, "")

            result.append(clean_delim)
            in_table = True
            continue

        if trimmed.startswith("|"):
            clean_row = trimmed
            if not clean_row.endswith("|"):
                clean_row = clean_row + " |"

            if in_table and table_cols > 0:
                cell_count = len(re.findall(r"\|", clean_row)) - 1
                if cell_count < table_cols:
                    clean_row = clean_row[:-1] + (" |" * (table_cols - cell_count))

            result.append(clean_row)
            continue

        if in_table:
            in_table = False
            table_cols = 0
            if trimmed != "":
                result.append("")

        result.append(line)

    return "\n".join(result)

raw = """| Category | Key Points |
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
| Is Known Pollutant? | Yes (is_known_pollutant = true)."""

cleaned = normalize_markdown_tables(raw)
print("=== CLEANED OUTPUT ===")
print(cleaned)

