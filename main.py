"""Entrypoint for the web-kernel and CLI tools (imperal validate/build).

Sets up sys.path, purges stale module cache, then imports ext/chat and all
handler modules so their decorators register on the same Extension instance
-- same pattern as PagerDuty Connector's / Mirth Connect Connector's main.py.
"""

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

_LOCAL = (
    "app", "schemas", "followupboss_client",
    "handlers_connection", "handlers_people", "handlers_deals",
    "handlers_activity", "handlers_admin", "handlers_analytics",
    "panels", "panels_settings",
)
for _mod in _LOCAL:
    sys.modules.pop(_mod, None)

from app import ext, chat  # noqa: E402,F401
import handlers_connection  # noqa: E402,F401
import handlers_people  # noqa: E402,F401
import handlers_deals  # noqa: E402,F401
import handlers_activity  # noqa: E402,F401
import handlers_admin  # noqa: E402,F401
import handlers_analytics  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_settings  # noqa: E402,F401
