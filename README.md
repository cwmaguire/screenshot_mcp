# MCP Screenshot Server

This is an MCP (Model Context Protocol) server that allows LLMs to take screenshots of the GUI.

## Installation

Ensure you have uv installed. Then, in the project directory:

```bash
uv sync
```

## Running the Server

To run the server:

```bash
uv run server.py
```

The server runs persistently via stdio, waiting for MCP client connections.

## Connecting to MCP Client

Configure your MCP client (e.g., Claude Desktop) to connect to this server by specifying the command:

```json
{
  "mcpServers": {
    "screenshot": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/mcp_screenshot_server"
    }
  }
}
```

Replace `/path/to/mcp_screenshot_server` with the actual path.

## Usage

Once connected, the LLM can call the `take_screenshot` tool to capture the current GUI screenshot. The tool returns the screenshot as a base64-encoded PNG image.

## How Screenshots Are Taken

**Linux/X11 Specific:** This server uses \`scrot\` to capture the **currently active (focused) window**.

- Captures screenshot with \`scrot -u\` (active window only).
- Processes image with **Tesseract OCR** for text extraction.
- Optionally sends to **Grok-4 AI** for analysis:
  - \`description\`: Detailed UI/text/code description.
  - \`question\`: Answer specific questions about the screenshot.
  - \`both\`: Both above.

**Machine Dependencies & Limitations:**
- Requires **X11** display server (\`scrot\` limited Wayland support).
- Runs on the **local machine** with GUI access (DISPLAY env var).
- Install deps: \`sudo apt install scrot tesseract-ocr\`.

## Requirements

- scrot (install via apt: `sudo apt install scrot`)
- Python 3.11.9
- Display server (X11 or Wayland)