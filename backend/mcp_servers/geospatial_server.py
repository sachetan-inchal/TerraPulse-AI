import json
from typing import Optional
from mcp.server.mcpserver import MCPServer
from services.geospatial_service import GeospatialService

geospatial_mcp = MCPServer("TerraPulse Geospatial Server")
_geo_service = GeospatialService()


@geospatial_mcp.tool()
def geocode_location(
    location_name: Optional[str] = None,
    location: Optional[str] = None,
    query: Optional[str] = None,
    place: Optional[str] = None,
    address: Optional[str] = None,
    city: Optional[str] = None
) -> str:
    """
    Geocode a human-readable city or place name into verified geographic coordinates (latitude, longitude)
    using OpenStreetMap Nominatim. Rejects invalid coordinates.
    """
    target = location_name or location or query or place or address or city
    if not target or not str(target).strip():
        return json.dumps({"error": "Missing location. Please specify 'location_name' or 'location'."})
    target = str(target).strip()
    try:
        loc = _geo_service.geocode(target)
        return json.dumps(loc.model_dump(), default=str)
    except Exception as e:
        return json.dumps({"error": f"Geocoding failed for '{target}': {str(e)}"})


@geospatial_mcp.tool()
def reverse_geocode_coordinates(latitude: float, longitude: float) -> str:
    """Reverse geocode latitude and longitude into verified human-readable place description."""
    try:
        desc = _geo_service.reverse_geocode(latitude, longitude)
        return json.dumps({"latitude": latitude, "longitude": longitude, "display_name": desc})
    except Exception as e:
        return json.dumps({"error": f"Reverse geocoding failed: {str(e)}"})


@geospatial_mcp.tool()
def create_investigation_buffer(latitude: float, longitude: float, radius_km: float = 2.0) -> str:
    """
    Create a circular investigation area buffer polygon around coordinates using Shapely.
    Calculates approximate area in km². Includes scientific disclaimer distinguishing
    investigation buffer from an atmospheric dispersion plume.
    """
    try:
        buf = _geo_service.create_investigation_buffer(latitude, longitude, radius_km=radius_km)
        return json.dumps(buf.model_dump(), default=str)
    except Exception as e:
        return json.dumps({"error": f"Buffer creation failed: {str(e)}"})


@geospatial_mcp.tool()
def find_nearby_emission_sources(latitude: float, longitude: float, radius_km: float = 10.0, limit: int = 5) -> str:
    """
    Locate real verified nearby industrial and point-source emission facilities from OpenStreetMap Overpass.
    Calculates distances from target coordinates. Never invents factories.
    """
    try:
        sources = _geo_service.find_nearby_emission_sources(latitude, longitude, radius_km=radius_km, limit=limit)
        return json.dumps([s.model_dump() for s in sources], default=str)
    except Exception as e:
        return json.dumps({"error": f"Emission source search failed: {str(e)}"})


if __name__ == "__main__":
    geospatial_mcp.run()

