"""Claude Forge - AI-powered Claude Code project setup tool."""
import io
import sys

__version__ = "0.2.0"

# Windows cp1254 encoding sorununu coz
# stdout'u UTF-8 ile sar (pytest ile cakismasin diye kontrol)
if sys.platform == "win32" and not hasattr(sys, "_called_from_test"):
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
