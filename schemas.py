"""Pydantic params models + SDL entity contracts for Follow Up Boss Connector.

All params models are module-scope (V17 federal invariant, same rule as
PagerDuty Connector / MuleSoft Connector's schemas.py). Organized by domain
to match handlers_*.py split (connection, people, deals/pipelines, events,
activity (calls/notes/tasks/appointments/text messages), templates,
users/teams, custom fields/tags, automations, webhooks, smart lists,
relationships, analytics).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectFollowUpBossParams(BaseModel):
    api_key: str = Field(
        "",
        description="Your personal Follow Up Boss API Key (Admin > API screen, e.g. fka_xxxxxxxx).",
    )
    system_name: str = Field(
        "",
        description="Optional: your Registered System name (Admin > API > Registered Systems), if you registered one with FUB support.",
    )
    system_key: str = Field(
        "",
        description="Optional: your Registered System key, paired with system_name above.",
    )
    label: str = Field("", description="Optional friendly name for this connection, e.g. the brokerage name.")


class ConnectionEntity(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    role: str = ""
    account_name: str = ""
    has_system_registration: bool = False


class ConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ConnectionEntity] = Field(default_factory=list)


class DisconnectParams(BaseModel):
    connection_id: str = Field("", description="Connection id to disconnect, from list_connections.")


class DeleteResult(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool = False
    detail: str = ""


class ConnIdParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


# ──────────────────────────────────────────────────────────────────────────
# People (contacts) -- the core resource
# ──────────────────────────────────────────────────────────────────────────


class ListPeopleParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    query: str = Field("", description="Free-text search across name/email/phone, e.g. 'Jane Smith'.")
    stage: str = Field("", description="Filter by pipeline stage name, e.g. 'Lead' or 'Under Contract'.")
    assigned_user_id: str = Field("", description="Filter to people assigned to one user id, from list_users.")
    tag: str = Field("", description="Filter to people carrying this exact tag, e.g. 'Hot Lead'.")
    include_trash: bool = Field(False, description="Include people in the Trash stage (excluded by default).")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class PersonEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    stage: str = ""
    source: str = ""
    emails: str = ""
    phones: str = ""
    assigned_to: str = ""
    tags: str = ""
    created: str = ""
    updated: str = ""
    last_activity: str = ""


class PersonList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[PersonEntity] = Field(default_factory=list)
    total: int = 0


class GetPersonParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id, from list_people.")


class CreatePersonParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    first_name: str = Field("", description="First name, e.g. 'Jane'.")
    last_name: str = Field("", description="Last name, e.g. 'Smith'.")
    email: str = Field("", description="Primary email address, e.g. 'jane.smith@example.com'.")
    phone: str = Field("", description="Primary phone number, e.g. '+1 555 010 2020'.")
    source: str = Field("", description="Lead source, e.g. 'Website' or 'Referral' -- can only be set on creation.")
    stage: str = Field("", description="Initial pipeline stage name, e.g. 'Lead'.")
    assigned_user_id: str = Field("", description="User id to assign this person to, from list_users.")
    background: str = Field("", description="Free-text background/notes about this person.")
    tags_csv: str = Field("", description="Comma-separated tags to apply, e.g. 'Buyer,Hot Lead'.")
    custom_fields_json: str = Field("", description="JSON object of custom field name/value pairs, e.g. {\"budget\": \"450000\"}.")


class UpdatePersonParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to update, from list_people.")
    first_name: str = Field("", description="New first name, leave blank to keep unchanged.")
    last_name: str = Field("", description="New last name, leave blank to keep unchanged.")
    stage: str = Field("", description="New pipeline stage name, e.g. 'Under Contract'.")
    assigned_user_id: str = Field("", description="Re-assign to this user id, from list_users.")
    background: str = Field("", description="Replace the free-text background/notes field.")
    custom_fields_json: str = Field("", description="JSON object of custom field name/value pairs to update.")


class DeletePersonParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to permanently delete, from list_people.")


class PersonTagsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id, from list_people.")
    tags_csv: str = Field(..., description="Comma-separated tags, e.g. 'Hot Lead,VIP'.")


class MergePeopleParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    primary_person_id: str = Field(..., description="Person id to keep, from list_people.")
    duplicate_person_id: str = Field(..., description="Duplicate person id to merge into the primary and remove.")


# ──────────────────────────────────────────────────────────────────────────
# Events -- the OFFICIAL way to bring new leads into FUB (NOT /people)
# ──────────────────────────────────────────────────────────────────────────


class CreateLeadEventParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    first_name: str = Field("", description="Lead's first name, e.g. 'Jane'.")
    last_name: str = Field("", description="Lead's last name, e.g. 'Smith'.")
    email: str = Field("", description="Lead's email address, e.g. 'jane@example.com'.")
    phone: str = Field("", description="Lead's phone number, e.g. '+15551234567'.")
    message: str = Field("", description="Inquiry text/message the lead sent, e.g. 'Interested in 123 Main St'.")
    source: str = Field(..., description="Lead source name shown in FUB, e.g. 'My Website' or 'Open House Sign-in'.")
    source_url: str = Field("", description="URL where the lead came from, e.g. the listing page they inquired on.")
    type: str = Field("General Inquiry", description="Event type, e.g. 'General Inquiry', 'Property Inquiry', 'Registration', 'Viewed Property'.")
    property_address: str = Field("", description="Address of the property this inquiry relates to, if any.")
    property_url: str = Field("", description="URL of the property listing this inquiry relates to, if any.")
    custom_fields_json: str = Field("", description="JSON object of custom field name/value pairs to attach to this lead.")


class ListEventsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field("", description="Filter to events for one person id, from list_people.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class EventEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    person_id: str = ""
    type: str = ""
    source: str = ""
    message: str = ""
    created: str = ""


class EventList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[EventEntity] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Deals & Pipelines
# ──────────────────────────────────────────────────────────────────────────


class ListDealsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    pipeline_id: str = Field("", description="Filter to deals in one pipeline, from list_pipelines.")
    stage_id: str = Field("", description="Filter to deals in one pipeline stage.")
    person_id: str = Field("", description="Filter to deals linked to one person.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class DealEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    price: str = ""
    stage: str = ""
    pipeline: str = ""
    status: str = ""
    people: str = ""
    users: str = ""
    created: str = ""
    updated: str = ""


class DealList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[DealEntity] = Field(default_factory=list)
    total: int = 0


class GetDealParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    deal_id: str = Field(..., description="Deal id, from list_deals.")


class CreateDealParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    name: str = Field(..., description="Deal name, e.g. '123 Main St -- Smith Purchase'.")
    pipeline_id: str = Field(..., description="Pipeline id this deal belongs to, from list_pipelines.")
    stage_id: str = Field(..., description="Initial pipeline stage id, from list_pipelines.")
    person_id: str = Field("", description="Person id to link as the deal's primary contact.")
    price: str = Field("", description="Deal price/value, e.g. '450000'.")
    assigned_user_id: str = Field("", description="User id to assign this deal to, from list_users.")


class UpdateDealParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    deal_id: str = Field(..., description="Deal id to update, from list_deals.")
    name: str = Field("", description="New deal name, if changing.")
    stage_id: str = Field("", description="New pipeline stage id, to move the deal.")
    price: str = Field("", description="New deal price/value.")
    assigned_user_id: str = Field("", description="New assigned user id.")
    status: str = Field("", description="Deal status, e.g. 'Active', 'Won', 'Lost'.")


class DeleteDealParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    deal_id: str = Field(..., description="Deal id to permanently delete.")


class ListPipelinesParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class PipelineStage(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    order: int = 0


class PipelineEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    stages: list[PipelineStage] = Field(default_factory=list)


class PipelineList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[PipelineEntity] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Notes
# ──────────────────────────────────────────────────────────────────────────


class ListNotesParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field("", description="Filter to notes on one person.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class NoteEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    subject: str = ""
    body: str = ""
    person_id: str = ""
    created_by: str = ""
    created: str = ""


class NoteList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[NoteEntity] = Field(default_factory=list)


class CreateNoteParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to attach this note to, from list_people.")
    subject: str = Field("", description="Short note subject, e.g. 'Called re: 123 Main St'.")
    body: str = Field(..., description="Note body text, e.g. 'Discussed financing options, wants to see the house Saturday.'")
    is_html: bool = Field(False, description="Whether body contains HTML markup.")


class UpdateNoteParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    note_id: str = Field(..., description="Note id to update, from list_notes.")
    subject: str = Field("", description="New subject, if changing.")
    body: str = Field("", description="New body text, if changing.")


class DeleteNoteParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    note_id: str = Field(..., description="Note id to permanently delete.")


# ──────────────────────────────────────────────────────────────────────────
# Tasks
# ──────────────────────────────────────────────────────────────────────────


class ListTasksParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field("", description="Filter to tasks on one person.")
    assigned_user_id: str = Field("", description="Filter to tasks assigned to one user id.")
    is_completed: str = Field("", description="Filter: 'true' for completed, 'false' for open, empty for both.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class TaskEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    person_id: str = ""
    assigned_to: str = ""
    due_date: str = ""
    is_completed: bool = False
    type: str = ""
    created: str = ""


class TaskList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[TaskEntity] = Field(default_factory=list)


class CreateTaskParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id this task relates to, from list_people.")
    name: str = Field(..., description="Task description, e.g. 'Follow up call re: financing pre-approval'.")
    due_date: str = Field("", description="Due date, ISO 8601, e.g. '2026-08-25T15:00:00Z'.")
    assigned_user_id: str = Field("", description="User id to assign this task to, from list_users.")
    type: str = Field("", description="Task type/category, e.g. 'Call', 'Email', 'Follow Up'.")


class UpdateTaskParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    task_id: str = Field(..., description="Task id to update, from list_tasks.")
    name: str = Field("", description="New task description, if changing.")
    due_date: str = Field("", description="New due date, ISO 8601, if changing.")
    is_completed: bool = Field(False, description="Mark this task as completed.")


class DeleteTaskParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    task_id: str = Field(..., description="Task id to permanently delete.")


# ──────────────────────────────────────────────────────────────────────────
# Calls
# ──────────────────────────────────────────────────────────────────────────


class ListCallsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field("", description="Filter to calls logged against one person.")
    user_id: str = Field("", description="Filter to calls made/logged by one user.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class CallEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    person_id: str = ""
    user_id: str = ""
    duration: int = 0
    outcome: str = ""
    note: str = ""
    is_incoming: bool = False
    created: str = ""


class CallList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[CallEntity] = Field(default_factory=list)


class LogCallParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id this call was with, from list_people.")
    duration: int = Field(0, description="Call duration in seconds, e.g. 180.")
    outcome: str = Field("", description="Call outcome, e.g. 'Interested', 'Left Voicemail', 'No Answer'.")
    note: str = Field("", description="Free-text note about the call, e.g. 'Discussed timeline, wants to view Saturday.'")
    is_incoming: bool = Field(False, description="Whether this was an incoming call (true) or outgoing (false).")
    phone: str = Field("", description="Phone number used for this call, e.g. '+15551234567'.")


# ──────────────────────────────────────────────────────────────────────────
# Text Messages
# ──────────────────────────────────────────────────────────────────────────


class ListTextMessagesParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field("", description="Filter to texts with one person.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class TextMessageEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    person_id: str = ""
    message: str = ""
    is_incoming: bool = False
    created: str = ""


class TextMessageList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[TextMessageEntity] = Field(default_factory=list)


class SendTextMessageParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to text, from list_people.")
    message: str = Field(..., description="SMS text to send, e.g. 'Hi Jane, following up on the 123 Main St showing -- still good for Saturday at 2pm?'")
    to_number: str = Field("", description="Phone number to text, if the person has more than one on file.")


class ListTextMessageTemplatesParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class TextMessageTemplateEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    message: str = ""


class TextMessageTemplateList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[TextMessageTemplateEntity] = Field(default_factory=list)


class CreateTextMessageTemplateParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    name: str = Field(..., description="Template name, e.g. 'Open House Follow-up'.")
    message: str = Field(..., description="Template text, e.g. 'Hi {firstName}, thanks for stopping by the open house today!'")


class UpdateTextMessageTemplateParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    template_id: str = Field(..., description="Template id to update, from list_text_message_templates.")
    name: str = Field("", description="New template name, if changing.")
    message: str = Field("", description="New template text, if changing.")


class DeleteTextMessageTemplateParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    template_id: str = Field(..., description="Template id to permanently delete.")


# ──────────────────────────────────────────────────────────────────────────
# Appointments
# ──────────────────────────────────────────────────────────────────────────


class ListAppointmentsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field("", description="Filter to appointments with one person.")
    user_id: str = Field("", description="Filter to appointments assigned to one user.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


class AppointmentEntity(sdl.Entity):
    id: str = ""
    title: str = ""
    person_id: str = ""
    user_id: str = ""
    start: str = ""
    end: str = ""
    type: str = ""
    outcome: str = ""
    location: str = ""


class AppointmentList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AppointmentEntity] = Field(default_factory=list)


class CreateAppointmentParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id this appointment is with, from list_people.")
    title: str = Field(..., description="Appointment title, e.g. 'Showing -- 123 Main St'.")
    start: str = Field(..., description="Start time, ISO 8601, e.g. '2026-08-25T15:00:00Z'.")
    end: str = Field("", description="End time, ISO 8601, e.g. '2026-08-25T16:00:00Z'.")
    type: str = Field("", description="Appointment type, e.g. 'Buyer Showing', 'Listing Presentation'.")
    assigned_user_id: str = Field("", description="User id to assign this appointment to, from list_users.")
    location: str = Field("", description="Location/address of the appointment, e.g. '123 Main St, Springfield'.")


class UpdateAppointmentParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    appointment_id: str = Field(..., description="Appointment id to update, from list_appointments.")
    title: str = Field("", description="New title, if changing.")
    start: str = Field("", description="New start time, ISO 8601, if changing.")
    end: str = Field("", description="New end time, ISO 8601, if changing.")
    outcome: str = Field("", description="Appointment outcome, e.g. 'Held', 'Cancelled', 'No Show'.")


class DeleteAppointmentParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    appointment_id: str = Field(..., description="Appointment id to permanently delete.")


class ListAppointmentTypesParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class AppointmentTypeEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""


class AppointmentTypeList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AppointmentTypeEntity] = Field(default_factory=list)


class ListAppointmentOutcomesParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class AppointmentOutcomeEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    is_held: bool = False


class AppointmentOutcomeList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AppointmentOutcomeEntity] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Custom Fields
# ──────────────────────────────────────────────────────────────────────────


class ListCustomFieldsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class CustomFieldEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    label: str = ""
    type: str = ""
    is_recurring: bool = False
    choices: str = ""


class CustomFieldList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[CustomFieldEntity] = Field(default_factory=list)


class CreateCustomFieldParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    label: str = Field(..., description="Display label shown in FUB, e.g. 'Preferred Contact Time'.")
    type: str = Field(..., description="Field type: 'text', 'date', 'number', or 'dropdown'.")
    choices_json: str = Field("", description="JSON array of choice strings, required when type='dropdown', e.g. '[\"Morning\",\"Afternoon\",\"Evening\"]'.")
    is_recurring: bool = Field(False, description="For date fields only: whether this is a recurring annual date (e.g. birthday) vs a one-time date.")


# ──────────────────────────────────────────────────────────────────────────
# Tags
# ──────────────────────────────────────────────────────────────────────────


class AddPersonTagsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to tag, from list_people.")
    tags: list[str] = Field(..., description="Tags to add, e.g. ['Hot Lead', 'First Time Buyer'].")


class RemovePersonTagsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to untag, from list_people.")
    tags: list[str] = Field(..., description="Tags to remove, e.g. ['Cold Lead'].")


# ──────────────────────────────────────────────────────────────────────────
# Users & Teams
# ──────────────────────────────────────────────────────────────────────────


class ListUsersParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class UserEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    email: str = ""
    role: str = ""
    is_active: bool = True


class UserList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[UserEntity] = Field(default_factory=list)


class ListTeamsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class TeamEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    member_count: int = 0


class TeamList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[TeamEntity] = Field(default_factory=list)


class ListPondsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class PondEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""


class PondList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[PondEntity] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Webhooks (Owner-only)
# ──────────────────────────────────────────────────────────────────────────


class ListWebhooksParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class WebhookEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    event: str = ""
    url: str = ""
    is_active: bool = True


class WebhookList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[WebhookEntity] = Field(default_factory=list)


class CreateWebhookParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    event: str = Field(..., description="Event to subscribe to, e.g. 'peopleCreated', 'peopleUpdated', 'peopleStageUpdated', 'callCreated'.")
    url: str = Field(..., description="HTTPS endpoint FUB should POST this event to.")


class DeleteWebhookParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    webhook_id: str = Field(..., description="Webhook id to permanently delete, from list_webhooks.")


# ──────────────────────────────────────────────────────────────────────────
# Smart Lists
# ──────────────────────────────────────────────────────────────────────────


class ListSmartListsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class SmartListEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    person_count: int = 0


class SmartListList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[SmartListEntity] = Field(default_factory=list)


class GetSmartListPeopleParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    smart_list_id: str = Field(..., description="Smart List id, from list_smart_lists.")
    limit: int = Field(25, ge=1, le=100, description="Max results per page (1-100).")
    offset: int = Field(0, ge=0, description="Pagination offset.")


# ──────────────────────────────────────────────────────────────────────────
# Relationships (spouse, family, referral source, etc.)
# ──────────────────────────────────────────────────────────────────────────


class ListPersonRelationshipsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to read relationships for, from list_people.")


class RelationshipEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    person_id: str = ""
    related_person_id: str = ""
    related_name: str = ""
    type: str = ""


class RelationshipList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[RelationshipEntity] = Field(default_factory=list)


class CreatePersonRelationshipParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Primary person id, from list_people.")
    related_person_id: str = Field(..., description="The other person id this relationship connects to.")
    type: str = Field(..., description="Relationship type, e.g. 'Spouse', 'Family Member', 'Referred By'.")


class DeletePersonRelationshipParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    relationship_id: str = Field(..., description="Relationship id to permanently delete.")


# ──────────────────────────────────────────────────────────────────────────
# Automations 2.0 (replaces legacy Action Plans -- see CONNECTOR_DISCOVERY.md)
# ──────────────────────────────────────────────────────────────────────────


class ListActionPlansParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class ActionPlanEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    is_active: bool = True
    step_count: int = 0


class ActionPlanList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ActionPlanEntity] = Field(default_factory=list)


class ApplyActionPlanParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to enroll, from list_people.")
    action_plan_id: str = Field(..., description="Action Plan id to apply, from list_action_plans.")


class RemoveActionPlanParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    person_id: str = Field(..., description="Person id to remove from the plan, from list_people.")
    action_plan_id: str = Field(..., description="Action Plan id to remove, from list_action_plans.")


class ListAutomationsParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class AutomationEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    trigger: str = ""
    is_active: bool = True


class AutomationList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AutomationEntity] = Field(default_factory=list)


class TriggerAutomationParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    automation_id: str = Field(..., description="Automation id to manually trigger, from list_automations.")
    person_id: str = Field(..., description="Person id to run this automation against, from list_people.")


# ──────────────────────────────────────────────────────────────────────────
# Templates (email)
# ──────────────────────────────────────────────────────────────────────────


class ListEmailTemplatesParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")


class EmailTemplateEntity(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    subject: str = ""
    body: str = ""


class EmailTemplateList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[EmailTemplateEntity] = Field(default_factory=list)


class CreateEmailTemplateParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    name: str = Field(..., description="Template name, e.g. 'New Listing Alert'.")
    subject: str = Field(..., description="Email subject line, e.g. 'A new home just hit the market!'")
    body: str = Field(..., description="Email body (HTML allowed), e.g. '<p>Hi {firstName}, thought you'd love this one...</p>'")


# ──────────────────────────────────────────────────────────────────────────
# Identity / account info
# ──────────────────────────────────────────────────────────────────────────


class IdentityEntity(sdl.Entity):
    id: str = ""
    title: str = ""
    account_name: str = ""
    user_name: str = ""
    user_email: str = ""
    role: str = ""
    is_owner: bool = False


# ──────────────────────────────────────────────────────────────────────────
# Imperal-side value-add: lead response speed & pipeline health
# (NOT native FUB endpoints -- built on top of People/Events/Deals/Tasks
# to close the "no single view of pipeline health" gap named in
# PREPARATION.md's human-words problem statement.)
# ──────────────────────────────────────────────────────────────────────────


class AuditLeadResponseParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    hours_threshold: int = Field(1, ge=1, le=72, description="Flag leads whose first response took longer than this many hours (real estate best practice: under 5 minutes, so 1 hour is already a miss).")
    days_back: int = Field(7, ge=1, le=90, description="Look at leads created within this many days.")


class LeadResponseFlag(sdl.Entity):
    id: str = ""
    title: str = ""
    person_id: str = ""
    name: str = ""
    assigned_to: str = ""
    created: str = ""
    first_response_minutes: int = 0
    status: str = ""


class LeadResponseReport(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[LeadResponseFlag] = Field(default_factory=list)
    total_leads_checked: int = 0
    total_flagged: int = 0
    threshold_hours: int = 0


class GetPipelineHealthParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    pipeline_id: str = Field("", description="Limit to one pipeline, from list_pipelines. Omit for all pipelines.")


class StageHealth(sdl.Entity):
    id: str = ""
    title: str = ""
    stage_name: str = ""
    deal_count: int = 0
    total_value: str = ""
    stale_deal_count: int = 0


class PipelineHealthReport(sdl.Entity):
    id: str = ""
    title: str = ""
    pipeline_name: str = ""
    stages: list[StageHealth] = Field(default_factory=list)
    total_deals: int = 0
    total_value: str = ""


class GetOverdueTasksReportParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    assigned_user_id: str = Field("", description="Limit to one agent's overdue tasks, from list_users. Omit for the whole team.")


class OverdueTaskEntity(sdl.Entity):
    id: str = ""
    title: str = ""
    task_id: str = ""
    name: str = ""
    person_id: str = ""
    person_name: str = ""
    assigned_to: str = ""
    due_date: str = ""
    days_overdue: int = 0


class OverdueTasksReport(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[OverdueTaskEntity] = Field(default_factory=list)
    total_overdue: int = 0


class GetAgentActivityReportParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    days_back: int = Field(7, ge=1, le=90, description="Look at activity within this many days.")


class AgentActivityEntity(sdl.Entity):
    id: str = ""
    title: str = ""
    user_id: str = ""
    name: str = ""
    calls_logged: int = 0
    texts_sent: int = 0
    notes_added: int = 0
    tasks_completed: int = 0
    appointments_held: int = 0


class AgentActivityReport(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AgentActivityEntity] = Field(default_factory=list)
    days_back: int = 0


class GetStaleLeadsReportParams(BaseModel):
    connection_id: str = Field("", description="Which connected Follow Up Boss account to use. Omit if only one is connected.")
    stage: str = Field("", description="Limit to one pipeline stage, e.g. 'Lead'. Omit for all active (non-closed) stages.")
    days_inactive: int = Field(14, ge=1, le=180, description="Flag people with no logged activity for at least this many days.")


class StaleLeadEntity(sdl.Entity):
    id: str = ""
    title: str = ""
    person_id: str = ""
    name: str = ""
    stage: str = ""
    assigned_to: str = ""
    last_activity: str = ""
    days_inactive: int = 0


class StaleLeadsReport(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[StaleLeadEntity] = Field(default_factory=list)
    total_flagged: int = 0
