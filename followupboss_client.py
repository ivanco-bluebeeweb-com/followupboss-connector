"""Follow Up Boss HTTP client -- single REST API v1 surface, Basic Auth via
per-user API Key (or Bearer via OAuth2 access token), optional System
Identification headers, thin wrappers over resource paths. Same shape as
pagerduty_client.py's ClientFail pattern -- uses the platform's own
`ctx.http` (async), never `requests`.

WHY BASIC AUTH WITH THE API KEY AS USERNAME, EMPTY PASSWORD.

Follow Up Boss's REST API v1 uses HTTP Basic Authentication where the
API Key IS the username and the password is left blank
(docs.followupboss.com/reference/authentication, confirmed 2026-08-22).
This is NOT a Bearer token scheme like most of the portfolio's newer
connectors -- mixing the two up produces a silent 401.

WHY OAuth2 BEARER IS A SEPARATE, OPTIONAL CODE PATH, NOT THE DEFAULT.

FUB also supports OAuth2 (docs.followupboss.com/docs/getting-started-with-
oauth) for multi-tenant marketplace-style integrations, using Bearer auth
instead of Basic. For a single user connecting their OWN account, the
personal API Key (Admin -> API) is simpler and is FUB's own recommended
starting point (docs.followupboss.com/docs/start-here-brand-new-
integration, confirmed 2026-08-22) -- so it is the only path this
connector implements in v1. The client function accepts either an
api_key (Basic) or an access_token (Bearer) so a future OAuth addition
does not require a rewrite, but no OAuth UI exists yet.

WHY SYSTEM IDENTIFICATION HEADERS ARE OPTIONAL, PER-CONNECTION FIELDS.

FUB asks integrators to register a "system name" and "system key"
(X-System / X-System-Key headers) for materially higher rate limits and
access to a few restricted resources (Automations, Attachments,
Webhooks, Inbox Apps -- help.followupboss.com Open API article,
confirmed 2026-08-22). Registration is a manual request to FUB support,
outside Imperal's control, so these headers are optional fields on
connect_followupboss: present if the user has already registered a
system name/key with FUB, silently omitted otherwise. Every restricted
call still WORKS without them at the lower default rate limit -- FUB
does not hard-block unregistered systems, it just throttles harder.

WHY 401 vs 403 ARE HANDLED DIFFERENTLY, SAME PRINCIPLE AS OTHER
IMPERAL CONNECTORS' CLIENTS.

A 401 means the credential itself is rejected. A 403 means the
credential is valid but the acting user's ROLE lacks permission for
this action -- FUB's role model (Owner/Admin/Agent/Lender) intentionally
restricts Agents from full People lists, Webhooks, etc.
(docs.followupboss.com/reference/authentication, confirmed 2026-08-22).
Handlers surface this distinction so a restricted Agent key does not
look like a broken connection.

WHY 429 IS RETRIED ONCE WITH `Retry-After`, SAME AS EVERY OTHER
IMPERAL CONNECTOR CLIENT.

FUB rate-limits on a sliding 10-second window, per context (`global`,
`events`, etc.), and returns a `Retry-After` header on 429
(docs.followupboss.com/reference/rate-limiting, confirmed 2026-08-22).
"""
from __future__ import annotations

import asyncio
import base64
from typing import Any

BASE_URL = "https://api.followupboss.com/v1"


class ClientFail(Exception):
    """Raised for any non-2xx Follow Up Boss response, carrying a human reason."""

    def __init__(self, reason: str, status: int = 0):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def _basic_auth_header(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _headers(
    api_key: str = "",
    access_token: str = "",
    *,
    system_name: str = "",
    system_key: str = "",
) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif api_key:
        headers["Authorization"] = _basic_auth_header(api_key)
    if system_name:
        headers["X-System"] = system_name
    if system_key:
        headers["X-System-Key"] = system_key
    return headers


def _map_error(status: int, body: Any) -> str:
    detail = ""
    if isinstance(body, dict):
        detail = str(body.get("errorMessage") or body.get("message") or body.get("error") or "")
    if status == 401:
        return "Follow Up Boss rejected this API Key/access token -- it may be wrong, revoked, or expired."
    if status == 403:
        return (
            "Follow Up Boss accepted the credential but refused this action -- the "
            "connected user's role (Agent/Lender) likely does not have permission for "
            "this resource, or this resource requires a Registered System."
            + (f" {detail}" if detail else "")
        )
    if status == 404:
        return "That Follow Up Boss resource was not found (wrong id, or it was deleted)."
    if status == 422:
        return f"Follow Up Boss rejected the request data.{(' ' + detail) if detail else ''}"
    if status == 429:
        return "Follow Up Boss rate-limited this connection -- too many requests too quickly."
    return f"Follow Up Boss API error ({status}).{(' ' + detail) if detail else ''}"


async def request(
    ctx,
    method: str,
    path: str,
    *,
    api_key: str = "",
    access_token: str = "",
    system_name: str = "",
    system_key: str = "",
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    _retried: bool = False,
) -> dict[str, Any]:
    """One call against FUB REST API v1. `path` starts with '/', e.g. '/people'."""
    if not api_key and not access_token:
        raise ClientFail("No Follow Up Boss credential configured for this connection.")
    url = f"{BASE_URL}{path}"
    headers = _headers(api_key, access_token, system_name=system_name, system_key=system_key)
    try:
        method_u = method.upper()
        if method_u == "GET":
            resp = await ctx.http.get(url, headers=headers, params=params)
        elif method_u == "POST":
            resp = await ctx.http.post(url, headers=headers, params=params, json=json_body)
        elif method_u == "PUT":
            resp = await ctx.http.put(url, headers=headers, params=params, json=json_body)
        elif method_u == "DELETE":
            resp = await ctx.http.delete(url, headers=headers, params=params)
        else:
            raise ClientFail(f"Unsupported HTTP method: {method}")
    except ClientFail:
        raise
    except Exception as e:
        raise ClientFail(f"Could not reach Follow Up Boss's API: {e}")

    if resp.status_code == 429 and not _retried:
        wait = resp.headers.get("Retry-After") if hasattr(resp, "headers") else None
        try:
            await asyncio.sleep(min(float(wait), 5.0) if wait else 1.0)
        except (TypeError, ValueError):
            await asyncio.sleep(1.0)
        return await request(
            ctx, method, path,
            api_key=api_key, access_token=access_token,
            system_name=system_name, system_key=system_key,
            params=params, json_body=json_body, _retried=True,
        )

    body_raw = getattr(resp, "body", None)
    body = body_raw if isinstance(body_raw, (dict, list)) else {}

    if resp.status_code >= 400:
        raise ClientFail(_map_error(resp.status_code, body), resp.status_code)

    if resp.status_code == 204 or body == {}:
        return {}

    return body if isinstance(body, dict) else {"items": body}


async def get_all(
    ctx,
    path: str,
    list_key: str,
    *,
    api_key: str = "",
    access_token: str = "",
    system_name: str = "",
    system_key: str = "",
    params: dict[str, Any] | None = None,
    limit: int = 100,
    max_items: int = 1000,
) -> list[dict[str, Any]]:
    """Paginate a FUB GET list endpoint (offset/limit/_metadata.total shape,
    docs.followupboss.com/reference/requests-and-responses + list endpoints,
    confirmed 2026-08-22)."""
    out: list[dict[str, Any]] = []
    offset = 0
    q = dict(params or {})
    q["limit"] = min(limit, 100)
    while len(out) < max_items:
        q["offset"] = offset
        body = await request(
            ctx, "GET", path,
            api_key=api_key, access_token=access_token,
            system_name=system_name, system_key=system_key,
            params=q,
        )
        items = body.get(list_key) or []
        out.extend(items)
        meta = body.get("_metadata") or {}
        total = meta.get("total")
        if not items:
            break
        offset += len(items)
        if total is not None and offset >= total:
            break
        if len(items) < q["limit"]:
            break
    return out[:max_items]


# ──────────────────────────────────────────────────────────────────────────
# Domain wrappers -- thin, one function per meaningful FUB operation.
# Every wrapper takes `ctx` first (platform HTTP client lives on ctx.http)
# plus the resolved connection's api_key/system_name/system_key, same
# calling convention as pagerduty_client.py's validate_rest_key etc.
# ──────────────────────────────────────────────────────────────────────────


def _auth(conn: dict) -> dict:
    return {
        "api_key": conn.get("api_key", ""),
        "access_token": conn.get("access_token", ""),
        "system_name": conn.get("system_name", ""),
        "system_key": conn.get("system_key", ""),
    }


async def get_identity(ctx, conn: dict) -> dict[str, Any]:
    body = await request(ctx, "GET", "/identity", **_auth(conn))
    account = body.get("account") or {}
    user = body.get("me") or body.get("user") or {}
    return {
        "account_name": account.get("name", ""),
        "user_name": user.get("name", ""),
        "user_email": user.get("email", ""),
        "role": user.get("role", body.get("role", "")),
    }


# -- People --------------------------------------------------------------

async def list_people(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/people", "people", **_auth(conn), params=filters)


async def get_person(ctx, conn: dict, person_id: str) -> dict:
    return await request(ctx, "GET", f"/people/{person_id}", **_auth(conn))


async def create_person(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/people", **_auth(conn), json_body=payload)


async def update_person(ctx, conn: dict, person_id: str, payload: dict) -> dict:
    return await request(ctx, "PUT", f"/people/{person_id}", **_auth(conn), json_body=payload)


async def delete_person(ctx, conn: dict, person_id: str) -> dict:
    return await request(ctx, "DELETE", f"/people/{person_id}", **_auth(conn))


# -- Events (the correct lead-intake channel) -----------------------------

async def create_event(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/events", **_auth(conn), json_body=payload)


async def list_events(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/events", "events", **_auth(conn), params=filters)


# -- Deals / Pipelines -----------------------------------------------------

async def list_deals(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/deals", "deals", **_auth(conn), params=filters)


async def get_deal(ctx, conn: dict, deal_id: str) -> dict:
    return await request(ctx, "GET", f"/deals/{deal_id}", **_auth(conn))


async def create_deal(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/deals", **_auth(conn), json_body=payload)


async def update_deal(ctx, conn: dict, deal_id: str, payload: dict) -> dict:
    return await request(ctx, "PUT", f"/deals/{deal_id}", **_auth(conn), json_body=payload)


async def delete_deal(ctx, conn: dict, deal_id: str) -> dict:
    return await request(ctx, "DELETE", f"/deals/{deal_id}", **_auth(conn))


async def list_pipelines(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/pipelines", "pipelines", **_auth(conn))


# -- Notes ------------------------------------------------------------------

async def list_notes(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/notes", "notes", **_auth(conn), params=filters)


async def create_note(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/notes", **_auth(conn), json_body=payload)


async def update_note(ctx, conn: dict, note_id: str, payload: dict) -> dict:
    return await request(ctx, "PUT", f"/notes/{note_id}", **_auth(conn), json_body=payload)


async def delete_note(ctx, conn: dict, note_id: str) -> dict:
    return await request(ctx, "DELETE", f"/notes/{note_id}", **_auth(conn))


# -- Calls --------------------------------------------------------------

async def list_calls(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/calls", "calls", **_auth(conn), params=filters)


async def log_call(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/calls", **_auth(conn), json_body=payload)


# -- Text Messages --------------------------------------------------------

async def list_text_messages(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/textMessages", "textmessages", **_auth(conn), params=filters)


async def send_text_message(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/textMessages", **_auth(conn), json_body=payload)


async def list_text_message_templates(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/textMessageTemplates", "textmessagetemplates", **_auth(conn))


async def create_text_message_template(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/textMessageTemplates", **_auth(conn), json_body=payload)


# -- Email templates --------------------------------------------------------

async def update_text_message_template(ctx, conn: dict, template_id: str, payload: dict) -> dict:
    return await request(ctx, "PUT", f"/textMessageTemplates/{template_id}", **_auth(conn), json_body=payload)


async def delete_text_message_template(ctx, conn: dict, template_id: str) -> dict:
    return await request(ctx, "DELETE", f"/textMessageTemplates/{template_id}", **_auth(conn))

async def list_email_templates(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/templates", "templates", **_auth(conn))


async def create_email_template(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/templates", **_auth(conn), json_body=payload)


# -- Appointments -----------------------------------------------------------

async def list_appointments(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/appointments", "appointments", **_auth(conn), params=filters)


async def create_appointment(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/appointments", **_auth(conn), json_body=payload)


async def list_appointment_types(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/appointmentTypes", "appointmenttypes", **_auth(conn))


async def list_appointment_outcomes(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/appointmentOutcomes", "appointmentoutcomes", **_auth(conn))


async def update_appointment(ctx, conn: dict, appt_id: str, payload: dict) -> dict:
    return await request(ctx, "PUT", f"/appointments/{appt_id}", **_auth(conn), json_body=payload)


async def delete_appointment(ctx, conn: dict, appt_id: str) -> dict:
    return await request(ctx, "DELETE", f"/appointments/{appt_id}", **_auth(conn))


# -- Tasks --------------------------------------------------------------

async def list_tasks(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/tasks", "tasks", **_auth(conn), params=filters)


async def create_task(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/tasks", **_auth(conn), json_body=payload)


async def update_task(ctx, conn: dict, task_id: str, payload: dict) -> dict:
    return await request(ctx, "PUT", f"/tasks/{task_id}", **_auth(conn), json_body=payload)


async def delete_task(ctx, conn: dict, task_id: str) -> dict:
    return await request(ctx, "DELETE", f"/tasks/{task_id}", **_auth(conn))


# -- Custom fields ------------------------------------------------------

async def list_custom_fields(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/customFields", "customfields", **_auth(conn))


async def create_custom_field(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/customFields", **_auth(conn), json_body=payload)


# -- Tags -----------------------------------------------------------------

async def add_person_tags(ctx, conn: dict, person_id: str, tags: list[str]) -> dict:
    return await request(ctx, "PUT", f"/people/{person_id}", **_auth(conn), json_body={"tags": tags, "_tagOp": "add"})


async def remove_person_tags(ctx, conn: dict, person_id: str, tags: list[str]) -> dict:
    return await request(ctx, "PUT", f"/people/{person_id}", **_auth(conn), json_body={"tags": tags, "_tagOp": "remove"})


# -- Users / Teams / Groups ------------------------------------------------

async def list_users(ctx, conn: dict, **filters) -> list[dict]:
    return await get_all(ctx, "/users", "users", **_auth(conn), params=filters)


async def get_user(ctx, conn: dict, user_id: str) -> dict:
    return await request(ctx, "GET", f"/users/{user_id}", **_auth(conn))


async def list_teams(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/teams", "teams", **_auth(conn))


async def list_groups(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/groups", "groups", **_auth(conn))


async def list_ponds(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/ponds", "ponds", **_auth(conn))


# -- Webhooks (Owner-only) --------------------------------------------------

async def list_webhooks(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/webhooks", "webhooks", **_auth(conn))


async def create_webhook(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/webhooks", **_auth(conn), json_body=payload)


async def delete_webhook(ctx, conn: dict, webhook_id: str) -> dict:
    return await request(ctx, "DELETE", f"/webhooks/{webhook_id}", **_auth(conn))


# -- Smart Lists ------------------------------------------------------------

async def list_smart_lists(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/smartLists", "smartlists", **_auth(conn))


async def get_smart_list_people(ctx, conn: dict, smart_list_id: str, **filters) -> list[dict]:
    return await get_all(ctx, f"/smartLists/{smart_list_id}/people", "people", **_auth(conn), params=filters)


# -- Action Plans (legacy) / Automations 2.0 --------------------------------

async def list_action_plans(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/actionPlans", "actionplans", **_auth(conn))


async def apply_action_plan(ctx, conn: dict, person_id: str, action_plan_id: str) -> dict:
    return await request(
        ctx, "POST", "/actionPlansPeople", **_auth(conn),
        json_body={"personId": person_id, "actionPlanId": action_plan_id},
    )


async def remove_action_plan(ctx, conn: dict, person_id: str, action_plan_id: str) -> dict:
    return await request(
        ctx, "DELETE", "/actionPlansPeople", **_auth(conn),
        json_body={"personId": person_id, "actionPlanId": action_plan_id},
    )


async def list_automations(ctx, conn: dict) -> list[dict]:
    return await get_all(ctx, "/automations", "automations", **_auth(conn))


async def trigger_automation(ctx, conn: dict, automation_id: str, person_id: str) -> dict:
    return await request(
        ctx, "POST", f"/automations/{automation_id}/trigger", **_auth(conn),
        json_body={"personId": person_id},
    )


# -- Relationships ------------------------------------------------------

async def list_relationships(ctx, conn: dict, person_id: str) -> list[dict]:
    return await get_all(ctx, "/peopleRelationships", "relationships", **_auth(conn), params={"personId": person_id})


async def create_relationship(ctx, conn: dict, payload: dict) -> dict:
    return await request(ctx, "POST", "/peopleRelationships", **_auth(conn), json_body=payload)


async def delete_relationship(ctx, conn: dict, relationship_id: str) -> dict:
    return await request(ctx, "DELETE", f"/peopleRelationships/{relationship_id}", **_auth(conn))
