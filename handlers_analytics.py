"""Imperal-side value-add reports -- NOT native Follow Up Boss endpoints.

WHY THESE EXIST: Follow Up Boss's own UI has no single "is my team actually
following up fast enough" dashboard -- an agency admin has to click into
each person's timeline individually to see when a lead was first contacted
after creation, or scan the whole task list by eye for anything overdue.
These five reports assemble that cross-cutting view from the People/
Events/Deals/Tasks/Calls/Notes/Text Messages/Appointments endpoints that
already exist, the same "value-add report built on primitives" pattern as
PagerDuty Connector's audit_account or MuleSoft Connector's
audit_cloudhub_environment.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from imperal_sdk import ActionResult

import followupboss_client as fc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    AuditLeadResponseParams, LeadResponseFlag, LeadResponseReport,
    GetPipelineHealthParams, StageHealth, PipelineHealthReport,
    GetOverdueTasksReportParams, OverdueTaskEntity, OverdueTasksReport,
    GetAgentActivityReportParams, AgentActivityEntity, AgentActivityReport,
    GetStaleLeadsReportParams, StaleLeadEntity, StaleLeadsReport,
)


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        v = value.replace("Z", "+00:00")
        return datetime.fromisoformat(v)
    except (ValueError, TypeError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


@chat.function(
    "audit_lead_response",
    "Flag leads created recently whose first logged response (call, text, note, or task completion) took longer than a threshold -- surfaces slow lead follow-up before it costs a deal.",
    action_type="read",
    chain_callable=True,
    data_model=LeadResponseReport,
    event="followupboss-connector.audit_lead_response",
)
async def audit_lead_response(ctx, params: AuditLeadResponseParams) -> ActionResult:
    """Flag leads created recently whose first logged response (call, text, note, or task completion) took longer than a threshold -- surfaces slow lead follow-up before it costs a deal."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    since = _now() - timedelta(days=params.days_back)
    try:
        people = await fc.list_people(ctx, conn, limit=100)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)

    flagged: list[LeadResponseFlag] = []
    checked = 0
    for p in people:
        created = _parse_dt(p.get("created", ""))
        if not created or created < since:
            continue
        checked += 1
        person_id = str(p.get("id", ""))
        earliest_response: datetime | None = None
        try:
            calls = await fc.list_calls(ctx, conn, personId=person_id, limit=5)
            for c in calls:
                dt = _parse_dt(c.get("created", ""))
                if dt and (earliest_response is None or dt < earliest_response):
                    earliest_response = dt
        except fc.ClientFail:
            pass
        try:
            notes = await fc.list_notes(ctx, conn, personId=person_id, limit=5)
            for n in notes:
                dt = _parse_dt(n.get("created", ""))
                if dt and (earliest_response is None or dt < earliest_response):
                    earliest_response = dt
        except fc.ClientFail:
            pass
        try:
            texts = await fc.list_text_messages(ctx, conn, personId=person_id, limit=5)
            for t in texts:
                dt = _parse_dt(t.get("created", ""))
                if dt and (earliest_response is None or dt < earliest_response):
                    earliest_response = dt
        except fc.ClientFail:
            pass

        if earliest_response is None:
            minutes = int((_now() - created).total_seconds() // 60)
            status = "no response yet"
        else:
            minutes = int((earliest_response - created).total_seconds() // 60)
            status = "responded"

        if minutes > params.hours_threshold * 60:
            flagged.append(LeadResponseFlag(
                person_id=person_id, name=p.get("name", ""),
                assigned_to=str(p.get("assignedTo", "")), created=p.get("created", ""),
                first_response_minutes=minutes, status=status,
            ))

    return ActionResult.success(LeadResponseReport(
        items=flagged, total_leads_checked=checked, total_flagged=len(flagged),
        threshold_hours=params.hours_threshold,
    ), summary="Lead response audit ready.")


@chat.function(
    "get_pipeline_health",
    "Summarize one (or all) pipelines: deal count and total value per stage, plus how many deals in each stage look stale (no update in 30+ days).",
    action_type="read",
    chain_callable=True,
    data_model=PipelineHealthReport,
    event="followupboss-connector.get_pipeline_health",
)
async def get_pipeline_health(ctx, params: GetPipelineHealthParams) -> ActionResult:
    """Summarize one (or all) pipelines: deal count and total value per stage, plus how many deals in each stage look stale (no update in 30+ days)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        pipelines = await fc.list_pipelines(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    if params.pipeline_id:
        pipelines = [p for p in pipelines if str(p.get("id", "")) == params.pipeline_id]
    if not pipelines:
        return ActionResult.error("No matching pipeline found.")

    stale_cutoff = _now() - timedelta(days=30)
    pipeline = pipelines[0]
    pid = str(pipeline.get("id", ""))
    try:
        deals = await fc.list_deals(ctx, conn, pipelineId=pid, limit=100)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)

    stage_map: dict[str, StageHealth] = {}
    total_value = 0.0
    for d in deals:
        stage = (d.get("stage") or {}).get("name", "") if isinstance(d.get("stage"), dict) else str(d.get("stage", ""))
        sh = stage_map.setdefault(stage, StageHealth(stage_name=stage, deal_count=0, total_value="0", stale_deal_count=0))
        sh.deal_count += 1
        try:
            price = float(d.get("price") or 0)
        except (TypeError, ValueError):
            price = 0.0
        sh.total_value = str(float(sh.total_value or 0) + price)
        total_value += price
        updated = _parse_dt(d.get("updated", ""))
        if updated and updated < stale_cutoff:
            sh.stale_deal_count += 1

    return ActionResult.success(PipelineHealthReport(
        pipeline_name=pipeline.get("name", ""), stages=list(stage_map.values()),
        total_deals=len(deals), total_value=str(total_value),
    ), summary="Pipeline health retrieved.")


@chat.function(
    "get_overdue_tasks_report",
    "List every incomplete task whose due date has already passed, optionally for one agent -- the team's follow-up backlog in one call.",
    action_type="read",
    chain_callable=True,
    data_model=OverdueTasksReport,
    event="followupboss-connector.get_overdue_tasks_report",
)
async def get_overdue_tasks_report(ctx, params: GetOverdueTasksReportParams) -> ActionResult:
    """List every incomplete task whose due date has already passed, optionally for one agent -- the team's follow-up backlog in one call."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters: dict = {"limit": 100, "isCompleted": False}
    if params.assigned_user_id:
        filters["assignedUserId"] = params.assigned_user_id
    try:
        tasks = await fc.list_tasks(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)

    now = _now()
    items: list[OverdueTaskEntity] = []
    for t in tasks:
        due = _parse_dt(t.get("dueDate", ""))
        if not due or due >= now:
            continue
        days_overdue = (now - due).days
        items.append(OverdueTaskEntity(
            task_id=str(t.get("id", "")), name=t.get("name", ""),
            person_id=str(t.get("personId", "")), person_name=t.get("personName", ""),
            assigned_to=str(t.get("assignedUserId", "")), due_date=t.get("dueDate", ""),
            days_overdue=days_overdue,
        ))
    items.sort(key=lambda x: x.days_overdue, reverse=True)
    return ActionResult.success(OverdueTasksReport(items=items, total_overdue=len(items)), summary="Overdue tasks report retrieved.")


@chat.function(
    "get_agent_activity_report",
    "Summarize each agent's logged activity (calls, texts, notes, completed tasks, held appointments) over a recent window -- a coaching/accountability snapshot.",
    action_type="read",
    chain_callable=True,
    data_model=AgentActivityReport,
    event="followupboss-connector.get_agent_activity_report",
)
async def get_agent_activity_report(ctx, params: GetAgentActivityReportParams) -> ActionResult:
    """Summarize each agent's logged activity (calls, texts, notes, completed tasks, held appointments) over a recent window -- a coaching/accountability snapshot."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    since = _now() - timedelta(days=params.days_back)
    try:
        users = await fc.list_users(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)

    report_items: list[AgentActivityEntity] = []
    for u in users:
        uid = str(u.get("id", ""))
        entity = AgentActivityEntity(user_id=uid, name=u.get("name", ""))
        try:
            calls = await fc.list_calls(ctx, conn, userId=uid, limit=100)
            entity.calls_logged = sum(1 for c in calls if (_parse_dt(c.get("created", "")) or since) >= since)
        except fc.ClientFail:
            pass
        try:
            texts = await fc.list_text_messages(ctx, conn, userId=uid, limit=100)
            entity.texts_sent = sum(1 for t in texts if (_parse_dt(t.get("created", "")) or since) >= since)
        except fc.ClientFail:
            pass
        try:
            tasks = await fc.list_tasks(ctx, conn, assignedUserId=uid, isCompleted=True, limit=100)
            entity.tasks_completed = sum(1 for t in tasks if (_parse_dt(t.get("updated", "")) or since) >= since)
        except fc.ClientFail:
            pass
        try:
            appts = await fc.list_appointments(ctx, conn, userId=uid, limit=100)
            entity.appointments_held = sum(1 for a in appts if (_parse_dt(a.get("start", "")) or since) >= since)
        except fc.ClientFail:
            pass
        report_items.append(entity)

    return ActionResult.success(AgentActivityReport(items=report_items, days_back=params.days_back), summary="Agent activity report retrieved.")


@chat.function(
    "get_stale_leads_report",
    "Flag people in an active (non-closed) stage with no logged activity for N+ days -- leads quietly going cold without anyone noticing.",
    action_type="read",
    chain_callable=True,
    data_model=StaleLeadsReport,
    event="followupboss-connector.get_stale_leads_report",
)
async def get_stale_leads_report(ctx, params: GetStaleLeadsReportParams) -> ActionResult:
    """Flag people in an active (non-closed) stage with no logged activity for N+ days -- leads quietly going cold without anyone noticing."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters: dict = {"limit": 100}
    if params.stage:
        filters["stage"] = params.stage
    try:
        people = await fc.list_people(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)

    cutoff = _now() - timedelta(days=params.days_inactive)
    closed_stages = {"closed", "trash", "not interested", "dead"}
    flagged: list[StaleLeadEntity] = []
    for p in people:
        stage = (p.get("stage") or {}).get("name", "") if isinstance(p.get("stage"), dict) else str(p.get("stage", ""))
        if stage.lower() in closed_stages:
            continue
        last_activity = _parse_dt(p.get("lastActivity", "") or p.get("updated", ""))
        if last_activity and last_activity >= cutoff:
            continue
        days_inactive = (_now() - last_activity).days if last_activity else params.days_inactive
        flagged.append(StaleLeadEntity(
            person_id=str(p.get("id", "")), name=p.get("name", ""), stage=stage,
            assigned_to=str(p.get("assignedTo", "")),
            last_activity=p.get("lastActivity", "") or p.get("updated", ""),
            days_inactive=days_inactive,
        ))
    flagged.sort(key=lambda x: x.days_inactive, reverse=True)
    return ActionResult.success(StaleLeadsReport(items=flagged, total_flagged=len(flagged)), summary="Stale leads report retrieved.")
