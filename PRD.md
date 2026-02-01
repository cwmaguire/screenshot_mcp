# Product Requirements Document: MCP Screenshot Server

## Overview
This document outlines the requirements and implementation plan for an MCP (Model Context Protocol) server that enables Large Language Models (LLMs) to take screenshots of the GUI and receive them for analysis. The server will be implemented in Python using `uv` for dependency management, targeting Python 3.11.9 via pyenv. Screenshots will be taken using the `scrot` tool and stored temporarily in a system tmp directory for automatic cleanup.

## Purpose
- Provide LLMs with the ability to capture and view GUI screenshots to understand visual context during interactions.
- Run as a persistent process for reliable, on-demand screenshot capture in a local environment.
- Ensure local security (no authentication or rate limiting needed, as per user requirements).

## Key Features
- **Screenshot Tool**: A core MCP tool that captures the current GUI screenshot using `scrot`.
  - Saves screenshots as image files (e.g., PNG) in `/tmp/` directory.
  - Returns the file path or base64-encoded content to the LLM for viewing.
- **Persistent Server**: The server runs continuously, listening for MCP requests via stdio (standard MCP protocol).
  - Optionally integrates FastAPI for HTTP-based endpoints if additional serving is needed (e.g., for direct image access), but primary interface is MCP.
- **Automatic Cleanup**: Screenshots are stored in `/tmp/`, leveraging OS automatic deletion on reboot or tmp cleanup.
- **Error Handling**: Basic error reporting for `scrot` failures (e.g., if display not available).

## Technical Stack
- **Language**: Python 3.11.9 (managed via pyenv; do not use system Python).
- **Dependency Management**: `uv` for installing and managing Python packages and virtual environments.
- **Screenshot Tool**: `scrot` (already available on Ubuntu 22.04).
- **Server Framework**: FastAPI for HTTP serving (if needed), combined with MCP protocol library.
- **MCP Integration**: Use an MCP Python SDK (e.g., `mcp-python` or similar; confirm availability via web search during implementation).
- **OS**: Ubuntu 22.04.

## Requirements
- **Functional**:
  - MCP tool named `take_screenshot` that:
    - Accepts optional parameters (e.g., delay, filename).
    - Executes `scrot` to capture the full screen.
    - Saves to `/tmp/screenshot_<timestamp>.png`.
    - Returns the file path and/or base64-encoded image data.
  - Server must be MCP-compliant: Expose tools via stdio interface for client connection.
- **Non-Functional**:
  - Performance: Screenshots should be taken quickly (< 1 second).
  - Reliability: Handle cases where GUI is not available.
  - Security: Local only; no network exposure beyond MCP client.
  - Scalability: Single-user, local machine; no concurrency concerns.

## Implementation Plan
1. **Project Setup**:
   - Create a new Python project directory (e.g., `mcp_screenshot_server`).
   - Initialize with `uv init` and configure for Python 3.11.9.
   - Add dependencies: `fastapi`, `uvicorn`, MCP SDK (e.g., `mcp-server` if available), and any image handling libs like `Pillow` for base64 encoding.

2. **MCP Server Structure**:
   - Define MCP tools using the SDK.
   - Implement the `take_screenshot` tool:
     - Use `subprocess` to call `scrot`.
     - Handle file saving and encoding.
   - Set up the server to run persistently with `uv run`.

3. **Integration and Testing**:
   - Ensure MCP client (e.g., Claude Desktop) can connect and call the tool.
   - Test screenshot capture and delivery (verify images are viewable by LLMs).
   - Add logging for debugging.

4. **Deployment**:
   - Package as a script that can be run with `uv run server.py`.
   - Provide instructions for starting the server and connecting via MCP.

## Risks and Assumptions
- **MCP SDK Availability**: Assumes a Python MCP library exists; if not, may need custom stdio handling.
- **Scrot Compatibility**: Assumes `scrot` works without issues on the system.
- **Local Environment**: All operations are local; no cloud or multi-user support.
- **Dependencies**: `uv` and pyenv are correctly set up.

## Timeline and Milestones
- Week 1: Project setup and basic MCP server skeleton.
- Week 2: Implement screenshot tool and FastAPI integration.
- Week 3: Testing, error handling, and documentation.

## Success Criteria
- LLMs can successfully request and receive screenshots.
- Server runs persistently without issues.
- Screenshots are automatically cleaned up.