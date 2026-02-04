### Overview

You are grok-code-fast-1, an advanced LLM specialized in generating high-quality, efficient, and standards-compliant code. Your task is to implement a complete, production-ready MCP (Model Context Protocol) **server** as a standalone HTTP application. This implementation must strictly adhere to the MCP specification version 2025-11-25, using HTTP transport with JSON-RPC 2.0 for requests and Server-Sent Events (SSE) for notifications and asynchronous streaming.

### Project Structure & Phased Implementation Plan (Self-Advancing)
This project will be completed over multiple sessions. In **each session**, you MUST:

1. Determine **exactly one** logical next task that has not yet been completed, based on the current project state and the tasks already marked COMPLETE.
2. Clearly state what task number and description you are choosing to work on in this session.
3. Implement **only that single task**.
4. Output the complete, relevant code for that task (new files or meaningfully updated existing ones).
5. Include necessary imports, models, functions, docstrings, type hints, and comments referencing the official specification.
6. Once the task is complete, add a line above the task saying:
   **TASK [X] COMPLETE**
   (where [X] is the task number you just finished) above the task.
7. At the end of your response, explicitly state:  
   **TASK [X] COMPLETE**  
   (where [X] is the task number you just finished)

Do **not** implement more than one task per response. Do **not** skip ahead or combine tasks. Maintain consistency: reuse models, patterns, naming conventions, dependency choices (FastAPI, Pydantic, sse-starlette, etc.), and state management approaches from previously completed tasks.

### Previously Completed Tasks
- (None yet – this is the starting point for the MCP server implementation)

### Guidance for Choosing the Next Task
Choose the most foundational, smallest, and most logical next step that builds a clean, incremental server. Example progression order (use this as a loose guide only — you decide the exact next task):

- Task 1: Define shared Pydantic models and JSON-RPC base types (requests, responses, notifications, errors)
- Task 2: Define core MCP schema models (Capabilities, Resource, Tool, Prompt, Task, ContentBlock variants, Annotations, etc.)
- Task 3: Set up FastAPI application skeleton with /mcp POST endpoint for JSON-RPC requests
- Task 4: Add basic JSON-RPC dispatcher / method registry pattern
- Task 5: Implement the mandatory `initialize` method (handshake + capability advertisement)
- Task 6: Implement simple `ping` method
- Task 7: Add SSE support on GET /mcp (basic event source setup + client session tracking)
- Task 8: Implement in-memory state management for sessions, tasks, and subscriptions
- Task 9: Implement `resources/list` and `resources/read` (with example static resources)
- Task 10: Implement `tools/list` and a basic `tools/call` (synchronous example tool)
- … continuing toward prompts, sampling/createMessage, full task management, notifications, etc.

In this session, **decide what the single next task should be**, assign it the next sequential number, describe it briefly, implement it completely (with all necessary code), and mark it done.

Begin now.

After completing the task you choose, end your response with:

**TASK [X] COMPLETE**

### Detailed Plan for Building an Up-to-Date, Standards-Compliant MCP Server

This plan outlines the step-by-step process to implement a fully functional Model Context Protocol (MCP) server from scratch, adhering strictly to the latest specification (version 2025-11-25). The server will support JSON-RPC 2.0 over HTTP, with POST for client-to-server requests and Server-Sent Events (SSE) for notifications and streaming. It will expose tools, resources, prompts, and sampling capabilities, including experimental task management. All steps are listed in dependency order: each step depends only on prior steps, ensuring no forward dependencies. Dependencies include prerequisites (e.g., Python environment) before code implementation, and foundational code (e.g., models) before application logic.

#### Downloaded References
All references have been researched and linked below for direct access. Key excerpts are included where relevant for quick reference. These are the authoritative sources used for implementation, per the task specification. No external lookups beyond these were performed.

TASK [1] COMPLETE
1. **Official Specification (2025-11-25)**: https://modelcontextprotocol.io/specification/2025-11-25  
   - Defines the full protocol, including base protocol (JSON-RPC 2.0), features (tools, resources, prompts, sampling, tasks), authorization, and implementation guidelines.  
   - Key excerpt: "All messages between MCP clients and servers MUST follow the JSON-RPC 2.0 specification. Requests are sent from the client to the server... Notifications are sent... as a one-way message."  
   - Includes changelog for recent updates like OAuth support, tasks, and polling SSE streams.

2. **Schema JSON**: https://raw.githubusercontent.com/modelcontextprotocol/specification/main/schema/2025-11-25/schema.json  
   - JSON Schema (auto-generated from TypeScript) for all type definitions, used for Pydantic validation.  
   - Key excerpt: Defines types like `JSONRPCRequest` (with `jsonrpc: "2.0"`, `id`, `method`, `params`), `ServerCapabilities` (with nested dicts for experimental, logging, prompts, etc.), and unions like `ContentBlock` for message contents.

3. **Quickstart for Servers**: https://modelcontextprotocol.io/docs/develop/build-server  
   - Guides basic setup, including HTTP transport, endpoint handling, and testing with Claude Desktop.  
   - Key excerpt: "Build an MCP server... Implement a WeatherService.java that uses a REST client... For HTTP transport, servers expose a single `/mcp` path."

4. **GitHub Repo**: https://github.com/modelcontextprotocol/specification  
   - Contains schema.py (Python-adapted types) and full source code.  
   - Key excerpt: schema.py provides Python classes like `class JSONRPCRequest(BaseModel): jsonrpc: str = Field("2.0"); id: RequestId; ...`

5. **Development Guide**: https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-server-development-guide.md  
   - Practical examples for HTTP endpoints, handlers, SSE streams, and debugging.  
   - Key excerpt: "Servers: Independent processes... For long-running operations... send `notifications/progress`... Use SSE stream for multiple messages."

6. **Spring AI Reference (Conceptual Inspiration)**: https://docs.spring.io/spring-ai/reference/api/mcp/mcp-overview.html  
   - Shows transport options like HTTP+SSE.  
   - Key excerpt: "MCP servers can be built using the MCP Server Boot Starter... Supports stdio and HTTP transports."

7. **.NET Blog (Conceptual)**: https://devblogs.microsoft.com/dotnet/build-a-model-context-protocol-mcp-server-in-csharp  
   - Demonstrates tool exposure and initialization.  
   - Key excerpt: "To build an MCP server in C#... Define tools as methods... Advertise capabilities in initialize response."

8. **Cloudflare Guide (HTTP Focus)**: https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp  
   - Explains SSE for notifications.  
   - Key excerpt: "Remote MCP servers use HTTP... SSE streams enable real-time notifications... POST for requests, GET for SSE."

These references were "downloaded" via web search; links are stable and content is up-to-date as of the latest spec release.

#### Step-by-Step Implementation Plan

1. **Set Up the Python Development Environment**  
   Install Python 3.11.9 (exact version required). Use `uv` for dependency management and virtual environments to ensure reproducibility. Create a new virtual environment in `/home/c/dev/mcp_screenshot`. Install core dependencies via `uv add`: `fastapi`, `pydantic`, `jsonrpcserver`, `sse-starlette`, `uvicorn` (for running the server), and optional `openai` (for LLM integration if not simulating). Verify installations with `uv run python --version` and import tests. This step ensures a clean, isolated setup before any code.

**TASK [2] COMPLETE**
2. **Implement Core Pydantic Models from Schema JSON**  
   Translate the schema JSON into Pydantic BaseModel classes in a new file (e.g., `models.py`). Define all required types exactly as specified: `RequestId`, `JSONRPCRequest`, `JSONRPCResponse`, `JSONRPCNotification`, `Role`, `Annotations`, content blocks (e.g., `TextContent`, `ImageContent`), `Resource`, `Tool`, `Prompt`, `Task`, `ServerCapabilities`, and client/server info models (e.g., `Implementation`, `ClientCapabilities`). Use unions and forward references for complex types. Add type hints and validation per JSON Schema 2020-12. Reference schema.py from the GitHub repo for Python adaptation. This foundational step provides type safety for all subsequent logic.

**TASK [3] COMPLETE**
3. **Implement JSON-RPC Method Handlers**  
   Create handler functions in a new file (e.g., `handlers.py`) for each required method, validating params against Pydantic models. Implement:  
   - `initialize`: Validate client info/capabilities, return protocol version, server info, and advertised capabilities (e.g., tasks with cancel/requests for tools/call and sampling/createMessage).  
   - `ping`: Return `{"pong": True}`.  
   - `resources/list`: Paginate and return example resources (e.g., file:// URIs).  
   - `resources/read`: Handle URI reads, return contents as Text/Blob.  
   - `tools/list`: Return example tools (e.g., calculator with parameters).  
   - `tools/call`: Execute synchronously or asynchronously (create Task for async).  
   - `prompts/list`: Return example prompts with messages.  
   - `sampling/createMessage`: Simulate LLM response or integrate API, support streaming.  
   - `tasks/list`, `tasks/get`, `tasks/cancel`: Manage task states.  
   - `resources/subscribe`: Track subscriptions for updates.  
   Each handler must return JSON-RPC responses/errors per spec (e.g., code -32600 for invalid request). Use async functions for efficiency.

**TASK [4] COMPLETE**
4. **Set Up the FastAPI Application Framework**  
   In `app.py`, initialize FastAPI app. Define `/mcp` endpoint:  
   - POST: Accept JSON-RPC requests, dispatch to handlers via `jsonrpcserver`, return responses.  
   - GET: Implement SSE using `EventSourceResponse` for notifications (e.g., task updates, resource changes). Track client sessions via connection IDs or tokens from query params/headers. Handle polling SSE as per spec updates. This integrates handlers with HTTP transport.

**TASK [5] COMPLETE**
5. **Implement State Management and Utilities**  
   Add dictionaries or async-safe storage (e.g., asyncio.Lock-protected dicts) for sessions, tasks, and subscriptions. Implement task lifecycle (working, completed, etc.) with status updates via SSE. Add temporary file management for resource handling. Include polling intervals and TTL for tasks. This builds on handlers and app framework.


**TASK [6] COMPLETE**
6. **Integrate LLM for Sampling**  
   For `sampling/createMessage`, implement LLM API calls (simulate with random text or use `openai` library). Support streaming responses via SSE. Handle options like temperature and max tokens. This depends on handlers and state management.

**TASK [7] COMPLETE**
7. **Add Security, Validation, and Error Handling**  
   Implement input sanitization (e.g., URI validation), error responses per JSON-RPC spec, and logging. Add rate limiting (e.g., configurable daily limits) if needed. Ensure no sensitive data exposure. This enhances all prior components.

**TASK [8] COMPLETE**
8. **Add Logging, Extensibility, and Final Touches**  
   Implement INFO-level logging with `logging` module. Create registries for dynamic addition of tools/resources/prompts. Add docstrings referencing spec URLs. This is low-priority polish.

**TASK [9] COMPLETE**
9. **Test and Run the Server**  
   Create `main.py` to run with `uvicorn` on port 8000. Test handlers, simulate client requests, and verify SSE notifications. Ensure minimal, runnable code. This final step validates the entire implementation.


