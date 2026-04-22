# Phase 1 — Foundation & MVP: Implementation Plan
### AI Dev Assistant Dashboard · Django · React/TypeScript · OpenAI · PostgreSQL
**Timeline:** Weeks 1–3

---

## Goal

Deliver a working chat interface that can:
- Authenticate users (register / login / JWT)
- Create and persist chat sessions with full message history
- Send messages to OpenAI and stream back responses
- Accept uploaded log files and return AI-generated analysis

---

## User Review Required

> [!IMPORTANT]
> Phase 1 does **not** include vector search, code ingestion, or command execution. Those are Phase 2+. Make sure stakeholders understand the MVP scope before proceeding.

> [!WARNING]
> JWT tokens must be stored in **httpOnly cookies or in-memory only** — never in `localStorage`. This is a hard security requirement per the blueprint.

> [!CAUTION]
> The `OPENAI_API_KEY` must never be committed to source control. Use `django-environ` and a `.env` file from day one — even in development.

---

## Open Questions

> [!NOTE]
> 1. **React scaffold tool** — The plan mentions `create-react-app`, but that project is now unmaintained. Should we use **Vite + React + TypeScript** instead? It is significantly faster and the current community standard.
> 2. **Log file storage** — Phase 1 stores raw log text in a `TextField`. For large logs this may be slow. Should we store files to disk/S3 and keep only a reference in the DB, or is DB storage acceptable for MVP?
> 3. **Streaming** — Should the Phase 1 chat endpoint stream tokens back to the frontend via SSE/WebSocket, or is a full-response JSON reply acceptable for MVP?

---

## Proposed Changes

---

### Environment & Infrastructure

#### [NEW] `backend/requirements.txt`
Core Python dependencies for the project.

```
django>=5.0
djangorestframework>=3.15
psycopg2-binary>=2.9
openai>=1.0
django-cors-headers>=4.3
djangorestframework-simplejwt>=5.3
django-environ>=0.11.2
tiktoken>=0.7
ruff>=0.4
django-extensions>=3.2
ipython
```

#### Local PostgreSQL Setup (No Docker)
PostgreSQL runs directly on the host machine. No Docker is used for local development.

```bash
# Start PostgreSQL service
sudo systemctl start postgresql

# Create the database
psql -U postgres -c "CREATE DATABASE ai_dashboard;"

# Verify it exists
psql -U postgres -c "\l" | grep ai_dashboard
```

#### [NEW] `.env.example`
Template environment file — documents all required variables with safe placeholder values.

```
SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://postgres:postgres@localhost:5432/ai_dashboard
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
SANDBOX_DIR=/tmp/ai_dashboard_sandbox
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

---

### Backend — Django Project Scaffold

#### [NEW] `backend/manage.py`
Standard Django entry point.

#### [NEW] `backend/config/settings.py`
Single settings file for all environments (local-only, no split):
- `DEBUG = True` (set via env, defaults to `True`)
- `CORS_ALLOW_ALL_ORIGINS = True` (local dev)
- `EMAIL_BACKEND` set to console backend
- Installed apps (all 6 custom apps + DRF + CORS + JWT)
- Database config via `DATABASE_URL` from environment
- JWT auth as the default DRF authentication class
- `OPENAI_API_KEY` and `OPENAI_MODEL` loaded from env
- `SANDBOX_DIR` loaded from env

#### [NEW] `backend/config/urls.py`
Root URL config — routes to each app's `urls.py` under `/api/`.

#### [NEW] `backend/config/wsgi.py` and `backend/config/asgi.py`
Standard entry points. ASGI scaffolded now for Django Channels in Phase 3.

---

### Backend — `apps/users` (Auth & RBAC)

> **AI Tool: Claude** — security-critical.

#### [NEW] `backend/apps/users/models.py`
Custom `User` model extending `AbstractUser` with `role` field (admin / developer / viewer).

#### [NEW] `backend/apps/users/views.py`
- `LoginView` — validates credentials, returns JWT in httpOnly cookies
- `LogoutView` — blacklists refresh token
- `MeView` — returns current user data

#### [NEW] `backend/apps/users/serializers.py`
`UserSerializer` — exposes `id`, `username`, `email`, `role`.

#### [NEW] `backend/apps/users/urls.py`
```
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
POST /api/auth/token/refresh/
```

---

### Backend — `apps/chat` (Sessions & Messages)

#### [NEW] `backend/apps/chat/models.py`
`ChatSession` and `Message` models — exact schema from blueprint.

#### [NEW] `backend/apps/chat/serializers.py`
`ChatSessionSerializer` and `MessageSerializer`.

#### [NEW] `backend/apps/chat/views.py`
- `ChatSessionViewSet` — scoped to `request.user`
- `MessageView` — POST sends to OpenAI, saves both turns, returns assistant message

#### [NEW] `backend/apps/chat/urls.py`
```
POST/GET /api/chat/sessions/
GET/DELETE /api/chat/sessions/{id}/
POST/GET /api/chat/sessions/{id}/messages/
```

---

### Backend — `apps/logs` (Log Upload & Analysis)

#### [NEW] `backend/apps/logs/models.py`
`LogFile` model — exact schema from blueprint.

#### [NEW] `backend/apps/logs/views.py`
- `LogUploadView` — multipart file upload
- `LogListView` — list user's logs
- `LogAnalysisView` — runs `LogAnalyzer` + `OpenAIClient`, caches in `analysis` field

---

### Backend — `services/` (Business Logic)

> **AI Tool: Claude** — all service files are critical.

#### [NEW] `backend/services/openai_client.py`
`OpenAIClient` with `chat_completion`, `embed_text`, `embed_batch`, retry logic.

#### [NEW] `backend/services/log_parser.py`
`LogAnalyzer` with `extract_errors`, `summarize_for_ai`, `build_analysis_prompt`.

#### [NEW] `backend/services/contracts.py`
Protocol interfaces (`IOpenAIClient`) — ground truth for all service callers.

---

### Backend — Placeholder Apps (Scaffold Only)

Create minimal structure for Phase 2+ apps so migrations don't break:
- `backend/apps/code_analysis/`
- `backend/apps/commands/`
- `backend/apps/ai_layer/`

---

### Frontend — React/TypeScript Scaffold

> **AI Tool: OpenCode** for scaffold; **Claude** for store; **Gemini** for components.

#### [NEW] `frontend/` — Vite + React + TypeScript

#### [NEW] `frontend/src/types/` — `chat.ts`, `auth.ts`, `logs.ts`

#### [NEW] `frontend/src/api/` — `client.ts` (Axios), `auth.ts`, `chat.ts`, `logs.ts`

#### [NEW] `frontend/src/store/useAppStore.ts` — Zustand store per blueprint interface

#### [NEW] `frontend/src/components/`
- `Layout/AppLayout.tsx` — 3-panel split
- `Chat/ChatWindow.tsx`, `MessageList.tsx`, `MessageBubble.tsx`, `MessageInput.tsx`
- `SessionSidebar/SessionList.tsx`, `NewSessionButton.tsx`
- `LogViewer/LogUploadForm.tsx`, `LogAnalysisCard.tsx`

#### [NEW] `frontend/src/pages/` — `AuthPage.tsx`, `DashboardPage.tsx`

#### [NEW] `frontend/src/App.tsx` — React Router with protected routes

---

### Scripts

#### [NEW] `scripts/test_openai.py` — API key smoke test
#### [NEW] `scripts/seed_db.py` — Creates test user, session, messages

---

## Verification Plan

### Automated Tests

```bash
python manage.py check
python manage.py test apps.users apps.chat apps.logs --verbosity=2
python scripts/test_openai.py
npx tsc --noEmit
npm run test
```

### Phase 1 Completion Criteria

```
□ User can register and log in
□ JWT stored correctly (httpOnly cookie/memory — NOT localStorage)
□ Create new chat session → appears in sidebar
□ Send message → AI responds within 5 seconds
□ Chat history persists across page refresh
□ Log file uploads successfully
□ Log analysis returns error patterns and AI summary
□ All API errors show user-friendly messages in UI
□ python manage.py check returns no errors
□ All tests pass: python manage.py test
```

---

*Last updated: 2026-04-22. Update as decisions are made during Phase 1 execution.*
