# MCP Screenshot Server - Grok CLI Initial Prompt

## Project Summary

This is an MCP (Model Context Protocol) server that enables LLMs to capture screenshots of the currently active GUI window. The server provides a `take_screenshot` tool that:

- Captures the active window using `scrot`
- Processes the image with OCR using `tesseract` for text extraction
- Optionally analyzes screenshots with Grok-4 AI in three modes:
  - `description`: Detailed description of visible text, code, or UI elements
  - `question`: Answers specific questions about the screenshot
  - `both`: Provides both description and answers questions

Key features include rate limiting (configurable daily limit, default 1000), health monitoring, async processing with timeouts, temporary file management, and comprehensive error handling. The server runs persistently via stdio and integrates with MCP clients like Claude Desktop.

This MCP server ONLY supports HTTP.
Do not *EVER* try and implement the server as stdio.

## Extra Rules for the LLM

- Always use uv for running Python
- Always use uv for installing Python dependencies
- Never edit files outside of /home/c/dev/mcp_screenshot
