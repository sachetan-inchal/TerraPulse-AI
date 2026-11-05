from mcp.server.mcpserver import MCPServer
from services.openaq_service import OpenAQService

mcp = MCPServer("TerraPulse Environmental Server")
_openaq = OpenAQService()


@mcp.tool()
def get_air_quality(location: str) -> dict:
    """Get real air quality information for a location using OpenAQ v3 API."""
    try:
        stations = _openaq.search_locations(query=location, limit=1)
        if not stations:
            return {"error": f"No active monitoring stations found in OpenAQ for {location}"}

        station = stations[0]
        latest = _openaq.get_latest_measurements(station.id)
        return {
            "station_id": station.id,
            "station_name": station.name,
            "coordinates": station.coordinates.model_dump() if station.coordinates else None,
            "measurements": [m.model_dump() for m in latest.measurements],
            "notes": latest.notes,
            "source_dataset": "OpenAQ API v3"
        }
    except Exception as e:
        return {"error": f"Failed to retrieve air quality data: {str(e)}"}


if __name__ == "__main__":
    mcp.run()
