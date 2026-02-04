# Product Requirements Document: MCP Screenshot Server v2

## Overview
This document outlines the updated requirements and implementation plan for an MCP (Model Context Protocol) server that enables Large Language Models (LLMs) to take screenshots of the GUI, capture them, and optionally analyze them using xAI's grok-4 model. The server will be implemented in Python using `uv` for dependency management, targeting Python 3.11.9 via pyenv. Screenshots will be taken using the `scrot` tool and stored temporarily in a system tmp directory for automatic cleanup.

## Purpose
- Provide LLMs with the ability to capture and view GUI screenshots for visual context during interactions.
- Enable advanced analysis of screenshots by querying grok-4 for detailed descriptions or answers to specific questions.
- Run as a persistent process for reliable, on-demand screenshot capture and analysis in a local environment.
- Ensure local security (no authentication or rate limiting needed beyond daily limits for xAI API).
- Limit xAI API usage to 1000 screenshots per day and handle out-of-tokens scenarios gracefully.

## Key Features
- **Screenshot Capture**: Uses `scrot` to capture the full GUI desktop.
- **Image Encoding**: Converts screenshots to base64 for transmission and storage.
- **grok-4 Integration**: Optional analysis modes:
  - **Description Mode**: Get a detailed debugging description of the image.
  - **Question Mode**: Ask a specific question about the image and receive an answer.
  - **Both Mode**: Receive both a description and an answer to a question.
- **Rate Limiting**: Enforce a daily limit of 1000 images sent to grok-4.
- **Error Handling**: Fail entirely on API errors, including out-of-tokens detection.

## Technical Requirements
- **Dependencies**:
  - Python 3.11.9
  - `scrot` for screenshot capture
  - `fastapi`, `uvicorn`, `mcp` (MCP SDK), `pillow` for image handling
  - `xai` (xAI SDK) for grok-4 API calls
- **Environment Variables**:
  - `XAI_API_KEY`: Required for xAI API authentication.
- **Rate Limiting Implementation**:
  - Track daily usage in `/tmp/screenshot_daily_count.txt`
  - Detect and flag out-of-tokens in `/tmp/out_of_tokens.flag`
- **Tool Interface**:
  - Tool Name: `take_screenshot`
  - Parameters:
    - `mode` (required): Enum ["question", "description", "both"]
    - `question` (optional): String, required if mode is "question" or "both"
  - Output: Image (base64) + optional grok-4 analysis text

## Implementation Plan
1. Add xAI SDK dependency.
2. Implement rate limiting and out-of-tokens detection.
3. Modify MCP tool schema to accept mode and question.
4. Integrate grok-4 API calls with appropriate prompts.
5. Update error handling to fail on API issues.
6. Test with real API calls.

## Usage
- Run the server: `uv run server.py`
- Connect MCP client (e.g., Claude Desktop).
- Call `take_screenshot` with desired mode and optional question.
- Receive screenshot image and grok-4 analysis if requested.

## Limitations
- Requires GUI environment for `scrot`.
- xAI API key needed for analysis features.
- Daily limit of 1000 analyses.
- Fails on API errors to prevent invalid responses.