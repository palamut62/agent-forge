"""Agent Forge - multi-target AI assistant setup and management tool."""
import os
import sys

__version__ = "0.2.0"

def _running_under_pytest() -> bool:
    """Detect pytest without depending on a fragile custom sentinel."""
    return "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ


def _configure_utf8_stream(stream) -> None:
    """Prefer in-place reconfiguration to avoid breaking capture wrappers."""
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")


# Windows cp1254 encoding sorununu coz.
# Stream nesnelerini yeniden sarmak pytest gibi capture araclariyla cakisabildigi icin
# yalnizca gerekli durumlarda mevcut stream'i yerinde yeniden configure et.
if sys.platform == "win32" and not _running_under_pytest():
    _configure_utf8_stream(sys.stdout)
    _configure_utf8_stream(sys.stderr)
