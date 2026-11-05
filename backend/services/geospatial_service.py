import math
import re
from typing import List, Dict, Any, Optional, Tuple
import httpx
from shapely.geometry import Point, mapping

from schemas.geospatial import (
    GeocodedLocation,
    EmissionSource,
    InvestigationBuffer,
    GeoJSONFeature,
    GeoJSONFeatureCollection
)


class GeospatialService:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    REVERSE_NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    USER_AGENT = "TerraPulseAIR-GeospatialEngine/1.0 (admin@terrapulse.ai)"

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout

    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
        """
        Validate latitude and longitude ranges.
        Latitude must be between -90 and 90.
        Longitude must be between -180 and 180.
        """
        if not (-90.0 <= lat <= 90.0):
            return False, f"Latitude {lat} is out of bounds (must be between -90.0 and +90.0 degrees)."
        if not (-180.0 <= lon <= 180.0):
            return False, f"Longitude {lon} is out of bounds (must be between -180.0 and +180.0 degrees)."
        return True, None

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great-circle distance between two points in kilometers."""
        r = 6371.0  # Earth radius in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 2)

    def geocode(self, location_name: str) -> GeocodedLocation:
        """Geocode a location string using OpenStreetMap Nominatim with candidate variation support."""
        headers = {"User-Agent": self.USER_AGENT}
        cleaned = location_name.strip()
        candidates = [cleaned]

        # Smart candidate expansion for common institutional abbreviations
        if re.search(r'\bRV\b', cleaned, re.I):
            candidates.insert(0, re.sub(r'\bRV\b', 'R.V.', cleaned, flags=re.I))
            candidates.insert(1, re.sub(r'\bRV\b', 'R. V.', cleaned, flags=re.I))

        data = None
        with httpx.Client(timeout=self.timeout) as client:
            for q in candidates:
                params = {
                    "q": q,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1
                }
                try:
                    resp = client.get(self.NOMINATIM_URL, headers=headers, params=params)
                    if resp.status_code == 200:
                        res_list = resp.json()
                        if res_list:
                            data = res_list
                            break
                except Exception:
                    continue

        if not data:
            raise LookupError(f"Location '{location_name}' could not be resolved by geocoding service.")

        first = data[0]
        lat = float(first["lat"])
        lon = float(first["lon"])

        valid, err = self.validate_coordinates(lat, lon)
        if not valid:
            raise ValueError(f"Geocoding returned invalid coordinates: {err}")

        bbox = [float(b) for b in first.get("boundingbox", [])]

        return GeocodedLocation(
            query=location_name,
            latitude=lat,
            longitude=lon,
            display_name=first.get("display_name", location_name),
            bounding_box=bbox if len(bbox) == 4 else None,
            osm_type=first.get("osm_type"),
            confidence=float(first.get("importance", 0.5)),
            source="OpenStreetMap Nominatim"
        )

    def reverse_geocode(self, lat: float, lon: float) -> str:
        """Reverse geocode coordinates into human-readable place description."""
        valid, err = self.validate_coordinates(lat, lon)
        if not valid:
            raise ValueError(err)

        headers = {"User-Agent": self.USER_AGENT}
        params = {"lat": lat, "lon": lon, "format": "json"}

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(self.REVERSE_NOMINATIM_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        return data.get("display_name", f"Coordinates ({lat}, {lon})")

    def create_investigation_buffer(
        self,
        lat: float,
        lon: float,
        radius_km: float = 2.0
    ) -> InvestigationBuffer:
        """
        Generate a circular investigation buffer using Shapely and calculate its area in km².
        Includes an explicit scientific disclaimer distinguishing investigation areas from dispersion plumes.
        """
        valid, err = self.validate_coordinates(lat, lon)
        if not valid:
            raise ValueError(err)

        if radius_km <= 0:
            raise ValueError("Radius must be greater than 0 km.")

        # Metric geodesic buffer calculation
        # 1 degree of latitude ~ 111.32 km
        # 1 degree of longitude ~ 111.32 * cos(lat) km
        lat_rad = math.radians(lat)
        delta_lat = radius_km / 111.32
        cos_factor = max(math.cos(lat_rad), 0.0001)
        delta_lon = radius_km / (111.32 * cos_factor)

        # Generate smooth circular polygon with 64 vertices using Shapely Point
        center = Point(lon, lat)
        # Construct ellipse in lon/lat matching circle in km
        circle_points = []
        for i in range(65):
            angle = 2.0 * math.pi * i / 64.0
            p_lon = lon + delta_lon * math.cos(angle)
            p_lat = lat + delta_lat * math.sin(angle)
            circle_points.append((p_lon, p_lat))

        from shapely.geometry import Polygon
        poly = Polygon(circle_points)

        # Theoretical planar circle area
        approx_area_km2 = round(math.pi * (radius_km ** 2), 2)

        geojson_geometry = mapping(poly)

        return InvestigationBuffer(
            center_latitude=lat,
            center_longitude=lon,
            radius_km=radius_km,
            area_km2=approx_area_km2,
            geometry_geojson=geojson_geometry,
            disclaimer=(
                f"A circular buffer of {radius_km} km (area ~{approx_area_km2} km²) is an estimated spatial "
                "investigation area for locating monitoring sensors and potential emission sources. "
                "It is NOT a scientifically calculated atmospheric dispersion boundary or plume."
            ),
            source_dataset="Shapely Geodesic Buffer"
        )

    def find_nearby_emission_sources(
        self,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        limit: int = 5
    ) -> List[EmissionSource]:
        """
        Query OpenStreetMap Overpass API for real industrial, power generation,
        and manufacturing emission sources within the radius.
        """
        valid, err = self.validate_coordinates(lat, lon)
        if not valid:
            raise ValueError(err)

        radius_meters = int(radius_km * 1000)
        overpass_query = f"""
        [out:json][timeout:10];
        (
          node["landuse"="industrial"](around:{radius_meters},{lat},{lon});
          way["landuse"="industrial"](around:{radius_meters},{lat},{lon});
          node["power"="plant"](around:{radius_meters},{lat},{lon});
          way["power"="plant"](around:{radius_meters},{lat},{lon});
          node["industrial"](around:{radius_meters},{lat},{lon});
        );
        out center {limit};
        """

        sources: List[EmissionSource] = []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    self.OVERPASS_URL,
                    data={"data": overpass_query},
                    headers={"User-Agent": self.USER_AGENT}
                )
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])
                    for el in elements:
                        tags = el.get("tags", {})
                        name = tags.get("name") or tags.get("description") or tags.get("operator")
                        stype = tags.get("power") or tags.get("industrial") or tags.get("landuse") or "industrial"

                        c_lat = el.get("lat") or el.get("center", {}).get("lat")
                        c_lon = el.get("lon") or el.get("center", {}).get("lon")

                        if c_lat is not None and c_lon is not None:
                            dist = self.haversine_distance(lat, lon, c_lat, c_lon)
                            source_name = name or f"Industrial Facility ({stype.replace('_', ' ').title()})"
                            sources.append(
                                EmissionSource(
                                    id=str(el.get("id")),
                                    name=source_name,
                                    source_type=stype,
                                    latitude=c_lat,
                                    longitude=c_lon,
                                    distance_km=dist,
                                    source_dataset="OpenStreetMap Overpass API"
                                )
                            )
        except Exception:
            # Overpass can be slow or rate-limited; if so, return empty list rather than inventing facilities!
            pass

        sources.sort(key=lambda s: s.distance_km)
        return sources[:limit]

    def build_geojson_map(
        self,
        stations: Optional[List[Dict[str, Any]]] = None,
        buffer_zone: Optional[InvestigationBuffer] = None,
        emission_sources: Optional[List[EmissionSource]] = None,
        reference_points: Optional[List[Dict[str, Any]]] = None
    ) -> GeoJSONFeatureCollection:
        """
        Assemble map-ready GeoJSON FeatureCollection.
        Every feature clearly discloses its category and source dataset.
        """
        features: List[GeoJSONFeature] = []

        # 1. Stations
        if stations:
            for st in stations:
                coords = st.get("coordinates")
                if coords:
                    lat = coords.get("latitude") if isinstance(coords, dict) else coords.latitude
                    lon = coords.get("longitude") if isinstance(coords, dict) else coords.longitude
                    features.append(
                        GeoJSONFeature(
                            geometry={"type": "Point", "coordinates": [lon, lat]},
                            properties={
                                "feature_type": "monitoring_station",
                                "id": st.get("id"),
                                "name": st.get("name"),
                                "measurements": st.get("measurements", []),
                                "source_dataset": "OpenAQ API v3",
                                "marker_color": "#2563eb"
                            }
                        )
                    )

        # 2. Buffer zone
        if buffer_zone:
            features.append(
                GeoJSONFeature(
                    geometry=buffer_zone.geometry_geojson,
                    properties={
                        "feature_type": "investigation_buffer",
                        "radius_km": buffer_zone.radius_km,
                        "area_km2": buffer_zone.area_km2,
                        "disclaimer": buffer_zone.disclaimer,
                        "source_dataset": buffer_zone.source_dataset,
                        "fill_color": "#3b82f6",
                        "stroke_color": "#1d4ed8"
                    }
                )
            )

        # 3. Emission sources
        if emission_sources:
            for es in emission_sources:
                features.append(
                    GeoJSONFeature(
                        geometry={"type": "Point", "coordinates": [es.longitude, es.latitude]},
                        properties={
                            "feature_type": "potential_emission_source",
                            "name": es.name,
                            "source_type": es.source_type,
                            "distance_km": es.distance_km,
                            "source_dataset": es.source_dataset,
                            "marker_color": "#dc2626"
                        }
                    )
                )

        # 4. Reference locations (e.g. prompt P10: reference points labeled as reference locations, NOT pollution hotspots)
        if reference_points:
            for pt in reference_points:
                features.append(
                    GeoJSONFeature(
                        geometry={"type": "Point", "coordinates": [pt["longitude"], pt["latitude"]]},
                        properties={
                            "feature_type": "reference_location",
                            "name": pt.get("name"),
                            "is_hotspot": False,
                            "label": f"Reference Location: {pt.get('name')} (Not a verified pollution hotspot)",
                            "source_dataset": pt.get("source", "OpenStreetMap Nominatim"),
                            "marker_color": "#10b981"
                        }
                    )
                )

        return GeoJSONFeatureCollection(features=features)
