"""The single 'App settings' screen (center slot) -- connection management
(disconnect per account) for Follow Up Boss Connector. Split out of
panels.py per the same convention as PagerDuty Connector's / MuleSoft
Connector's panels_settings.py.

Per ~/UI_INTERFACE_STANDARD.md: the left sidebar never wraps the connect
form in a Card, and disconnect / secondary account management (never
exposed in the sidebar itself) live here. The one secondary "App settings"
button sits LAST at the bottom of the sidebar. All setup instructions for
adding a Registered System live only in followupboss_connect_help's modal,
not duplicated here.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from handlers_connection import _load_connections


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("account_name") or c.get("id", "")
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text(f"{c.get('role', '')} · {c.get('account_name', '')}", variant="caption"),
        ui.Text(
            "Registered System attached" if c.get("has_system_registration") else "No Registered System",
            variant="caption",
        ),
        ui.Button(
            "Disconnect", variant="danger", size="sm",
            on_click=ui.Call("disconnect_followupboss", {"connection_id": c.get("id")}),
        ),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=1, children=[
            ui.Text("No Follow Up Boss accounts connected.", variant="caption"),
        ])
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=3, children=children)


@ext.panel("followupboss_settings", slot="center", title="Follow Up Boss settings", center_overlay=True)
async def followupboss_settings_panel(ctx, **kwargs) -> object:
    connections = await _load_connections(ctx)
    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        ui.Header(text="Follow Up Boss settings", level=2,
                  subtitle="Manage your connected accounts"),
        ui.Text("Connected accounts", variant="subtitle"),
        _connections_section(connections),
    ])
