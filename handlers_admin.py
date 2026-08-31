"""Admin/config surfaces: Custom Fields, Tags, Users/Teams/Ponds, Webhooks,
Smart Lists, Action Plans (legacy) + Automations 2.0, Person Relationships,
Email Templates. Grouped together since they are mostly read-heavy
configuration/organization resources rather than day-to-day CRM activity.
"""
from __future__ import annotations

import json as _json

from imperal_sdk import ActionResult

import followupboss_client as fc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ListCustomFieldsParams, CustomFieldEntity, CustomFieldList, CreateCustomFieldParams,
    AddPersonTagsParams, RemovePersonTagsParams,
    ListUsersParams, UserEntity, UserList,
    ListTeamsParams, TeamEntity, TeamList,
    ListPondsParams, PondEntity, PondList,
    ListWebhooksParams, WebhookEntity, WebhookList, CreateWebhookParams, DeleteWebhookParams,
    ListSmartListsParams, SmartListEntity, SmartListList, GetSmartListPeopleParams,
    ListPersonRelationshipsParams, RelationshipEntity, RelationshipList,
    CreatePersonRelationshipParams, DeletePersonRelationshipParams,
    ListActionPlansParams, ActionPlanEntity, ActionPlanList,
    ApplyActionPlanParams, RemoveActionPlanParams,
    ListAutomationsParams, AutomationEntity, AutomationList, TriggerAutomationParams,
    ListEmailTemplatesParams, EmailTemplateEntity, EmailTemplateList, CreateEmailTemplateParams,
    DeleteResult, PersonList, PersonEntity,
)


# -- Custom Fields -----------------------------------------------------

@chat.function(
    "list_custom_fields",
    "List custom field definitions configured on this Follow Up Boss account.",
    action_type="read",
    chain_callable=True,
    data_model=CustomFieldList,
    event="followupboss-connector.list_custom_fields",
)
async def list_custom_fields(ctx, params: ListCustomFieldsParams) -> ActionResult:
    """List custom field definitions configured on this Follow Up Boss account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        fields = await fc.list_custom_fields(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [CustomFieldEntity(id=str(f.get("id", "")), name=f.get("name", ""), label=f.get("label", ""),
                                type=f.get("type", ""), is_recurring=bool(f.get("isRecurring", False)),
                                choices=", ".join(f.get("choices") or [])) for f in fields]
    return ActionResult.success(CustomFieldList(items=items), summary="Custom fields listed.")


@chat.function(
    "create_custom_field",
    "Create a new custom field on this Follow Up Boss account (text, date, number, or dropdown).",
    action_type="write",
    chain_callable=True,
    data_model=CustomFieldEntity,
    event="followupboss-connector.create_custom_field",
    effects=['create:custom_field'],
)
async def create_custom_field(ctx, params: CreateCustomFieldParams) -> ActionResult:
    """Create a new custom field on this Follow Up Boss account (text, date, number, or dropdown)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"label": params.label, "type": params.type}
    if params.type == "dropdown":
        if not params.choices_json:
            return ActionResult.error("choices_json is required when type='dropdown'.")
        try:
            payload["choices"] = _json.loads(params.choices_json)
        except (TypeError, ValueError):
            return ActionResult.error("choices_json is not valid JSON.")
    if params.type == "date" and params.is_recurring:
        payload["isRecurring"] = True
    try:
        field = await fc.create_custom_field(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(CustomFieldEntity(id=str(field.get("id", "")), name=field.get("name", ""),
                 label=field.get("label", ""), type=field.get("type", "")), summary="Custom field created.")


# -- Tags ----------------------------------------------------------------

@chat.function(
    "add_person_tags",
    "Add one or more tags to a person.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.add_person_tags",
    effects=['update:person'],
)
async def add_person_tags(ctx, params: AddPersonTagsParams) -> ActionResult:
    """Add one or more tags to a person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.add_person_tags(ctx, conn, params.person_id, params.tags)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Added tags to person {params.person_id}."), summary="Person tags created.")


@chat.function(
    "remove_person_tags",
    "Remove one or more tags from a person.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.remove_person_tags",
    effects=['update:person'],
)
async def remove_person_tags(ctx, params: RemovePersonTagsParams) -> ActionResult:
    """Remove one or more tags from a person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.remove_person_tags(ctx, conn, params.person_id, params.tags)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Removed tags from person {params.person_id}."), summary="Person tags deleted.")


# -- Users / Teams / Ponds -------------------------------------------------

@chat.function(
    "list_users",
    "List users (agents/staff) on this Follow Up Boss account.",
    action_type="read",
    chain_callable=True,
    data_model=UserList,
    event="followupboss-connector.list_users",
)
async def list_users(ctx, params: ListUsersParams) -> ActionResult:
    """List users (agents/staff) on this Follow Up Boss account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        users = await fc.list_users(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [UserEntity(id=str(u.get("id", "")), name=u.get("name", ""), email=u.get("email", ""),
                         role=u.get("role", ""), is_active=bool(u.get("isActive", True))) for u in users]
    return ActionResult.success(UserList(items=items), summary="Users listed.")


@chat.function(
    "list_teams",
    "List teams configured on this Follow Up Boss account.",
    action_type="read",
    chain_callable=True,
    data_model=TeamList,
    event="followupboss-connector.list_teams",
)
async def list_teams(ctx, params: ListTeamsParams) -> ActionResult:
    """List teams configured on this Follow Up Boss account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        teams = await fc.list_teams(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [TeamEntity(id=str(t.get("id", "")), name=t.get("name", ""),
                         member_count=len(t.get("users") or [])) for t in teams]
    return ActionResult.success(TeamList(items=items), summary="Teams listed.")


@chat.function(
    "list_ponds",
    "List Ponds (shared lead pools agents can claim from) configured on this account.",
    action_type="read",
    chain_callable=True,
    data_model=PondList,
    event="followupboss-connector.list_ponds",
)
async def list_ponds(ctx, params: ListPondsParams) -> ActionResult:
    """List Ponds (shared lead pools agents can claim from) configured on this account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        ponds = await fc.list_ponds(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [PondEntity(id=str(p.get("id", "")), name=p.get("name", "")) for p in ponds]
    return ActionResult.success(PondList(items=items), summary="Ponds listed.")


# -- Webhooks (Owner-only) -------------------------------------------------

@chat.function(
    "list_webhooks",
    "List webhook subscriptions configured on this Follow Up Boss account (Account Owner role required by FUB).",
    action_type="read",
    chain_callable=True,
    data_model=WebhookList,
    event="followupboss-connector.list_webhooks",
)
async def list_webhooks(ctx, params: ListWebhooksParams) -> ActionResult:
    """List webhook subscriptions configured on this Follow Up Boss account (Account Owner role required by FUB)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        hooks = await fc.list_webhooks(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [WebhookEntity(id=str(h.get("id", "")), event=h.get("event", ""), url=h.get("url", ""),
                            is_active=bool(h.get("isActive", True))) for h in hooks]
    return ActionResult.success(WebhookList(items=items), summary="Webhooks listed.")


@chat.function(
    "create_webhook",
    "Subscribe to a Follow Up Boss event (e.g. peopleCreated, peopleStageUpdated, callCreated) -- FUB will POST to your URL.",
    action_type="write",
    chain_callable=True,
    data_model=WebhookEntity,
    event="followupboss-connector.create_webhook",
    effects=['create:webhook'],
)
async def create_webhook(ctx, params: CreateWebhookParams) -> ActionResult:
    """Subscribe to a Follow Up Boss event (e.g. peopleCreated, peopleStageUpdated, callCreated) -- FUB will POST to your URL."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        hook = await fc.create_webhook(ctx, conn, {"event": params.event, "url": params.url})
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(WebhookEntity(id=str(hook.get("id", "")), event=hook.get("event", ""),
                 url=hook.get("url", ""), is_active=True), summary="Webhook created.")


@chat.function(
    "delete_webhook",
    "Permanently remove a webhook subscription.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_webhook",
    effects=['delete:webhook'],
)
async def delete_webhook(ctx, params: DeleteWebhookParams) -> ActionResult:
    """Permanently remove a webhook subscription."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_webhook(ctx, conn, params.webhook_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Webhook {params.webhook_id} deleted."), summary="Webhook deleted.")


# -- Smart Lists ------------------------------------------------------------

@chat.function(
    "list_smart_lists",
    "List Smart Lists (saved dynamic filters) configured on this Follow Up Boss account.",
    action_type="read",
    chain_callable=True,
    data_model=SmartListList,
    event="followupboss-connector.list_smart_lists",
)
async def list_smart_lists(ctx, params: ListSmartListsParams) -> ActionResult:
    """List Smart Lists (saved dynamic filters) configured on this Follow Up Boss account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        lists = await fc.list_smart_lists(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [SmartListEntity(id=str(s.get("id", "")), name=s.get("name", ""),
                              person_count=int(s.get("personCount", 0) or 0)) for s in lists]
    return ActionResult.success(SmartListList(items=items), summary="Smart lists listed.")


@chat.function(
    "get_smart_list_people",
    "List the people currently matching one Smart List's saved filter.",
    action_type="read",
    chain_callable=True,
    data_model=PersonList,
    event="followupboss-connector.get_smart_list_people",
)
async def get_smart_list_people(ctx, params: GetSmartListPeopleParams) -> ActionResult:
    """List the people currently matching one Smart List's saved filter."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        people = await fc.get_smart_list_people(ctx, conn, params.smart_list_id, limit=params.limit, offset=params.offset)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [PersonEntity(id=str(p.get("id", "")), name=p.get("name", ""),
                           first_name=p.get("firstName", ""), last_name=p.get("lastName", ""),
                           stage=(p.get("stage") or {}).get("name", "") if isinstance(p.get("stage"), dict) else str(p.get("stage", "")),
                           source=p.get("source", "")) for p in people]
    return ActionResult.success(PersonList(items=items, total=len(items)), summary="Smart list people retrieved.")


# -- Person Relationships ---------------------------------------------------

@chat.function(
    "list_person_relationships",
    "List a person's linked relationships (e.g. spouse, co-buyer, referral source).",
    action_type="read",
    chain_callable=True,
    data_model=RelationshipList,
    event="followupboss-connector.list_person_relationships",
)
async def list_person_relationships(ctx, params: ListPersonRelationshipsParams) -> ActionResult:
    """List a person's linked relationships (e.g. spouse, co-buyer, referral source)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        rels = await fc.list_relationships(ctx, conn, params.person_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [RelationshipEntity(id=str(r.get("id", "")), person_id=str(r.get("personId", "")),
                                 related_person_id=str(r.get("relatedPersonId", "")),
                                 related_name=r.get("relatedName", ""), type=r.get("type", "")) for r in rels]
    return ActionResult.success(RelationshipList(items=items), summary="Person relationships listed.")


@chat.function(
    "create_person_relationship",
    "Link two people together with a named relationship (e.g. spouse, co-buyer).",
    action_type="write",
    chain_callable=True,
    data_model=RelationshipEntity,
    event="followupboss-connector.create_person_relationship",
    effects=['create:relationship'],
)
async def create_person_relationship(ctx, params: CreatePersonRelationshipParams) -> ActionResult:
    """Link two people together with a named relationship (e.g. spouse, co-buyer)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"personId": params.person_id, "relatedPersonId": params.related_person_id, "type": params.type}
    try:
        rel = await fc.create_relationship(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(RelationshipEntity(id=str(rel.get("id", "")), person_id=params.person_id,
                 related_person_id=params.related_person_id, type=params.type), summary="Person relationship created.")


@chat.function(
    "delete_person_relationship",
    "Permanently remove a relationship link between two people.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_person_relationship",
    effects=['delete:relationship'],
)
async def delete_person_relationship(ctx, params: DeletePersonRelationshipParams) -> ActionResult:
    """Permanently remove a relationship link between two people."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_relationship(ctx, conn, params.relationship_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Relationship {params.relationship_id} deleted."), summary="Person relationship deleted.")


# -- Action Plans (legacy) / Automations 2.0 --------------------------------

@chat.function(
    "list_action_plans",
    "List Action Plans configured on this account (legacy multi-step nurture sequences -- see also list_automations for Automations 2.0).",
    action_type="read",
    chain_callable=True,
    data_model=ActionPlanList,
    event="followupboss-connector.list_action_plans",
)
async def list_action_plans(ctx, params: ListActionPlansParams) -> ActionResult:
    """List Action Plans configured on this account (legacy multi-step nurture sequences -- see also list_automations for Automations 2.0)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        plans = await fc.list_action_plans(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [ActionPlanEntity(id=str(p.get("id", "")), name=p.get("name", ""),
                               is_active=bool(p.get("isActive", True)),
                               step_count=int(p.get("stepCount", 0) or 0)) for p in plans]
    return ActionResult.success(ActionPlanList(items=items), summary="Action plans listed.")


@chat.function(
    "apply_action_plan",
    "Enroll a person into an Action Plan (starts its sequence of steps).",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.apply_action_plan",
    effects=['update:person'],
)
async def apply_action_plan(ctx, params: ApplyActionPlanParams) -> ActionResult:
    """Enroll a person into an Action Plan (starts its sequence of steps)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.apply_action_plan(ctx, conn, params.person_id, params.action_plan_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Person {params.person_id} enrolled in Action Plan {params.action_plan_id}."), summary="Apply action plan done.")


@chat.function(
    "remove_action_plan",
    "Remove a person from an Action Plan (stops its remaining steps).",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.remove_action_plan",
    effects=['update:person'],
)
async def remove_action_plan(ctx, params: RemoveActionPlanParams) -> ActionResult:
    """Remove a person from an Action Plan (stops its remaining steps)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.remove_action_plan(ctx, conn, params.person_id, params.action_plan_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Person {params.person_id} removed from Action Plan {params.action_plan_id}."), summary="Action plan deleted.")


@chat.function(
    "list_automations",
    "List Automations 2.0 configured on this account (the newer trigger-based rules engine).",
    action_type="read",
    chain_callable=True,
    data_model=AutomationList,
    event="followupboss-connector.list_automations",
)
async def list_automations(ctx, params: ListAutomationsParams) -> ActionResult:
    """List Automations 2.0 configured on this account (the newer trigger-based rules engine)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        autos = await fc.list_automations(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [AutomationEntity(id=str(a.get("id", "")), name=a.get("name", ""), trigger=a.get("trigger", ""),
                               is_active=bool(a.get("isActive", True))) for a in autos]
    return ActionResult.success(AutomationList(items=items), summary="Automations listed.")


@chat.function(
    "trigger_automation",
    "Manually run an Automation against one person, outside of its normal trigger condition.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.trigger_automation",
    effects=['update:person'],
)
async def trigger_automation(ctx, params: TriggerAutomationParams) -> ActionResult:
    """Manually run an Automation against one person, outside of its normal trigger condition."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.trigger_automation(ctx, conn, params.automation_id, params.person_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Automation {params.automation_id} triggered for person {params.person_id}."), summary="Automation trigger requested.")


# -- Email Templates ---------------------------------------------------

@chat.function(
    "list_email_templates",
    "List saved email templates on this Follow Up Boss account.",
    action_type="read",
    chain_callable=True,
    data_model=EmailTemplateList,
    event="followupboss-connector.list_email_templates",
)
async def list_email_templates(ctx, params: ListEmailTemplatesParams) -> ActionResult:
    """List saved email templates on this Follow Up Boss account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        templates = await fc.list_email_templates(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [EmailTemplateEntity(id=str(t.get("id", "")), name=t.get("name", ""),
                                  subject=t.get("subject", ""), body=t.get("body", "")) for t in templates]
    return ActionResult.success(EmailTemplateList(items=items), summary="Email templates listed.")


@chat.function(
    "create_email_template",
    "Create a reusable email template.",
    action_type="write",
    chain_callable=True,
    data_model=EmailTemplateEntity,
    event="followupboss-connector.create_email_template",
    effects=['create:template'],
)
async def create_email_template(ctx, params: CreateEmailTemplateParams) -> ActionResult:
    """Create a reusable email template."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"name": params.name, "subject": params.subject, "body": params.body}
    try:
        template = await fc.create_email_template(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(EmailTemplateEntity(id=str(template.get("id", "")), name=params.name,
                 subject=params.subject, body=params.body), summary="Email template created.")
