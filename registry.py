"""
Registry for dynamic registration of MCP tools, resources, and prompts.

This module provides classes to register and manage tools, resources, and prompts
dynamically, allowing for extensibility in the MCP server.

Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
"""

from typing import Dict, List, Callable, Any, Optional, Awaitable
from models import Tool, Resource, Prompt, CallToolResponse, ReadResourceResponse, GetPromptResponse, JSONRPCError


class ToolRegistry:
    """
    Registry for MCP tools.

    Allows dynamic registration of tools with their definitions and handlers.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], CallToolResponse]] = {}

    def register_tool(self, name: str, tool: Tool, handler: Callable[[Dict[str, Any]], Awaitable[CallToolResponse]]):
        """
        Register a tool with its definition and handler function.

        Args:
            name: Unique name for the tool
            tool: Tool model instance
            handler: Async function that takes arguments dict and returns CallToolResponse
        """
        self._tools[name] = tool
        self._handlers[name] = handler

    def get_tools(self) -> List[Tool]:
        """Get list of all registered tools."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a specific tool by name."""
        return self._tools.get(name)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResponse:
        """Call the handler for a tool."""
        handler = self._handlers.get(name)
        if handler is None:
            return CallToolResponse(
                content=[{"type": "text", "text": f"Tool '{name}' not found"}]
            )
        try:
            return await handler(arguments)
        except Exception as e:
            return CallToolResponse(
                content=[{"type": "text", "text": f"Error calling tool '{name}': {str(e)}"}]
            )


class ResourceRegistry:
    """
    Registry for MCP resources.

    Allows dynamic registration of resources with their handlers.
    """

    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._handlers: Dict[str, Callable[[str], ReadResourceResponse]] = {}

    def register_resource(self, uri: str, resource: Resource, handler: Callable[[str], Awaitable[ReadResourceResponse]]):
        """
        Register a resource with its definition and handler function.

        Args:
            uri: URI for the resource
            resource: Resource model instance
            handler: Function that takes URI and returns ReadResourceResponse
        """
        self._resources[uri] = resource
        self._handlers[uri] = handler

    def get_resources(self) -> List[Resource]:
        """Get list of all registered resources."""
        return list(self._resources.values())

    def get_resource(self, uri: str) -> Optional[Resource]:
        """Get a specific resource by URI."""
        return self._resources.get(uri)

    async def read_resource(self, uri: str) -> ReadResourceResponse:
        """Read the content of a resource."""
        handler = self._handlers.get(uri)
        if handler is None:
            return ReadResourceResponse(
                contents=[{"type": "text", "text": f"Resource '{uri}' not found"}]
            )
        try:
            return await handler(uri)
        except Exception as e:
            return ReadResourceResponse(
                contents=[{"type": "text", "text": f"Error reading resource '{uri}': {str(e)}"}]
            )


class PromptRegistry:
    """
    Registry for MCP prompts.

    Allows dynamic registration of prompts with their definitions and message generators.
    """

    def __init__(self):
        self._prompts: Dict[str, Prompt] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], GetPromptResponse]] = {}

    def register_prompt(self, name: str, prompt: Prompt, handler: Callable[[Dict[str, Any]], Awaitable[GetPromptResponse]]):
        """
        Register a prompt with its definition and handler function.

        Args:
            name: Unique name for the prompt
            prompt: Prompt model instance
            handler: Function that takes arguments dict and returns GetPromptResponse
        """
        self._prompts[name] = prompt
        self._handlers[name] = handler

    def get_prompts(self) -> List[Prompt]:
        """Get list of all registered prompts."""
        return list(self._prompts.values())

    def get_prompt(self, name: str) -> Optional[Prompt]:
        """Get a specific prompt by name."""
        return self._prompts.get(name)

    async def get_prompt_response(self, name: str, arguments: Dict[str, Any]) -> GetPromptResponse:
        """Get the prompt response with messages."""
        handler = self._handlers.get(name)
        if handler is None:
            return GetPromptResponse(
                name=name,
                description="Prompt not found",
                arguments=None,
                messages=[]
            )
        try:
            return await handler(arguments)
        except Exception as e:
            return GetPromptResponse(
                name=name,
                description=f"Error generating prompt: {str(e)}",
                arguments=None,
                messages=[]
            )


# Global registry instances
tool_registry = ToolRegistry()
resource_registry = ResourceRegistry()
prompt_registry = PromptRegistry()