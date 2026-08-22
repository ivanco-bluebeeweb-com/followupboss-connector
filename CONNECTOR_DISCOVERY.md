# Follow Up Boss Connector — Connector Discovery

**Дата discovery:** 2026-08-22
**Статус:** Ярусы 1-3 пройдены (свежее чтение официальной документации `docs.followupboss.com`, `help.followupboss.com` и разбор публичной карты покрытия FUB API v1 из открытого MCP-сервера `github.com/nerdsnipe-inc/follow-up-boss-mcp`, 2026-08-22). Влад заранее заявил объём — «максимальная форма со всеми доступными функциями с их стороны и всеми возможными функциями внутри нашего приложения для повышения эффективности» (Vikunja #2284) — поэтому по `CONNECTOR_DISCOVERY_STANDARD.md` Шаг 5 (запрос подтверждения объёма) считается закрытым этим прямым поручением: делаем Ярус 1+2+3.

---

## 1. Целевой сервис и источники

Follow Up Boss (FUB) — доминирующая CRM для агентов и команд недвижимости в США, с 2023 в составе Zillow Group. Единственная API-поверхность: REST API v1, `https://api.followupboss.com/v1/<resource>`. В отличие от PagerDuty (4 разные поверхности), у FUB одна база URL, но **дуальная авторизация** и **ролевая модель доступа**, которые критично не перепутать.

Источники (прочитаны 2026-08-22): `docs.followupboss.com/reference/{getting-started,authentication,rate-limiting,identity,people-post,webhooks-guide,deals-get,deals-post,actionplans-get,smartlists-get,users-get,teams-get,appointments-get,appointments-post,pipelines-get,textmessagetemplates-get,textmessagetemplates-post,textmessages-get,peoplerelationships,peoplerelationships-post,templates-get,webhooks-post}`, `docs.followupboss.com/docs/getting-started-with-oauth`, `docs.followupboss.com/docs/start-here-brand-new-integration`, `help.followupboss.com/hc/en-us/articles/33217901299095-Automations-2-0-Migration`, `github.com/nerdsnipe-inc/follow-up-boss-mcp` (сторонний открытый MCP-сервер, заявляет «160 tools across 25 modules — full coverage of the Follow Up Boss API v1» — использован как проверочная карта покрытия ресурсов, не как первичный источник семантики).

**Важный вывод Discovery:** официального публичного `openapi.json` на `docs.followupboss.com` не найдено (ReadMe.io-реф без явной ссылки на схему); часть справочных страниц (`list-people` и др.) отдаёт JS-защиту и недоступна базовому ридеру — карта ниже собрана по доступным reference-страницам конкретных ресурсов + перекрёстно проверена по независимой карте покрытия (25 модулей / 160 функций стороннего MCP), что даёт высокую уверенность в полноте, но отдельные редкие параметры полей будут уточняться на этапе реализации по мере чтения оставшихся `*-get`/`*-post` страниц.

---

## 2. Авторизация — дуальная, с ролевыми ограничениями

| Способ | Механизм | Когда использовать |
|---|---|---|
| **API Key (Basic Auth)** | Персональный ключ пользователя (`fka_...`) из Admin → API. Используется как username в HTTP Basic Auth, пароль — пустая строка. | Основной путь для BYOK-коннектора одного аккаунта — простой, как HubSpot Private App Token / Klaviyo API Key. |
| **OAuth 2.0 (Bearer)** | Отдельный флоу `docs.followupboss.com/docs/getting-started-with-oauth`, нужен при построении публичного multi-tenant приложения, которое подключается от имени МНОГИХ FUB-аккаунтов без ручного получения ключа каждым пользователем. | Опционально, Ярус 3 — если Imperal захочет пройти официальную регистрацию OAuth-приложения у FUB. |

**Ролевая модель — критично для дизайна ошибок:**
- **Owner** — полный доступ, включая Webhooks.
- **Admin/Broker** — почти всё, **кроме Webhooks** (создание/изменение/удаление вебхуков доступно только Owner).
- **Agent** — доступ только к своим назначенным контактам/контактам, где он collaborator; ограниченный доступ к Action Plans/Automations.
- **Lender** — аналогично ограничен, своя область видимости.

Коннектор должен трактовать `403 Forbidden` на Webhooks/полный список People от Admin/Agent-ключа как ожидаемое поведение внешнего сервиса (роль ключа), а не как баг коннектора — сообщение пользователю должно объяснять это прямо.

**System Identification (важно для лимитов и части ресурсов):** запросы без валидного заголовка `X-System-Key` (+ `X-System`) идут по значительно более низкому rate-limit, а часть ресурсов — **Automations, Attachments, Webhooks, Inbox Apps** — доступны ТОЛЬКО зарегистрированным системам. Регистрация делается пользователем в Admin → API → Registered Systems (свой `system name` + `system key`) либо Imperal подаёт заявку на собственную регистрацию как разработчик у FUB support. **Решение по регистрации Imperal как системы — открытый вопрос, требует внешней переписки, не блокирует Ярус 1/2 (People/Deals/Notes/Calls/Tasks/Events работают и без регистрации), но ограничивает Ярус 3 (Automations/Webhooks/Attachments/Inbox Apps) до момента регистрации.**

**Expired-аккаунт:** при истечении подписки FUB API Key остаётся валидным, но большинство эндпоинтов начинают отдавать `403`; исключение — `POST /v1/events` (приём новых лидов) продолжает работать, чтобы не терять данные.

---

## 3. Rate Limiting

Скользящее окно 10 секунд, **контекстное** — у каждого эндпоинта один контекст (`global`, `events` и т.д.) со своим лимитом, отражённым в заголовках ответа:

```
X-RateLimit-Limit / X-RateLimit-Remaining / X-RateLimit-Window / X-RateLimit-Context
```

При превышении — `429 Too Many Requests` + заголовок `Retry-After` (секунды до повтора). Без `X-System-Key` лимиты значительно ниже. Коннектор должен читать эти заголовки и (Ярус 2) экспонировать понятную обратную связь при 429, а не глухо падать.

---

## 4. Карта возможностей (по модулям, направление на каждую)

| Модуль | Возможность | Ingress/Egress/Both | Комментарий |
|---|---|---|---|
| **Identity** | `GET /identity` — проверка валидности ключа, кто владелец, какая роль | Ingress | Первый вызов после connect — валидация + определение роли для UI |
| **People (контакты/лиды)** | list/get/create/update/delete people; поиск по email/phone/tag/stage; custom fields через `?fields=allFields` | Both | Ядро CRM. **Quirk:** custom fields не возвращаются без явного параметра `allFields` |
| **People — Relationships** | list/create/update/delete relationships (напр. супруг/супруга контакта) | Both | Отдельный подресурс People |
| **People — Notes** | list/create/update/delete notes на контакте | Both | |
| **People — Tags** | добавление/удаление тегов (в т.ч. массово) | Both | Массовые изменения тегов → батчинг вебхука |
| **Deals (сделки)** | list/get/create/update/delete deals; привязка к pipeline/stage | Both | Real-estate эквивалент Opportunity/Deal в обычных CRM |
| **Pipelines & Stages** | list pipelines; list/get stages per pipeline | Ingress (read-only справочник) | Настраивается в UI FUB, через API — только чтение |
| **Appointments** | list/get/create/update/delete appointments; appointment types; appointment outcomes | Both | Показы объектов/встречи |
| **Tasks** | list/get/create/update/delete tasks | Both | |
| **Calls** | list/get/create/log calls (включая длительность, исход) | Both | Интеграция с VoIP-провайдерами через API |
| **Text Messages (SMS)** | list/get/create/send text messages; text message templates (CRUD) | Both | |
| **Email Templates / Templates** | list/get/create/update/delete email + текстовые шаблоны | Both | |
| **Events** | `POST /v1/events` — приём нового лида/события извне (Zillow-подобная интеграция); list events | Egress-в-FUB / Ingress-из-FUB | Ключевой ingress-канал для лидов из внешних источников |
| **Users** | list/get users (агенты, лендеры и т.д.); их роли и назначения | Ingress (в основном read) | |
| **Teams / Groups / Ponds** | list/get teams, groups, lead ponds (общие пулы лидов) | Both (частично read-only в зависимости от плана) | Ponds — специфика real-estate distribution-логики |
| **Pipelines/Custom Fields** | list/get/create custom field definitions на People/Deals | Both | Нужно для того, чтобы наш UI показывал реальные кастомные поля аккаунта |
| **Smart Lists** | list/get smart lists (сохранённые сегменты контактов по условиям) | Ingress | Готовые сегменты — полезны для bulk-действий |
| **Action Plans (legacy)** | list/get action plans; запуск на контакте/удаление с контакта | Both | Мигрирует в Automations 2.0 (см. §5), но остаётся в проде у части аккаунтов — оставляем поддержку read+apply |
| **Automations 2.0** | list/get automations; ручной trigger (`Manual Trigger`) на контакте | Both | Новая система, официально в роллауте 2026; см. §5 |
| **Webhooks** | list/create/update/delete webhook subscriptions на все People-события + др. | Both | **Только Owner-роль + желательно Registered System** |
| **Inbox Apps** | list/register inbox apps (интеграция с Inbox-каналом FUB) | Both | Требует Registered System |
| **Attachments** | upload/list/get file attachments на контакт | Both | Требует Registered System |
| **Reactions** | list/create reactions на активность (лайки/emoji на событие в ленте) | Both | Нишевая, но часть полного покрытия |

---

## 5. Webhook-события (детали для идемпотентности обработчика)

`peopleCreated`, `peopleUpdated`, `peopleDeleted`, `peopleTagsCreated`, `peopleStageUpdated`, `peopleRelationshipCreated`, `peopleRelationshipUpdated`, `peopleRelationshipDeleted` — плюс события по Deals/Calls/Notes/TextMessages/Tasks по аналогичному паттерну `<resource>Created/Updated/Deleted`.

**Батчинг:** массовые операции (bulk tag add/remove, stage change, source change, agent/lender reassignment) могут породить ОДНО логическое событие, разбитое на несколько HTTP POST-запросов подряд — обработчик обязан быть идемпотентным по паре (person id, updated field), не предполагать «один вебхук = одно изменение».

**Custom Fields в вебхуке:** чтобы увидеть значения custom fields в `peopleUpdated`-пейлоаде, подписка должна быть создана с соответствующим query-параметром — иначе пейлоад их не содержит (тот же quirk, что и в GET /people).

---

## 6. Action Plans → Automations 2.0 — переходный период

FUB официально мигрирует Action Plans (легаси-система «if new lead then do X,Y,Z по расписанию») на новую систему **Automations 2.0** (объявлено и раскатывается в течение 2026 года, `help.followupboss.com/.../Automations-2-0-Migration`, `Automations-2-0-Manual-Trigger`). Оба API-поверхности (legacy `/actionPlans` и новый Automations-эндпоинт) существуют параллельно на переходный период.

**Архитектурное решение:** коннектор реализует ОБА слоя (list/get/apply на Action Plans; list/get/manual-trigger на Automations 2.0) за единым набором функций в UI, чтобы не ломаться независимо от того, на какой системе находится конкретный аккаунт пользователя — тот же принцип, что PagerDuty Rulesets (legacy) vs Event Orchestrations (текущий).

---

## 7. Ярусы (объём релиза)

### Ярус 1 — критический костяк (must-have, ядро value proposition)
`connect_followupboss` (API Key, Basic Auth) + `get_identity` (валидация + определение роли) + `disconnect_followupboss` + `list_connections`; People (list/get/create/update/delete, search by email/phone/tag/stage, custom fields via `allFields`); People Notes (CRUD); People Tags (add/remove, bulk); Deals (list/get/create/update/delete); Pipelines & Stages (list, read-only); Tasks (CRUD); Calls (list/create/log); Text Messages (list/create/send); Appointments (CRUD + types/outcomes); Events (`POST /events` для приёма лидов, list events); Users (list/get); Teams/Groups/Ponds (list/get).

### Ярус 2 — расширенная полнота (то, что делает коннектор «максимальным»)
People Relationships (CRUD); Custom Field definitions (list/get/create); Smart Lists (list/get); Templates — email + SMS (CRUD); Action Plans legacy (list/get/apply-to-person/remove-from-person); Automations 2.0 (list/get/manual-trigger); аудит rate-limit заголовков с понятной обратной связью при 429.

### Ярус 3 — продвинутая автоматизация и Registered-System функции (полный максимум)
Webhooks (CRUD, Owner-only с явной проверкой роли); Inbox Apps (list/register, Registered System); Attachments (upload/list/get, Registered System); Reactions (list/create). Плюс: собственная System Registration Imperal у FUB (открытый вопрос, вне кода) — как только получена, разблокирует полноту Яруса 3 для всех пользователей коннектора без их собственной регистрации.

**Итого:** ~90-100 функций (примерно на уровне Shopify/PagerDuty по масштабу портфеля) — оправдано тем, что FUB — полноценная многодоменная CRM (contacts × deals × pipelines × automation × communications), а не CRUD над одной сущностью.

---

## 8. Value-add функции Imperal (сверх нативного API — «эффективность внутри нашего приложения»)

- **Bulk-операции с preview-then-apply** (bulk tag/stage/assign по списку people id или по Smart List) — по паттерну HubSpot/Klaviyo/WordPress Hub bulk_*.
- **Aggregated health-аудит аккаунта** (`audit_followupboss_account`): распределение лидов без первого контакта дольше N минут (SLA response time — критично для real estate, где скорость решает конверсию), контакты без назначенного агента, «протухшие» сделки без активности N дней, дубликаты по email/phone среди People.
- **Единый слой поверх Action Plans + Automations 2.0**, чтобы UI не различал, на какой системе находится конкретный аккаунт (см. §6).
- **Rate-limit-aware batching**: коннектор сам разбивает крупные bulk-запросы с учётом `X-RateLimit-*` заголовков, а не полагается на то, что пользователь будет вручную ловить 429.

---

## 9. Что НЕ делаем (явные границы)

- Полноценный OAuth 2.0 Authorization Code флоу с публичной регистрацией Imperal как OAuth App у FUB — не в Ярусе 1/2 (BYOK через персональный API Key покрывает подавляющее большинство сценариев одного аккаунта); зафиксировано как возможное расширение Яруса 3+, не блокирует релиз.
- Не строим приём вебхуков конкретно на нашей стороне в первой итерации кода (это стандартный `ext.webhook`-паттерн из имеющихся коннекторов типа Keragon/Zapier), но ФУНКЦИИ управления вебхуками (create/list/delete подписки) — да, входят в Ярус 3.
- Inbox Apps / Attachments — реализуются полноценно, но их реальная работоспособность зависит от Registered System, который может не быть настроен у конкретного пользователя; сообщение об ошибке должно объяснять именно это, а не выглядеть как баг коннектора.
