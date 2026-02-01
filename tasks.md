# Tasks for Implementing MCP Screenshot Server PRD

## Instructions for LLM
Read PRD.md first, then continue. This file breaks down the PRD into very granular, sequential tasks that must be completed in order. Each task has a prerequisite check to ensure order.

- **Reading Incomplete Tasks**: Scan the file for tasks marked with `[ ]` (incomplete). Start with the first `[ ]` task. Do not work on any task marked `[x]` (complete) or skip ahead.
- **Working on Tasks**: Focus on **ONE** incomplete task at a time. Read its description carefully. If it requires using tools (e.g., bash, create_file), call them as needed. Assume the current working directory is `/home/c/dev/mcp_screenshot` unless specified.
- **Marking Complete**: After successfully completing a task, update this file by changing `[ ]` to `[x]` for that task ONLY. Do not modify other tasks. If a task fails or needs clarification, note it in your response without marking complete.
- **General Rules**: Use `uv` for all Python-related operations (no system pip or Python). If a task requires confirmation (e.g., file operations), handle it appropriately. Provide a brief summary of what was done after marking a task complete.
- **Prerequisites**: Tasks are ordered so dependencies are met. Do not proceed to a task if its prerequisite is not `[x]`.

## Tasks

- [x] **Task 1: Verify uv installation**  
  Prerequisite: None.  
  Description: Check if `uv` is installed on the system. Run `uv --version` via bash. If installed, proceed. If not, install it using `curl -LsSf https://astral.sh/uv/install.sh | sh` and verify.

- [x] **Task 2: Verify pyenv and Python 3.11.9**  
  Prerequisite: Task 1 complete.  
  Description: Ensure pyenv is set up and Python 3.11.9 is available. Run `pyenv versions` via bash to list versions. If 3.11.9 is not listed, install it with `pyenv install 3.11.9`. Set it as global with `pyenv global 3.11.9`. Verify with `python --version`.

- [x] **Task 3: Create project directory**  
  Prerequisite: Task 2 complete.  
  Description: Create a new directory named `mcp_screenshot_server` inside `/home/c/dev/mcp_screenshot`. Use bash `mkdir mcp_screenshot_server`. Change into it with `cd mcp_screenshot_server`.

- [x] **Task 4: Initialize uv project**  
  Prerequisite: Task 3 complete.  
  Description: In the `mcp_screenshot_server` directory, run `uv init` to create a new Python project. This should generate `pyproject.toml` and other files. Confirm Python version is set to 3.11.9 in the config.

- [x] **Task 5: Add FastAPI dependency**  
  Prerequisite: Task 4 complete.  
  Description: Use `uv add fastapi` to add FastAPI to the project. This updates `pyproject.toml` and installs it.

- [x] **Task 6: Add Uvicorn dependency**  
  Prerequisite: Task 5 complete.  
  Description: Use `uv add uvicorn` to add Uvicorn for running the server.

- [x] **Task 7: Research MCP Python SDK**  
  Prerequisite: Task 6 complete.  
  Description: Use web_search to find a suitable MCP Python SDK (e.g., search "mcp python sdk" or "model context protocol python"). Identify the package name (e.g., `mcp-server`). If none exists, note that custom stdio handling may be needed.

- [x] **Task 8: Add MCP SDK dependency**  
  Prerequisite: Task 7 complete.  
  Description: Based on Task 7, add the MCP SDK with `uv add <package_name>`. If no SDK, skip and note for custom implementation.

- [x] **Task 9: Add Pillow dependency**  
  Prerequisite: Task 8 complete.  
  Description: Use `uv add pillow` for image handling (base64 encoding).

- [x] **Task 10: Create main server file**  
  Prerequisite: Task 9 complete.  
  Description: Create a file `server.py` in the project directory. Use create_file with initial content: basic FastAPI app setup and imports (fastapi, uvicorn, any MCP libs).

- [x] **Task 11: Define MCP tools structure**  
  Prerequisite: Task 10 complete.  
  Description: In `server.py`, add code to define MCP tools using the SDK. If no SDK, set up basic stdio handling. Include a placeholder for `take_screenshot` tool.

- [x] **Task 12: Implement take_screenshot tool logic**  
  Prerequisite: Task 11 complete.  
  Description: In `server.py`, implement the `take_screenshot` function: Use subprocess to call `scrot` with options (e.g., save to /tmp/screenshot_<timestamp>.png). Add file saving and base64 encoding using Pillow. Return path and/or base64.

- [x] **Task 13: Add error handling for scrot**  
  Prerequisite: Task 12 complete.  
  Description: In the `take_screenshot` function, add try-except for subprocess errors (e.g., if scrot fails). Return error messages if applicable.

- [x] **Task 14: Set up persistent server run**  
  Prerequisite: Task 13 complete.  
  Description: Modify `server.py` to run as a persistent MCP server (e.g., via stdio loop or FastAPI). Add `if __name__ == "__main__":` to start the server with `uv run server.py`.

- [x] **Task 15: Add logging**  
  Prerequisite: Task 14 complete.  
  Description: Import and configure logging in `server.py` (e.g., basic logging to console for debugging screenshot captures).

- [x] **Task 16: Test server startup**  
  Prerequisite: Task 15 complete.  
  Description: Run `uv run server.py` via bash. Check for errors. If it starts successfully (persistent), stop it (Ctrl+C). Note any issues.

- [x] **Task 17: Test scrot functionality**  
  Prerequisite: Task 16 complete.  
  Description: Manually test `scrot` via bash (e.g., `scrot test.png`). Verify it saves to current dir or /tmp. Delete test file after.

- [x] **Task 18: Integrate with MCP client**  
  Prerequisite: Task 17 complete.  
  Description: Assuming MCP client (e.g., Claude) is set up, configure it to connect to the server. Run the server and attempt a tool call. Verify connection.

- [x] **Task 19: Test screenshot capture and delivery**  
  Prerequisite: Task 18 complete.  
  Description: Via the MCP client, call the `take_screenshot` tool. Check if image is captured, saved, and delivered (e.g., base64 viewable). Verify /tmp cleanup behavior.

- [x] **Task 20: Create README.md**  
  Prerequisite: Task 19 complete.  
  Description: Create `README.md` in the project directory with instructions: how to run (`uv run server.py`), connect to MCP client, and usage examples.

- [x] **Task 21: Final review and cleanup**  
  Prerequisite: Task 20 complete.  
  Description: Review all code for adherence to PRD. Run a full test cycle. Clean up any temp files. Mark this as the last task.
