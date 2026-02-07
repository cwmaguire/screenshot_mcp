"""
JSON-RPC method handlers for the MCP Screenshot Server.

This file implements handlers for all required MCP methods, including the custom take_screenshot tool.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Union

import pytesseract
from PIL import Image
from pydantic import ValidationError

from models import (
    JSONRPCError,
    JSONRPCResponse,
    InitializeRequest,
    InitializeResponse,
    PingRequest,
    PingResponse,
    ListResourcesRequest,
    ListResourcesResponse,
    ReadResourceRequest,
    ReadResourceResponse,
    ListToolsRequest,
    ListToolsResponse,
    CallToolRequest,
    CallToolResponse,
    ListPromptsRequest,
    ListPromptsResponse,
    GetPromptRequest,
    GetPromptResponse,
    CreateMessageRequest,
    CreateMessageResponse,
    ListTasksRequest,
    ListTasksResponse,
    GetTaskRequest,
    GetTaskResponse,
    CancelTaskRequest,
    CancelTaskResponse,
    SubscribeRequest,
    SubscribeResponse,
    ServerCapabilities,
    Implementation,
    Tool,
    Resource,
    Prompt,
    PromptMessage,
    Task,
    TaskState,
    TextContent,
    ImageContent,
    ContentBlock,
    Annotations,
)
from state import state
from utils import temp_manager, take_screenshot, extract_text_from_image, analyze_screenshot_with_grok, generate_message_with_grok, validate_uri, get_file_content
from registry import tool_registry, resource_registry, prompt_registry

logger = logging.getLogger(__name__)

# State management is handled by the state module

# Rate limiting (simple in-memory, configurable)
rate_limit: Dict[str, List[float]] = {}
DAILY_LIMIT = int(os.getenv("SCREENSHOT_DAILY_LIMIT", "1000"))

async def handle_initialize(params: InitializeRequest) -> Union[InitializeResponse, JSONRPCError]:
    """
    Handle the initialize method handshake.

    Validates client capabilities and returns server information and advertised capabilities.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        # Validate params
        if not isinstance(params, InitializeRequest):
            params = InitializeRequest(**params)

        logger.info("Initializing MCP connection with client protocol version: %s", params.protocolVersion)

        # Server capabilities for screenshot server
        capabilities = ServerCapabilities(
            experimental={},
            logging={},
            prompts={"listChanged": True},
            resources={"listChanged": True, "subscribe": True},
            sampling={},
            tools={"listChanged": True},
        )

        response = InitializeResponse(
            protocolVersion="2025-11-25",
            capabilities=capabilities,
            serverInfo=Implementation(
                name="MCP Screenshot Server",
                version="1.0.0",
            ),
        )
        return response
    except ValidationError as e:
        return JSONRPCError(code=-32602, message="Invalid params", data=str(e))
    except Exception as e:
        logger.error(f"Error in initialize: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_ping(params: PingRequest) -> Union[PingResponse, JSONRPCError]:
    """
    Handle the ping method.

    Returns a simple pong response.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        logger.info("Ping received from client")
        return PingResponse(pong=True)
    except Exception as e:
        logger.error(f"Error in ping: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_resources_list(params: ListResourcesRequest) -> Union[ListResourcesResponse, JSONRPCError]:
    """
    Handle resources/list method.

    Returns a list of available resources.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        resources = resource_registry.get_resources()
        return ListResourcesResponse(resources=resources)
    except Exception as e:
        logger.error(f"Error in resources/list: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_resources_read(params: ReadResourceRequest) -> Union[ReadResourceResponse, JSONRPCError]:
    """
    Handle resources/read method.

    Reads and returns the content of a resource URI.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        return await resource_registry.read_resource(params.uri)
    except Exception as e:
        logger.error(f"Error in resources/read: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_tools_list(params: ListToolsRequest) -> Union[ListToolsResponse, JSONRPCError]:
    """
    Handle tools/list method.

    Returns a list of available tools.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        tools = tool_registry.get_tools()
        return ListToolsResponse(tools=tools)
    except Exception as e:
        logger.error(f"Error in tools/list: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_tools_call(params: CallToolRequest) -> Union[CallToolResponse, JSONRPCError]:
    """
    Handle tools/call method.

    Executes the specified tool.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        logger.info("Calling tool: %s", params.name)
        return await tool_registry.call_tool(params.name, params.arguments or {})
    except Exception as e:
        logger.error(f"Error in tools/call: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_take_screenshot(arguments: Dict[str, Any]) -> CallToolResponse:
    """
    Handle the take_screenshot tool call.

    Captures screenshot, performs OCR, and optionally analyzes with Grok-4.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    # Input validation
    mode = arguments.get("mode", "description")
    question = arguments.get("question")

    if mode not in ["description", "question", "both"]:
        return CallToolResponse(
            content=[TextContent(type="text", text="Invalid mode. Must be 'description', 'question', or 'both'.")]
        )

    if mode in ["question", "both"] and not question:
        return CallToolResponse(
            content=[TextContent(type="text", text="Question required for 'question' or 'both' mode.")]
        )

    if question and not isinstance(question, str):
        return CallToolResponse(
            content=[TextContent(type="text", text="Question must be a string.")]
        )

    logger.info("Processing take_screenshot with mode: %s", mode)

    # Rate limiting check (placeholder, will be improved)
    client_id = "default"  # TODO: get from session
    now = time.time()
    if client_id not in rate_limit:
        rate_limit[client_id] = []
    rate_limit[client_id] = [t for t in rate_limit[client_id] if now - t < 86400]  # 24 hours
    if len(rate_limit[client_id]) >= DAILY_LIMIT:
        return CallToolResponse(
            content=[TextContent(type="text", text="Daily screenshot limit exceeded.")]
        )
    rate_limit[client_id].append(now)

    async with temp_manager.create_temp_file() as screenshot_path:
        try:
            # Capture screenshot
            if not await take_screenshot(screenshot_path):
                raise Exception("Failed to capture screenshot")

            content: List[ContentBlock] = []

            # Grok-4 analysis
            mode = arguments.get("mode", "description")
            question = arguments.get("question")
            logger.info("Starting Grok analysis with mode: %s", mode)

            if mode in ["description", "both"]:
                logger.info("Generating description")
                description = await analyze_screenshot_with_grok(screenshot_path, mode="description")
                logger.info("Description generated, length: %d", len(description or ""))
                content.append(TextContent(type="text", text=f"Description: {description}"))

            if mode in ["question", "both"]:
                if not question:
                    return CallToolResponse(
                        content=[TextContent(type="text", text="Question required for question mode.")]
                    )
                logger.info("Answering question")
                answer = await analyze_screenshot_with_grok(screenshot_path, mode="question", question=question)
                logger.info("Answer generated, length: %d", len(answer or ""))
                content.append(TextContent(type="text", text=f"Answer: {answer}"))

            logger.info("Screenshot processing and analysis completed")
            return CallToolResponse(content=content)

        except Exception as e:
            logger.error(f"Error in take_screenshot: {e}")
            return CallToolResponse(
                content=[TextContent(type="text", text=f"Error capturing screenshot: {str(e)}")]
            )

async def handle_screenshot_analysis_prompt(arguments: Dict[str, Any]) -> GetPromptResponse:
    """
    Handler for the screenshot_analysis prompt.

    Generates messages for screenshot analysis with optional focus area.
    """
    focus_area = arguments.get("focus_area", "general") if arguments else "general"
    messages = [
        PromptMessage(
            role="user",
            content=[
                TextContent(
                    type="text",
                    text=f"Analyze this screenshot focusing on {focus_area}. Describe the UI elements, text content, and overall layout."
                )
            ]
        ),
        PromptMessage(
            role="assistant",
            content=[
                TextContent(
                    type="text",
                    text="I'll analyze the screenshot based on the provided image and focus area."
                )
            ]
        )
    ]
    return GetPromptResponse(
        name="screenshot_analysis",
        description="Analyze a screenshot for UI elements, text content, and overall description.",
        arguments=[
            {
                "name": "focus_area",
                "description": "Specific area to focus on (e.g., 'buttons', 'text', 'layout')",
                "required": False
            }
        ],
        messages=messages
    )

async def handle_code_review_screenshot_prompt(arguments: Dict[str, Any]) -> GetPromptResponse:
    """
    Handler for the code_review_screenshot prompt.

    Generates messages for code review from screenshot.
    """
    messages = [
        PromptMessage(
            role="user",
            content=[
                TextContent(
                    type="text",
                    text="Review the code visible in this screenshot. Identify any potential issues, bugs, or improvements."
                )
            ]
        ),
        PromptMessage(
            role="assistant",
            content=[
                TextContent(
                    type="text",
                    text="I'll review the code in the screenshot for quality and potential issues."
                )
            ]
        )
    ]
    return GetPromptResponse(
        name="code_review_screenshot",
        description="Review code visible in a screenshot for potential issues or improvements.",
        arguments=None,
        messages=messages
    )

async def handle_prompts_list(params: ListPromptsRequest) -> Union[ListPromptsResponse, JSONRPCError]:
    """
    Handle prompts/list method.

    Returns a list of available prompts.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        prompts = prompt_registry.get_prompts()
        return ListPromptsResponse(prompts=prompts)
    except Exception as e:
        logger.error(f"Error in prompts/list: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_prompts_get(params: GetPromptRequest) -> Union[GetPromptResponse, JSONRPCError]:
    """
    Handle prompts/get method.

    Returns the prompt template with messages for the given name.

    Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
    """
    try:
        return await prompt_registry.get_prompt_response(params.name, params.arguments or {})
    except Exception as e:
        logger.error(f"Error in prompts/get: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_sampling_create_message(params: CreateMessageRequest) -> Union[CreateMessageResponse, JSONRPCError]:
    """
    Handle sampling/createMessage method.

    Creates a message using LLM sampling.
    """
    try:
        # TODO: Implement LLM integration
        return CreateMessageResponse(
            model="grok-4",
            role="assistant",
            content=[TextContent(type="text", text="TODO: Simulated LLM response")]
        )
    except Exception as e:
        logger.error(f"Error in sampling/createMessage: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_tasks_list(params: ListTasksRequest) -> Union[ListTasksResponse, JSONRPCError]:
    """
    Handle tasks/list method.

    Returns a list of tasks.
    """
    try:
        tasks_list = await state.list_tasks()
        return ListTasksResponse(tasks=tasks_list)
    except Exception as e:
        logger.error(f"Error in tasks/list: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_tasks_get(params: GetTaskRequest) -> Union[GetTaskResponse, JSONRPCError]:
    """
    Handle tasks/get method.

    Returns details of a specific task.
    """
    try:
        task = await state.get_task(params.taskId)
        if not task:
            return JSONRPCError(code=-32000, message="Task not found")
        return GetTaskResponse(task=task)
    except Exception as e:
        logger.error(f"Error in tasks/get: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_tasks_cancel(params: CancelTaskRequest) -> Union[CancelTaskResponse, JSONRPCError]:
    """
    Handle tasks/cancel method.

    Cancels a running task.
    """
    try:
        task = await state.get_task(params.taskId)
        if not task:
            return JSONRPCError(code=-32000, message="Task not found")
        # Update task status to cancelled
        await state.update_task(params.taskId, status="cancelled")
        return CancelTaskResponse()
    except Exception as e:
        logger.error(f"Error in tasks/cancel: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_resources_subscribe(params: SubscribeRequest) -> Union[SubscribeResponse, JSONRPCError]:
    """
    Handle resources/subscribe method.

    Subscribes to resource updates.
    """
    try:
        # TODO: Implement subscription logic
        return SubscribeResponse()
    except Exception as e:
        logger.error(f"Error in resources/subscribe: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

async def handle_sampling_create_message(params: CreateMessageRequest) -> Union[CreateMessageResponse, JSONRPCError]:
    """
    Handle sampling/createMessage method.

    Creates a message using LLM (Grok-4).
    """
    try:
        # Validate params
        if not isinstance(params, CreateMessageRequest):
            params = CreateMessageRequest(**params)

        # Convert messages to dict format for LLM
        messages = []
        for msg in params.messages:
            content_list = []
            for block in msg.content:
                if isinstance(block, TextContent):
                    content_list.append({"type": "text", "text": block.text})
                elif isinstance(block, ImageContent):
                    content_list.append({"type": "image", "image_url": {"url": f"data:{block.mimeType};base64,{block.data}"}})
                # Handle other content types as needed
            messages.append({"role": msg.role, "content": content_list})

        # Generate response using Grok
        generated_text = await generate_message_with_grok(messages, params.maxTokens)

        if generated_text is None:
            return JSONRPCError(code=-32603, message="Failed to generate message")

        content = TextContent(type="text", text=generated_text)

        response = CreateMessageResponse(
            role="assistant",
            content=content,
            model="grok-4",
            stopReason="endTurn"
        )
        return response
    except ValidationError as e:
        return JSONRPCError(code=-32602, message="Invalid params", data=str(e))
    except Exception as e:
        logger.error(f"Error in sampling/createMessage: {e}")
        return JSONRPCError(code=-32603, message="Internal error")

# Register default tools, resources, and prompts
tool_registry.register_tool(
    "take_screenshot",
    Tool(
        name="take_screenshot",
        description="Capture a screenshot of the currently active GUI window, extract text via OCR, and optionally analyze with Grok-4 AI.",
        inputSchema={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["description", "question", "both"],
                    "default": "description",
                    "description": "Analysis mode: 'description' for detailed description, 'question' for answering a specific question, 'both' for both."
                },
                "question": {
                    "type": "string",
                    "description": "Question to ask about the screenshot (required if mode is 'question' or 'both')."
                }
            },
            "required": []
        }
    ),
    handle_take_screenshot
)

prompt_registry.register_prompt(
    "screenshot_analysis",
    Prompt(
        name="screenshot_analysis",
        description="Analyze a screenshot for UI elements, text content, and overall description.",
        arguments=[
            {
                "name": "focus_area",
                "description": "Specific area to focus on (e.g., 'buttons', 'text', 'layout')",
                "required": False
            }
        ]
    ),
    handle_screenshot_analysis_prompt
)

prompt_registry.register_prompt(
    "code_review_screenshot",
    Prompt(
        name="code_review_screenshot",
        description="Review code visible in a screenshot for potential issues or improvements.",
        arguments=None
    ),
    handle_code_review_screenshot_prompt
)

# Method registry
METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "ping": handle_ping,
    "resources/list": handle_resources_list,
    "resources/read": handle_resources_read,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "prompts/list": handle_prompts_list,
    "sampling/createMessage": handle_sampling_create_message,
    "tasks/list": handle_tasks_list,
    "tasks/get": handle_tasks_get,
    "tasks/cancel": handle_tasks_cancel,
    "resources/subscribe": handle_resources_subscribe,
}