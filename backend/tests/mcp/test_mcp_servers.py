import pytest
from mcp_servers.client_manager import MCPClientManager


@pytest.mark.asyncio
async def test_mcp_discovery_and_tool_call():
    mgr = MCPClientManager()
    await mgr.initialize()
    tools = await mgr.list_tools()
    tool_names = [t["name"] for t in tools]

    # Verify key tools discovered
    assert "search_air_quality_locations" in tool_names
    assert "search_scientific_publications" in tool_names
    assert "create_investigation_buffer" in tool_names

    # Verify tool execution
    res = await mgr.call_tool(
        "create_investigation_buffer",
        {"latitude": 12.97, "longitude": 77.59, "radius_km": 1.0}
    )
    assert res["success"] is True
    assert res["data"]["area_km2"] > 0

