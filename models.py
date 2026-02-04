"""
Pydantic models for MCP (Model Context Protocol) based on the specification schema.

This file defines the core data models used for JSON-RPC communication and MCP features,
translated from the JSON Schema at https://modelcontextprotocol.io/specification/2025-11-25/schema.json
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union, Literal


# Base JSON-RPC types
RequestId = Union[str, int]


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message."""
    jsonrpc: str = Field("2.0")
    id: RequestId
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response message."""
    jsonrpc: str = Field("2.0")
    id: RequestId
    result: Any


class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification message."""
    jsonrpc: str = Field("2.0")
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error response."""
    jsonrpc: str = Field("2.0")
    id: Optional[RequestId] = None
    error: Dict[str, Any]  # Contains 'code', 'message', 'data'


# MCP-specific models

class Implementation(BaseModel):
    """Information about the implementation."""
    name: str
    version: str


class ClientCapabilities(BaseModel):
    """Capabilities declared by the client."""
    experimental: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


class InitializeRequestParams(BaseModel):
    """Parameters for the initialize request."""
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation


class ServerCapabilities(BaseModel):
    """Capabilities advertised by the server."""
    experimental: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


class InitializeResult(BaseModel):
    """Result of the initialize request."""
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: Optional[str] = None


# Content blocks for messages

class TextContent(BaseModel):
    """Text content block."""
    type: Literal["text"]
    text: str


class ImageContent(BaseModel):
    """Image content block."""
    type: Literal["image"]
    data: str  # Base64-encoded image data
    mimeType: str


class ToolCallContent(BaseModel):
    """Tool call content block."""
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultContent(BaseModel):
    """Tool result content block."""
    type: Literal["tool_result"]
    toolUseId: str
    content: List[Union["TextContent", "ImageContent"]]  # Recursive reference
    isError: Optional[bool] = None


ContentBlock = Union[TextContent, ImageContent, ToolCallContent, ToolResultContent]


# Role for messages
Role = Literal["user", "assistant"]


class SamplingMessage(BaseModel):
    """A message in sampling requests."""
    role: Role
    content: List[ContentBlock]


class ModelPreferences(BaseModel):
    """Preferences for model selection in sampling."""
    hints: Optional[List[Dict[str, Any]]] = None
    costPriority: Optional[float] = None
    speedPriority: Optional[float] = None
    intelligencePriority: Optional[float] = None


class CreateMessageRequestParams(BaseModel):
    """Parameters for the sampling/createMessage request."""
    messages: List[SamplingMessage]
    modelPreferences: Optional[ModelPreferences] = None
    systemPrompt: Optional[str] = None
    includeContext: Optional[Literal["none", "thisServer", "allServers"]] = None
    temperature: Optional[float] = None
    maxTokens: int
    stopSequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateMessageResult(BaseModel):
    """Result of the sampling/createMessage request."""
    role: Role
    content: ContentBlock
    model: str
    stopReason: Optional[Literal["endTurn", "stopSequence", "maxTokens"]] = None


# Aliases for consistency with other request/response models
CreateMessageRequest = CreateMessageRequestParams
CreateMessageResponse = CreateMessageResult


# Annotations for content
class Annotations(BaseModel):
    """Optional annotations for content."""
    audience: Optional[List[Role]] = None
    priority: Optional[float] = None


# Resource model
class Resource(BaseModel):
    """A resource available on the server."""
    uri: str
    mimeType: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    annotations: Optional[Annotations] = None


# Tool model
class Tool(BaseModel):
    """A tool available on the server."""
    name: str
    description: Optional[str] = None
    inputSchema: Dict[str, Any]  # JSON Schema for tool input


# Prompt models
class PromptMessage(BaseModel):
    """A message in a prompt."""
    role: Role
    content: List[ContentBlock]


class Prompt(BaseModel):
    """A prompt template."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None
    messages: Optional[List[PromptMessage]] = None


class GetPromptRequest(BaseModel):
    """Parameters for the prompts/get request."""
    name: str
    arguments: Optional[Dict[str, Any]] = None


# Aliases for consistency
GetPromptResponse = Prompt


# Task state enum
TaskState = Literal["pending", "running", "completed", "cancelled", "failed"]

# Task model (experimental)
class Task(BaseModel):
    """A task representing asynchronous work."""
    id: str
    name: str
    description: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    status: TaskState
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# Request and Response models for handlers

# Initialize
InitializeRequest = InitializeRequestParams
InitializeResponse = InitializeResult

# Ping
class PingRequest(BaseModel):
    """Parameters for the ping request (empty)."""
    pass

class PingResponse(BaseModel):
    """Response for the ping request."""
    pong: bool = True

# Resources
class ListResourcesRequest(BaseModel):
    """Parameters for resources/list request."""
    pass

class ListResourcesResponse(BaseModel):
    """Response for resources/list request."""
    resources: List[Resource]

class ReadResourceRequest(BaseModel):
    """Parameters for resources/read request."""
    uri: str

class ReadResourceResponse(BaseModel):
    """Response for resources/read request."""
    contents: List[ContentBlock]

# Tools
class ListToolsRequest(BaseModel):
    """Parameters for tools/list request."""
    pass

class ListToolsResponse(BaseModel):
    """Response for tools/list request."""
    tools: List[Tool]

class CallToolRequest(BaseModel):
    """Parameters for tools/call request."""
    name: str
    arguments: Optional[Dict[str, Any]] = None

class CallToolResponse(BaseModel):
    """Response for tools/call request."""
    content: List[ContentBlock]

# Prompts
class ListPromptsRequest(BaseModel):
    """Parameters for prompts/list request."""
    pass

class ListPromptsResponse(BaseModel):
    """Response for prompts/list request."""
    prompts: List[Prompt]

class GetPromptResponse(BaseModel):
    """Response for prompts/get request."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None
    messages: List[PromptMessage]

# Sampling
CreateMessageResponse = CreateMessageResult

# Tasks
class ListTasksRequest(BaseModel):
    """Parameters for tasks/list request."""
    pass

class ListTasksResponse(BaseModel):
    """Response for tasks/list request."""
    tasks: List[Task]

class GetTaskRequest(BaseModel):
    """Parameters for tasks/get request."""
    id: str

class GetTaskResponse(BaseModel):
    """Response for tasks/get request."""
    task: Task

class CancelTaskRequest(BaseModel):
    """Parameters for tasks/cancel request."""
    id: str
    reason: Optional[str] = None

class CancelTaskResponse(BaseModel):
    """Response for tasks/cancel request."""
    task: Task

# Resources subscribe
class SubscribeRequest(BaseModel):
    """Parameters for resources/subscribe request."""
    uri: str

class SubscribeResponse(BaseModel):
    """Response for resources/subscribe request."""
    pass