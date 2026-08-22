"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), SAME REASONING AS PagerDuty Connector /
Stripe Connector / MuleSoft Connector.

Follow Up Boss is the user's OWN real-estate CRM account -- Imperal cannot
and should not broker access to someone else's book of leads/clients
centrally. The user pastes their own personal API Key once, Vault-encrypted
via `ctx.secrets`, and every call runs against their own FUB account.

WHY A PLAIN API KEY (Basic Auth), NOT OAUTH2, FOR THE PRIMARY CONNECTION --
SAME REASONING AS PagerDuty Connector / Stripe Connector.

FUB's REST API v1 authenticates with a personal API Key sent as HTTP Basic
Auth (username = key, password blank) -- docs.followupboss.com/reference/
authentication, confirmed during Discovery 2026-08-22. FUB's own "Start
Here" guide recommends this path for a single account integration over
OAuth2, which exists mainly for multi-tenant marketplace-style apps.
`connect_followupboss` validates the pasted key against `GET /identity`
(cheap, always-available call that also reports the account/role) and
stores it.

WHY ONE SECRET HOLDING A JSON ARRAY FOR CONNECTIONS, SAME PRECEDENT AS
PagerDuty Connector / MuleSoft Connector / Power Automate Connector.

A user may manage more than one FUB account (e.g. an agency running
several brokerage brands, or an admin helping several teams). `ctx.secrets`
only supports a fixed, manifest-declared set of NAMES -- there is no "one
secret per connection" primitive, so `followupboss_connections` holds a
JSON array of `{id, label, api_key, system_name, system_key, role,
account_name}` objects, and every tool's `connection_id` parameter
addresses one entry in that array -- see handlers_connection.py's
`_load_connections`/`_save_connections` helpers.

WHY SYSTEM NAME/KEY ARE STORED PER-CONNECTION, NOT AS A SEPARATE SECRET.

Unlike PagerDuty's per-service Integration Keys (which are independent of
the account credential), FUB's System Identification headers
(`X-System`/`X-System-Key`) are a property OF one specific account's
registration with FUB support -- they travel with that account's API Key,
not as a separate reusable resource. They live inline on the connection
record instead of their own secret.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "followupboss-connector",
    version="0.1.0",
    display_name="Follow Up Boss",
    description=(
        "Connect your own Follow Up Boss (FUB) real-estate CRM account to "
        "manage leads, contacts, deals, and follow-up activity from "
        "Imperal -- People (contacts) with tags, custom fields, and "
        "relationships; lead intake via Events (the correct, "
        "automation-triggering way to add leads, not raw People creation); "
        "Deals and Pipelines/Stages; Tasks and Notes; Calls and Text "
        "Messages (with templates); Appointments (with types/outcomes); "
        "Users, Teams/Groups/Ponds; Custom Fields; Smart Lists; "
        "Automations 2.0 / legacy Action Plans; Webhooks; plus value-add "
        "reports (stale-lead detection, agent response-time audit, "
        "pipeline health) not available in the native FUB UI. Uses your "
        "own personal API Key -- nothing is hosted or proxied by Imperal "
        "beyond the request itself."
    ),
    icon="icon.svg",
    capabilities=[
        "followupboss:read",
        "followupboss:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="followupboss",
    description=(
        "Follow Up Boss Connector -- connect your own FUB account via your "
        "personal API Key, then manage people/contacts, leads (via "
        "events), deals, pipelines, tasks, notes, calls, text messages, "
        "appointments, users, teams, custom fields, smart lists, "
        "automations/action plans, webhooks, and run efficiency reports "
        "(stale leads, response time, pipeline health)."
    ),
)

ext.secret(
    "followupboss_connections",
    (
        "Your connected Follow Up Boss accounts -- stored as a JSON array, "
        "one entry per account, each with its own personal API Key. "
        "Managed through connect_followupboss / disconnect_followupboss -- "
        "you should not need to edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one account connection is stored, same shape as PagerDuty
    Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("followupboss_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} Follow Up Boss account(s) connected." if count
            else "Not connected yet -- run connect_followupboss."
        ),
    }
