"""Activity: Notes, Tasks, Calls, Text Messages (+templates), Appointments
(+types/outcomes) -- every day-to-day touchpoint an agent logs against a
person, grouped in one module since they share the same CRUD shape.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import followupboss_client as fc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ListNotesParams, NoteEntity, NoteList, CreateNoteParams,
    UpdateNoteParams, DeleteNoteParams, DeleteResult,
    ListTasksParams, TaskEntity, TaskList, CreateTaskParams,
    UpdateTaskParams, DeleteTaskParams,
    ListCallsParams, CallEntity, CallList, LogCallParams,
    ListTextMessagesParams, TextMessageEntity, TextMessageList,
    SendTextMessageParams,
    ListTextMessageTemplatesParams, TextMessageTemplateEntity, TextMessageTemplateList,
    CreateTextMessageTemplateParams, UpdateTextMessageTemplateParams,
    DeleteTextMessageTemplateParams,
    ListAppointmentsParams, AppointmentEntity, AppointmentList,
    CreateAppointmentParams, UpdateAppointmentParams, DeleteAppointmentParams,
    ListAppointmentTypesParams, AppointmentTypeEntity, AppointmentTypeList,
    ListAppointmentOutcomesParams, AppointmentOutcomeEntity, AppointmentOutcomeList,
)


# -- Notes -----------------------------------------------------------------

@chat.function(
    "list_notes",
    "List notes, optionally filtered to one person.",
    action_type="read",
    chain_callable=True,
    data_model=NoteList,
    event="followupboss-connector.list_notes",
)
async def list_notes(ctx, params: ListNotesParams) -> ActionResult:
    """List notes, optionally filtered to one person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters = {"limit": params.limit, "offset": params.offset}
    if params.person_id:
        filters["personId"] = params.person_id
    try:
        notes = await fc.list_notes(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [NoteEntity(id=str(n.get("id", "")), subject=n.get("subject", ""), body=n.get("body", ""),
                         person_id=str(n.get("personId", "")), created_by=str(n.get("createdBy", "")),
                         created=n.get("created", "")) for n in notes]
    return ActionResult.success(NoteList(items=items), summary="Notes listed.")


@chat.function(
    "create_note",
    "Add a note to a person's timeline.",
    action_type="write",
    chain_callable=True,
    data_model=NoteEntity,
    event="followupboss-connector.create_note",
    effects=['create:note'],
)
async def create_note(ctx, params: CreateNoteParams) -> ActionResult:
    """Add a note to a person's timeline."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"personId": params.person_id, "body": params.body, "isHtml": params.is_html}
    if params.subject:
        payload["subject"] = params.subject
    try:
        note = await fc.create_note(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(NoteEntity(id=str(note.get("id", "")), subject=note.get("subject", ""),
                                            body=note.get("body", ""), person_id=str(note.get("personId", "")),
                                            created=note.get("created", "")), summary="Note created.")


@chat.function(
    "update_note",
    "Update an existing note's subject and/or body.",
    action_type="write",
    chain_callable=True,
    data_model=NoteEntity,
    event="followupboss-connector.update_note",
    effects=['update:note'],
)
async def update_note(ctx, params: UpdateNoteParams) -> ActionResult:
    """Update an existing note's subject and/or body."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {}
    if params.subject:
        payload["subject"] = params.subject
    if params.body:
        payload["body"] = params.body
    if not payload:
        return ActionResult.error("No fields to update.")
    try:
        note = await fc.update_note(ctx, conn, params.note_id, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(NoteEntity(id=str(note.get("id", "")), subject=note.get("subject", ""),
                                            body=note.get("body", "")), summary="Note updated.")


@chat.function(
    "delete_note",
    "Permanently delete a note.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_note",
    effects=['delete:note'],
)
async def delete_note(ctx, params: DeleteNoteParams) -> ActionResult:
    """Permanently delete a note."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_note(ctx, conn, params.note_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Note {params.note_id} deleted."), summary="Note deleted.")


# -- Tasks -------------------------------------------------------------

@chat.function(
    "list_tasks",
    "List tasks, optionally filtered by person, assigned agent, or completion status.",
    action_type="read",
    chain_callable=True,
    data_model=TaskList,
    event="followupboss-connector.list_tasks",
)
async def list_tasks(ctx, params: ListTasksParams) -> ActionResult:
    """List tasks, optionally filtered by person, assigned agent, or completion status."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters = {"limit": params.limit, "offset": params.offset}
    if params.person_id:
        filters["personId"] = params.person_id
    if params.assigned_user_id:
        filters["assignedUserId"] = params.assigned_user_id
    if params.is_completed:
        filters["isCompleted"] = params.is_completed
    try:
        tasks = await fc.list_tasks(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [TaskEntity(id=str(t.get("id", "")), name=t.get("name", ""), person_id=str(t.get("personId", "")),
                         assigned_to=str(t.get("assignedUserId", "")), due_date=t.get("dueDate", ""),
                         is_completed=bool(t.get("isCompleted", False)), type=t.get("type", ""),
                         created=t.get("created", "")) for t in tasks]
    return ActionResult.success(TaskList(items=items), summary="Tasks listed.")


@chat.function(
    "create_task",
    "Create a follow-up task against a person.",
    action_type="write",
    chain_callable=True,
    data_model=TaskEntity,
    event="followupboss-connector.create_task",
    effects=['create:task'],
)
async def create_task(ctx, params: CreateTaskParams) -> ActionResult:
    """Create a follow-up task against a person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"personId": params.person_id, "name": params.name}
    if params.due_date:
        payload["dueDate"] = params.due_date
    if params.assigned_user_id:
        payload["assignedUserId"] = params.assigned_user_id
    if params.type:
        payload["type"] = params.type
    try:
        task = await fc.create_task(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(TaskEntity(id=str(task.get("id", "")), name=task.get("name", ""),
                                            due_date=task.get("dueDate", "")), summary="Task created.")


@chat.function(
    "update_task",
    "Update a task's name, due date, or mark it completed.",
    action_type="write",
    chain_callable=True,
    data_model=TaskEntity,
    event="followupboss-connector.update_task",
    effects=['update:task'],
)
async def update_task(ctx, params: UpdateTaskParams) -> ActionResult:
    """Update a task's name, due date, or mark it completed."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {}
    if params.name:
        payload["name"] = params.name
    if params.due_date:
        payload["dueDate"] = params.due_date
    if params.is_completed:
        payload["isCompleted"] = True
    if not payload:
        return ActionResult.error("No fields to update.")
    try:
        task = await fc.update_task(ctx, conn, params.task_id, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(TaskEntity(id=str(task.get("id", "")), name=task.get("name", ""),
                                            is_completed=bool(task.get("isCompleted", False))), summary="Task updated.")


@chat.function(
    "delete_task",
    "Permanently delete a task.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_task",
    effects=['delete:task'],
)
async def delete_task(ctx, params: DeleteTaskParams) -> ActionResult:
    """Permanently delete a task."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_task(ctx, conn, params.task_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Task {params.task_id} deleted."), summary="Task deleted.")


# -- Calls ---------------------------------------------------------------

@chat.function(
    "list_calls",
    "List logged calls, optionally filtered by person or user.",
    action_type="read",
    chain_callable=True,
    data_model=CallList,
    event="followupboss-connector.list_calls",
)
async def list_calls(ctx, params: ListCallsParams) -> ActionResult:
    """List logged calls, optionally filtered by person or user."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters = {"limit": params.limit, "offset": params.offset}
    if params.person_id:
        filters["personId"] = params.person_id
    if params.user_id:
        filters["userId"] = params.user_id
    try:
        calls = await fc.list_calls(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [CallEntity(id=str(c.get("id", "")), person_id=str(c.get("personId", "")),
                         user_id=str(c.get("userId", "")), duration=int(c.get("duration", 0) or 0),
                         outcome=c.get("outcome", ""), note=c.get("note", ""),
                         is_incoming=bool(c.get("isIncoming", False)), created=c.get("created", "")) for c in calls]
    return ActionResult.success(CallList(items=items), summary="Calls listed.")


@chat.function(
    "log_call",
    "Log a call made or received with a person, with duration/outcome/note.",
    action_type="write",
    chain_callable=True,
    data_model=CallEntity,
    event="followupboss-connector.log_call",
    effects=['create:call'],
)
async def log_call(ctx, params: LogCallParams) -> ActionResult:
    """Log a call made or received with a person, with duration/outcome/note."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"personId": params.person_id, "isIncoming": params.is_incoming}
    if params.duration:
        payload["duration"] = params.duration
    if params.outcome:
        payload["outcome"] = params.outcome
    if params.note:
        payload["note"] = params.note
    if params.phone:
        payload["phone"] = params.phone
    try:
        call = await fc.log_call(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(CallEntity(id=str(call.get("id", "")), person_id=str(call.get("personId", "")),
                 user_id=str(call.get("userId", "")), duration=int(call.get("duration", 0) or 0),
                 outcome=call.get("outcome", ""), note=call.get("note", ""),
                 is_incoming=bool(call.get("isIncoming", False)), created=call.get("created", "")), summary="Log call done.")


# -- Text Messages ---------------------------------------------------------

@chat.function(
    "list_text_messages",
    "List SMS/text message history, optionally filtered to one person.",
    action_type="read",
    chain_callable=True,
    data_model=TextMessageList,
    event="followupboss-connector.list_text_messages",
)
async def list_text_messages(ctx, params: ListTextMessagesParams) -> ActionResult:
    """List SMS/text message history, optionally filtered to one person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters = {"limit": params.limit, "offset": params.offset}
    if params.person_id:
        filters["personId"] = params.person_id
    try:
        texts = await fc.list_text_messages(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [TextMessageEntity(id=str(t.get("id", "")), person_id=str(t.get("personId", "")),
                                message=t.get("message", ""), is_incoming=bool(t.get("isIncoming", False)),
                                created=t.get("created", "")) for t in texts]
    return ActionResult.success(TextMessageList(items=items), summary="Text messages listed.")


@chat.function(
    "send_text_message",
    "Send an SMS text message to a person through Follow Up Boss's own texting feature.",
    action_type="write",
    chain_callable=True,
    data_model=TextMessageEntity,
    event="followupboss-connector.send_text_message",
    effects=['create:text_message'],
)
async def send_text_message(ctx, params: SendTextMessageParams) -> ActionResult:
    """Send an SMS text message to a person through Follow Up Boss's own texting feature."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"personId": params.person_id, "message": params.message}
    if params.to_number:
        payload["toNumber"] = params.to_number
    try:
        text = await fc.send_text_message(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(TextMessageEntity(id=str(text.get("id", "")), person_id=str(text.get("personId", "")),
                 message=text.get("message", ""), is_incoming=False, created=text.get("created", "")), summary="Text message send requested.")


@chat.function(
    "list_text_message_templates",
    "List saved SMS templates.",
    action_type="read",
    chain_callable=True,
    data_model=TextMessageTemplateList,
    event="followupboss-connector.list_text_message_templates",
)
async def list_text_message_templates(ctx, params: ListTextMessageTemplatesParams) -> ActionResult:
    """List saved SMS templates."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        templates = await fc.list_text_message_templates(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [TextMessageTemplateEntity(id=str(t.get("id", "")), name=t.get("name", ""),
                                        message=t.get("message", "")) for t in templates]
    return ActionResult.success(TextMessageTemplateList(items=items), summary="Text message templates listed.")


@chat.function(
    "create_text_message_template",
    "Create a reusable SMS template.",
    action_type="write",
    chain_callable=True,
    data_model=TextMessageTemplateEntity,
    event="followupboss-connector.create_text_message_template",
    effects=['create:template'],
)
async def create_text_message_template(ctx, params: CreateTextMessageTemplateParams) -> ActionResult:
    """Create a reusable SMS template."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        t = await fc.create_text_message_template(ctx, conn, {"name": params.name, "message": params.message})
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(TextMessageTemplateEntity(id=str(t.get("id", "")), name=t.get("name", ""),
                 message=t.get("message", "")), summary="Text message template created.")


@chat.function(
    "update_text_message_template",
    "Update an existing SMS template's name and/or text.",
    action_type="write",
    chain_callable=True,
    data_model=TextMessageTemplateEntity,
    event="followupboss-connector.update_text_message_template",
    effects=['update:template'],
)
async def update_text_message_template(ctx, params: UpdateTextMessageTemplateParams) -> ActionResult:
    """Update an existing SMS template's name and/or text."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {}
    if params.name:
        payload["name"] = params.name
    if params.message:
        payload["message"] = params.message
    if not payload:
        return ActionResult.error("No fields to update -- pass a new name and/or message.")
    try:
        t = await fc.update_text_message_template(ctx, conn, params.template_id, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(TextMessageTemplateEntity(id=str(t.get("id", "")), name=t.get("name", ""),
                 message=t.get("message", "")), summary="Text message template updated.")


@chat.function(
    "delete_text_message_template",
    "Permanently delete an SMS template.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_text_message_template",
    effects=['delete:template'],
)
async def delete_text_message_template(ctx, params: DeleteTextMessageTemplateParams) -> ActionResult:
    """Permanently delete an SMS template."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_text_message_template(ctx, conn, params.template_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Template {params.template_id} deleted."), summary="Text message template deleted.")


# -- Appointments ------------------------------------------------------

@chat.function(
    "list_appointments",
    "List appointments/showings, optionally filtered by person or assigned agent.",
    action_type="read",
    chain_callable=True,
    data_model=AppointmentList,
    event="followupboss-connector.list_appointments",
)
async def list_appointments(ctx, params: ListAppointmentsParams) -> ActionResult:
    """List appointments/showings, optionally filtered by person or assigned agent."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    filters = {"limit": params.limit, "offset": params.offset}
    if params.person_id:
        filters["personId"] = params.person_id
    if params.user_id:
        filters["userId"] = params.user_id
    try:
        appts = await fc.list_appointments(ctx, conn, **filters)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [AppointmentEntity(id=str(a.get("id", "")), title=a.get("title", ""),
                                person_id=str(a.get("personId", "")), user_id=str(a.get("assignedUserId", "")),
                                start=a.get("start", ""), end=a.get("end", ""), type=a.get("type", ""),
                                outcome=a.get("outcome", ""), location=a.get("location", "")) for a in appts]
    return ActionResult.success(AppointmentList(items=items), summary="Appointments listed.")


@chat.function(
    "create_appointment",
    "Schedule a new appointment (e.g. a showing or listing presentation) with a person.",
    action_type="write",
    chain_callable=True,
    data_model=AppointmentEntity,
    event="followupboss-connector.create_appointment",
    effects=['create:appointment'],
)
async def create_appointment(ctx, params: CreateAppointmentParams) -> ActionResult:
    """Schedule a new appointment (e.g. a showing or listing presentation) with a person."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {"personId": params.person_id, "title": params.title, "start": params.start}
    if params.end:
        payload["end"] = params.end
    if params.type:
        payload["type"] = params.type
    if params.assigned_user_id:
        payload["assignedUserId"] = params.assigned_user_id
    if params.location:
        payload["location"] = params.location
    try:
        appt = await fc.create_appointment(ctx, conn, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(AppointmentEntity(id=str(appt.get("id", "")), title=appt.get("title", ""),
                 person_id=str(appt.get("personId", "")), user_id=str(appt.get("assignedUserId", "")),
                 start=appt.get("start", ""), end=appt.get("end", ""), type=appt.get("type", ""),
                 outcome=appt.get("outcome", ""), location=appt.get("location", "")), summary="Appointment created.")


@chat.function(
    "update_appointment",
    "Update an appointment's title/timing, or record its outcome (Held/Cancelled/No Show).",
    action_type="write",
    chain_callable=True,
    data_model=AppointmentEntity,
    event="followupboss-connector.update_appointment",
    effects=['update:appointment'],
)
async def update_appointment(ctx, params: UpdateAppointmentParams) -> ActionResult:
    """Update an appointment's title/timing, or record its outcome (Held/Cancelled/No Show)."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    payload = {}
    if params.title:
        payload["title"] = params.title
    if params.start:
        payload["start"] = params.start
    if params.end:
        payload["end"] = params.end
    if params.outcome:
        payload["outcome"] = params.outcome
    if not payload:
        return ActionResult.error("No fields to update -- pass at least one field to change.")
    try:
        appt = await fc.update_appointment(ctx, conn, params.appointment_id, payload)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(AppointmentEntity(id=str(appt.get("id", "")), title=appt.get("title", ""),
                 person_id=str(appt.get("personId", "")), user_id=str(appt.get("assignedUserId", "")),
                 start=appt.get("start", ""), end=appt.get("end", ""), type=appt.get("type", ""),
                 outcome=appt.get("outcome", ""), location=appt.get("location", "")), summary="Appointment updated.")


@chat.function(
    "delete_appointment",
    "Permanently delete an appointment.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="followupboss-connector.delete_appointment",
    effects=['delete:appointment'],
)
async def delete_appointment(ctx, params: DeleteAppointmentParams) -> ActionResult:
    """Permanently delete an appointment."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        await fc.delete_appointment(ctx, conn, params.appointment_id)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    return ActionResult.success(DeleteResult(ok=True, detail=f"Appointment {params.appointment_id} deleted."), summary="Appointment deleted.")


@chat.function(
    "list_appointment_types",
    "List the appointment type options configured in this Follow Up Boss account.",
    action_type="read",
    chain_callable=True,
    data_model=AppointmentTypeList,
    event="followupboss-connector.list_appointment_types",
)
async def list_appointment_types(ctx, params: ListAppointmentTypesParams) -> ActionResult:
    """List the appointment type options configured in this Follow Up Boss account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        types_ = await fc.list_appointment_types(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [AppointmentTypeEntity(id=str(t.get("id", "")), name=t.get("name", "")) for t in types_]
    return ActionResult.success(AppointmentTypeList(items=items), summary="Appointment types listed.")


@chat.function(
    "list_appointment_outcomes",
    "List the appointment outcome options (e.g. Held, No Show, Cancelled) configured in this account.",
    action_type="read",
    chain_callable=True,
    data_model=AppointmentOutcomeList,
    event="followupboss-connector.list_appointment_outcomes",
)
async def list_appointment_outcomes(ctx, params: ListAppointmentOutcomesParams) -> ActionResult:
    """List the appointment outcome options (e.g. Held, No Show, Cancelled) configured in this account."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        outcomes = await fc.list_appointment_outcomes(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [AppointmentOutcomeEntity(id=str(o.get("id", "")), name=o.get("name", ""),
                                       is_held=bool(o.get("isHeld", False))) for o in outcomes]
    return ActionResult.success(AppointmentOutcomeList(items=items), summary="Appointment outcomes listed.")


@chat.function(
    "list_appointment_types",
    "List the appointment type options configured on this account (e.g. 'Buyer Showing', 'Listing Presentation').",
    action_type="read",
    chain_callable=True,
    data_model=AppointmentTypeList,
    event="followupboss-connector.list_appointment_types",
)
async def list_appointment_types(ctx, params: ListAppointmentTypesParams) -> ActionResult:
    """List the appointment type options configured on this account (e.g. 'Buyer Showing', 'Listing Presentation')."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        types = await fc.list_appointment_types(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [AppointmentTypeEntity(id=str(t.get("id", "")), name=t.get("name", "")) for t in types]
    return ActionResult.success(AppointmentTypeList(items=items), summary="Appointment types listed.")


@chat.function(
    "list_appointment_outcomes",
    "List the appointment outcome options configured on this account (e.g. 'Showed', 'No Show', 'Cancelled').",
    action_type="read",
    chain_callable=True,
    data_model=AppointmentOutcomeList,
    event="followupboss-connector.list_appointment_outcomes",
)
async def list_appointment_outcomes(ctx, params: ListAppointmentOutcomesParams) -> ActionResult:
    """List the appointment outcome options configured on this account (e.g. 'Showed', 'No Show', 'Cancelled')."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Follow Up Boss account connected. Use connect_followupboss first.")
    try:
        outcomes = await fc.list_appointment_outcomes(ctx, conn)
    except fc.ClientFail as e:
        return ActionResult.error(e.reason)
    items = [AppointmentOutcomeEntity(id=str(o.get("id", "")), name=o.get("name", "")) for o in outcomes]
    return ActionResult.success(AppointmentOutcomeList(items=items), summary="Appointment outcomes listed.")
