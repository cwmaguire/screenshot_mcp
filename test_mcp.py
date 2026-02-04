"""
Simple test to verify server imports and basic functionality.
This test doesn't require MCP server to be running.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_imports():
    """Test that all modules can be imported."""
    try:
        import config
        import exceptions
        from utils import RateLimiter, process_image, setup_logging
        print("✓ Core imports successful")

        # Try server import (may fail if MCP not installed)
        try:
            import server
            print("✓ Server import successful")
        except ImportError as e:
            print(f"⚠ Server import failed (expected in test env): {e}")

        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        import config
        print(f"✓ Config loaded: DAILY_LIMIT={config.config.DAILY_LIMIT}")
        print(f"✓ Config loaded: TEMP_DIR={config.config.TEMP_DIR}")
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running basic tests...")
    success = True
    success &= test_imports()
    success &= test_config()

    if success:
        print("✓ All tests passed")
    else:
        print("✗ Some tests failed")
        sys.exit(1)