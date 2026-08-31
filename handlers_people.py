"""People (contacts) and Events (the official lead-intake channel).

WHY create_lead_event IS SEPARATE FROM create_person, AND WHY IT IS THE
RECOMMENDED WAY TO ADD A NEW LEAD (not create_person).

Follow Up Boss's own docs explicitly warn: "Avoid sending leads through
/v1/people!" -- POST /people only creates a bare person record and runs
NO automations, no dedup search, no agent notification, no Lead Flow
assignment (docs.followupboss.com/reference/people-post, confirmed
2026-08-22). The correct channel for a NEW lead is POST /events, which:
dedupes against existing contacts, records the inquiry in the person's
timeline, notifies the assigned agent, applies Action Plans/Automations,
and runs FUB's own Lead Flow assignment logic. create_person therefore
stays for admin/back-office use (fixing a name, adding a contact you
already know isn't a "hot lead" event) and its docstring says so plainly;
create_lead_event is the one to reach for whenever a NEW inbound lead is
being recorded.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import followupboss_client as fc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ListPeopleParams, PersonEntity, PersonList,
    GetPersonParams, CreatePersonParams, UpdatePersonParams,
    DeletePersonParams, DeleteResult,
    CreateLeadEventParams, ListEventsParams, EventEntity, EventList,
)


def _person_entity(p: dict) -> PersonEntity:
    emails = ", ".join(e.get("value", "") for e in (p.get("emails") or []) if e.get("value"))
    phones = ", ".join(ph.get("value", "") for ph in (p.get("phones") or []) if ph.get("value"))
    assigned = p.get("assignedTo") or ""
    tags = ", ".join(p.get("tags") or [])
    return PersonEntity(
        id=str(p.get("id", "")),
        name=p.get("name", ""),
        first_name=p.get("firstName", ""),
        last_name=p.get("lastName", ""),
        stage=p.get("stage", ""),
        source=p.get("source", ""),
        emails=emails,
        phones=phones,
        assigned_to=assigned,
        tags=tags,
        created=p.get("created", ""),
        updated=p.get("updated", ""),
        last_activity=p.get("lastActivity", ""),
    )


@chat.function(
    "list_people",
    "List people (contacts) in the connected Follow Up Boss account, with search/stage/tag/agent filters.",
    action_type="read",
    chain_callable=True,
    data_model=PersonList,
    event="followupboss-connector.list_people",
)
async def list_people(ctx, params: ListPeopleParams) -> ActionResult:
    """List people (contacts) in the connected Follow Up Boss account, with search/stage/tag/agent filters."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters: dict = {}
    if params.query:
        filters["q"] = params.query
    if params.stage:
        filters["stage"] = params.stage
    if params.assigned_user_id:
        filters["assignedUserId"] = params.assigned_user_id
    if params.tag:
        filters["tags"] = params.tag
    if params.include_trash:
        filters["includeTrash"] = "true"
    filters["limit"] = params.limit
    filters["offset"] = params.offset
    try:
        people = await fc.list_people(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(PersonList(items=[_person_entity(p) for p in people], total=len(people)), summary="People listed.")


@chat.function(
    "get_person",
    "Read one person in full, including emails/phones/tags/custom fields.",
    action_type="read",
    chain_callable=True,
    data_model=PersonEntity,
    event="followupboss-connector.get_person",
)
async def get_person(ctx, params: GetPersonParams) -> ActionResult:
    """Read one person in full, including emails/phones/tags/custom fields."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        person = await fc.get_person(ctx, conn, params.person_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(_person_entity(person), summary="Person retrieved.")


@chat.function(
    "create_person",
    "Create a person record directly (admin/back-office use). For a NEW inbound lead, use create_lead_event instead -- it dedupes, notifies the agent, and runs automations; this endpoint does none of that.",
    action_type="write",
    chain_callable=True,
    data_model=PersonEntity,
    event="followupboss-connector.create_person",
    effects=['create:person'],
)
async def create_person(ctx, params: CreatePersonParams) -> ActionResult:
    """Create a person record directly (admin/back-office use). For a NEW inbound lead, use create_lead_event instead -- it dedupes, notifies the agent, and runs automations; this endpoint does none of that."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload: dict = {}
    if params.first_name:
        payload["firstName"] = params.first_name
    if params.last_name:
        payload["lastName"] = params.last_name
    if params.email:
        payload["emails"] = [{"value": params.email}]
    if params.phone:
        payload["phones"] = [{"value": params.phone}]
    if params.stage:
        payload["stage"] = params.stage
    if params.source:
        payload["source"] = params.source
    if params.assigned_user_id:
        payload["assignedUserId"] = params.assigned_user_id
    try:
        person = await fc.create_person(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(_person_entity(person), summary="Person created.")


@chat.function(
    "update_person",
    "Update selected fields of an existing person. Note: source/sourceUrl can only be set on creation, not changed here.",
    action_type="write",
    chain_callable=True,
    data_model=PersonEntity,
    event="followupboss-connector.update_person",
    effects=['update:person'],
)
async def update_person(ctx, params: UpdatePersonParams) -> ActionResult:
    """Update selected fields of an existing person. Note: source/sourceUrl can only be set on creation, not changed here."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload: dict = {}
    if params.first_name:
        payload["firstName"] = params.first_name
    if params.last_name:
        payload["lastName"] = params.last_name
    if params.email:
        payload["emails"] = [{"value": params.email}]
    if params.phone:
        payload["phones"] = [{"value": params.phone}]
    if params.stage:
        payload["stage"] = params.stage
    if params.assigned_user_id:
        payload["assignedUserId"] = params.assigned_user_id
    if params.background:
        payload["background"] = params.background
    if not payload:
        return ActionResult.error("No fields to update -- pass at least one field to change.")
    try:
        person = await fc.update_person(ctx, conn, params.person_id, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(_person_entity(person), summary="Person updated.")


@chat.function(
    "delete_person",
    "Permanently delete a person record. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_person",
    effects=['delete:person'],
)
async def delete_person(ctx, params: DeletePersonParams) -> ActionResult:
    """Permanently delete a person record. Cannot be undone."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_person(ctx, conn, params.person_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Person {params.person_id} deleted."), summary="Person deleted.")


@chat.function(
    "create_lead_event",
    "Record a NEW inbound lead the recommended Follow Up Boss way (POST /events) -- dedupes against existing contacts, notifies the assigned agent, applies Action Plans/Automations, and runs Lead Flow assignment. Use this instead of create_person for any new lead.",
    action_type="write",
    chain_callable=True,
    data_model=EventEntity,
    event="followupboss-connector.create_lead_event",
    effects=['create:event'],
)
async def create_lead_event(ctx, params: CreateLeadEventParams) -> ActionResult:
    """Record a NEW inbound lead the recommended Follow Up Boss way (POST /events) -- dedupes against existing contacts, notifies the assigned agent, applies Action Plans/Automations, and runs Lead Flow assignment. Use this instead of create_person for any new lead."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    person: dict = {}
    if params.first_name:
        person["firstName"] = params.first_name
    if params.last_name:
        person["lastName"] = params.last_name
    if params.email:
        person["emails"] = [{"value": params.email}]
    if params.phone:
        person["phones"] = [{"value": params.phone}]
    payload = {
        "source": params.source,
        "type": params.type,
        "person": person,
    }
    if params.message:
        payload["message"] = params.message
    if params.source_url:
        payload["sourceUrl"] = params.source_url
    if params.property_address or params.property_url:
        payload["property"] = {
            k: v for k, v in {
                "street": params.property_address,
                "url": params.property_url,
            }.items() if v
        }
    if params.custom_fields_json:
        import json as _json
        try:
            payload["customFields"] = _json.loads(params.custom_fields_json)
        except (TypeError, ValueError):
            return ActionResult.error("custom_fields_json is not valid JSON.")
    try:
        result = await fc.create_event(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(EventEntity(
        id=str(result.get("id", "")),
        type=result.get("type", params.type),
        person_id=str((result.get("person") or {}).get("id", "")),
        source=params.source,
        message=params.message,
        created=result.get("created", ""),
    ), summary="Lead event created.")


@chat.function(
    "list_events",
    "List recorded lead events (inquiries, property views, registrations), optionally filtered to one person.",
    action_type="read",
    chain_callable=True,
    data_model=EventList,
    event="followupboss-connector.list_events",
)
async def list_events(ctx, params: ListEventsParams) -> ActionResult:
    """List recorded lead events (inquiries, property views, registrations), optionally filtered to one person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters: dict = {}
    if params.person_id:
        filters["personId"] = params.person_id
    filters["limit"] = params.limit
    filters["offset"] = params.offset
    try:
        events = await fc.list_events(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(EventList(items=[
        EventEntity(
            id=str(e.get("id", "")),
            type=e.get("type", ""),
            person_id=str((e.get("person") or {}).get("id", "")),
            source=e.get("source", ""),
            message=e.get("message", ""),
            created=e.get("created", ""),
        ) for e in events
    ]), summary="Events listed.")
