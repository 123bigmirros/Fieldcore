import os

import requests
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection


class HTTPMCPTool(BaseTool):
    """Proxy tool that invokes MCP tools via HTTP API."""

    server_url: str = ""
    tool_name: str = ""

    async def execute(self, **kwargs) -> ToolResult:
        """Execute an MCP tool via HTTP API."""
        try:
            from app.logger import logger

            logger.info(
                f"HTTPMCPTool.execute '{self.tool_name}' with caller_id: "
                f"'{kwargs.get('caller_id', 'NOT_SET')}'"
            )

            # Use longer timeout for human command tools (they dispatch to Machine Agents)
            tool_timeout = 180 if "human_send" in self.tool_name else 30

            response = requests.post(
                f"{self.server_url}/api/v1/mcp/tools/{self.tool_name}/invoke",
                json={"parameters": kwargs},
                timeout=tool_timeout,
            )

            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {}) if result.get("success") else {}
                return ToolResult(output=data.get("result", ""))
            else:
                error_msg = f"HTTP error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return ToolResult(error=error_msg)

        except Exception as e:
            error_msg = f"MCP tool invocation failed: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)


class HTTPMCPClients(ToolCollection):
    """Tool collection that connects to an MCP server via HTTP API."""

    server_url: str = ""
    description: str = "HTTP MCP client tools"
    sessions: dict = {}

    def __init__(self, server_url: str = os.getenv("MCP_SERVER_URL", "http://localhost:8003")):
        super().__init__()
        self.server_url = server_url
        self.name = "http_mcp"
        self.sessions = {"http_api": None}
    async def initialize(self) -> None:
        """Initialize the HTTP MCP client by fetching the tool list."""
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/mcp/tools", timeout=10
            )

            if response.status_code == 200:
                resp_json = response.json()
                # Unwrap unified envelope: data.tools
                data = resp_json.get("data", resp_json)
                tools_list = data.get("tools", [])

                for tool_info in tools_list:
                    tool_name = tool_info["name"]
                    description = tool_info.get("description", "")
                    parameters = tool_info.get("parameters", {})

                    http_tool = HTTPMCPTool(
                        name=f"mcp_python_{tool_name}",
                        description=description,
                        parameters=parameters,
                        server_url=self.server_url,
                        tool_name=tool_name,
                    )

                    self.tool_map[http_tool.name] = http_tool

                self.tools = tuple(self.tool_map.values())

                logger.info(
                    f"HTTP MCP client initialized, available tools: {list(self.tool_map.keys())}"
                )
            else:
                logger.error(f"Failed to fetch tool list: {response.status_code}")

        except Exception as e:
            logger.error(f"HTTP MCP client initialization failed: {e}")

    async def call_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Invoke a specific tool."""
        full_tool_name = f"mcp_python_{tool_name}"
        if full_tool_name not in self.tool_map:
            return ToolResult(error=f"Tool {tool_name} not found")

        tool = self.tool_map[full_tool_name]
        return await tool.execute(**kwargs)

    async def list_tools(self):
        """Return tool list, compatible with MCP client interface."""
        from mcp.types import ListToolsResult, Tool

        tools = []
        for tool_name, tool_obj in self.tool_map.items():
            original_name = tool_name.replace("mcp_python_", "")
            tools.append(
                Tool(
                    name=original_name,
                    description=tool_obj.description,
                    inputSchema=tool_obj.parameters,
                )
            )

        return ListToolsResult(tools=tools)

    async def disconnect(self):
        """Disconnect (no-op for HTTP client)."""
        logger.info("HTTP MCP client disconnected")
