You are grok-code-fast-1, an advanced LLM specialized in generating high-quality, efficient, and standards-compliant code. Your task is to implement an MCP (Model Context Protocol) server based on the following detailed specification. This specification is derived from the latest official MCP standards as of February 2026, specifically version 2025-11-25. You must adhere strictly to this spec without deviations, assumptions, or additions unless explicitly allowed. Ignore any prior knowledge or lookups; use only the details provided here.

### Core Objectives
- Implement a fully functional MCP server that supports JSON-RPC 2.0 over HTTP (using POST for requests and Server-Sent Events (SSE) for notifications and streaming responses where applicable).
- The server must handle LLM integration: it should expose tools, resources, prompts, and support sampling for generating responses from an integrated LLM (e.g., via an API like Grok or OpenAI, but simulate if needed for testing).
- Support both synchronous and asynchronous operations, with task management for long-running requests.
- Ensure security: validate inputs, handle errors per spec, and avoid exposing sensitive data.
- Target language: Python 3.11.9, using libraries like FastAPI for HTTP handling, pydantic for type validation and models, jsonrpcserver for JSON-RPC protocol handling, and sse-starlette for SSE support.
- The server should be minimal but complete: include logging, capability negotiation, and extensibility points.
- For the LLM CLI integration: the server should allow the CLI to act as a client, sending requests like tools/call or sampling/createMessage.

### Key References and Up-to-Date Documentation
Use these as your sole sources for protocol details. Do not perform external lookups; embed relevant excerpts in your code comments.
- Official Specification: https://modelcontextprotocol.io/specification/2025-11-25 – This defines the authoritative requirements, based on the schema at https://github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.py (adapted for Python).
- Schema JSON: https://raw.githubusercontent.com/modelcontextprotocol/specification/main/schema/2025-11-25/schema.json – Use this for all type definitions and validation; implement with Pydantic.
- Quickstart for Servers: https://modelcontextprotocol.io/docs/develop/build-server – Guides on basic setup, including HTTP transport.
- GitHub Repo: https://github.com/modelcontextprotocol/specification – Contains schema.py for Python type hints.
- Development Guide: https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-server-development-guide.md – Practical examples for HTTP endpoints and handlers.
- Spring AI Reference (for conceptual inspiration, not implementation): https://docs.spring.io/spring-ai/reference/api/mcp/mcp-overview.html – Shows transport options like HTTP+SSE.
- .NET Blog (conceptual): https://devblogs.microsoft.com/dotnet/build-a-model-context-protocol-mcp-server-in-csharp – Demonstrates tool exposure and initialization.
- Cloudflare Guide (HTTP focus): https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp – Explains SSE for notifications.

### Protocol Overview (Targeted for Implementation)
MCP is JSON-RPC 2.0 based, transport-agnostic, but you must implement over HTTP:
- **Endpoint**: Single path `/mcp` handling POST (client -> server requests) and GET (server -> client SSE for notifications).
- **Messages**: All are JSON objects with `jsonrpc: "2.0"`, `id` (for requests/responses), `method`, `params`.
- **Notifications**: Sent via SSE (event: message, data: JSON string).
- **Errors**: Use JSON-RPC error responses with `code`, `message`, `data`.
- **Sessions**: Stateful; track client sessions via connection IDs or tokens.
- **Capabilities Negotiation**: Done in `initialize` response.

Extracted Key Schema Elements (Implement These Types Exactly):
```python
# From schema.py – Define these as Pydantic models in your code for validation.
from typing import Union, List, Dict, Optional, Literal
from pydantic import BaseModel, Field

RequestId = Union[str, int]

class JSONRPCRequest(BaseModel):
    jsonrpc: str = Field("2.0")
    id: RequestId
    method: str
    params: Optional[Dict] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = Field("2.0")
    id: RequestId
    result: Optional[Dict] = None
    error: Optional[Dict[str, Union[int, str, Dict]]] = None

class JSONRPCNotification(BaseModel):
    jsonrpc: str = Field("2.0")
    method: str
    params: Optional[Dict] = None

# Annotations (for resources, tools, etc.)
Role = Literal["user", "assistant", "system"]
class Annotations(BaseModel):
    audience: Optional[List[Role]] = None
    lastModified: Optional[str] = None
    priority: Optional[int] = None

# Content Blocks (for messages, tools)
# Define subtypes like TextContent, ImageContent, etc., as separate BaseModels per schema.
ContentBlock = Union["TextContent", "ImageContent", "AudioContent", "ToolCallContent", "ResourceLink"]  # Forward refs or use separate classes.

# Resources
class Resource(BaseModel):
    name: str
    title: Optional[str] = None
    uri: str
    mimeType: Optional[str] = None
    description: Optional[str] = None
    size: Optional[int] = None
    icons: Optional[List["Icon"]] = None  # Define Icon as BaseModel.
    annotations: Optional[Annotations] = None

# Tools
class Tool(BaseModel):  # Extend from a BaseMetadata if defined.
    description: str
    parameters: Dict  # JSONSchema dict per Draft 2020-12.
    returns: Optional[Dict] = None  # JSONSchema.

# Prompts
class Prompt(BaseModel):  # Extend from BaseMetadata.
    description: str
    messages: List["PromptMessage"]  # Define PromptMessage.
    arguments: Optional[List["PromptArgument"]] = None  # Define PromptArgument.

# Tasks
TaskStatus = Literal["working", "input_required", "completed", "failed", "cancelled"]
class Task(BaseModel):
    taskId: str
    status: TaskStatus
    statusMessage: Optional[str] = None
    createdAt: str
    lastUpdatedAt: str
    ttl: Optional[int] = None
    pollInterval: Optional[int] = None

# Capabilities (Server advertises these)
class ServerCapabilities(BaseModel):
    experimental: Optional[Dict[str, Dict]] = None
    logging: Optional[Dict] = None
    completions: Optional[Dict] = None
    prompts: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": False})
    resources: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"subscribe": False, "listChanged": False})
    tools: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": False})
    tasks: Optional[Dict[str, Dict]] = Field(default_factory=lambda: {
        "list": {},
        "cancel": {},
        "requests": {"tools": {"call": {}}, "sampling": {"createMessage": {}}}
    })
    # Add more per client capabilities.
```

### Required Methods to Implement (Server Handlers)
Implement handlers for these JSON-RPC methods. Validate params against Pydantic models. Return results or errors.
1. **initialize** (Required: Handshake)
   - Params: { clientInfo: Implementation; capabilities: ClientCapabilities; }  # Define these models.
   - Result: { protocolVersion: "2025-11-25"; capabilities: ServerCapabilities; serverInfo: { name: str; version: str; }; instructions: Optional[str]; }
   - Advertise: Support for tasks (with cancel and requests for tools/call, sampling/createMessage), resources (listChanged: True), tools (listChanged: True), prompts.

2. **ping** (Health check)
   - Params: Optional _meta.
   - Result: { pong: True; }

3. **resources/list** (List available resources)
   - Params: PaginatedRequestParams (cursor: Optional[str]; limit: Optional[int]).
   - Result: { resources: List[Resource]; nextCursor: Optional[str]; }
   - Implement: Return at least 2 example resources (e.g., file URIs like "file://example.txt").

4. **resources/read** (Read a resource)
   - Params: { uri: str; }
   - Result: { contents: List[ResourceContents]; }  # Define ResourceContents (Text or Blob).
   - Implement: Handle file:// URIs by reading local files; return base64 for blobs.

5. **tools/list** (List tools)
   - Params: PaginatedRequestParams.
   - Result: { tools: List[Tool]; nextCursor: Optional[str]; }
   - Implement: Provide at least 2 example tools (e.g., a calculator tool with parameters).

6. **tools/call** (Invoke a tool)
   - Params: { toolName: str; arguments: Dict; taskId: Optional[str]; }  # If taskId, make async.
   - Result: If sync: { result: Any; }; If async: { taskId: str; }
   - Implement: Simulate tool execution; for async, create Task and notify via SSE on status changes.

7. **prompts/list** (List prompts)
   - Params: PaginatedRequestParams.
   - Result: { prompts: List[Prompt]; nextCursor: Optional[str]; }
   - Implement: Return example prompts with messages.

8. **sampling/createMessage** (Generate LLM response)
   - Params: { messages: List[Message]; options: SamplingOptions; taskId: Optional[str]; }  # Define Message, SamplingOptions.
   - Result: If sync: { message: Message; }; If async: { taskId: str; }
   - Implement: Integrate with an LLM API (e.g., simulate with random text or use openai library if configured); stream via SSE if streaming option set.

9. **tasks/list** (List tasks)
   - Params: { filter: Optional[TaskFilter]; }  # Define TaskFilter.
   - Result: { tasks: List[Task]; }

10. **tasks/get** (Get task status)
    - Params: { taskId: str; }
    - Result: Task model.

11. **tasks/cancel** (Cancel task)
    - Params: { taskId: str; }
    - Result: { cancelled: bool; }

12. **resources/subscribe** (If capabilities support subscribe)
    - Params: { uri: str; }
    - Result: { subscriptionId: str; }
    - Implement: Notify via SSE on resource changes.

### Implementation Structure
- Use FastAPI app: from fastapi import FastAPI, Request, Response; from sse_starlette.sse import EventSourceResponse.
- JSON-RPC handling: Use jsonrpcserver library to dispatch methods.
- SSE: For GET /mcp, yield events based on client ID (from query param or header).
- Validation: Parse incoming JSON with Pydantic, validate against models.
- State Management: Use a dict or async-safe storage (e.g., asyncio.Lock protected dict) for sessions, tasks.
- Logging: Use logging module with INFO level.
- Startup: Run with uvicorn on port 8000.
- Error Handling: Catch exceptions, return JSON-RPC errors (e.g., code -32600 for invalid request).
- Extensibility: Define a registry for tools/resources/prompts to add dynamically.
- Testing: Include a simple main.py to run the server; simulate LLM with a mock function.

### Additional Directives
- Generate complete, runnable code: Include all imports, models, handlers, and app setup.
- Efficiency: Use async where possible (e.g., async def for endpoints).
- Security: Sanitize URIs, limit file access to a safe directory.
- Documentation: Add docstrings and comments referencing the spec URLs.
- No Extras: Do not add authentication unless specified; keep minimal.
