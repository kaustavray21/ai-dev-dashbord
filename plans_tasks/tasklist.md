# ✅ Phase 1 — Foundation & MVP: Task Checklist
### AI Dev Assistant Dashboard · Weeks 1–3

> Tick each box as you complete a task. Tasks are grouped by domain and ordered by dependency — work top to bottom within each section.

---

## 🗂️ SECTION 0 — Environment & Project Bootstrap

### 0.1 System Prerequisites
- [ ] Confirm Python ≥ 3.11 is installed (`python --version`)
- [ ] Confirm Node.js ≥ 20 is installed (`node --version`)
- [ ] Confirm PostgreSQL is running and accessible (`psql -U postgres -c "\l"`)
- [ ] Confirm `git` is initialized in the project root (`git init`)

### 0.2 Python Virtual Environment
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] Create `backend/requirements/base.txt` with core packages
- [ ] Create `backend/requirements/dev.txt` extending base
- [ ] Create `backend/requirements/prod.txt` extending base
- [ ] Install dev requirements: `pip install -r backend/requirements/dev.txt`
- [ ] Freeze and verify install: `pip freeze | grep django`

### 0.3 Environment Variables
- [ ] Create `.env.example` with all required variable keys (no real values)
- [ ] Copy to `.env`: `cp .env.example .env`
- [ ] Fill in `.env` with real values:
  - [ ] `SECRET_KEY` — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  - [ ] `DATABASE_URL` — point to local PostgreSQL
  - [ ] `OPENAI_API_KEY` — paste real key
  - [ ] `OPENAI_MODEL` — set to `gpt-4o`
  - [ ] `CORS_ALLOWED_ORIGINS` — set to `http://localhost:5173`
- [ ] Add `.env` to `.gitignore` (verify it is ignored: `git status`)

### 0.4 Docker / Database Setup
- [ ] Create `docker/docker-compose.yml` with PostgreSQL service
- [ ] Start PostgreSQL (Docker or local): confirm it's accepting connections
- [ ] Create the database: `psql -U postgres -c "CREATE DATABASE ai_dashboard;"`
- [ ] Verify DB exists: `psql -U postgres -c "\l" | grep ai_dashboard`

---

## 🐍 SECTION 1 — Django Backend Scaffold

### 1.1 Django Project Initialization
- [ ] Run `django-admin startproject config backend/` (or manually scaffold)
- [ ] Restructure `config/` to use a `settings/` subdirectory:
  - [ ] Create `backend/config/settings/__init__.py`
  - [ ] Create `backend/config/settings/base.py`
  - [ ] Create `backend/config/settings/dev.py`
  - [ ] Create `backend/config/settings/prod.py` (stub)
- [ ] Update `manage.py` to point to `config.settings.dev`
- [ ] Create `backend/config/wsgi.py`
- [ ] Create `backend/config/asgi.py`
- [ ] Update `backend/config/urls.py` to include app URL routes under `/api/`
- [ ] Run `python manage.py check` — must return **no errors**

### 1.2 Base Settings (`config/settings/base.py`)
- [ ] Load environment variables using `django-environ`
- [ ] Set `SECRET_KEY` from env
- [ ] Set `ALLOWED_HOSTS` from env
- [ ] Configure `DATABASES` using `DATABASE_URL` from env
- [ ] Add all required apps to `INSTALLED_APPS`:
  - [ ] `rest_framework`
  - [ ] `corsheaders`
  - [ ] `rest_framework_simplejwt`
  - [ ] `apps.users`
  - [ ] `apps.chat`
  - [ ] `apps.logs`
  - [ ] `apps.code_analysis`
  - [ ] `apps.commands`
  - [ ] `apps.ai_layer`
- [ ] Add `corsheaders.middleware.CorsMiddleware` to `MIDDLEWARE` (before `CommonMiddleware`)
- [ ] Configure `REST_FRAMEWORK` to use JWT as default authentication
- [ ] Set `OPENAI_API_KEY` from env
- [ ] Set `OPENAI_MODEL` from env (default `gpt-4o`)
- [ ] Set `AUTH_USER_MODEL = 'users.User'`

### 1.3 Dev Settings (`config/settings/dev.py`)
- [ ] Set `DEBUG = True`
- [ ] Set `CORS_ALLOW_ALL_ORIGINS = True`
- [ ] Set `EMAIL_BACKEND` to console backend

---

## 👤 SECTION 2 — `apps/users` (Authentication & RBAC)

### 2.1 App Creation
- [ ] Run `python manage.py startapp users backend/apps/users`
- [ ] Update `apps.py` with correct `name = 'apps.users'`

### 2.2 User Model
- [ ] Create `backend/apps/users/models.py`:
  - [ ] Extend `AbstractUser`
  - [ ] Add `role` field with `TextChoices`: `admin`, `developer`, `viewer`
  - [ ] Add `created_at = DateTimeField(auto_now_add=True)`
- [ ] Set `AUTH_USER_MODEL = 'users.User'` in base settings

### 2.3 Serializers
- [ ] Create `backend/apps/users/serializers.py`:
  - [ ] `UserSerializer` — exposes `id`, `username`, `email`, `role`, `created_at`

### 2.4 Views
- [ ] Create `backend/apps/users/views.py`:
  - [ ] `LoginView` — validates credentials, issues JWT access + refresh tokens in httpOnly cookies
  - [ ] `LogoutView` — blacklists refresh token, clears cookies
  - [ ] `MeView` — returns serialized current user (requires auth)

### 2.5 URL Routing
- [ ] Create `backend/apps/users/urls.py`:
  - [ ] `POST /api/auth/login/`
  - [ ] `POST /api/auth/logout/`
  - [ ] `GET  /api/auth/me/`
  - [ ] `POST /api/auth/token/refresh/`
- [ ] Include `users.urls` in `config/urls.py`

### 2.6 Admin & Migrations
- [ ] Register `User` in `backend/apps/users/admin.py` with `list_display`, `search_fields`
- [ ] Run `python manage.py makemigrations users`
- [ ] Run `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Verify superuser login at `http://localhost:8000/admin/`

### 2.7 Auth Tests
- [ ] Write `backend/apps/users/tests.py`:
  - [ ] `test_login_with_valid_credentials_returns_200`
  - [ ] `test_login_with_invalid_credentials_returns_401`
  - [ ] `test_me_endpoint_requires_auth`
  - [ ] `test_me_returns_correct_user_data`
- [ ] Run: `python manage.py test apps.users --verbosity=2` — all pass

---

## 💬 SECTION 3 — `apps/chat` (Sessions & Messages)

### 3.1 App Creation
- [ ] Run `python manage.py startapp chat backend/apps/chat`
- [ ] Update `apps.py` with correct `name = 'apps.chat'`

### 3.2 Models
- [ ] Create `backend/apps/chat/models.py`:
  - [ ] `ChatSession` model:
    - [ ] `id` — `UUIDField(primary_key=True, default=uuid.uuid4)`
    - [ ] `user` — `ForeignKey(User, on_delete=CASCADE)`
    - [ ] `title` — `CharField(max_length=255, blank=True)`
    - [ ] `context_type` — `CharField(max_length=20, default='general')` — choices: `general`, `code`, `logs`
    - [ ] `created_at` — `DateTimeField(auto_now_add=True)`
    - [ ] `meta` — `JSONField(default=dict)`
  - [ ] `Message` model:
    - [ ] `session` — `ForeignKey(ChatSession, related_name='messages', on_delete=CASCADE)`
    - [ ] `role` — `CharField(max_length=20, choices=ROLES)` — `user`, `assistant`, `system`
    - [ ] `content` — `TextField()`
    - [ ] `tool_calls` — `JSONField(null=True, blank=True)`
    - [ ] `tokens_used` — `IntegerField(default=0)`
    - [ ] `created_at` — `DateTimeField(auto_now_add=True)`

### 3.3 Serializers
- [ ] Create `backend/apps/chat/serializers.py`:
  - [ ] `MessageSerializer` — all fields
  - [ ] `ChatSessionSerializer` — all fields + `message_count` annotation

### 3.4 Views
- [ ] Create `backend/apps/chat/views.py`:
  - [ ] `ChatSessionListCreateView` — `GET` (list sessions for user), `POST` (create session)
  - [ ] `ChatSessionDetailView` — `GET` (retrieve), `DELETE` (destroy) — scoped to `request.user`
  - [ ] `MessageListCreateView`:
    - [ ] `GET` — return all messages for session (ordered by `created_at`)
    - [ ] `POST` — accept `{ content }`, call `OpenAIClient.chat_completion()`, save user + assistant messages, return assistant message

### 3.5 URL Routing
- [ ] Create `backend/apps/chat/urls.py`:
  - [ ] `POST/GET /api/chat/sessions/`
  - [ ] `GET/DELETE /api/chat/sessions/<uuid:id>/`
  - [ ] `POST/GET /api/chat/sessions/<uuid:id>/messages/`
- [ ] Include `chat.urls` in `config/urls.py`

### 3.6 Admin & Migrations
- [ ] Register `ChatSession` and `Message` in `backend/apps/chat/admin.py`
- [ ] Run `python manage.py makemigrations chat`
- [ ] Run `python manage.py migrate`

### 3.7 Chat Tests
- [ ] Write `backend/apps/chat/tests.py`:
  - [ ] `test_create_session_requires_auth`
  - [ ] `test_create_session_returns_uuid`
  - [ ] `test_list_sessions_only_returns_own_sessions`
  - [ ] `test_delete_session_removes_messages`
  - [ ] `test_send_message_saves_user_and_assistant_turns` (mock OpenAI)
  - [ ] `test_message_history_returned_in_order`
- [ ] Run: `python manage.py test apps.chat --verbosity=2` — all pass

---

## 📋 SECTION 4 — `apps/logs` (Log Upload & Analysis)

### 4.1 App Creation
- [ ] Run `python manage.py startapp logs backend/apps/logs`
- [ ] Update `apps.py` with correct `name = 'apps.logs'`

### 4.2 Model
- [ ] Create `backend/apps/logs/models.py`:
  - [ ] `LogFile` model:
    - [ ] `user` — `ForeignKey(User, on_delete=CASCADE)`
    - [ ] `name` — `CharField(max_length=255)`
    - [ ] `content` — `TextField()` (raw log text)
    - [ ] `file_size` — `IntegerField()`
    - [ ] `analysis` — `JSONField(null=True)` (AI-generated)
    - [ ] `analyzed_at` — `DateTimeField(null=True)`
    - [ ] `uploaded_at` — `DateTimeField(auto_now_add=True)`

### 4.3 Serializers
- [ ] Create `backend/apps/logs/serializers.py`:
  - [ ] `LogFileSerializer` — all fields, `content` write-only on upload

### 4.4 Views
- [ ] Create `backend/apps/logs/views.py`:
  - [ ] `LogUploadView` — `POST /api/logs/upload/` — accept multipart file, read text, store in `content` + `file_size`
  - [ ] `LogListView` — `GET /api/logs/` — list user's log files (exclude `content` for performance)
  - [ ] `LogAnalysisView` — `GET /api/logs/<id>/analysis/` — if `analysis` already cached return it, else run `LogAnalyzer` + `OpenAIClient` then cache

### 4.5 URL Routing
- [ ] Create `backend/apps/logs/urls.py`:
  - [ ] `POST /api/logs/upload/`
  - [ ] `GET  /api/logs/`
  - [ ] `GET  /api/logs/<int:id>/analysis/`
- [ ] Include `logs.urls` in `config/urls.py`

### 4.6 Admin & Migrations
- [ ] Register `LogFile` in `backend/apps/logs/admin.py`
- [ ] Run `python manage.py makemigrations logs`
- [ ] Run `python manage.py migrate`

### 4.7 Log Tests
- [ ] Write `backend/apps/logs/tests.py`:
  - [ ] `test_upload_log_file_stores_content`
  - [ ] `test_upload_requires_auth`
  - [ ] `test_list_logs_returns_only_own_files`
  - [ ] `test_analysis_endpoint_returns_cached_result_if_exists`
  - [ ] `test_analysis_calls_openai_on_first_request` (mock OpenAI)
- [ ] Run: `python manage.py test apps.logs --verbosity=2` — all pass

---

## 🤖 SECTION 5 — `services/` (Business Logic Layer)

### 5.1 `services/contracts.py`
- [ ] Create `backend/services/__init__.py`
- [ ] Create `backend/services/contracts.py`:
  - [ ] Define `IOpenAIClient(Protocol)`:
    - [ ] `chat_completion(messages, tools, stream) -> dict`
    - [ ] `embed_text(text) -> list[float]`
    - [ ] `embed_batch(texts) -> list[list[float]]`

### 5.2 `services/openai_client.py`
- [ ] Create `backend/services/openai_client.py`:
  - [ ] `OpenAIClient` class:
    - [ ] `__init__` — loads `api_key` and `model` from Django settings
    - [ ] `chat_completion(messages, tools=None, stream=False) -> dict` — base AI call method
    - [ ] `embed_text(text: str) -> list[float]` — single embedding with `text-embedding-3-small`
    - [ ] `embed_batch(texts: list[str]) -> list[list[float]]` — batch embedding (scaffold for Phase 2)
    - [ ] Retry logic: catch `openai.RateLimitError`, backoff 2s/4s/8s, max 3 retries
    - [ ] Log `tokens_used` from each response to a Django logger
  - [ ] Verify `OpenAIClient` satisfies `IOpenAIClient` protocol

### 5.3 `services/log_parser.py`
- [ ] Create `backend/services/log_parser.py`:
  - [ ] `LogAnalyzer` class:
    - [ ] `ERROR_PATTERNS` — 4 regex patterns from blueprint
    - [ ] `extract_errors(log_text: str) -> list[dict]` — pure regex, returns list of matches with line numbers
    - [ ] `summarize_for_ai(log_text: str, max_chars=8000) -> str` — trim to most relevant portion (focus on error lines ± context)
    - [ ] `build_analysis_prompt(log_text: str) -> list[dict]` — returns OpenAI `messages` array (system + user)
    - [ ] `analyze(log_text: str, openai_client) -> dict` — orchestrates: extract → summarize → prompt → call → return structured result

---

## 🧪 SECTION 6 — Placeholder Apps (Scaffold Only)

> These apps will be fully implemented in Phase 2+. Create minimal structure now so all migrations work from day one.

### 6.1 `apps/code_analysis`
- [ ] Run `python manage.py startapp code_analysis backend/apps/code_analysis`
- [ ] Update `apps.py` with `name = 'apps.code_analysis'`
- [ ] Leave `models.py` empty (just imports)

### 6.2 `apps/commands`
- [ ] Run `python manage.py startapp commands backend/apps/commands`
- [ ] Update `apps.py` with `name = 'apps.commands'`
- [ ] Leave `models.py` empty

### 6.3 `apps/ai_layer`
- [ ] Run `python manage.py startapp ai_layer backend/apps/ai_layer`
- [ ] Update `apps.py` with `name = 'apps.ai_layer'`
- [ ] Leave `models.py` empty

### 6.4 Final Migration Check
- [ ] Run `python manage.py makemigrations` — should show "No changes detected" for placeholder apps
- [ ] Run `python manage.py migrate` — all migrations applied cleanly
- [ ] Run `python manage.py check` — **zero errors or warnings**

---

## 🔧 SECTION 7 — Scripts

### 7.1 OpenAI Smoke Test
- [ ] Create `scripts/test_openai.py`:
  - [ ] Instantiates `OpenAIClient`
  - [ ] Sends `"Hello, respond with one word."` as user message
  - [ ] Prints response content and `tokens_used`
  - [ ] Prints `"✅ OpenAI connection OK"` on success, `"❌ Failed: {error}"` on exception
- [ ] Run: `python scripts/test_openai.py` — confirm `✅` output

### 7.2 Database Seed Script
- [ ] Create `scripts/seed_db.py`:
  - [ ] Creates a test user (`testdev` / `testpass123`)
  - [ ] Creates 2 chat sessions (one `general`, one `logs`)
  - [ ] Creates 3 messages per session
  - [ ] Prints confirmation for each created object
- [ ] Run: `python scripts/seed_db.py` — confirm all objects created

---

## ⚛️ SECTION 8 — React/TypeScript Frontend

### 8.1 Project Scaffold
- [ ] From project root run: `npm create vite@latest frontend -- --template react-ts`
- [ ] `cd frontend && npm install`
- [ ] Install additional dependencies:
  ```
  npm install axios zustand @tanstack/react-query \
    react-router-dom lucide-react
  ```
- [ ] Create `frontend/.env` with `VITE_API_URL=http://localhost:8000`
- [ ] Add `frontend/.env` to `.gitignore`
- [ ] Run `npm run dev` — confirm Vite dev server starts on port 5173

### 8.2 TypeScript Types
- [ ] Create `frontend/src/types/auth.ts`:
  - [ ] `User` interface: `id`, `username`, `email`, `role`
  - [ ] `LoginRequest`: `username`, `password`
  - [ ] `AuthResponse`: `access`, `refresh`, `user`

- [ ] Create `frontend/src/types/chat.ts`:
  - [ ] `ChatSession` interface: `id`, `title`, `context_type`, `created_at`, `meta`
  - [ ] `Message` interface: `id`, `role`, `content`, `tool_calls?`, `created_at`
  - [ ] `ToolCall` interface: `id`, `type`, `function: { name, arguments }`

- [ ] Create `frontend/src/types/logs.ts`:
  - [ ] `LogFile` interface: `id`, `name`, `file_size`, `uploaded_at`, `analyzed_at`
  - [ ] `LogAnalysis` interface: `errors`, `summary`, `recommendations`

### 8.3 Axios API Client
- [ ] Create `frontend/src/api/client.ts`:
  - [ ] Axios instance with `baseURL` from `import.meta.env.VITE_API_URL`
  - [ ] Request interceptor: attaches `Authorization: Bearer <token>` from memory store
  - [ ] Response interceptor: handles `401` → clears auth + redirect to `/login`
  - [ ] Response interceptor: handles `500` → logs error

- [ ] Create `frontend/src/api/auth.ts`:
  - [ ] `login(username, password)` → `POST /api/auth/login/`
  - [ ] `logout()` → `POST /api/auth/logout/`
  - [ ] `getMe()` → `GET /api/auth/me/`

- [ ] Create `frontend/src/api/chat.ts`:
  - [ ] `createSession(type)` → `POST /api/chat/sessions/`
  - [ ] `getSessions()` → `GET /api/chat/sessions/`
  - [ ] `getSession(id)` → `GET /api/chat/sessions/{id}/`
  - [ ] `deleteSession(id)` → `DELETE /api/chat/sessions/{id}/`
  - [ ] `sendMessage(sessionId, content)` → `POST /api/chat/sessions/{id}/messages/`
  - [ ] `getMessages(sessionId)` → `GET /api/chat/sessions/{id}/messages/`

- [ ] Create `frontend/src/api/logs.ts`:
  - [ ] `uploadLog(file: File)` → `POST /api/logs/upload/` (multipart/form-data)
  - [ ] `getLogs()` → `GET /api/logs/`
  - [ ] `getLogAnalysis(id)` → `GET /api/logs/{id}/analysis/`

### 8.4 Zustand Store
- [ ] Create `frontend/src/store/useAppStore.ts`:
  - [ ] State: `sessions`, `activeSessionId`, `messages`, `isLoading`, `user`
  - [ ] Action: `createSession(type)` — calls API, appends to `sessions`
  - [ ] Action: `sendMessage(sessionId, content)` — appends optimistic user message, calls API, appends assistant response
  - [ ] Action: `loadSession(sessionId)` — fetches messages, sets `activeSessionId`
  - [ ] Action: `login(username, password)` — calls API, sets `user` + stores token in memory
  - [ ] Action: `logout()` — calls API, clears `user` + token

### 8.5 Layout Components
- [ ] Create `frontend/src/components/Layout/AppLayout.tsx`:
  - [ ] 3-column CSS Grid layout: sidebar (260px) | chat (flex-grow) | right panel (320px)
  - [ ] Responsive: right panel collapses below 1200px, sidebar collapses below 768px

### 8.6 Chat Components
- [ ] Create `frontend/src/components/Chat/MessageBubble.tsx`:
  - [ ] User messages: right-aligned, primary color bubble
  - [ ] Assistant messages: left-aligned, neutral bubble with AI avatar icon
  - [ ] `system` role: centered, muted italic text

- [ ] Create `frontend/src/components/Chat/MessageList.tsx`:
  - [ ] Renders list of `MessageBubble` components
  - [ ] Auto-scrolls to bottom when new message arrives
  - [ ] Shows loading spinner when `isLoading === true`

- [ ] Create `frontend/src/components/Chat/MessageInput.tsx`:
  - [ ] Auto-resizing `<textarea>`
  - [ ] Submit on `Enter` (shift+Enter for newline)
  - [ ] Disabled + shows spinner while `isLoading`
  - [ ] Character counter for context awareness

- [ ] Create `frontend/src/components/Chat/ChatWindow.tsx`:
  - [ ] Composes `MessageList` + `MessageInput`
  - [ ] Shows empty state when no session is active

### 8.7 Session Sidebar Components
- [ ] Create `frontend/src/components/SessionSidebar/SessionList.tsx`:
  - [ ] Lists all sessions sorted by `created_at` descending
  - [ ] Highlights `activeSessionId`
  - [ ] Shows `context_type` icon (💬 general, 📁 code, 📋 logs)
  - [ ] Click → calls `loadSession(id)`

- [ ] Create `frontend/src/components/SessionSidebar/NewSessionButton.tsx`:
  - [ ] Button that opens a small modal / inline picker
  - [ ] Picker shows 3 options: `General`, `Code`, `Logs`
  - [ ] On select → calls `createSession(type)`

### 8.8 Log Components
- [ ] Create `frontend/src/components/LogViewer/LogUploadForm.tsx`:
  - [ ] Drag-and-drop file zone + file picker fallback
  - [ ] Shows file name + size after selection
  - [ ] Upload button → calls `uploadLog(file)`
  - [ ] Shows success/error toast after upload

- [ ] Create `frontend/src/components/LogViewer/LogAnalysisCard.tsx`:
  - [ ] Displays `errors[]` as a list with line numbers
  - [ ] Displays AI `summary` as a prose paragraph
  - [ ] Shows loading skeleton while analysis is fetching

### 8.9 Pages & Routing
- [ ] Create `frontend/src/pages/AuthPage.tsx`:
  - [ ] Login form: username + password inputs
  - [ ] Calls `login()` from store on submit
  - [ ] Redirects to `/` on success
  - [ ] Shows error message on failure

- [ ] Create `frontend/src/pages/DashboardPage.tsx`:
  - [ ] Renders `AppLayout` with `SessionSidebar` + `ChatWindow`
  - [ ] Loads sessions on mount via `getSessions()`

- [ ] Create `frontend/src/App.tsx`:
  - [ ] React Router `BrowserRouter`
  - [ ] Route `/login` → `AuthPage`
  - [ ] Route `/` → `DashboardPage` (protected: redirect to `/login` if not authenticated)

### 8.10 Frontend Type Check
- [ ] Run `npx tsc --noEmit` — **zero TypeScript errors**
- [ ] Run `npm run lint` — **zero lint errors** (if ESLint is configured)

---

## 🔗 SECTION 9 — Backend ↔ Frontend Integration

### 9.1 CORS Verification
- [ ] Start Django dev server: `python manage.py runserver`
- [ ] Start Vite dev server: `npm run dev`
- [ ] Open browser DevTools → Network tab
- [ ] Confirm no CORS errors on any request from `localhost:5173` to `localhost:8000`

### 9.2 Auth Flow Integration
- [ ] Navigate to `http://localhost:5173/login`
- [ ] Submit login form with superuser credentials
- [ ] Confirm redirect to `/`
- [ ] Confirm `GET /api/auth/me/` returns correct user in Network tab
- [ ] Confirm JWT token is **not** visible in `localStorage` (check Application tab)
- [ ] Refresh page — confirm user remains logged in

### 9.3 Chat Flow Integration
- [ ] Click "New Session" → select "General"
- [ ] Confirm new session appears in sidebar
- [ ] Type a message and send
- [ ] Confirm `POST /api/chat/sessions/{id}/messages/` appears in Network tab
- [ ] Confirm AI response appears in chat within 5 seconds
- [ ] Refresh page — confirm message history persists

### 9.4 Log Upload Integration
- [ ] Upload a `.log` or `.txt` file via `LogUploadForm`
- [ ] Confirm `POST /api/logs/upload/` returns `200`
- [ ] Click "Analyze" on the uploaded log
- [ ] Confirm `GET /api/logs/{id}/analysis/` returns structured analysis
- [ ] Confirm `LogAnalysisCard` renders the results

---

## ✅ SECTION 10 — Phase 1 Completion Verification

### 10.1 Backend Final Checks
- [ ] `python manage.py check` — **no errors or warnings**
- [ ] `python manage.py test apps.users apps.chat apps.logs --verbosity=2` — **all tests pass**
- [ ] `python scripts/test_openai.py` — **`✅ OpenAI connection OK`**
- [ ] `ruff check backend/` — **zero linting issues**

### 10.2 Frontend Final Checks
- [ ] `npx tsc --noEmit` — **zero TypeScript errors**
- [ ] `npm run build` — **production build succeeds with no errors**

### 10.3 Functional Acceptance Criteria
- [ ] User can register and log in
- [ ] JWT stored correctly (httpOnly cookie / memory — **NOT** `localStorage`)
- [ ] Create new chat session → appears in sidebar immediately
- [ ] Send message → AI responds within 5 seconds
- [ ] Chat history persists across page refresh
- [ ] Log file uploads successfully
- [ ] Log analysis returns error patterns and AI summary
- [ ] All API errors show user-friendly messages in UI (no raw stack traces)
- [ ] App is usable on a 1280×800 viewport

### 10.4 Security Spot-Check
- [ ] Unauthenticated request to `GET /api/chat/sessions/` returns `401`
- [ ] User A cannot access User B's chat sessions or log files
- [ ] `OPENAI_API_KEY` is not present anywhere in frontend build output (`npm run build && grep -r "sk-" dist/`)
- [ ] `DEBUG = False` works without errors in production settings

---

## 📝 Notes & Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| _fill in_ | React scaffold: Vite vs CRA | _fill in_ |
| _fill in_ | Log storage: DB TextField vs file/S3 | _fill in_ |
| _fill in_ | Chat streaming: SSE vs full-response | _fill in_ |

---

> **Phase 1 is complete when all boxes in Section 10 are checked.**
> Move to [Phase 2 — Code Intelligence & Vector Search] only after all acceptance criteria pass.
