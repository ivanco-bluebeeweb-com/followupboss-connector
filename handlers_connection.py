"""Connection management: connect/disconnect Follow Up Boss accounts, list
connections, resolve which one a call should use. Same shape as PagerDuty
Connector's handlers_connection.py -- async, one secret holding a JSON
array, ActionResult.success()/.error().
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import followupboss_client as fc
from app import ext, chat
from schemas import (
    NoParams,
    ConnectFollowUpBossParams, ConnectionEntity, ConnectionList,
    DisconnectParams, DeleteResult,
    IdentityEntity,
)

_CONN_SECRET = "followupboss_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_CONN_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, items: list[dict]) -> None:
    await ctx.secrets.set(_CONN_SECRET, json.dumps(items))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    conns = await _load_connections(ctx)
    if not conns:
        return None
    if connection_id:
        for c in conns:
            if c.get("id") == connection_id:
                return c
        return None
    return conns[0]


def _entity(c: dict) -> ConnectionEntity:
    return ConnectionEntity(
        id=c.get("id", ""),
        title=c.get("label") or c.get("account_name") or "Follow Up Boss",
        connected=True,
        detail=c.get("account_name", ""),
        role=c.get("role", ""),
        account_name=c.get("account_name", ""),
        has_system_registration=bool(c.get("system_name") and c.get("system_key")),
    )


@chat.function(
    "connect_followupboss",
    "Connect a Follow Up Boss account by saving your personal API Key, after checking it actually works.",
    action_type="write",
    chain_callable=True,
    data_model=ConnectionEntity,
    event="followupboss-connector.connect_followupboss",
    effects=["followupboss.provider.connected"],
)
async def connect_followupboss(ctx, params: ConnectFollowUpBossParams) -> ActionResult:
    """Connect a Follow Up Boss account by saving your personal API Key
    (Admin > API), after checking it actually works. Optionally also save
    a Registered System name/key if you have one, for higher rate limits
    and access to Automations/Attachments/Webhooks/Inbox Apps endpoints."""
    if not params.api_key.strip():
        return ActionResult.error("API Key is required. Find it in Follow Up Boss under Admin > API.")

    probe_conn = {
        "api_key": params.api_key.strip(),
        "system_name": params.system_name.strip(),
        "system_key": params.system_key.strip(),
    }
    try:
        identity = await fc.get_identity(ctx, probe_conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)

    conns = await _load_connections(ctx)
    entry = {
        "id": str(uuid.uuid4()),
        "label": params.label.strip() or identity.get("account_name") or "Follow Up Boss",
        "api_key": params.api_key.strip(),
        "system_name": params.system_name.strip(),
        "system_key": params.system_key.strip(),
        "role": identity.get("role", ""),
        "account_name": identity.get("account_name", ""),
    }
    conns.append(entry)
    await _save_connections(ctx, conns)
    return ActionResult.success(_entity(entry), message=f"Connected to {entry['label']} as {entry['role'] or 'user'}.", summary="Followupboss connected.")


@chat.function(
    "disconnect_followupboss",
    "Disconnect a Follow Up Boss account: deletes the saved API Key.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.disconnect_followupboss",
    effects=["followupboss.provider.disconnected"],
)
async def disconnect_followupboss(ctx, params: DisconnectParams) -> ActionResult:
    """Disconnect a Follow Up Boss account: deletes the saved API Key.
    Nothing in your Follow Up Boss account itself is changed."""
    conns = await _load_connections(ctx)
    if not conns:
        return ActionResult.error("No Follow Up Boss accounts are connected.")
    target_id = params.connection_id or conns[0].get("id")
    remaining = [c for c in conns if c.get("id") != target_id]
    if len(remaining) == len(conns):
        return ActionResult.error("Connection not found.")
    await _save_connections(ctx, remaining)
    return ActionResult.success(DeleteResult(ok=True, detail="Disconnected."), message="Follow Up Boss account disconnected.", summary="Followupboss disconnected.")


@chat.function(
    "list_connections",
    "List the connected Follow Up Boss accounts.",
    action_type="read",
    chain_callable=True,
    data_model=ConnectionList,
    event="followupboss-connector.list_connections",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Follow Up Boss accounts."""
    conns = await _load_connections(ctx)
    return ActionResult.success(ConnectionList(items=[_entity(c) for c in conns]), summary="Connections listed.")


@chat.function(
    "get_identity",
    "Read the connected Follow Up Boss account's identity: account name, your user name/email, and your role.",
    action_type="read",
    chain_callable=True,
    data_model=IdentityEntity,
    event="followupboss-connector.get_identity",
)
async def get_identity(ctx, params: NoParams) -> ActionResult:
    """Read the connected Follow Up Boss account's identity: account name,
    your user name/email, and your role (Owner/Admin/Agent/Lender)."""
    conn = await resolve_connection(ctx)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        identity = await fc.get_identity(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(IdentityEntity(
        account_name=identity.get("account_name", ""),
        user_name=identity.get("user_name", ""),
        user_email=identity.get("user_email", ""),
        role=identity.get("role", ""),
        is_owner=identity.get("role", "").lower() == "owner",
    ), summary="Identity retrieved.")
