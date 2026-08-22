"""Panel UI -- connections list/connect form + a quick "recent leads" view
in the left sidebar.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as PagerDuty
Connector's / MuleSoft Connector's panels.py).

Every section is a plain ui.Stack, content stacked vertically and
left-aligned, sections separated by ui.Divider() -- no Card
border/background/shadow anywhere in this slot. Disconnect lives only in
the "App settings" screen (panels_settings.py). The one secondary "App
settings" button is always the LAST element at the bottom of the sidebar.

Form container is stretched full-width (align="stretch") and its Input
fields use native `label=`/`placeholder=` per UI_INTERFACE_STANDARD.md's
Label+Field+gap-container rule -- no separate ui.Text label lines, no
duplicated setup instructions here (the full walkthrough lives only in
followupboss_connect_help's modal).
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from handlers_connection import _load_connections
import followupboss_client as fc


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__followupboss_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("account_name") or c.get("id", "")
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text(f"{c.get('role', '')} · {c.get('account_name', '')}", variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Follow Up Boss accounts connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _person_row(p: dict) -> ui.UINode:
    stage = (p.get("stage") or {}).get("name", "") if isinstance(p.get("stage"), dict) else str(p.get("stage", ""))
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(p.get("name", "") or f"{p.get('firstName','')} {p.get('lastName','')}".strip(), variant="body"),
        ui.Text(f"{stage} · {p.get('source', '')}", variant="caption"),
    ])


def _people_section(people: list[dict]) -> ui.UINode:
    if not people:
        return ui.Text("No recent leads yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, p in enumerate(people):
        if i > 0:
            children.append(ui.Divider())
        children.append(_person_row(p))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    """Plain content, no Card wrapper. Stretched full-width per
    UI_INTERFACE_STANDARD.md. No intro heading/description text here --
    the full walkthrough lives ONLY in followupboss_connect_help's modal
    (button below opens it); repeating it here would duplicate that
    instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__followupboss_connect_help")),
        ui.Form(
            action="connect_followupboss",
            submit_label="Verify and connect",
            children=[
                ui.Text("Personal API Key", variant="caption"),
                ui.Input(param_name="api_key",
                          placeholder="Paste your Follow Up Boss API Key (fka_...)"),
                ui.Text("Registered System name (optional)", variant="caption"),
                ui.Input(param_name="system_name",
                          placeholder="Only if FUB support registered one for you"),
                ui.Text("Registered System key (optional)", variant="caption"),
                ui.Input(param_name="system_key",
                          placeholder="Paired with the system name above"),
                ui.Text("Label (optional)", variant="caption"),
                ui.Input(param_name="label",
                          placeholder="e.g. Main brokerage account"),
            ],
        ),
    ])


@ext.panel("followupboss_connect", slot="left", title="Follow Up Boss", icon="🏠",
           default_width=320, min_width=260, max_width=420)
async def followupboss_connect_panel(ctx, **kwargs) -> object:
    connections = await _load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="Follow Up Boss", level=2,
                        subtitle="Manage leads, deals and follow-up from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    first = connections[0]
    people: list[dict] = []
    try:
        people = await fc.list_people(ctx, first, limit=10, sort="created")
    except fc.ClientFail:
        people = []

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connected accounts", variant="subtitle"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        ui.Text(f"Recent leads -- {first.get('label') or first.get('account_name', '')}", variant="subtitle"),
        _people_section(people),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("followupboss_connect_help", slot="center",
           title="How to connect Follow Up Boss", center_overlay=True)
async def followupboss_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. In Follow Up Boss, go to Admin > API."),
        ui.Text("2. Under \"API Access\", copy your personal API Key (starts with fka_)."),
        ui.Text("3. Paste it into the form here and click \"Verify and connect\"."),
        ui.Divider(),
        ui.Alert(
            title="Registered System (optional, higher rate limits)",
            message=(
                "If your team registered a named integration with Follow "
                "Up Boss support, you'll also have a System name and "
                "System key. Adding both here raises your API rate limit "
                "and is required for some endpoints (e.g. certain "
                "webhook and automation actions). Most users can safely "
                "leave these blank."
            ),
            type="info",
        ),
        ui.Divider(),
        ui.Link(
            label="Open Follow Up Boss's official API authentication guide",
            href="https://docs.followupboss.com/reference/authentication",
        ),
    ])
    return ui.Dialog(
        title="How to connect Follow Up Boss",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )


@ext.panel("followupboss_center", slot="center", title="Follow Up Boss", icon="🏠", center_overlay=True)
async def followupboss_center_panel(ctx, **kwargs) -> object:
    """Base center panel -- per UI_INTERFACE_STANDARD.md. This app has no
    list/detail content of its own to show in the center by default
    (everything lives in the sidebar). MUST carry center_overlay=True: per
    docs.imperal.io/en/concepts/panels, a plain slot="center" panel is
    registered but the Panel app never fetches it at session-init without
    that flag. Text is the shared canonical wording -- must stay identical
    across every app in this situation."""
    return ui.Empty(
        message="Nothing to show here -- this app is managed entirely from the sidebar.",
        icon="👈",
    )
