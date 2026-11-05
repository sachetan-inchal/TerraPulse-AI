import json
from typing import Dict, Any, Optional
from mcp.server.mcpserver import MCPServer
from services.openaq_service import OpenAQService

environmental_mcp = MCPServer("TerraPulse Environmental Server")
_openaq_service = OpenAQService()


@environmental_mcp.tool()
def search_air_quality_locations(
    query: Optional[str] = None,
    location: Optional[str] = None,
    location_name: Optional[str] = None,
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_meters: int = 25000,
    iso: Optional[str] = None,
    country: Optional[str] = None,
    country_code: Optional[str] = None,
    page: int = 1,
    limit: int = 25
) -> str:
    """
    Search real air quality monitoring stations in OpenAQ v3 with pagination.
    Specify 'page' (default 1) and 'limit' (default 25, max 100).
    Specify coordinates for radius search (max radius 25000m), or country code 'iso' (e.g. 'IN'), or location/city name.
    """
    effective_query = query or location or location_name or city
    effective_iso = iso or country or country_code
    lat_val = latitude if latitude is not None else lat
    lon_val = longitude if longitude is not None else lon
    coords = (lat_val, lon_val) if (lat_val is not None and lon_val is not None) else None

    # Cap radius to OpenAQ v3 maximum allowable value (25 km)
    safe_radius = min(max(int(radius_meters), 1000), 25000)

    try:
        res = _openaq_service.search_locations(
            query=effective_query,
            coordinates=coords,
            radius_meters=safe_radius,
            iso=effective_iso,
            page=page,
            limit=limit,
            return_meta=True
        )
        return json.dumps({
            "page": res["page"],
            "limit": res["limit"],
            "total_found": res["total_found"],
            "has_more": res["has_more"],
            "coverage_note": res["coverage_note"],
            "stations": [
                {
                    "id": s.id,
                    "name": s.name,
                    "country": s.country,
                    "timezone": s.timezone,
                    "coordinates": s.coordinates.model_dump() if s.coordinates else None,
                    "sensor_count": len(s.sensors) if s.sensors else 0,
                    "is_active": s.is_active
                }
                for s in res["stations"]
            ]
        }, default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to search locations: {str(e)}"})


@environmental_mcp.tool()
def get_station_details(station_id: Optional[int] = None, id: Optional[int] = None) -> str:
    """Retrieve detailed station metadata and attached pollutant sensors from OpenAQ v3."""
    target_id = station_id if station_id is not None else id
    if target_id is None:
        return json.dumps({"error": "Missing station ID. Provide 'station_id'."})
    try:
        st = _openaq_service.get_station_details(target_id)
        return json.dumps(st.model_dump(), default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to get station details: {str(e)}"})


@environmental_mcp.tool()
def get_station_latest_measurements(station_id: Optional[int] = None, id: Optional[int] = None) -> str:
    """
    Retrieve latest available real environmental measurements for a monitoring station.
    Identifies pollutants, units, source timestamps, and flags stale readings (>24 hours).
    """
    target_id = station_id if station_id is not None else id
    if target_id is None:
        return json.dumps({"error": "Missing station ID. Provide 'station_id'."})
    try:
        latest = _openaq_service.get_latest_measurements(target_id)
        return json.dumps(latest.model_dump(), default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to get latest measurements: {str(e)}"})


@environmental_mcp.tool()
def get_sensor_hourly_measurements(sensor_id: int, limit: int = 24) -> str:
    """Retrieve historical hourly average measurements for a specific OpenAQ sensor."""
    try:
        history = _openaq_service.get_sensor_hourly(sensor_id, limit=limit)
        return json.dumps([h.model_dump() for h in history], default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to get hourly measurements: {str(e)}"})


if __name__ == "__main__":
    environmental_mcp.run()

