# AI Dev Assistant Dashboard — Execution Blueprint
### Django · React/TypeScript · OpenAI API · PostgreSQL

---

## PART 0 — DATABASE DECISION

### PostgreSQL over MySQL — Justified

| Criterion | PostgreSQL | MySQL |
|---|---|---|
| **JSON/JSONB support** | Native, fully indexed, queryable | Basic JSON type, limited indexing |
| **Full-text search** | Built-in `tsvector`/`tsquery` | Requires extra config or plugins |
| **Vector extension** | `pgvector` — embeddings stored natively | No native vector support |
| **Django ORM fit** | First-class support, all features work | Works but some advanced features limited |
| **Array fields** | Native (`ArrayField`) | Emulated via JSON |
| **Scalability** | Horizontal + vertical, MVCC, WAL | Solid but less advanced concurrency |
| **Async support** | Full async with `psycopg3` | Requires extra setup |

**Verdict:** PostgreSQL wins on every dimension relevant to this system. The `pgvector` extension alone is decisive — it lets you store OpenAI embeddings directly in the same DB as your app data, eliminating the need for a separate vector database in Phase 1 and 2. Use `pgvector` + PostgreSQL as your single storage backend. Only graduate to Pinecone/Qdrant if you scale to millions of vectors.

---

## PART 1 — PROJECT STRUCTURE

```
ai-dev-dashboard/
├── backend/                        # Django project
│   ├── config/                     # settings, urls, wsgi, asgi
│   ├── apps/
│   │   ├── core/                   # base models, permissions, mixins
│   │   ├── chat/                   # chat sessions, messages
│   │   ├── logs/                   # log upload, parsing, analysis
│   │   ├── code_analysis/          # repo parsing, embeddings, insights
│   │   ├── commands/               # command generation, sandboxed execution
│   │   ├── ai_layer/               # OpenAI integration, agent orchestration
│   │   └── users/                  # auth, RBAC
│   ├── services/                   # business logic layer (no Django coupling)
│   │   ├── openai_client.py
│   │   ├── embeddings.py
│   │   ├── log_parser.py
│   │   ├── code_parser.py
│   │   └── command_sandbox.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   └── manage.py
│
├── frontend/                       # React + TypeScript
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   ├── LogViewer/
│   │   │   ├── Terminal/
│   │   │   ├── CodeInsight/
│   │   │   └── Layout/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── store/                  # Zustand or Redux Toolkit
│   │   ├── api/                    # Axios instances, API calls
│   │   ├── types/                  # TypeScript interfaces
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
│
├── scripts/
│   ├── seed_db.py
│   ├── test_openai.py
│   └── test_sandbox.py
│
└── docs/
    └── api_spec.md
```

---

## PART 2 — MULTI-PHASE DEVELOPMENT PLAN

---

### PHASE 1 — Foundation & MVP (Weeks 1–3)

**Goal:** A working chat interface that can answer questions about uploaded code and logs using OpenAI.

---

#### 1.1 Backend — Django Setup

**Files to create:**

```
backend/config/settings/base.py
backend/config/settings/dev.py
backend/config/urls.py
backend/apps/users/models.py
backend/apps/users/views.py
backend/apps/chat/models.py
backend/apps/chat/views.py
backend/apps/chat/serializers.py
backend/apps/ai_layer/openai_client.py
```

**Django apps to register:**
```
INSTALLED_APPS = [
    ...
    'rest_framework',
    'corsheaders',
    'apps.users',
    'apps.chat',
    'apps.logs',
    'apps.code_analysis',
    'apps.commands',
    'apps.ai_layer',
]
```

**Database models — Phase 1:**

```python
# chat/models.py
class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    context_type = models.CharField(  # 'general' | 'code' | 'logs'
        max_length=20, default='general'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict)  # repo path, log file ref, etc.

class Message(models.Model):
    ROLES = [('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')]
    session = models.ForeignKey(ChatSession, related_name='messages',
                                on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLES)
    content = models.TextField()
    tool_calls = models.JSONField(null=True, blank=True)  # OpenAI tool use
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

**API endpoints — Phase 1:**

```
POST   /api/auth/login/
POST   /api/auth/logout/
GET    /api/auth/me/

POST   /api/chat/sessions/
GET    /api/chat/sessions/
GET    /api/chat/sessions/{id}/
DELETE /api/chat/sessions/{id}/

POST   /api/chat/sessions/{id}/messages/      ← main chat endpoint
GET    /api/chat/sessions/{id}/messages/

POST   /api/logs/upload/
GET    /api/logs/                              ← list uploaded logs
GET    /api/logs/{id}/analysis/               ← get AI analysis of log
```

**Core AI service — Phase 1:**

```python
# services/openai_client.py
class OpenAIClient:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL  # "gpt-4o"

    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False
    ) -> dict:
        """Base method — all AI calls route through here."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream"] = True
        return self.client.chat.completions.create(**kwargs)

    def embed_text(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
```

**Data flow — Phase 1 Chat:**

```
User types message
        ↓
POST /api/chat/sessions/{id}/messages/
        ↓
ChatView.post()
        ↓
Load full session message history from DB
        ↓
Build OpenAI messages array (system prompt + history + new message)
        ↓
OpenAIClient.chat_completion(messages)
        ↓
Save both user message and assistant response to DB
        ↓
Return response to frontend
        ↓
Frontend renders message in chat panel
```

---

#### 1.2 Frontend — Phase 1

**Core components:**

```
Layout (3-panel split: sidebar | chat | right panel)
ChatWindow
  └── MessageList
  └── MessageInput
  └── MessageBubble
SessionSidebar
  └── SessionList
  └── NewSessionButton
AuthPage
  └── LoginForm
```

**State shape (Zustand):**

```typescript
interface AppStore {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: Record<string, Message[]>;
  isLoading: boolean;
  user: User | null;

  // actions
  createSession: (type: string) => Promise<void>;
  sendMessage: (sessionId: string, content: string) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
}
```

**Key TypeScript types:**

```typescript
// types/chat.ts
interface ChatSession {
  id: string;
  title: string;
  context_type: 'general' | 'code' | 'logs';
  created_at: string;
  meta: Record<string, unknown>;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls?: ToolCall[];
  created_at: string;
}

// types/ai.ts
interface ToolCall {
  id: string;
  type: 'function';
  function: { name: string; arguments: string };
}
```

---

#### 1.3 Log Upload & Analysis — Phase 1

**Model:**

```python
# logs/models.py
class LogFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    content = models.TextField()           # raw log text
    file_size = models.IntegerField()
    analysis = models.JSONField(null=True) # AI-generated analysis
    analyzed_at = models.DateTimeField(null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

**Log analysis service:**

```python
# services/log_parser.py
class LogAnalyzer:
    ERROR_PATTERNS = [
        r'(?P<level>ERROR|CRITICAL|FATAL)\s+(?P<msg>.+)',
        r'Traceback \(most recent call last\)',
        r'(?P<code>\d{3})\s+(?P<path>/\S+)',   # HTTP status codes
        r'Exception:\s+(?P<exception>\w+)',
    ]

    def extract_errors(self, log_text: str) -> list[dict]:
        """Pure regex extraction — fast, no AI needed."""
        errors = []
        for pattern in self.ERROR_PATTERNS:
            for match in re.finditer(pattern, log_text, re.MULTILINE):
                errors.append({
                    'pattern': pattern,
                    'match': match.groupdict(),
                    'line': log_text[:match.start()].count('\n') + 1
                })
        return errors

    def summarize_for_ai(self, log_text: str, max_chars: int = 8000) -> str:
        """Trim log to most relevant portion for OpenAI context window."""
        errors = self.extract_errors(log_text)
        # Build a focused excerpt around error lines
        ...
```

---

### PHASE 2 — Code Intelligence & Vector Search (Weeks 4–6)

**Goal:** Attach a real code repository to a chat session. Ask questions, get answers grounded in actual code context.

---

#### 2.1 pgvector Setup

```bash
# Install extension
CREATE EXTENSION vector;
```

```python
# Install in Python
pip install pgvector

# code_analysis/models.py
from pgvector.django import VectorField

class CodeChunk(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE,
                                null=True, blank=True)
    repo_path = models.CharField(max_length=500)
    file_path = models.CharField(max_length=500)
    chunk_index = models.IntegerField()
    content = models.TextField()
    language = models.CharField(max_length=50)
    embedding = VectorField(dimensions=1536)  # text-embedding-3-small
    token_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # HNSW index for fast approximate nearest neighbor
            HnswIndex(
                name='code_embedding_idx',
                fields=['embedding'],
                m=16, ef_construction=64,
                opclasses=['vector_cosine_ops']
            )
        ]
```

#### 2.2 Repository Parsing Service

```python
# services/code_parser.py
SUPPORTED_EXTENSIONS = {
    '.py': 'python', '.ts': 'typescript', '.tsx': 'typescript',
    '.js': 'javascript', '.jsx': 'javascript', '.java': 'java',
    '.go': 'go', '.rs': 'rust', '.cpp': 'cpp', '.c': 'c',
    '.yaml': 'yaml', '.yml': 'yaml', '.json': 'json', '.md': 'markdown'
}
IGNORE_DIRS = {'node_modules', '.git', '__pycache__', 'venv', '.env',
               'dist', 'build', '.next', 'coverage'}
MAX_FILE_SIZE_KB = 500
CHUNK_SIZE_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 50

class RepoParser:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def walk_files(self) -> Generator[Path, None, None]:
        for path in self.repo_path.rglob('*'):
            if path.is_file():
                if any(d in path.parts for d in IGNORE_DIRS):
                    continue
                if path.suffix in SUPPORTED_EXTENSIONS:
                    if path.stat().st_size < MAX_FILE_SIZE_KB * 1024:
                        yield path

    def chunk_file(self, file_path: Path) -> list[dict]:
        """Split file into overlapping token-bounded chunks."""
        content = file_path.read_text(errors='replace')
        # Use tiktoken for accurate token counting
        ...
        return chunks

    def parse_repo(self) -> list[dict]:
        """Walk repo, chunk all files, return list of chunk dicts."""
        all_chunks = []
        for file_path in self.walk_files():
            chunks = self.chunk_file(file_path)
            all_chunks.extend(chunks)
        return all_chunks
```

**Ingestion task (Celery):**

```python
# code_analysis/tasks.py
@shared_task(bind=True, max_retries=2)
def ingest_repository(self, session_id: str, repo_path: str):
    """Parse repo → embed each chunk → store in pgvector."""
    parser = RepoParser(repo_path)
    client = OpenAIClient()
    chunks = parser.parse_repo()

    # Batch embed (OpenAI allows 2048 items per request)
    for batch in batched(chunks, 100):
        texts = [c['content'] for c in batch]
        embeddings = client.embed_batch(texts)
        CodeChunk.objects.bulk_create([
            CodeChunk(session_id=session_id,
                      repo_path=repo_path,
                      file_path=c['file_path'],
                      chunk_index=c['index'],
                      content=c['content'],
                      language=c['language'],
                      embedding=emb,
                      token_count=c['tokens'])
            for c, emb in zip(batch, embeddings)
        ])
```

**Semantic search:**

```python
# services/embeddings.py
class VectorSearch:
    def search_code(
        self,
        query: str,
        session_id: str,
        top_k: int = 8
    ) -> list[CodeChunk]:
        query_embedding = OpenAIClient().embed_text(query)
        # pgvector cosine similarity search
        return CodeChunk.objects.filter(
            session_id=session_id
        ).order_by(
            L2Distance('embedding', query_embedding)
        )[:top_k]
```

#### 2.3 RAG Chat Flow — Phase 2

```
User: "Why is the authentication middleware failing?"
        ↓
Embed user query → query_embedding
        ↓
VectorSearch.search_code(query, session_id, top_k=8)
        ↓
Retrieve top 8 most relevant code chunks
        ↓
Build system prompt:
  "You are a senior engineer. Use the following code context to answer."
  [CONTEXT: chunk1, chunk2, ..., chunk8]
        ↓
OpenAI chat completion with context-enriched prompt
        ↓
Response cites relevant files and explains the issue
```

#### 2.4 New API Endpoints — Phase 2

```
POST   /api/code/ingest/            ← start repo ingestion (returns task_id)
GET    /api/code/ingest/{task_id}/  ← poll ingestion status
GET    /api/code/search/            ← semantic search (q=, session_id=)
GET    /api/code/files/             ← list indexed files for session
DELETE /api/code/session/{id}/      ← clear all embeddings for session
```

#### 2.5 Frontend — Phase 2 Additions

```
RepoExplorer (left panel)
  └── FileTree
  └── IngestButton
  └── IngestionProgress (polling task_id)

CodeInsightPanel (right panel)
  └── SelectedCodeExplainer
  └── RelevantChunksViewer
  └── BugDetectionCard

MonacoEditor (code viewer, read-only with syntax highlighting)
```

---

### PHASE 3 — AI Terminal & Command Engine (Weeks 7–9)

**Goal:** Users describe what they want to do; the system generates shell commands, shows risk level, waits for confirmation, then executes safely.

---

#### 3.1 Command Model

```python
# commands/models.py
class CommandRequest(models.Model):
    RISK_LEVELS = [
        ('safe', 'Safe'),          # read-only, no side effects
        ('moderate', 'Moderate'),  # creates/modifies files
        ('dangerous', 'Dangerous') # deletes, installs, network ops
    ]
    STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('executed', 'Executed'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_intent = models.TextField()        # "restart the backend server"
    generated_command = models.TextField()  # "sudo systemctl restart gunicorn"
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS)
    risk_explanation = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    execution_output = models.TextField(blank=True)
    execution_error = models.TextField(blank=True)
    exit_code = models.IntegerField(null=True)
    executed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 3.2 Command Generation Service

```python
# services/command_sandbox.py
COMMAND_GENERATION_PROMPT = """
You are a DevOps assistant. Given the user's intent, generate the exact shell
command to accomplish it. Assess risk level.

Respond ONLY in JSON:
{
  "command": "<exact shell command>",
  "risk_level": "safe|moderate|dangerous",
  "risk_explanation": "<one sentence explaining why>",
  "alternatives": ["<safer alternative if exists>"],
  "requires_sudo": true|false
}
"""

BLACKLISTED_PATTERNS = [
    r'rm\s+-rf\s+/', r'dd\s+if=', r'mkfs\.',
    r':\(\)\{.*\}', r'wget.*\|\s*sh', r'curl.*\|\s*bash',
    r'chmod\s+777', r'> /dev/sd', r'shutdown', r'reboot',
    r'DROP\s+DATABASE', r'TRUNCATE',
]

class CommandEngine:
    def generate(self, intent: str) -> dict:
        """Generate command + risk assessment using OpenAI."""
        ...

    def validate_safety(self, command: str) -> tuple[bool, str]:
        """Check command against blacklist before any execution."""
        for pattern in BLACKLISTED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command matches dangerous pattern: {pattern}"
        return True, "OK"

    def execute(self, command_request: CommandRequest) -> dict:
        """
        Execute only after:
        1. User explicitly approved via API
        2. Safety validation passes
        3. Status is 'approved'
        """
        if command_request.status != 'approved':
            raise PermissionError("Command not approved by user")

        is_safe, reason = self.validate_safety(command_request.generated_command)
        if not is_safe:
            command_request.status = 'failed'
            command_request.execution_error = reason
            command_request.save()
            raise SecurityError(reason)

        # Execute in subprocess with timeout
        try:
            result = subprocess.run(
                command_request.generated_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,             # hard limit
                cwd=settings.SANDBOX_DIR
            )
            command_request.execution_output = result.stdout
            command_request.execution_error = result.stderr
            command_request.exit_code = result.returncode
            command_request.status = 'executed'
            command_request.executed_at = timezone.now()
            command_request.save()
            return {'stdout': result.stdout, 'stderr': result.stderr,
                    'exit_code': result.returncode}
        except subprocess.TimeoutExpired:
            command_request.status = 'failed'
            command_request.execution_error = 'Execution timed out (30s)'
            command_request.save()
            raise
```

#### 3.3 Terminal API Endpoints

```
POST   /api/commands/generate/         ← user intent → generated command
POST   /api/commands/{id}/approve/     ← user explicitly approves
POST   /api/commands/{id}/reject/      ← user rejects
POST   /api/commands/{id}/execute/     ← server executes (only if approved)
GET    /api/commands/history/          ← command execution history
```

#### 3.4 WebSocket for Live Output (Django Channels)

```python
# commands/consumers.py
class TerminalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        await self.channel_layer.group_add(
            f'terminal_{self.session_id}', self.channel_name
        )
        await self.accept()

    async def terminal_output(self, event):
        await self.send(text_data=json.dumps({
            'type': 'output',
            'data': event['data']
        }))
```

#### 3.5 Frontend Terminal — Phase 3

```
AITerminal (bottom panel)
  └── xterm.js instance (for rendering)
  └── IntentInput ("What do you want to do?")
  └── CommandPreview
       └── CommandText (Monaco-style code block)
       └── RiskBadge (safe=green, moderate=yellow, dangerous=red)
       └── RiskExplanation
       └── ApproveButton / RejectButton
  └── ExecutionOutput (live via WebSocket)
  └── CommandHistory
```

---

### PHASE 4 — GitHub Integration & Automated Fixes (Weeks 10–12)

**Goal:** Connect to a GitHub repo, fetch PRs/issues, generate fixes, open PRs automatically.

---

#### 4.1 GitHub Service

```python
# services/github_client.py
class GitHubClient:
    def __init__(self, token: str):
        self.g = Github(token)  # PyGithub

    def get_repo(self, owner: str, name: str) -> Repository:
        return self.g.get_repo(f"{owner}/{name}")

    def get_open_issues(self, repo: Repository) -> list[dict]:
        ...

    def create_pull_request(
        self,
        repo: Repository,
        branch: str,
        title: str,
        body: str,
        base: str = 'main'
    ) -> PullRequest:
        ...

    def commit_fix(
        self,
        repo: Repository,
        branch: str,
        file_path: str,
        new_content: str,
        commit_message: str
    ):
        ...
```

#### 4.2 Automated Fix Workflow

```
1. User: "Fix the bug in auth/middleware.py causing 401 errors"
2. System fetches file content from GitHub
3. VectorSearch finds related code chunks
4. AI generates diff/fix
5. System creates new branch: fix/auth-middleware-{timestamp}
6. Commits fixed file
7. Opens PR with AI-generated description
8. Returns PR URL to user
```

---

### PHASE 5 — Production Hardening (Weeks 13–14)

- Rate limiting (django-ratelimit)
- Request logging (structlog)
- Error tracking (Sentry)
- API authentication (JWT with refresh tokens)
- Environment configs (django-environ)
- Celery + Redis for background tasks
- Nginx + Gunicorn deployment
- Docker Compose for full stack
- GitHub Actions CI/CD pipeline
- Health check endpoints

---

## PART 3 — AI TOOL ASSIGNMENT STRATEGY

---

### Tool Profiles

| Tool | Strengths | Limitations |
|---|---|---|
| **Claude** | Architecture design, complex reasoning, multi-file integration, security analysis, system design critique | Slower for bulk generation |
| **Gemini** | Broad knowledge, large context window (1M tokens), multi-file awareness | Less precise on deep logic |
| **OpenCode** | Autonomous repo-level edits, running in terminal, file operations, iteration | May need guidance on architecture |
| **Qwen (Ollama)** | Fast local generation, boilerplate, repetitive patterns, no API cost | Weaker on novel architecture |

---

### Module → AI Tool Assignments

#### Claude (This Conversation) — Critical Architecture & Logic

Use Claude for anything where **wrong design compounds into bigger problems later**.

| Module / File | Why Claude |
|---|---|
| `services/openai_client.py` | Core AI integration — token management, retry logic, streaming |
| `services/command_sandbox.py` | Security-critical — blacklist design, subprocess safety |
| `services/embeddings.py` | RAG design — chunking strategy, similarity search logic |
| `apps/ai_layer/agent.py` | Agent orchestration — tool selection, multi-step reasoning |
| `config/settings/` (all) | Security settings, CORS, ALLOWED_HOSTS, SECRET_KEY handling |
| `apps/users/` (RBAC) | Auth + permissions — wrong design creates security holes |
| Database schema design | Relationships, indexes, pgvector setup |
| `services/log_parser.py` | Combined regex + AI logic — complex hybrid design |
| API contract definition | Endpoint design, request/response shapes, error codes |
| WebSocket consumer design | Async correctness, channel layer architecture |
| `services/github_client.py` | Multi-step workflow, branch/PR automation logic |
| Celery task design | Task dependencies, retry logic, failure handling |

**How to use Claude:** Give full context. Provide existing related files. Ask for the complete file with reasoning. Then verify and test manually.

---

#### Gemini — Large-Scale File Generation & Cross-File Awareness

Use Gemini when you need to **generate many files at once** or reason across a large codebase.

| Task | Why Gemini |
|---|---|
| Generate all Django model files at once | 1M context fits your entire schema plan |
| Generate all serializers from existing models | Reads all models, generates matching serializers |
| Generate all test files for an existing app | Reads all views/services, writes comprehensive tests |
| Scaffold the entire React component tree | Can see all TypeScript types and generate consistent components |
| API documentation generation | Reads all views and serializers, generates OpenAPI spec |
| Refactoring across multiple files | Large context = sees all interdependencies |

**How to use Gemini:** Upload all relevant files as context. Ask for multiple files in one shot. Review for correctness after.

---

#### OpenCode — Terminal-Resident Iterative Development

Use OpenCode for tasks you want to **run, test, and fix in a loop** directly in your repo.

| Task | Why OpenCode |
|---|---|
| Initial Django project scaffolding | `django-admin startproject`, app creation, directory setup |
| Running migrations and checking output | Executes commands, sees errors, fixes automatically |
| Installing packages and updating requirements | Reads errors, updates requirements.txt |
| Iterative bug fixing after test failures | Runs tests, sees failures, edits files, re-runs |
| Database migration generation and application | Runs `makemigrations`, handles conflicts |
| Boilerplate CRUD views + URL routing | Repetitive but must match existing models |
| Setting up Celery + Redis configuration | File edits + running test tasks |

**How to use OpenCode:** Run it inside the repo. Give it a specific, bounded task. Let it run-and-fix cycles. Review the diff before committing.

---

#### Qwen via Ollama (Antigravity) — Fast Local Boilerplate

Use Qwen for **offline, fast, no-cost generation** of repetitive or low-risk code.

| Task | Why Qwen |
|---|---|
| Django admin.py registrations | Pure boilerplate, no architecture |
| TypeScript type interfaces from JSON schema | Mechanical transformation |
| URL routing files | Repetitive patterns |
| Simple React UI components (cards, badges, buttons) | Standard patterns |
| Utility functions (date formatting, string manipulation) | Low-risk helpers |
| .env.example templates | Standard format |
| requirements.txt additions | Package names |
| Simple CSS/Tailwind styling | Iterative, easy to fix |
| Test data fixtures | JSON/Python fixture files |

**How to use Qwen:** Paste a small, self-contained spec. Get output. Paste into file. Quick manual review.

---

### Per-Phase AI Tool Routing

```
PHASE 1 (Foundation)
├── Architecture decisions        → Claude
├── Django project scaffold       → OpenCode (run startproject, startapp)
├── Model design                  → Claude (review schema)
├── Model code                    → Qwen (implement Claude's schema)
├── Serializers                   → Qwen
├── Base views (CRUD)             → OpenCode
├── OpenAI service                → Claude
├── React project scaffold        → OpenCode (npx create-react-app)
├── Component tree planning       → Claude
├── React components              → Gemini (multi-component, consistent types)
├── Zustand store                 → Claude (complex state logic)
└── API integration (axios)       → Qwen

PHASE 2 (Vector Search)
├── pgvector schema               → Claude (index strategy)
├── Chunking algorithm            → Claude (token overlap logic)
├── Embedding batch logic         → Claude (rate limit handling)
├── Celery task design            → Claude
├── Celery task code              → OpenCode (run and test)
├── RepoExplorer component        → Gemini
├── CodeInsightPanel              → Gemini
└── MonacoEditor integration      → Qwen (standard setup)

PHASE 3 (Terminal)
├── Sandbox security design       → Claude (critical)
├── Blacklist patterns            → Claude (security review)
├── Command generation prompt     → Claude
├── WebSocket consumer            → Claude
├── xterm.js integration          → Qwen
├── Terminal UI components        → Gemini
└── Risk badge component          → Qwen

PHASE 4 (GitHub)
├── GitHub workflow design        → Claude
├── PyGithub integration          → OpenCode (run and test)
├── PR generation logic           → Claude
└── GitHub UI components          → Qwen

PHASE 5 (Production)
├── Security review               → Claude
├── Docker/Nginx config           → OpenCode
├── CI/CD pipeline                → Gemini (full YAML)
└── Rate limiting setup           → Qwen
```

---

## PART 4 — STEP-BY-STEP DEVELOPMENT WORKFLOW

---

### Stage 1: Planning → Code Generation

```
Step 1.  Open this blueprint in one window.
Step 2.  For each module, identify the assigned AI tool (see Part 3).
Step 3.  Before generating any code, define the exact interface:
         - What does this function take as input?
         - What does it return?
         - What side effects does it have?
Step 4.  When prompting Claude: include (a) the relevant section of this
         blueprint, (b) any already-written related files, (c) exact
         interface spec. Ask for the full file, not a snippet.
Step 5.  When prompting Gemini: upload all models/types files as context
         before asking it to generate dependent files.
Step 6.  When prompting Qwen/OpenCode: give short, self-contained specs.
         Boilerplate doesn't need architectural context.
```

---

### Stage 2: Integration Protocol

**The golden rule: integrate one module at a time. Never merge two AI-generated modules that haven't each been independently tested.**

```
For each new module:
  1. Generate code (AI tool per Part 3)
  2. Read the generated code manually — understand it
  3. Check imports: do all referenced functions/classes exist?
  4. Check types: do TypeScript interfaces match backend response shapes?
  5. Run linter (ruff for Python, eslint for TS)
  6. Write a minimal smoke test
  7. Run the test
  8. Only then integrate with dependent modules
```

**Frontend ↔ Backend integration checklist:**

```
□ Backend endpoint returns correct HTTP status codes
□ Response shape matches TypeScript interface exactly
  (field names, types, nullability)
□ CORS allows frontend origin
□ Authentication header is sent correctly
□ Error responses are handled (not just 200s)
□ Loading states are represented in Zustand store
□ Network errors are caught and displayed to user
```

---

### Stage 3: Testing Strategy

#### Backend Testing

```bash
# Run after each Phase
python manage.py test apps.chat --verbosity=2
python manage.py test apps.logs
python manage.py test apps.code_analysis
python manage.py test apps.commands

# Integration test: full chat flow
python scripts/test_chat_flow.py

# OpenAI integration test (uses real API, run sparingly)
python scripts/test_openai.py

# Vector search test
python scripts/test_vector_search.py
```

**Test template for each service:**

```python
# tests/test_command_engine.py
class CommandEngineSecurityTests(TestCase):
    def test_blacklisted_rm_rf_rejected(self):
        engine = CommandEngine()
        is_safe, _ = engine.validate_safety("rm -rf /")
        self.assertFalse(is_safe)

    def test_safe_ls_approved(self):
        engine = CommandEngine()
        is_safe, _ = engine.validate_safety("ls -la")
        self.assertTrue(is_safe)

    def test_execution_requires_approved_status(self):
        cmd = CommandRequest(status='pending', ...)
        with self.assertRaises(PermissionError):
            CommandEngine().execute(cmd)
```

#### Frontend Testing

```bash
# Type checking
npx tsc --noEmit

# Unit tests
npm run test

# E2E (Playwright, add in Phase 3)
npx playwright test
```

#### Command Execution Testing — Special Protocol

**Never test command execution against your actual system.** Use this protocol:

```bash
# 1. Create isolated test directory
mkdir /tmp/ai_dashboard_sandbox
export SANDBOX_DIR=/tmp/ai_dashboard_sandbox

# 2. Test only 'safe' commands first
# Start with: ls, pwd, echo, cat (read-only)

# 3. For 'moderate' commands, test in sandbox dir only
# cat /tmp/ai_dashboard_sandbox/test.txt
# mkdir /tmp/ai_dashboard_sandbox/newdir

# 4. 'Dangerous' commands: NEVER execute in tests
# Unit test only validates they are blocked

# 5. Verify blacklist manually:
python manage.py shell
>>> from services.command_sandbox import CommandEngine
>>> e = CommandEngine()
>>> e.validate_safety("rm -rf /")       # should be False
>>> e.validate_safety("ls -la")          # should be True
>>> e.validate_safety("wget bad | sh")   # should be False
```

---

### Stage 4: Handling Inconsistencies Between AI Tools

**The problem:** Claude generates a service interface. Qwen generates code that calls it. The method signatures differ. System breaks.

**Solution — the Contract File:**

```python
# services/contracts.py
# ─────────────────────────────────────────────────────────────────
# THIS FILE IS THE GROUND TRUTH FOR ALL SERVICE INTERFACES.
# Any AI tool that generates code calling a service MUST match this.
# Update this file whenever a service interface changes.
# ─────────────────────────────────────────────────────────────────

from typing import Protocol

class IOpenAIClient(Protocol):
    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        stream: bool
    ) -> dict: ...

    def embed_text(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

class IVectorSearch(Protocol):
    def search_code(
        self,
        query: str,
        session_id: str,
        top_k: int
    ) -> list: ...  # returns list[CodeChunk]

class ICommandEngine(Protocol):
    def generate(self, intent: str) -> dict: ...
    def validate_safety(self, command: str) -> tuple[bool, str]: ...
    def execute(self, command_request) -> dict: ...
```

**When an AI tool generates code that calls another service:** paste the relevant Protocol from `contracts.py` into the prompt. Tell the AI tool: "match this interface exactly."

---

### Stage 5: Iterative Refinement Workflow

```
Problem found (test failure, wrong output, type error)
        ↓
Identify which module owns the problem
        ↓
Choose AI tool based on problem type:
  - Architecture problem       → Claude
  - Wrong output, fix one file → OpenCode or Qwen
  - Spans multiple files       → Gemini
        ↓
Provide: (1) the broken code, (2) the error message,
         (3) the test that failed or the expected behavior
        ↓
AI generates fix
        ↓
You read the fix before applying
        ↓
Run the test again
        ↓
Commit with message: "fix(module): description [AI-assisted]"
```

---

### Stage 6: Manual Verification Checklist (Per Phase)

#### Phase 1 Completion Criteria

```
□ User can register and log in
□ JWT token is stored correctly (httpOnly cookie or memory, NOT localStorage)
□ Create new chat session → appears in sidebar
□ Send message → AI responds within 5 seconds
□ Chat history persists across page refresh
□ Log file uploads successfully
□ Log analysis returns error patterns and AI summary
□ All API errors show user-friendly messages in UI
□ python manage.py check returns no errors
□ All tests pass: python manage.py test
```

#### Phase 2 Completion Criteria

```
□ Repo path can be attached to a chat session
□ Ingestion task runs and reports progress
□ After ingestion: "how many files indexed?" returns correct count
□ Ask about a specific function → response cites correct file
□ Ask about a bug → response references actual code
□ Embedding search returns results in < 200ms
□ Large repo (> 1000 files) ingests without memory crash
□ Celery task handles errors gracefully (logs failure, doesn't crash worker)
```

#### Phase 3 Completion Criteria

```
□ User types intent → command is generated
□ Risk level is always shown before execution
□ 'dangerous' commands show red badge and require extra confirmation
□ Approving a 'safe' command → executes → output appears in terminal
□ Blacklisted command → blocked even if somehow approved
□ Command history is logged to DB
□ WebSocket connection recovers after disconnect
□ Timeout (30s) kills hanging commands
```

---

## PART 5 — QUICK REFERENCE: PROMPT TEMPLATES

### For Claude (Architecture)

```
I am building [module name] for the AI Dev Assistant Dashboard.

Context:
- Django backend, React/TypeScript frontend
- PostgreSQL + pgvector
- Already built: [list existing files]

The interface this module must satisfy:
[paste from contracts.py]

Related existing code:
[paste 1-2 related files]

Please generate the complete implementation of [filename].
Focus on: [specific concern — security / correctness / performance].
Explain any non-obvious design decisions inline as comments.
```

### For Gemini (Multi-file Generation)

```
Here is the full Django models file: [paste]
Here is the TypeScript types file: [paste]
Here is an example serializer: [paste]

Generate:
1. Serializers for ALL models in the models file
2. ViewSets for each serializer
3. URL router configuration

Match the exact field names and types. Use consistent naming conventions.
```

### For OpenCode (Terminal Tasks)

```
Task: Set up Celery with Redis for the Django backend.

The project is at: ~/ai-dev-dashboard/backend/
Requirements file is at: requirements/dev.txt
Settings file is at: config/settings/dev.py

Steps:
1. Install celery[redis] and update requirements
2. Create backend/celery.py with correct app config
3. Update config/__init__.py to load celery
4. Add CELERY_BROKER_URL to dev.py
5. Test with: celery -A backend worker --loglevel=info

Run each step, check for errors, and fix before proceeding.
```

### For Qwen (Boilerplate)

```
Generate a Django admin.py for these models:
[paste model names and fields]

Register all models with basic list_display and search_fields.
No custom admin actions needed.
```

---

## PART 6 — ENVIRONMENT SETUP COMMANDS

```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install django djangorestframework psycopg2-binary pgvector \
  openai celery[redis] django-cors-headers channels channels-redis \
  PyGithub structlog sentry-sdk tiktoken python-environ ruff

# Frontend
npx create-react-app frontend --template typescript
cd frontend
npm install axios zustand @tanstack/react-query \
  @monaco-editor/react xterm xterm-addon-fit \
  tailwindcss @headlessui/react lucide-react

# Database
psql -U postgres -c "CREATE DATABASE ai_dashboard;"
psql -U postgres -d ai_dashboard -c "CREATE EXTENSION vector;"

# Redis (for Celery)
docker run -d -p 6379:6379 redis:alpine

# Verify OpenAI connection
python scripts/test_openai.py
```

---

## PART 7 — DECISION LOG (Fill in as you build)

| Decision | Option A | Option B | Chosen | Reason |
|---|---|---|---|---|
| Vector DB | pgvector | Pinecone | pgvector | Single DB, Phase 1-2 sufficient |
| Auth method | JWT | Session | JWT | Stateless, good for API |
| State manager | Zustand | Redux | Zustand | Less boilerplate |
| Task queue | Celery | RQ | Celery | More features, better Django integration |
| WebSocket | Django Channels | Socket.io | Django Channels | Native Django |
| CSS | Tailwind | CSS Modules | Tailwind | Faster iteration |

---

*This blueprint is a living document. Update the Decision Log and contracts.py as you build. Every major architectural change should be reviewed with Claude before implementation.*