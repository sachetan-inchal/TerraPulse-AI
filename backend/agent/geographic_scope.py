import re
from typing import Dict, Any, Optional, Tuple, List


class GeographicScopeAnalyzer:
    """
    Analyzes user queries to determine geographic scope (Country, State, City, Local, or Non-spatial),
    target entity, primary investigation objective, and tool capability boundaries.
    """

    KNOWN_COUNTRIES = {
        "usa": "US", "united states": "US", "united states of america": "US", "us": "US", "america": "US",
        "india": "IN", "china": "CN", "united kingdom": "GB", "uk": "GB", "great britain": "GB",
        "canada": "CA", "australia": "AU", "germany": "DE", "france": "FR", "japan": "JP",
        "brazil": "BR", "russia": "RU", "italy": "IT", "spain": "ES", "mexico": "MX",
        "south africa": "ZA", "indonesia": "ID", "nigeria": "NG", "egypt": "EG"
    }

    KNOWN_STATES_PROVINCES = {
        "california": "US-CA", "texas": "US-TX", "florida": "US-FL", "new york state": "US-NY",
        "illinois": "US-IL", "pennsylvania": "US-PA", "ohio": "US-OH", "georgia": "US-GA",
        "washington state": "US-WA", "michigan": "US-MI", "colorado": "US-CO",
        "karnataka": "IN-KA", "maharashtra": "IN-MH", "tamil nadu": "IN-TN", "delhi ncr": "IN-DL",
        "uttar pradesh": "IN-UP", "west bengal": "IN-WB", "gujarat": "IN-GJ", "telangana": "IN-TG",
        "kerala": "IN-KL", "punjab": "IN-PB", "haryana": "IN-HR", "rajasthan": "IN-RJ",
        "bavaria": "DE-BY", "ontario": "CA-ON", "quebec": "CA-QC", "british columbia": "CA-BC"
    }

    KNOWN_CITIES = {
        "delhi": "IN", "new delhi": "IN", "bengaluru": "IN", "bangalore": "IN", "mumbai": "IN",
        "chennai": "IN", "kolkata": "IN", "hyderabad": "IN", "pune": "IN", "ahmedabad": "IN",
        "london": "GB", "new york": "US", "new york city": "US", "nyc": "US", "los angeles": "US",
        "chicago": "US", "houston": "US", "san francisco": "US", "seattle": "US",
        "beijing": "CN", "shanghai": "CN", "tokyo": "JP", "paris": "FR", "berlin": "DE"
    }

    LOCAL_PATTERNS = [
        r"\bnear\s+([a-zA-Z0-9\s\.\-]+)",
        r"\baround\s+([a-zA-Z0-9\s\.\-]+)",
        r"\bvicinity\s+of\s+([a-zA-Z0-9\s\.\-]+)",
        r"\bclose\s+to\s+([a-zA-Z0-9\s\.\-]+)",
        r"\brvce\b",
        r"\br\.?v\.?\s*college\b",
        r"\bcollege\b",
        r"\bcampus\b",
        r"\bneighborhood\b",
        r"\bward\b"
    ]

    @classmethod
    def analyze(cls, prompt: str) -> Dict[str, Any]:
        """
        Analyze prompt text to extract objective, geographic scope, and operational boundaries.
        """
        p_lower = prompt.lower().strip()

        # 1. Determine Objective
        is_emission = bool(re.search(r"\b(emission|sources|factory|factories|industrial|point[\s\-]source|emitters?|plants?)\b", p_lower))
        is_ambient = bool(re.search(r"\b(air quality|measurements?|readings?|stations?|concentrations?|aqi|pm2\.?5|pm10|no2|so2|o3|ozone)\b", p_lower))
        is_chemical_profile = bool(re.search(r"\b(what is|explain|compare|properties|health effects|chemical|pollutant intelligence|xyz-927)\b", p_lower)) and not is_ambient and not is_emission
        is_research = bool(re.search(r"\b(papers?|publications?|crossref|doi|literature|wikipedia|studies)\b", p_lower))

        if is_emission and not is_ambient:
            objective_type = "EMISSION_SOURCES"
        elif is_ambient and not is_emission:
            objective_type = "AMBIENT_AIR_QUALITY"
        elif is_chemical_profile:
            objective_type = "POLLUTANT_INTELLIGENCE"
        elif is_research:
            objective_type = "RESEARCH_LITERATURE"
        else:
            objective_type = "MULTI_SOURCE_INVESTIGATION"

        # 2. Determine Geographic Scope
        scope_type = "NON_SPATIAL"
        target_name = None
        iso_code = None

        # Check for Local first (e.g. "near RVCE")
        is_local = False
        for pat in cls.LOCAL_PATTERNS:
            m = re.search(pat, p_lower)
            if m:
                is_local = True
                if m.groups() and m.group(1):
                    target_name = m.group(1).strip()
                elif "rvce" in p_lower or "rv college" in p_lower:
                    target_name = "RV College of Engineering"
                break

        if is_local:
            scope_type = "LOCAL"
            if not target_name:
                target_name = "Local Vicinity / Coordinates"
        else:
            # Check Country
            for c_name, c_iso in cls.KNOWN_COUNTRIES.items():
                pattern = rf"\b{re.escape(c_name)}\b"
                if re.search(pattern, p_lower):
                    scope_type = "COUNTRY"
                    target_name = c_name.upper() if len(c_name) <= 3 else c_name.title()
                    iso_code = c_iso
                    break

            # Check State/Province
            if scope_type == "NON_SPATIAL":
                for s_name, s_code in cls.KNOWN_STATES_PROVINCES.items():
                    pattern = rf"\b{re.escape(s_name)}\b"
                    if re.search(pattern, p_lower):
                        scope_type = "STATE_PROVINCE"
                        target_name = s_name.title()
                        iso_code = s_code.split("-")[0]
                        break

            # Check City
            if scope_type == "NON_SPATIAL":
                for city_name, c_iso in cls.KNOWN_CITIES.items():
                    pattern = rf"\b{re.escape(city_name)}\b"
                    if re.search(pattern, p_lower):
                        scope_type = "CITY"
                        target_name = city_name.title()
                        iso_code = c_iso
                        break

        # 3. Tool Capability & Operational Boundaries
        if scope_type == "COUNTRY":
            tool_compatibility = (
                f"Existing spatial tools (e.g., 'find_nearby_emission_sources') operate on local coordinate radii (max 25-50 km). "
                f"They CANNOT execute a complete nationwide inventory for '{target_name}'. "
                f"STRICT RULE: Never silently substitute a single city (e.g., New York, Delhi) for a nationwide request. "
                f"The agent must identify this nationwide scope limitation, propose or execute a defensible regional sample "
                f"if appropriate (clearly labeled as a partial sample), or explain why a full nationwide inventory requires "
                f"national registry databases beyond localized radius tools."
            )
            strict_rule = (
                "NEVER silently substitute a single city for a country-level inquiry. "
                "Explicitly declare the nationwide scope and explain the radius limitations of local spatial search tools."
            )
        elif scope_type == "STATE_PROVINCE":
            tool_compatibility = (
                f"Existing spatial tools operate on local coordinate radii. They cannot cover an entire state/province '{target_name}' in a single call. "
                f"STRICT RULE: Acknowledge the state-level scope, evaluate tool radius limits, and advise the user or label any sampled inquiry clearly."
            )
            strict_rule = (
                "Recognize state-level scope and evaluate geographic capabilities of available tools. "
                "Do not pretend a local radius search covers the whole state."
            )
        elif scope_type == "LOCAL":
            tool_compatibility = (
                f"Directly suitable for local geocoding ('geocode_location') and local point-source search ('find_nearby_emission_sources')."
            )
            strict_rule = (
                "Geocode the local place to verified coordinates, then query nearby emission sources. "
                "Do NOT automatically call OpenAQ unless ambient air quality concentrations were explicitly requested."
            )
        elif scope_type == "CITY":
            tool_compatibility = (
                f"Suitable for geocoding and city-scale monitoring station lookup ('search_air_quality_locations')."
            )
            strict_rule = (
                "Use city geocoding or city station search. Distinguish ambient stations from emission sources."
            )
        else:
            tool_compatibility = "Non-spatial or general scientific inquiry."
            strict_rule = "Answer using pollutant intelligence, scientific research, or cause analysis as appropriate."

        return {
            "prompt": prompt,
            "objective_type": objective_type,
            "scope_type": scope_type,
            "target_name": target_name,
            "iso_code": iso_code,
            "tool_compatibility_note": tool_compatibility,
            "strict_rule": strict_rule
        }

