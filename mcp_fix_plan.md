# MCP Screenshot Server Fix Plan

## Overview
This document outlines a detailed plan to address the critical issues identified in the code analysis. The fixes prioritize async correctness, concurrency safety, and reliability while maintaining backward compatibility.

## Phase 1: Critical Async Fixes (High Priority)

### 1.1 Convert Blocking Subprocess Calls to Async
**Target**: `server.py` - `take_screenshot()` function

**Current Problem**: `subprocess.run(["scrot", "-u", filename])` blocks the event loop.

**Solution**:
```python
async def take_screenshot(mode: Optional[str] = "description", question: Optional[str] = None):
    # ... existing validation ...
    timestamp = int(time.time())
    filename = f"/tmp/screenshot_{timestamp}.png"

    # Replace blocking subprocess.run with async subprocess
    process = await asyncio.create_subprocess_exec(
        "scrot", "-u", filename,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.wait()

    if process.returncode != 0:
        raise ScreenshotCaptureError(f"scrot failed with return code {process.returncode}")
```

**Files to modify**: `server.py`
**Testing**: Verify screenshot capture still works, test concurrent requests don't block.

### 1.2 Move Image Processing to Thread Pool
**Target**: `server.py` - Image processing section

**Current Problem**: PIL operations and OCR block the event loop.

**Solution**:
```python
# Create thread pool executor for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=4)

async def take_screenshot(mode: Optional[str] = "description", question: Optional[str] = None):
    # ... screenshot capture ...

    # Move all image processing to thread
    img, ocr_text, img_base64 = await asyncio.get_event_loop().run_in_executor(
        executor, process_image, filename
    )

def process_image(filename: str) -> tuple[Image.Image, str, str]:
    """CPU-bound image processing function"""
    with Image.open(filename) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Save original
        original_filename = filename.replace('.png', '_original.png')
        img.save(original_filename)

        # Crop
        img = img.crop((0, 60, img.width - 20, img.height))

        # OCR (blocking, but in thread)
        try:
            ocr_text = pytesseract.image_to_string(img).strip()
        except Exception as e:
            ocr_text = ""

        # Encode to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return img, ocr_text, img_base64
```

**Files to modify**: `server.py`
**Dependencies**: Add `concurrent.futures` import
**Testing**: Verify image processing produces same results, measure performance impact.

## Phase 2: Concurrency and Safety Fixes

### 2.1 Implement Atomic Rate Limiting
**Target**: Rate limiting functions in `server.py` and `manual_screenshot.py`

**Current Problem**: File-based counters have race conditions.

**Solution**:
```python
import fcntl
import os

class RateLimiter:
    def __init__(self, count_file: str, daily_limit: int = 1000):
        self.count_file = count_file
        self.daily_limit = daily_limit

    def _atomic_read_write(self, operation):
        """Atomic file operation with locking"""
        with open(self.count_file, 'a+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                content = f.read().strip()
                result = operation(content)
                f.seek(0)
                f.truncate()
                f.write(result)
                return result
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_daily_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            content = self._atomic_read_write(lambda x: x)
            if content.startswith(today + ":"):
                return int(content.split(":")[1])
        except (FileNotFoundError, ValueError):
            pass
        return 0

    def increment_daily_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        def op(content):
            current_count = 0
            if content.startswith(today + ":"):
                current_count = int(content.split(":")[1])
            new_count = current_count + 1
            return f"{today}:{new_count}"
        return int(self._atomic_read_write(op).split(":")[1])
```

**Files to modify**: `server.py`, create `utils/rate_limiter.py`
**Dependencies**: Add `fcntl` import
**Testing**: Test concurrent requests, verify counter accuracy.

### 2.2 Add Operation Timeouts
**Target**: All long-running operations

**Solution**:
```python
# In take_screenshot
try:
    # OCR and image processing with timeout
    img, ocr_text, img_base64 = await asyncio.wait_for(
        asyncio.get_event_loop().run_in_executor(executor, process_image, filename),
        timeout=30.0  # 30 second timeout
    )
except asyncio.TimeoutError:
    raise ProcessingTimeoutError("Image processing timed out")

# API call with timeout
try:
    response = await asyncio.wait_for(chat.sample(), timeout=60.0)
except asyncio.TimeoutError:
    raise APIError("Grok-4 API call timed out")
```

**Files to modify**: `server.py`
**Testing**: Test with slow operations, verify timeouts work.

## Phase 3: Error Handling and Resource Management

### 3.1 Implement Specific Exception Types
**Target**: `server.py` and new `exceptions.py`

**Solution**:
```python
# exceptions.py
class ScreenshotError(Exception):
    """Base exception for screenshot operations"""
    pass

class ScreenshotCaptureError(ScreenshotError):
    """Screenshot capture failed"""
    pass

class ImageProcessingError(ScreenshotError):
    """Image processing failed"""
    pass

class OCRError(ImageProcessingError):
    """OCR processing failed"""
    pass

class RateLimitError(ScreenshotError):
    """Rate limit exceeded"""
    pass

class APIError(ScreenshotError):
    """AI API call failed"""
    pass

# In server.py
async def take_screenshot(mode: Optional[str] = "description", question: Optional[str] = None):
    try:
        # ... existing logic ...
        if get_daily_count() >= DAILY_LIMIT:
            raise RateLimitError(f"Daily screenshot limit of {DAILY_LIMIT} reached")
        # ... rest of function ...
    except ScreenshotCaptureError:
        raise
    except ImageProcessingError:
        raise
    except APIError:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in take_screenshot: {e}")
        raise ScreenshotError(f"Unexpected error: {e}") from e
```

**Files to create**: `exceptions.py`
**Files to modify**: `server.py`
**Testing**: Test error scenarios, verify proper exception propagation.

### 3.2 Implement Resource Cleanup
**Target**: Temporary file management

**Solution**:
```python
import atexit
import tempfile
import shutil

class TempFileManager:
    def __init__(self, base_dir: str = "/tmp"):
        self.base_dir = base_dir
        self.temp_files = set()
        atexit.register(self.cleanup)

    def create_temp_file(self, suffix: str = ".png") -> str:
        """Create temporary file and track it for cleanup"""
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.base_dir)
        os.close(fd)  # Close the file descriptor, keep path
        self.temp_files.add(path)
        return path

    def cleanup(self):
        """Clean up all tracked temporary files"""
        for path in self.temp_files.copy():
            try:
                if os.path.exists(path):
                    os.unlink(path)
                self.temp_files.discard(path)
            except OSError:
                pass  # File may have been deleted already

# Usage in take_screenshot
temp_manager = TempFileManager()

async def take_screenshot(mode: Optional[str] = "description", question: Optional[str] = None):
    filename = temp_manager.create_temp_file(".png")
    original_filename = filename.replace('.png', '_original.png')

    try:
        # ... process screenshot ...
        # Don't auto-delete files, let client decide based on response
        # temp_manager.temp_files.discard(filename)
        # temp_manager.temp_files.discard(original_filename)
        pass
    except Exception:
        # Cleanup on error
        temp_manager.cleanup()
        raise
```

**Files to create**: `utils/temp_manager.py`
**Files to modify**: `server.py`
**Testing**: Verify files are cleaned up on errors and server shutdown.

## Phase 4: Code Organization and Configuration

### 4.1 Extract Shared Modules
**Structure**:
```
mcp_screenshot/
├── server.py              # Main server
├── exceptions.py          # Custom exceptions
├── config.py              # Configuration management
├── utils/
│   ├── __init__.py
│   ├── rate_limiter.py    # Rate limiting logic
│   ├── temp_manager.py    # Temp file management
│   ├── image_processor.py # Image processing utilities
│   └── logger.py          # Logging configuration
├── tests/                 # Updated test files
└── pyproject.toml
```

### 4.2 Configuration Management
**Target**: `config.py`

**Solution**:
```python
import os
from typing import Optional

class Config:
    # File paths
    TEMP_DIR: str = os.getenv("SCREENSHOT_TEMP_DIR", "/tmp")
    COUNT_FILE: str = os.getenv("SCREENSHOT_COUNT_FILE", "/tmp/screenshot_daily_count.txt")
    TOKENS_FLAG: str = os.getenv("SCREENSHOT_TOKENS_FLAG", "/tmp/out_of_tokens.flag")

    # Limits
    DAILY_LIMIT: int = int(os.getenv("SCREENSHOT_DAILY_LIMIT", "1000"))

    # Timeouts
    OCR_TIMEOUT: float = float(os.getenv("SCREENSHOT_OCR_TIMEOUT", "30.0"))
    API_TIMEOUT: float = float(os.getenv("SCREENSHOT_API_TIMEOUT", "60.0"))
    SUBPROCESS_TIMEOUT: float = float(os.getenv("SCREENSHOT_SUBPROCESS_TIMEOUT", "10.0"))

    # Processing
    MAX_WORKERS: int = int(os.getenv("SCREENSHOT_MAX_WORKERS", "4"))
```

### 4.3 Unified Logging
**Target**: `utils/logger.py`

**Solution**:
```python
import logging
import sys
from pathlib import Path

def setup_logging(log_file: str = "server.log", level: int = logging.DEBUG):
    """Setup unified logging configuration"""
    # Create logger
    logger = logging.getLogger("mcp_screenshot")
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # File handler
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# In server.py
from utils.logger import setup_logging
logger = setup_logging()
```

## Phase 5: Testing and Monitoring

### 5.1 Update Test Files
- Remove outdated test approaches
- Use consistent async patterns
- Add tests for error conditions
- Mock external dependencies for unit tests

### 5.2 Add Health Checks
**Target**: New health check endpoint

**Solution**:
```python
@mcp.tool()
async def health_check() -> str:
    """Check server health and resource status"""
    health_status = {
        "status": "healthy",
        "temp_space": check_temp_space(),
        "rate_limit_status": get_rate_limit_status(),
        "dependencies": check_dependencies()
    }

    # Return unhealthy if any critical issues
    if not all(health_status.values()):
        health_status["status"] = "unhealthy"

    return json.dumps(health_status, indent=2)
```

## Implementation Order and Risk Assessment

### Priority Order:
1. **Phase 1**: Async fixes (highest risk, highest impact)
2. **Phase 2**: Concurrency fixes (medium risk, high impact)
3. **Phase 3**: Error handling (low risk, medium impact)
4. **Phase 4**: Code organization (low risk, low impact)
5. **Phase 5**: Testing (lowest risk, medium impact)

### Risk Mitigation:
- Implement changes incrementally with thorough testing
- Maintain backward compatibility for API
- Add comprehensive logging for debugging
- Create rollback plans for each phase
- Test under load to verify async improvements

### Success Criteria:
- No blocking operations in async functions
- Concurrent requests handled without race conditions
- Proper error reporting and resource cleanup
- Maintainable, well-organized codebase
- Comprehensive test coverage

## Timeline Estimate
- Phase 1: 2-3 days (critical async fixes)
- Phase 2: 2 days (concurrency and timeouts)
- Phase 3: 1-2 days (error handling and cleanup)
- Phase 4: 1-2 days (refactoring and configuration)
- Phase 5: 2-3 days (testing and monitoring)

Total: 8-12 days for complete implementation and testing.