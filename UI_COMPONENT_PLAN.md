# Follow Up Boss Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на `POST_CONNECT_EXPERIENCE.md` этого приложения.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(account) + `ui.Divider` + navigation `ui.ListItem`(People/Deals/Tasks/Smart Lists) + `ui.Button`("App settings") | Без карточек по стандарту. |
| People List (center, `center_overlay=True`) | `ui.Stats`(New leads today/Stale leads/Hot leads) + `ui.Select`(smart_list_filter) + `ui.DataTable`(name, stage Badge, source, last activity; sortable) | `DataTable` — стандартный способ обзора контактов/лидов CRM. |
| Person Detail | Back-button + `ui.KeyValue`(contact info/stage/assigned agent) + `ui.TagInput`(tags, editable=True) + `ui.Timeline`(events: inquiries, calls, texts, notes) + `ui.TextArea`(param_name="note", placeholder="Добавить заметку...") | `TagInput` для тегов контакта, `Timeline` для полной истории взаимодействий (сильная сторона FUB). |
| Deal Pipeline Board | Back-button + `ui.Row`(колонки-стадии через N×`ui.Column`, внутри каждой `ui.List`(сделки этой стадии как ListItem)) | В SDK нет Kanban-примитива (см. `UI_COMPONENT_VOCABULARY.md` §4) — pipeline собирается из `Row` колонок, каждая — `List`. |
| Deal Detail | Back-button + `ui.KeyValue`(price/stage/pipeline/close date) + `ui.Timeline`(stage history) | Симметрично Person Detail. |
| Task List | `ui.Select`(assigned_filter) + `ui.DataTable`(name, person, due date, status Badge overdue/upcoming/done; sortable) | Табличный обзор задач по follow-up. |
| Log Call/Text Dialog | `ui.Dialog`(title="Записать звонок", content=`ui.Stack`([`ui.Input`(type="number", duration_minutes), `ui.Select`(outcome), `ui.TextArea`(note)]), confirm_label="Сохранить") | Быстрый лог активности через модалку из любого места (напр. из Person Detail). |
| Smart Lists Overview | `ui.List`(smart lists: name, matched count) | Простой список сохранённых динамических фильтров. |
| Agent Activity Report | `ui.DataTable`(agent, calls, texts, notes, tasks completed; sortable) | Табличная сводка активности агентов для менеджера. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Webhooks CRUD]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__fub_sidebar` рендерит account + разделы,
   `auto_action` открывает People List (Smart List "All" по умолчанию).
2. Клик на контакт → Person Detail — `Timeline` истории + `TagInput` тегов.
3. Deal Pipeline Board доступен отдельным пунктом сайдбара — `Row` колонок по
   стадиям, клик на сделку → Deal Detail.
4. "Записать звонок/текст" — Dialog, доступный из Person Detail и списка задач.
5. Smart Lists Overview и Agent Activity Report — read-only разделы сайдбара.
6. App Settings — только через кнопку в сайдбаре, единственное место с disconnect.

## 3. Экраны/карточки (артефакты для реализации)

- `panels.py`: `__panel__fub_sidebar` (left).
- `panels_people.py`: `__panel__people_list` (center, `center_overlay=True`),
  `__panel__person_detail` (center, параметризован `person_id`).
- `panels_deals.py`: `__panel__deal_pipeline_board` (center),
  `__panel__deal_detail` (center, параметризован `deal_id`).
- `panels_tasks.py`: `__panel__task_list` (center).
- `panels_reports.py`: `__panel__smart_lists_overview` (center),
  `__panel__agent_activity_report` (center).
- `panels_settings.py`: `__panel__app_settings` (center overlay, Accordion,
  единственное место с disconnect).
