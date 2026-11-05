from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    rank: int
    name: str
    description: str
    likelihood: str  # High, Moderate, Low, or Insufficient Data
    supporting_measurements: List[str]
    supporting_mechanisms: List[str]
    contradicting_or_uncertain_factors: List[str]


class CauseAnalysisResult(BaseModel):
    investigation_location: Optional[str] = None
    ranked_hypotheses: List[Hypothesis]
    alternative_explanations: List[str]
    missing_critical_data: List[str]
    recommended_measurements: List[str]
    confidence_assessment: str
    uncertainty_level: str  # High, Medium, Low
    scientific_rationale: str
    medical_disclaimer: str = (
        "CRITICAL SAFETY NOTICE: TerraPulse AIR is an environmental exposure intelligence engine, "
        "NOT a medical diagnosis system. Reported health symptoms cannot be clinically attributed "
        "to a specific pollutant solely based on ambient concentrations and geographical location. "
        "Individuals experiencing acute symptoms must seek evaluation from qualified healthcare professionals."
    )


class EnvironmentalCauseAnalysisService:
    def analyze(
        self,
        location: Optional[str] = None,
        measurements: Optional[List[Dict[str, Any]]] = None,
        reported_observations: Optional[List[str]] = None,
        meteorological_conditions: Optional[Dict[str, Any]] = None,
        research_context: Optional[str] = None
    ) -> CauseAnalysisResult:
        """
        Evaluate environmental evidence and rank plausible source hypotheses.
        Applies chemical ratio heuristics and atmospheric physics.
        """
        measurements = measurements or []
        reported_observations = reported_observations or []
        meteorological_conditions = meteorological_conditions or {}

        # Parse available measurements
        values: Dict[str, float] = {}
        for m in measurements:
            param = str(m.get("parameter_name") or m.get("parameter") or "").upper().replace(".", "")
            val = m.get("value")
            if val is not None:
                try:
                    values[param] = float(val)
                except ValueError:
                    pass

        has_pm25 = "PM25" in values
        has_pm10 = "PM10" in values
        has_no2 = "NO2" in values
        has_so2 = "SO2" in values
        has_co = "CO" in values
        has_o3 = "O3" in values

        pm25_val = values.get("PM25", 0.0)
        pm10_val = values.get("PM10", 0.0)
        no2_val = values.get("NO2", 0.0)
        so2_val = values.get("SO2", 0.0)
        co_val = values.get("CO", 0.0)

        hypotheses: List[Hypothesis] = []
        rank_counter = 1

        # 1. Vehicular Traffic Exhaust Hypothesis
        traffic_support = []
        if has_no2 and no2_val > 40:
            traffic_support.append(f"Elevated NO2 ({no2_val} µg/m³) indicates fresh high-temperature combustion.")
        if has_pm25 and pm25_val > 30:
            traffic_support.append(f"Elevated fine PM2.5 ({pm25_val} µg/m³) consistent with vehicle exhaust.")
        if has_co and co_val > 1.0:
            traffic_support.append(f"Elevated CO ({co_val}) indicates incomplete hydrocarbon combustion.")

        traffic_likelihood = "High" if len(traffic_support) >= 2 else ("Moderate" if traffic_support else "Low")
        hypotheses.append(
            Hypothesis(
                rank=rank_counter,
                name="Motor Vehicular Traffic Emissions",
                description="Combustion emissions from gasoline and diesel passenger and freight transport.",
                likelihood=traffic_likelihood,
                supporting_measurements=traffic_support if traffic_support else ["Insufficient co-pollutant data to confirm traffic signature."],
                supporting_mechanisms=[
                    "Diesel engines emit primary soot (elemental carbon) and high NOx.",
                    "Fleet braking and tire abrasion contribute ultrafine and transition metal particles."
                ],
                contradicting_or_uncertain_factors=[
                    "Without diurnal peak traffic rush-hour data, continuous vs episodic contribution is uncertain."
                ]
            )
        )
        rank_counter += 1

        # 2. Industrial / Point Source Combustion
        industrial_support = []
        if has_so2 and so2_val > 20:
            industrial_support.append(f"Elevated SO2 ({so2_val} µg/m³) strongly indicates combustion of high-sulfur coal or heavy residual fuel oil.")
        if has_pm25 and pm25_val > 60:
            industrial_support.append(f"High particulate concentration ({pm25_val} µg/m³) consistent with heavy industrial plumes.")

        industrial_likelihood = "High" if (has_so2 and so2_val > 40) else ("Moderate" if industrial_support else "Low")
        hypotheses.append(
            Hypothesis(
                rank=rank_counter,
                name="Industrial Manufacturing & Power Generation",
                description="Point-source emissions from coal-fired boilers, metallurgical plants, or refineries.",
                likelihood=industrial_likelihood,
                supporting_measurements=industrial_support if industrial_support else ["SO2 is within background levels, weakening heavy fuel hypothesis."],
                supporting_mechanisms=[
                    "Combustion of sulfur-bearing industrial fuels releases gaseous SO2 and primary fine fly ash.",
                    "Secondary atmospheric transformation of SO2 creates regional sulfate aerosol episodes."
                ],
                contradicting_or_uncertain_factors=[
                    "Specific industrial facility downwind alignment requires wind vector verification."
                ]
            )
        )
        rank_counter += 1

        # 3. Biomass & Agricultural Burning
        biomass_support = []
        if has_pm25 and pm25_val > 50:
            biomass_support.append(f"Substantial fine PM2.5 ({pm25_val} µg/m³) typical of open vegetation/residue burning.")
        if any("haze" in obs.lower() or "smoke" in obs.lower() for obs in reported_observations):
            biomass_support.append("Reported observations note visible smoke haze.")

        hypotheses.append(
            Hypothesis(
                rank=rank_counter,
                name="Biomass & Agricultural Crop Residue Combustion",
                description="Open burning of post-harvest crop residue, fuelwood, or municipal solid waste.",
                likelihood="Moderate" if biomass_support else "Low",
                supporting_measurements=biomass_support if biomass_support else ["No direct chemical tracer (levoglucosan or potassium) currently available."],
                supporting_mechanisms=[
                    "Smoldering vegetative combustion releases high fractions of organic carbon and carbon monoxide.",
                    "Seasonal burning plumes can transport hundreds of kilometers under regional winds."
                ],
                contradicting_or_uncertain_factors=[
                    "Requires thermal anomaly satellite data (MODIS/VIIRS) or levoglucosan speciation to confirm."
                ]
            )
        )
        rank_counter += 1

        # 4. Meteorological Stagnation & Temperature Inversion
        met_support = []
        wind_speed = meteorological_conditions.get("wind_speed_ms") or meteorological_conditions.get("wind_speed")
        if wind_speed is not None and float(wind_speed) < 2.0:
            met_support.append(f"Low wind speed ({wind_speed} m/s) severely suppresses atmospheric ventilation.")
        if meteorological_conditions.get("inversion") is True or "winter" in str(meteorological_conditions).lower():
            met_support.append("Nocturnal boundary layer compression / temperature inversion trapping surface emissions.")

        hypotheses.append(
            Hypothesis(
                rank=rank_counter,
                name="Meteorological Inversion & Atmospheric Stagnation",
                description="Boundary layer trapping preventing vertical mixing and dispersion of surface pollutants.",
                likelihood="High" if met_support else "Moderate",
                supporting_measurements=met_support if met_support else ["Wind speed and vertical boundary layer height measurements not supplied."],
                supporting_mechanisms=[
                    "Temperature inversions act as an atmospheric lid, preventing vertical convection.",
                    "Low wind speeds cause local emissions to accumulate exponentially over time."
                ],
                contradicting_or_uncertain_factors=[
                    "Meteorology amplifies pollution concentrations but is an accumulation mechanism rather than the primary emission source."
                ]
            )
        )

        # Sort hypotheses by likelihood
        priority = {"High": 1, "Moderate": 2, "Low": 3, "Insufficient Data": 4}
        hypotheses.sort(key=lambda h: priority.get(h.likelihood, 5))
        for idx, h in enumerate(hypotheses, 1):
            h.rank = idx

        # Missing data list
        missing = []
        if not has_so2:
            missing.append("SO2 measurements (required to isolate industrial and coal burning from traffic).")
        if not has_co:
            missing.append("CO measurements (required to evaluate combustion completeness and vehicular fraction).")
        if not has_no2:
            missing.append("NO2 measurements (critical indicator of traffic and high-temperature combustion).")
        if "wind_speed" not in meteorological_conditions:
            missing.append("Local wind speed, wind direction, and mixing layer height data.")
        if not any("speciation" in str(m) for m in measurements):
            missing.append("Chemical speciation of PM2.5 (black carbon, sulfate, nitrate, organic carbon).")

        recs = [
            "Deploy multi-pollutant co-located monitoring (PM2.5, NO2, SO2, CO) at key receptors.",
            "Install sonic anemometer for 3D wind velocity and boundary layer turbulence assessment.",
            "Analyze PM2.5 filter samples for chemical markers (e.g., levoglucosan for biomass, vanadium/nickel for heavy oil, hopanes for vehicle oil).",
            "Cross-reference time-series hourly trends against local rush-hour traffic volumes."
        ]

        confidence = "Moderate" if len(values) >= 3 else "Low (Limited Sensor Coverage)"
        uncertainty = "Low" if len(values) >= 4 else "High"

        return CauseAnalysisResult(
            investigation_location=location,
            ranked_hypotheses=hypotheses,
            alternative_explanations=[
                "Regional long-range transboundary transport from upwind states or neighboring industrial corridors.",
                "Mechanical resuspension of mineral dust from construction and unpaved roads (if PM10 is elevated).",
                "Secondary photochemical particulate formation occurring downwind from distant precursor emissions."
            ],
            missing_critical_data=missing,
            recommended_measurements=recs,
            confidence_assessment=f"{confidence}: Assessment based on available pollutant ratios and standard atmospheric transport physics.",
            uncertainty_level=uncertainty,
            scientific_rationale=(
                "Distinguishing pollution sources requires examining stoichiometric ratios (e.g., PM2.5/PM10, NO2/SO2, CO/NOx). "
                "While current evidence highlights plausible candidates, definitive source apportionment requires chemical speciation "
                "or receptor modeling (e.g., Positive Matrix Factorization / PMF)."
            )
        )

