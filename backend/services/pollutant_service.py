from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class HealthEffects(BaseModel):
    short_term: List[str]
    long_term: List[str]
    susceptible_groups: List[str]
    medical_disclaimer: str = (
        "Environmental health information provided for scientific and risk context only; "
        "not intended as a medical diagnosis or individual clinical advice."
    )


class EnvironmentalStandards(BaseModel):
    who_annual_limit: Optional[str] = None
    who_24h_limit: Optional[str] = None
    epa_naaqs: Optional[str] = None
    cpcb_india_naaqs: Optional[str] = None


class PollutantProfile(BaseModel):
    code: str
    full_name: str
    pollutant_type: str  # Primary, Secondary, or Primary/Secondary
    physical_chemical_characteristics: str
    major_anthropogenic_sources: List[str]
    natural_sources: List[str]
    atmospheric_transport_lifetime: str
    environmental_and_ecosystem_impacts: List[str]
    exposure_pathways: List[str]
    health_effects: HealthEffects
    standards: EnvironmentalStandards
    established_scientific_consensus: List[str]
    scientific_uncertainties: List[str]
    is_known_pollutant: bool = True
    verification_notes: Optional[str] = None


KNOWN_POLLUTANTS: Dict[str, Dict[str, Any]] = {
    "PM2.5": {
        "code": "PM2.5",
        "full_name": "Fine Particulate Matter (diameter <= 2.5 µm)",
        "pollutant_type": "Primary and Secondary",
        "physical_chemical_characteristics": "Complex mixture of solid particles and liquid droplets with aerodynamic diameter <= 2.5 micrometers. Composed of elemental carbon, organic carbon compounds, sulfates, nitrates, trace metals, and bound water.",
        "major_anthropogenic_sources": [
            "Fossil fuel combustion in vehicle engines (especially diesel)",
            "Coal-fired and gas thermal power generation",
            "Industrial manufacturing and metallurgical smelting",
            "Biomass and agricultural waste burning",
            "Residential wood, charcoal, and trash combustion"
        ],
        "natural_sources": [
            "Wildfires and forest fires",
            "Dust storms and soil deflation",
            "Volcanic eruptions",
            "Sea spray aerosols"
        ],
        "atmospheric_transport_lifetime": "Atmospheric residence time ranging from days to weeks; can undergo long-range transboundary transport spanning hundreds to thousands of kilometers due to low gravitational settling velocity.",
        "environmental_and_ecosystem_impacts": [
            "Haze formation and severe impairment of atmospheric visibility",
            "Acidification of surface waters when deposition contains sulfates and nitrates",
            "Nutrient depletion in soils and alteration of ecosystem nutrient cycles",
            "Radiative forcing: light absorption by black carbon (warming) and scattering by sulfates (cooling)"
        ],
        "exposure_pathways": [
            "Inhalation deep into the respiratory tract, penetrating alveolar membranes directly into the systemic circulation"
        ],
        "health_effects": {
            "short_term": [
                "Eye, nose, and throat irritation",
                "Coughing, wheezing, and shortness of breath",
                "Aggravation of asthma and chronic bronchitis",
                "Acute cardiac events in vulnerable populations"
            ],
            "long_term": [
                "Chronic obstructive pulmonary disease (COPD)",
                "Ischemic heart disease, myocardial infarction, and stroke",
                "Reduced lung function development in children",
                "Lung cancer (classified as Group 1 carcinogen by IARC)"
            ],
            "susceptible_groups": [
                "Elderly individuals",
                "Children and infants",
                "People with pre-existing cardiopulmonary disease",
                "Outdoor workers and economically marginalized populations"
            ]
        },
        "standards": {
            "who_annual_limit": "5 µg/m³ (WHO 2021 Global Air Quality Guidelines)",
            "who_24h_limit": "15 µg/m³ (99th percentile, 3-4 exceedance days/year)",
            "epa_naaqs": "9.0 µg/m³ (Annual primary standard, revised 2024); 35 µg/m³ (24-hour)",
            "cpcb_india_naaqs": "40 µg/m³ (Annual); 60 µg/m³ (24-hour)"
        },
        "established_scientific_consensus": [
            "No safe threshold of PM2.5 exposure has been identified; adverse health impacts occur even below guideline levels.",
            "PM2.5 penetration into systemic vasculature induces systemic inflammation and endothelial dysfunction."
        ],
        "scientific_uncertainties": [
            "Relative differential toxicity of specific chemical constituent fractions (e.g. secondary organics vs polycyclic aromatic hydrocarbons vs transition metals).",
            "Synergistic toxicity interactions between co-pollutant mixtures."
        ]
    },
    "PM10": {
        "code": "PM10",
        "full_name": "Inhalable Coarse Particulate Matter (diameter <= 10 µm)",
        "pollutant_type": "Primary and Secondary",
        "physical_chemical_characteristics": "Inhalable particles with aerodynamic diameters between 2.5 and 10 micrometers. Dominated by crustal minerals, road dust, mechanically generated debris, and sea salts.",
        "major_anthropogenic_sources": [
            "Construction, demolition, and earthmoving operations",
            "Resuspension of road dust by vehicular traffic",
            "Open-cast mining and quarrying",
            "Agricultural tillage and harvesting"
        ],
        "natural_sources": [
            "Windblown mineral dust from arid regions and deserts",
            "Pollen and biological debris",
            "Volcanic ash"
        ],
        "atmospheric_transport_lifetime": "Hours to several days; settles closer to emission sources via gravitational deposition compared to fine PM2.5, though severe dust storms can carry coarse PM thousands of kilometers.",
        "environmental_and_ecosystem_impacts": [
            "Deposition on plant leaves blocking stomata and inhibiting photosynthesis",
            "Soil surface physical abrasion and crusting",
            "Deposition on cultural heritage monuments and solar panel efficiency degradation"
        ],
        "exposure_pathways": [
            "Inhalation deposit in upper airways (nasopharyngeal and tracheobronchial regions)"
        ],
        "health_effects": {
            "short_term": [
                "Nasal and throat irritation",
                "Exacerbation of asthma and allergic rhinitis",
                "Bronchoconstriction and coughing"
            ],
            "long_term": [
                "Accelerated decline in respiratory function",
                "Chronic bronchitis and recurrent respiratory infections"
            ],
            "susceptible_groups": ["Asthmatics", "Children", "Elderly", "Outdoor laborers"]
        },
        "standards": {
            "who_annual_limit": "15 µg/m³ (WHO 2021)",
            "who_24h_limit": "45 µg/m³",
            "epa_naaqs": "150 µg/m³ (24-hour, not to be exceeded more than once per year)",
            "cpcb_india_naaqs": "60 µg/m³ (Annual); 100 µg/m³ (24-hour)"
        },
        "established_scientific_consensus": [
            "Coarse PM is predominantly mechanically generated and primarily impacts the upper and central respiratory tract."
        ],
        "scientific_uncertainties": [
            "Health risks of biologically active endotoxins and allergens adhering to coarse dust surfaces."
        ]
    },
    "NO2": {
        "code": "NO2",
        "full_name": "Nitrogen Dioxide",
        "pollutant_type": "Primary and Secondary",
        "physical_chemical_characteristics": "Reddish-brown, pungent toxic gas; highly reactive free radical. Precursor to ground-level ozone (O3), secondary particulate nitrate, and nitric acid precipitation.",
        "major_anthropogenic_sources": [
            "Internal combustion vehicle exhaust (especially diesel)",
            "Fossil fuel combustion in power plants and industrial boilers",
            "Gas stoves and unvented heaters in indoor settings"
        ],
        "natural_sources": [
            "Lightning strikes in the troposphere",
            "Microbial soil processes (denitrification)",
            "Wildfires"
        ],
        "atmospheric_transport_lifetime": "Atmospheric lifetime of several hours to ~1 day in the planetary boundary layer before photolysis or chemical conversion into nitrate aerosols and nitric acid.",
        "environmental_and_ecosystem_impacts": [
            "Key catalyst in photochemical smog and tropospheric ozone formation",
            "Contribution to acid deposition impacting aquatic ecosystems and forests",
            "Eutrophication of nitrogen-sensitive water bodies and soil ecosystems"
        ],
        "exposure_pathways": [
            "Inhalation into the bronchial passages and terminal bronchioles"
        ],
        "health_effects": {
            "short_term": [
                "Airway inflammation in healthy individuals",
                "Heightened bronchial hyperresponsiveness in asthmatics",
                "Increased emergency room visits for respiratory symptoms"
            ],
            "long_term": [
                "Development and new-onset childhood asthma",
                "Impaired lung growth and reduced forced expiratory volume",
                "Increased susceptibility to respiratory pathogens"
            ],
            "susceptible_groups": ["Children", "People with asthma", "Individuals living near high-traffic corridors"]
        },
        "standards": {
            "who_annual_limit": "10 µg/m³ (WHO 2021)",
            "who_24h_limit": "25 µg/m³",
            "epa_naaqs": "53 ppb (Annual primary standard); 100 ppb (1-hour)",
            "cpcb_india_naaqs": "40 µg/m³ (Annual); 80 µg/m³ (24-hour)"
        },
        "established_scientific_consensus": [
            "NO2 is a reliable marker for traffic-related air pollution mixtures and directly induces airway hyperreactivity."
        ],
        "scientific_uncertainties": [
            "Disentangling the independent health effects of pure NO2 gas from ultrafine particles and polycyclic aromatic hydrocarbons emitted concurrently in traffic exhaust."
        ]
    },
    "SO2": {
        "code": "SO2",
        "full_name": "Sulfur Dioxide",
        "pollutant_type": "Primary (precursor to secondary sulfate PM)",
        "physical_chemical_characteristics": "Colorless, highly soluble reactive gas with a sharp, suffocating odor. Oxidizes in the atmosphere to sulfur trioxide (SO3) and sulfuric acid (H2SO4).",
        "major_anthropogenic_sources": [
            "Coal-fired and oil-fired power stations",
            "Industrial metal ore roasting and smelting (copper, nickel, iron)",
            "Petroleum refineries and chemical manufacturing",
            "Combustion of high-sulfur heavy fuel oil in maritime shipping"
        ],
        "natural_sources": [
            "Volcanic degassing and eruptions",
            "Oceanic dimethyl sulfide (DMS) oxidation",
            "Geothermal springs"
        ],
        "atmospheric_transport_lifetime": "1 to 4 days; oxidizes into sulfate aerosols which can travel thousands of kilometers.",
        "environmental_and_ecosystem_impacts": [
            "Major constituent of acid rain causing lake acidification and fish mortality",
            "Severe foliar damage to forest canopies and aluminum leaching from soils",
            "Accelerated corrosion of limestone, marble, and historical masonry"
        ],
        "exposure_pathways": [
            "Rapid inhalation absorption through moist mucus membranes of the upper respiratory tract"
        ],
        "health_effects": {
            "short_term": [
                "Rapid bronchoconstriction within minutes of exposure",
                "Wheezing, chest tightness, and coughing, particularly during exercise",
                "Mucous membrane irritation"
            ],
            "long_term": [
                "Aggravation of chronic cardiovascular and respiratory disease",
                "Compromised pulmonary defense mechanisms"
            ],
            "susceptible_groups": ["People with asthma during physical exertion", "Children", "Elderly"]
        },
        "standards": {
            "who_annual_limit": "Not specified in 2021 guidelines (focus on 24h limit)",
            "who_24h_limit": "40 µg/m³ (WHO 2021)",
            "epa_naaqs": "75 ppb (1-hour primary standard)",
            "cpcb_india_naaqs": "50 µg/m³ (Annual); 80 µg/m³ (24-hour)"
        },
        "established_scientific_consensus": [
            "Asthmatics experience marked bronchoconstriction at SO2 concentrations that do not cause symptoms in non-asthmatic individuals."
        ],
        "scientific_uncertainties": [
            "Threshold interactions between SO2 gas and cold, dry air during hyperventilation."
        ]
    },
    "CO": {
        "code": "CO",
        "full_name": "Carbon Monoxide",
        "pollutant_type": "Primary",
        "physical_chemical_characteristics": "Colorless, odorless, tasteless gas formed by incomplete combustion of carbon-containing fuels. Relatively unreactive in the lower troposphere.",
        "major_anthropogenic_sources": [
            "Motor vehicle exhaust (especially during cold starts, idling, or faulty catalytic converters)",
            "Incomplete combustion in faulty furnaces, gas appliances, and generators",
            "Industrial manufacturing and metal production",
            "Biomass and agricultural burning"
        ],
        "natural_sources": [
            "Photochemical oxidation of methane in the troposphere",
            "Wildfires and biomass burning",
            "Volcanic gas emissions"
        ],
        "atmospheric_transport_lifetime": "1 to 2 months globally; acts as a global tracer of combustion plumes and consumes atmospheric hydroxyl radicals (OH), indirectly lengthening methane lifetime.",
        "environmental_and_ecosystem_impacts": [
            "Indirect greenhouse warming by competing for OH radicals, slowing the breakdown of methane",
            "Minor direct plant phytotoxicity at typical ambient levels"
        ],
        "exposure_pathways": [
            "Rapid alveolar diffusion across lung membranes into red blood cells"
        ],
        "health_effects": {
            "short_term": [
                "Formation of carboxyhemoglobin (COHb), reducing oxygen delivery to organs",
                "Headache, dizziness, fatigue, nausea, and disorientation",
                "Myocardial ischemia and chest pain in individuals with coronary artery disease",
                "High concentrations cause asphyxiation and death (predominantly indoor/enclosed spaces)"
            ],
            "long_term": [
                "Subtle neurobehavioral impairments and memory deficits",
                "Low birth weight and fetal risk during pregnancy"
            ],
            "susceptible_groups": ["Patients with coronary heart disease", "Fetuses and pregnant women", "Elderly"]
        },
        "standards": {
            "who_annual_limit": "None (acute toxicity focus)",
            "who_24h_limit": "4 mg/m³ (WHO 2021 24-hour); 10 mg/m³ (8-hour)",
            "epa_naaqs": "9 ppm (8-hour); 35 ppm (1-hour)",
            "cpcb_india_naaqs": "2 mg/m³ (8-hour); 4 mg/m³ (1-hour)"
        },
        "established_scientific_consensus": [
            "CO binds to hemoglobin with approximately 200 to 250 times greater affinity than oxygen, shifting the oxyhemoglobin dissociation curve to the left."
        ],
        "scientific_uncertainties": [
            "Chronic sub-clinical neurological impacts of long-term ambient low-level exposure (under 5 ppm)."
        ]
    },
    "O3": {
        "code": "O3",
        "full_name": "Tropospheric (Ground-Level) Ozone",
        "pollutant_type": "Secondary (Photochemical)",
        "physical_chemical_characteristics": "Colorless, highly reactive, pungent oxidizing gas. Unlike stratospheric ozone which shields UV radiation, ground-level ozone is a destructive secondary air pollutant formed by solar ultraviolet reactions between NOx and volatile organic compounds (VOCs).",
        "major_anthropogenic_sources": [
            "Not emitted directly: formed photochemically from precursor NOx emissions (traffic, industry) and VOC emissions (solvents, chemical plants, gasoline vapors, unburned hydrocarbons)"
        ],
        "natural_sources": [
            "Biogenic VOC emissions from deciduous and coniferous trees (isoprene, terpenes)",
            "Stratospheric-tropospheric folding and ozone intrusion events",
            "Lightning NOx emissions"
        ],
        "atmospheric_transport_lifetime": "Hours to days in the planetary boundary layer; peaks during sunny, warm afternoons with stagnant air, forming regional photochemical smog plumes.",
        "environmental_and_ecosystem_impacts": [
            "Severe phytotoxicity: damages leaf foliage, induces chlorosis, and stunts forest tree growth",
            "Significant global reduction in crop yields (wheat, soybean, rice, and maize)",
            "Degradation of synthetic polymers, rubber products, and protective coatings"
        ],
        "exposure_pathways": [
            "Deep inhalation into lower respiratory bronchioles and alveolar surfaces"
        ],
        "health_effects": {
            "short_term": [
                "Chest pain, coughing, throat irritation, and airway constriction",
                "Inflammation of lung lining and transient reduction in lung vital capacity",
                "Marked aggravation of asthma and increased hospital admissions during heatwaves"
            ],
            "long_term": [
                "Development and acceleration of chronic asthma",
                "Permanent pulmonary tissue scarring and accelerated lung aging",
                "Increased premature respiratory mortality"
            ],
            "susceptible_groups": ["Active outdoor children and athletes", "Asthmatics", "Older adults with lung diseases"]
        },
        "standards": {
            "who_annual_limit": "60 µg/m³ (Peak season 8-hour mean, WHO 2021)",
            "who_24h_limit": "100 µg/m³ (8-hour daily maximum)",
            "epa_naaqs": "0.070 ppm (70 ppb) 8-hour primary standard",
            "cpcb_india_naaqs": "100 µg/m³ (8-hour); 180 µg/m³ (1-hour)"
        },
        "established_scientific_consensus": [
            "Ozone is a powerful oxidant that directly damages cellular lipids and proteins in respiratory epithelium.",
            "Ozone titration by fresh nitric oxide (NO) can cause urban core ozone concentrations to be lower than downwind rural concentrations."
        ],
        "scientific_uncertainties": [
            "Climate warming feedbacks on biogenic VOC emissions and regional ozone penalty effects."
        ]
    }
}


class PollutantService:
    def get_pollutant_profile(self, pollutant_name_or_code: str) -> PollutantProfile:
        """
        Retrieve structured, evidence-backed scientific intelligence for a pollutant.
        If unknown or fictional (e.g. XYZ-927), honestly reports it as unverified.
        """
        normalized = pollutant_name_or_code.strip().upper().replace(" ", "").replace("-", "")

        lookup_map = {
            "PM2.5": "PM2.5", "PM25": "PM2.5", "PARTICULATEMATTER2.5": "PM2.5", "PARTICULATEMATTER25": "PM2.5",
            "PM10": "PM10", "PARTICULATEMATTER10": "PM10",
            "NO2": "NO2", "NITROGENDIOXIDE": "NO2",
            "SO2": "SO2", "SULFURDIOXIDE": "SO2", "SULPHURDIOXIDE": "SO2",
            "CO": "CO", "CARBONMONOXIDE": "CO",
            "O3": "O3", "OZONE": "O3", "GROUNDLEVELOZONE": "O3"
        }

        matched_key = lookup_map.get(normalized)
        if not matched_key:
            # Check if any key is contained
            for k in KNOWN_POLLUTANTS:
                if k.upper() in normalized:
                    matched_key = k
                    break

        if matched_key and matched_key in KNOWN_POLLUTANTS:
            data = KNOWN_POLLUTANTS[matched_key]
            return PollutantProfile(**data)

        # UNKNOWN / FICTIONAL POLLUTANT (e.g., XYZ-927)
        # Must never fabricate properties, papers, or measurements!
        return PollutantProfile(
            code=pollutant_name_or_code,
            full_name=f"Unverified / Unknown Substance ({pollutant_name_or_code})",
            pollutant_type="Unknown",
            physical_chemical_characteristics="No verified chemical, physical, or toxicological data found in environmental registries (WHO, EPA, CPCB, PubChem, or CAS).",
            major_anthropogenic_sources=["Unknown — cannot verify emission sources for unrecognized compound."],
            natural_sources=["Unknown"],
            atmospheric_transport_lifetime="Unknown atmospheric chemistry and residence time.",
            environmental_and_ecosystem_impacts=["No established environmental impacts documented."],
            exposure_pathways=["Unknown"],
            health_effects=HealthEffects(
                short_term=["No verified short-term health effects documented in authoritative toxicological literature."],
                long_term=["No verified long-term health consequences documented."],
                susceptible_groups=["Unknown"],
                medical_disclaimer="Substance is unrecognized. Do not attribute clinical symptoms to unverified chemical entities."
            ),
            standards=EnvironmentalStandards(
                who_annual_limit=None,
                who_24h_limit=None,
                epa_naaqs=None,
                cpcb_india_naaqs=None
            ),
            established_scientific_consensus=[],
            scientific_uncertainties=[
                f"Substance '{pollutant_name_or_code}' is not recognized in standard air quality regulatory standards or atmospheric chemistry databases."
            ],
            is_known_pollutant=False,
            verification_notes=(
                f"Verification failed: '{pollutant_name_or_code}' is not an established criterion air pollutant. "
                "Per system policy, environmental properties and health hazards are not fabricated for unknown substances."
            )
        )

    def compare_pollutants(self, codes: List[str]) -> Dict[str, Any]:
        """Compare multiple pollutants, distinguishing primary vs secondary pollutants and standards."""
        profiles = [self.get_pollutant_profile(c) for c in codes]
        return {
            "requested": codes,
            "count": len(profiles),
            "primary_pollutants": [p.code for p in profiles if "Primary" in p.pollutant_type and p.is_known_pollutant],
            "secondary_pollutants": [p.code for p in profiles if "Secondary" in p.pollutant_type and p.is_known_pollutant],
            "profiles": [p.model_dump() for p in profiles],
            "comparison_summary": (
                "Primary pollutants (e.g., CO, primary SO2/NOx/PM) are directly emitted from combustion and mechanical processes. "
                "Secondary pollutants (e.g., O3, secondary nitrates/sulfates in PM2.5) are synthesized in the atmosphere via complex photochemical "
                "and gas-to-particle conversion reactions driven by sunlight, temperature, and precursor concentrations."
            )
        }

