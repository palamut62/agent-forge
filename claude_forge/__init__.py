"""Claude Forge - AI-powered Claude Code project setup tool."""
import io
import sys

__version__ = "0.1.0"

# Windows cp1254 encoding sorununu coz
# stdout'u UTF-8 ile sar
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
