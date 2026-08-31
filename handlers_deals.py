"""Deals & Pipelines -- the transaction-tracking side of Follow Up Boss
(distinct from People's lead-nurture stages; a Deal tracks one specific
transaction, e.g. a listing or a purchase, through its own pipeline).
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import followupboss_client as fc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ListDealsParams, DealEntity, DealList, GetDealParams,
    CreateDealParams, UpdateDealParams, DeleteDealParams, DeleteResult,
    ListPipelinesParams, PipelineEntity, PipelineList,
)


def _deal_entity(d: dict) -> DealEntity:
    people = ", ".join(p.get("name", "") for p in (d.get("people") or []) if p.get("name"))
    users = ", ".join(u.get("name", "") for u in (d.get("users") or []) if u.get("name"))
    return DealEntity(
        id=str(d.get("id", "")),
        name=d.get("name", ""),
        price=str(d.get("price", "")),
        stage=(d.get("stage") or {}).get("name", "") if isinstance(d.get("stage"), dict) else str(d.get("stage", "")),
        pipeline=(d.get("pipeline") or {}).get("name", "") if isinstance(d.get("pipeline"), dict) else str(d.get("pipeline", "")),
        status=d.get("status", ""),
        people=people,
        users=users,
        created=d.get("created", ""),
        updated=d.get("updated", ""),
    )


@chat.function(
    "list_deals",
    "List deals (transactions), optionally filtered by pipeline, stage, or linked person.",
    action_type="read",
    chain_callable=True,
    data_model=DealList,
    event="followupboss-connector.list_deals",
)
async def list_deals(ctx, params: ListDealsParams) -> ActionResult:
    """List deals (transactions), optionally filtered by pipeline, stage, or linked person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters: dict = {}
    if params.pipeline_id:
        filters["pipelineId"] = params.pipeline_id
    if params.stage_id:
        filters["stageId"] = params.stage_id
    if params.person_id:
        filters["personId"] = params.person_id
    filters["limit"] = params.limit
    filters["offset"] = params.offset
    try:
        deals = await fc.list_deals(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DealList(items=[_deal_entity(d) for d in deals], total=len(deals)), summary="Deals listed.")


@chat.function(
    "get_deal",
    "Read one deal in full.",
    action_type="read",
    chain_callable=True,
    data_model=DealEntity,
    event="followupboss-connector.get_deal",
)
async def get_deal(ctx, params: GetDealParams) -> ActionResult:
    """Read one deal in full."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        deal = await fc.get_deal(ctx, conn, params.deal_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(_deal_entity(deal), summary="Deal retrieved.")


@chat.function(
    "create_deal",
    "Create a new deal (transaction) in a pipeline stage, optionally linked to a person and price.",
    action_type="write",
    chain_callable=True,
    data_model=DealEntity,
    event="followupboss-connector.create_deal",
    effects=['create:deal'],
)
async def create_deal(ctx, params: CreateDealParams) -> ActionResult:
    """Create a new deal (transaction) in a pipeline stage, optionally linked to a person and price."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload: dict = {
        "name": params.name,
        "pipelineId": params.pipeline_id,
        "stageId": params.stage_id,
    }
    if params.person_id:
        payload["people"] = [{"id": params.person_id}]
    if params.price:
        payload["price"] = params.price
    if params.assigned_user_id:
        payload["users"] = [{"id": params.assigned_user_id}]
    try:
        deal = await fc.create_deal(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(_deal_entity(deal), summary="Deal created.")


@chat.function(
    "update_deal",
    "Update selected fields of an existing deal (name, stage, price, status).",
    action_type="write",
    chain_callable=True,
    data_model=DealEntity,
    event="followupboss-connector.update_deal",
    effects=['update:deal'],
)
async def update_deal(ctx, params: UpdateDealParams) -> ActionResult:
    """Update selected fields of an existing deal (name, stage, price, status)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload: dict = {}
    if params.name:
        payload["name"] = params.name
    if params.stage_id:
        payload["stageId"] = params.stage_id
    if params.price:
        payload["price"] = params.price
    if params.status:
        payload["status"] = params.status
    if not payload:
        return ActionResult.error("No fields to update -- pass at least one field to change.")
    try:
        deal = await fc.update_deal(ctx, conn, params.deal_id, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(_deal_entity(deal), summary="Deal updated.")


@chat.function(
    "delete_deal",
    "Permanently delete a deal. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_deal",
    effects=['delete:deal'],
)
async def delete_deal(ctx, params: DeleteDealParams) -> ActionResult:
    """Permanently delete a deal. Cannot be undone."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_deal(ctx, conn, params.deal_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Deal {params.deal_id} deleted."), summary="Deal deleted.")


@chat.function(
    "list_pipelines",
    "List pipelines and their stages (read-only -- pipelines/stages are configured inside Follow Up Boss itself).",
    action_type="read",
    chain_callable=True,
    data_model=PipelineList,
    event="followupboss-connector.list_pipelines",
)
async def list_pipelines(ctx, params: ListPipelinesParams) -> ActionResult:
    """List pipelines and their stages (read-only -- pipelines/stages are configured inside Follow Up Boss itself)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        pipelines = await fc.list_pipelines(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(PipelineList(items=[
        PipelineEntity(
            id=str(p.get("id", "")),
            name=p.get("name", ""),
            stages=", ".join(s.get("name", "") for s in (p.get("stages") or [])),
        ) for p in pipelines
    ]), summary="Pipelines listed.")
