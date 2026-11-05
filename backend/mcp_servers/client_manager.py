import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from mcp.server.mcpserver import MCPServer

from mcp_servers.environmental_server import environmental_mcp
from mcp_servers.research_server import research_mcp
from mcp_servers.geospatial_server import geospatial_mcp


class MCPClientManager:
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {
            "environmental": environmental_mcp,
            "research": research_mcp,
            "geospatial": geospatial_mcp
        }
        self._tool_to_server_map: Dict[str, str] = {}
        self._tool_schemas: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    async def initialize(self):
        """Discover tools and register schemas from all active MCP servers."""
        self._tool_to_server_map.clear()
        self._tool_schemas.clear()

        for server_name, server in self.servers.items():
            try:
                tools = await server.list_tools()
                for t in tools:
                    self._tool_to_server_map[t.name] = server_name
                    # Format tool schema compatible with ReAct agent / LLM
                    schema = {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema if hasattr(t, "inputSchema") else getattr(t, "input_schema", {}),
                        "server": server_name
                    }
                    self._tool_schemas[t.name] = schema
            except Exception as e:
                # Log server initialization failure
                pass
        self._initialized = True

    def get_registered_servers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "title": server.name,
                "status": "ONLINE"
            }
            for name, server in self.servers.items()
        ]

    async def list_tools(self) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()
        return list(self._tool_schemas.values())

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout_seconds: float = 25.0
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool via the responsible server with timeout,
        duration measurement, and error handling.
        """
        if not self._initialized:
            await self.initialize()

        server_name = self._tool_to_server_map.get(tool_name)
        if not server_name:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not registered on any connected MCP server.",
                "duration_ms": 0.0,
                "raw_result": None
            }

        server = self.servers[server_name]
        start_time = time.perf_counter()

        try:
            call_coro = server.call_tool(tool_name, arguments)
            result = await asyncio.wait_for(call_coro, timeout=timeout_seconds)

            dur_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

            # Extract content from CallToolResult
            raw_text = ""
            if hasattr(result, "content") and result.content:
                for block in result.content:
                    if hasattr(block, "text"):
                        raw_text += block.text
            elif hasattr(result, "structured_content"):
                raw_text = json.dumps(result.structured_content)

            # Try to parse as JSON if possible
            parsed_data = None
            try:
                parsed_data = json.loads(raw_text)
            except Exception:
                parsed_data = raw_text

            # Check if inner content is an error dict
            is_error = getattr(result, "is_error", False)
            if isinstance(parsed_data, dict) and "error" in parsed_data:
                is_error = True

            return {
                "success": not is_error,
                "tool_name": tool_name,
                "server": server_name,
                "arguments": arguments,
                "duration_ms": dur_ms,
                "raw_text": raw_text,
                "data": parsed_data,
                "error": parsed_data.get("error") if isinstance(parsed_data, dict) else (raw_text if is_error else None)
            }

        except asyncio.TimeoutError:
            dur_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return {
                "success": False,
                "tool_name": tool_name,
                "server": server_name,
                "arguments": arguments,
                "duration_ms": dur_ms,
                "error": f"Tool execution timed out after {timeout_seconds} seconds."
            }
        except Exception as e:
            dur_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return {
                "success": False,
                "tool_name": tool_name,
                "server": server_name,
                "arguments": arguments,
                "duration_ms": dur_ms,
                "error": f"MCP execution error: {str(e)}"
            }

