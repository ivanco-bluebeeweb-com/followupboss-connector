# Follow Up Boss Connector — Pricing History

Canonical scale and process: `/Users/vladivanco/Documents/Imperal OS/PRICING_POLICY.md`.
Reference precedent followed: PagerDuty Connector (`Apps/PagerDuty Connector/PRICING_HISTORY.md`).

## 2026-08-22 — Initial pricing applied, submitted for review

Sequence executed, in order (per PRICING_POLICY.md §1/§3, code-complete →
clean post-audit → deploy → price → deploy → submit, never price after
submit):

1. `imperal validate` clean: 0 errors, 0 warnings, 1 info (no `@ext.on_install`
   hook — optional, not required).
2. `tool-prices.json` written with all 66 chat functions covered, values
   restricted to the canonical scale `{0, 8, 16, 20, 40, 60}`:
   - `0` — connection/identity management (`connect_followupboss`,
     `disconnect_followupboss`, `list_connections`, `get_identity`).
   - `8` — all `list_*`/`get_*` reads.
   - `16` — standard create/update/delete CRUD (people, deals, notes,
     tasks, calls, text templates, appointments, custom fields, tags,
     webhooks, relationships, email templates).
   - `20` — higher-stakes single actions: `create_lead_event` (the
     correct lead-intake path, triggers agent notification + automations),
     `send_text_message` (sends a real SMS), `apply_action_plan`/
     `remove_action_plan`/`trigger_automation` (fires a multi-step
     automation sequence against a real contact).
   - `40` — Imperal value-add analytics reports (`audit_lead_response`,
     `get_pipeline_health`, `get_overdue_tasks_report`,
     `get_agent_activity_report`, `get_stale_leads_report`) — each
     aggregates multiple FUB endpoints server-side, same tier PagerDuty
     Connector uses for its own `audit_account`.
   - Mirrored into `imperal.json["pricing"]` (`model: per_action`,
     `currency: tokens`, `monthly_price: 0`, `free_tools`, `tool_prices`,
     `notes`).
3. `git init` + GitHub repo created (public,
   `ivanco-bluebeeweb-com/followupboss-connector`), pushed.
4. `developer.create_app` — first call returned a transient
   `API error 400: App 'followupboss-connector' not found`; a repeat call
   confirmed the app had actually been created (`App ID ... already
   exists`) — the first response was a stale/transient error, not a real
   failure. Logged as a new occurrence pattern, see step 6.
5. `developer.deploy_app` → 20/21 (only the advisory "no files >300 lines"
   warning, same class MuleSoft/PagerDuty/Stripe all carry). 66 tools
   synced.
6. `developer.update_pricing` (dict `pricing_config`, NOT a string, with
   explicit `revenue_split_dev` per PRICING_POLICY.md §3) — **first call
   failed** with a NEW, more informative error than previously seen:
   `"Pricing for 'followupboss-connector' did NOT save correctly: '<tool>'
   was not stored; ..."` for all 58 non-zero-priced tools (the 4 free
   tools priced at 0 DID save correctly). This is the same underlying bug
   class as Imperal Cloud task #2113 (opened 2026-08-19 on
   make-com-connector: `update_pricing`/`save_pricing` give no reliable
   way to confirm tool_prices were actually persisted) — logged as a new
   comment on #2113 with this connector's specific symptom (write-path
   failure now self-reported by the tool, rather than silent as before).
   **A second, identical `update_pricing` call succeeded** — the response
   echoed back the full app record with no "was not stored" error,
   confirming this was a transient write failure on the platform side,
   not a payload/format problem on ours.
7. `developer.deploy_app` again (manifest re-sync) → 20/21, unchanged.
8. `developer.submit_for_review` → all 4 checks passed
   (`git_url_https`, `display_name_set`, `description_set`,
   `last_deploy_succeeded`) → app now `pending_review`.

**Open follow-up (not fully closed programmatically):** neither
`update_pricing` nor any read-back tool echoes the saved `tool_prices` in
a form that can be diffed against what was sent — the platform's own
"did NOT save correctly" message is the only confirmation signal
available, and it only appeared on the FAILED first attempt, not as a
positive confirmation on the successful second attempt. Final human
visual confirmation in Developer → My Apps → Follow Up Boss → Pricing is
recommended before considering this fully closed, same recommendation as
PagerDuty Connector's own pricing history entry.

**Task tracking:** Imperal Cloud task #2113 (still open) now carries a
second live reproduction from this app, with the added detail that the
failure is isolated to non-zero `tool_prices` entries specifically (zero-
priced free tools persisted correctly on the same failed call). Vikunja
task #2296 (`[App Development] Follow Up Boss Connector`) tracks the
overall build; this pricing episode is referenced there as a comment-
worthy footnote if a UI-side discrepancy is later spotted.
