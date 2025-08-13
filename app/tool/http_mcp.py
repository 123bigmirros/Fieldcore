import requests
import json
from typing import Dict, List, Optional, Any
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection


class HTTPMCPTool(BaseTool):
    """通过HTTP API调用MCP服务器的工具代理"""

    server_url: str = ""
    tool_name: str = ""

    async def execute(self, **kwargs) -> ToolResult:
        """通过HTTP API执行MCP工具"""
        try:
            # 添加调试日志
            from app.logger import logger
            logger.info(f"🌐 HTTPMCPTool.execute '{self.tool_name}' with caller_id: '{kwargs.get('caller_id', 'NOT_SET')}'")

            # 准备请求数据
            data = {
                'tool_name': self.tool_name,
                'parameters': kwargs
            }

            # 发送HTTP请求
            response = requests.post(
                f"{self.server_url}/mcp/call_tool",
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return ToolResult(output=result.get('result', ''))
            else:
                error_msg = f"HTTP错误 {response.status_code}: {response.text}"
                logger.error(error_msg)
                return ToolResult(error=error_msg)

        except Exception as e:
            error_msg = f"调用MCP工具失败: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)


class HTTPMCPClients(ToolCollection):
    """通过HTTP API连接MCP服务器的工具集合"""

    server_url: str = ""
    description: str = "HTTP MCP客户端工具"
    sessions: dict = {}  # 添加sessions属性以保持兼容性

    def __init__(self, server_url: str = "http://localhost:8003"):
        super().__init__()
        self.server_url = server_url
        self.name = "http_mcp"
        self.sessions = {"http_api": None}  # 添加一个虚拟session

    async def initialize(self) -> None:
        """初始化HTTP MCP客户端，获取可用工具列表"""
        try:
            # 获取工具列表
            response = requests.get(f"{self.server_url}/mcp/list_tools", timeout=10)

            if response.status_code == 200:
                tools_data = response.json()

                # 为每个工具创建代理
                for tool_info in tools_data.get('tools', []):
                    tool_name = tool_info['name']
                    description = tool_info.get('description', '')
                    parameters = tool_info.get('parameters', {})

                    # 创建工具代理 - 使用mcp_python_前缀以保持兼容性
                    http_tool = HTTPMCPTool(
                        name=f"mcp_python_{tool_name}",
                        description=description,
                        parameters=parameters,
                        server_url=self.server_url,
                        tool_name=tool_name
                    )

                    self.tool_map[http_tool.name] = http_tool

                # 更新工具列表
                self.tools = tuple(self.tool_map.values())

                logger.info(f"HTTP MCP客户端初始化成功，可用工具: {list(self.tool_map.keys())}")
            else:
                logger.error(f"获取工具列表失败: {response.status_code}")

        except Exception as e:
            logger.error(f"HTTP MCP客户端初始化失败: {e}")

    async def call_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """调用指定的工具"""
        # 查找工具
        full_tool_name = f"mcp_python_{tool_name}"
        if full_tool_name not in self.tool_map:
            return ToolResult(error=f"工具 {tool_name} 不存在")

        # 执行工具
        tool = self.tool_map[full_tool_name]
        return await tool.execute(**kwargs)

    async def list_tools(self):
        """返回工具列表，保持与MCP客户端的兼容性"""
        from mcp.types import ListToolsResult, Tool

        tools = []
        for tool_name, tool_obj in self.tool_map.items():
            # 移除前缀
            original_name = tool_name.replace("mcp_python_", "")
            tools.append(Tool(
                name=original_name,
                description=tool_obj.description,
                inputSchema=tool_obj.parameters
            ))

        return ListToolsResult(tools=tools)

    async def disconnect(self):
        """断开连接，保持与MCP客户端的兼容性"""
        # HTTP客户端不需要特殊的断开连接逻辑
        logger.info("HTTP MCP客户端断开连接")
