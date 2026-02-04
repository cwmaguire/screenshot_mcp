"""
FastAPI application for MCP Screenshot Server.

This module sets up the FastAPI application with HTTP transport for MCP,
supporting JSON-RPC 2.0 over POST and Server-Sent Events (SSE) over GET
on the /mcp endpoint, as per MCP specification version 2025-11-25.
"""

import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI, Request, HTTPException, Response
from sse_starlette.sse import EventSourceResponse
from pydantic import ValidationError

from models import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCNotification, JSONRPCError,
    InitializeRequest, PingRequest, ListResourcesRequest, ReadResourceRequest,
    ListToolsRequest, CallToolRequest, ListPromptsRequest, GetPromptRequest,
    CreateMessageRequest, ListTasksRequest, GetTaskRequest, CancelTaskRequest,
    SubscribeRequest
)
from state import state
from handlers import (
    handle_initialize,
    handle_ping,
    handle_resources_list,
    handle_resources_read,
    handle_tools_list,
    handle_tools_call,
    handle_prompts_list,
    handle_prompts_get,
    handle_sampling_create_message,
    handle_tasks_list,
    handle_tasks_get,
    handle_tasks_cancel,
    handle_resources_subscribe,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Screenshot Server", version="0.1.0")

# State management is handled by the state module

# Method dispatcher
METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "ping": handle_ping,
    "resources/list": handle_resources_list,
    "resources/read": handle_resources_read,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "prompts/list": handle_prompts_list,
    "prompts/get": handle_prompts_get,
    "sampling/createMessage": handle_sampling_create_message,
    "tasks/list": handle_tasks_list,
    "tasks/get": handle_tasks_get,
    "tasks/cancel": handle_tasks_cancel,
    "resources/subscribe": handle_resources_subscribe,
}

@app.post("/mcp")
async def handle_jsonrpc_request(request: Request) -> JSONRPCResponse:
    """
    Handle JSON-RPC 2.0 requests over HTTP POST.

    Validates the request against JSONRPCRequest model,
    dispatches to the appropriate handler, and returns a JSONRPCResponse.
    Reference: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        data = await request.json()
        if "id" in data:
            rpc_request = JSONRPCRequest(**data)
        else:
            # Handle notification
            rpc_notification = JSONRPCNotification(**data)
            # For notifications, return 200 with empty body
            logger.info(f"Received notification: {rpc_notification.method}")
            return Response(content="", status_code=200)
    except Exception as e:
        logger.error(f"Invalid JSON-RPC request: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON-RPC request")

    method = rpc_request.method
    params = rpc_request.params or {}
    id = rpc_request.id

    if method not in METHOD_HANDLERS:
        error = {
            "code": -32601,
            "message": "Method not found",
            "data": {"method": method}
        }
        return JSONRPCResponse(jsonrpc="2.0", id=id, error=error)

    try:
        handler = METHOD_HANDLERS[method]

        # Parse params into the appropriate model
        if method == "initialize":
            parsed_params = InitializeRequest(**params)
        elif method == "ping":
            parsed_params = PingRequest(**params)
        elif method == "resources/list":
            parsed_params = ListResourcesRequest(**params)
        elif method == "resources/read":
            parsed_params = ReadResourceRequest(**params)
        elif method == "tools/list":
            parsed_params = ListToolsRequest(**params)
        elif method == "tools/call":
            parsed_params = CallToolRequest(**params)
        elif method == "prompts/list":
            parsed_params = ListPromptsRequest(**params)
        elif method == "prompts/get":
            parsed_params = GetPromptRequest(**params)
        elif method == "sampling/createMessage":
            parsed_params = CreateMessageRequest(**params)
        elif method == "tasks/list":
            parsed_params = ListTasksRequest(**params)
        elif method == "tasks/get":
            parsed_params = GetTaskRequest(**params)
        elif method == "tasks/cancel":
            parsed_params = CancelTaskRequest(**params)
        elif method == "resources/subscribe":
            parsed_params = SubscribeRequest(**params)
        else:
            parsed_params = params  # Fallback

        response = await handler(parsed_params)
        if isinstance(response, JSONRPCError):
            return JSONRPCError(jsonrpc="2.0", id=id, error=response.error)
        else:
            return JSONRPCResponse(jsonrpc="2.0", id=id, result=response.model_dump())
    except ValidationError as e:
        logger.error(f"Validation error for method {method}: {e}")
        error = {
            "code": -32602,
            "message": "Invalid params",
            "data": str(e)
        }
        return JSONRPCError(jsonrpc="2.0", id=id, error=error)
    except Exception as e:
        logger.error(f"Error handling method {method}: {e}")
        error = {
            "code": -32603,
            "message": "Internal error",
            "data": str(e)
        }
        return JSONRPCError(jsonrpc="2.0", id=id, error=error)

@app.get("/mcp")
async def handle_sse(request: Request) -> EventSourceResponse:
    """
    Handle Server-Sent Events (SSE) for notifications and streaming.

    Establishes an SSE stream for sending JSONRPCNotification messages
    to the client, supporting polling and real-time updates.
    Reference: https://modelcontextprotocol.io/specification/2025-11-25
    """
    # Simple session tracking (use a unique ID from query or header)
    session_id = request.query_params.get("session_id", "default")
    # Create session if not exists
    await state.create_session(session_id, {})

    queue = await state.get_event_queue(session_id)

    async def event_generator():
        """Generate SSE events from the notification queue."""
        try:
            while True:
                # Wait for notifications (with timeout for polling)
                try:
                    notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": "notification",
                        "data": notification.model_dump_json()
                    }
                except asyncio.TimeoutError:
                    # Send a ping to keep connection alive
                    yield {"event": "ping", "data": "{}"}
        except Exception as e:
            logger.error(f"SSE error: {e}")
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())

# Utility function to send notifications (to be called from handlers)
async def send_notification(session_id: str, notification: JSONRPCNotification):
    """Send a notification to a specific session's SSE queue."""
    if session_id in sessions:
        await sessions[session_id].put(notification)