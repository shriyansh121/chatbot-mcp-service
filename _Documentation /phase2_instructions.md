# 🔧 Phase 2: Backend — Server + MCP + GCP Tools

> **Goal:** Build the FastAPI server, MCP tool server, GCP service modules, and wire everything together.
> **Rule:** You code it, I review it. Ask me if stuck.

---

## New Folder Structure Inside `backend/app/`

```
backend/app/
├── __init__.py              ← exists
├── main.py                  ← FastAPI app (exists, currently empty)
├── db/                      ← exists (your models, base, session)
│   ├── base.py
│   ├── session.py
│   └── models/
├── core/                    ← NEW: Agent + LLM provider logic
│   ├── __init__.py
│   ├── agent.py             # LangGraph agent setup
│   └── providers/           # Multi-model support (later)
│       └── __init__.py
├── gcp/                     ← NEW: GCP service modules
│   ├── __init__.py
│   ├── vm.py                # Compute Engine
│   ├── storage.py           # Cloud Storage
│   ├── vpc.py               # VPC Networks
│   ├── cloudsql.py          # Cloud SQL
│   ├── gke.py               # GKE Clusters
│   ├── functions.py         # Cloud Functions
│   ├── dns.py               # DNS Zones
│   ├── loadbalancer.py      # Load Balancers
│   └── billing.py           # Billing (LAST)
├── mcp/                     ← NEW: MCP Tool Server
│   ├── __init__.py
│   ├── server.py            # MCP server setup + tool registration
│   └── tools.py             # LangChain @tool wrappers for agent
├── server/                  ← NEW: FastAPI routers
│   ├── __init__.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py        # GET /health
│   │   ├── auth.py          # POST /auth/login, /auth/register
│   │   ├── chat.py          # POST /api/v1/chat
│   │   └── sessions.py      # GET/POST/DELETE /api/v1/sessions
│   └── middleware/
│       ├── __init__.py
│       └── auth.py          # JWT token verification middleware
├── services/                ← NEW: Business logic layer
│   ├── __init__.py
│   ├── auth_service.py      # Hash passwords, create JWT, verify
│   ├── chat_service.py      # Orchestrate: router → agent → format → save
│   └── session_service.py   # CRUD for sessions + messages
└── lib/                     ← NEW: Utilities
    ├── __init__.py
    ├── logger.py             # Structured logging
    └── config.py             # Central config (reads .env, config.yaml)
```

---

## Build Order (Do These In Sequence)

### Step 1: Create ALL empty folders + `__init__.py` files

Create every folder listed above with an empty `__init__.py` inside each.
This sets up the Python package structure so imports work.

---

### Step 2: `lib/config.py` — Central Config

**What it does:** Single place to load all settings (DB URL, API keys, GCP project ID, etc.)

**What to put:**
- Use `pydantic-settings` (like old project's `config/settings.py`)
- Load from `.env.dev` using `dotenv`
- Fields needed: `DATABASE_URL`, `GROQ_API_KEY`, `PROJECT_ID`, `BILLING_ID`, `REGION`, `ZONE`
- Export a global `settings` instance

**Reference:** Look at [old settings.py](file:///Users/shriyansh/Documents/project_gbot/config/settings.py) — same pattern but simpler (no YAML needed for now)

**New dependency:** Add `pydantic-settings` to requirements.txt

---

### Step 3: `lib/logger.py` — Logger

**What it does:** Creates named loggers for each module.

**What to put:**
- A `setup_logger(name)` function that returns a Python `logging.Logger`
- Console output + optional file output
- Use `sys.stderr` (not stdout) for MCP compatibility

**Reference:** Directly copy pattern from [old logger.py](file:///Users/shriyansh/Documents/project_gbot/src/lib/logger.py)

---

### Step 4: `gcp/vm.py` — First GCP Service (VM ONLY)

**What it does:** Calls Google Cloud Compute API to list/get VM instances.

**What to put:**
- `list_vms(project_id=None)` → returns list of VM dicts
- `get_vm_details(instance_name, project_id=None)` → returns single VM dict
- Use `google-cloud-compute` library
- Get `project_id` from your `config.settings` if not provided
- Extract only useful fields (name, status, zone, IPs) — NOT raw API dump

**Reference:** [old vm.py](file:///Users/shriyansh/Documents/project_gbot/src/gcp/vm.py) — you can use the same logic but import config from your new `lib/config.py`

**New dependency:** Add `google-cloud-compute` to requirements.txt

> [!IMPORTANT]
> Build and TEST just `vm.py` first. Don't build all 9 services at once.
> Create a test script: `python -c "from app.gcp.vm import list_vms; print(list_vms())"`

---

### Step 5: `mcp/tools.py` — LangChain Tool Wrappers

**What it does:** Wraps your GCP functions as LangChain `@tool` so the agent can call them.

**What to put:**
- Import from `app.gcp.vm` (and later other services)
- Each function decorated with `@tool` from `langchain_core.tools`
- A `get_tools()` function that returns list of all tools
- Helper `_to_json_string(data)` to safely convert API results

**Reference:** [old tools.py](file:///Users/shriyansh/Documents/project_gbot/src/lib/tools.py) — same pattern, start with just VM tools

**New dependency:** Add `langchain-core` to requirements.txt

---

### Step 6: `core/agent.py` — LangGraph Agent

**What it does:** Creates the AI agent that uses tools to answer questions.

**What to put:**
- `create_agent()` function that:
  1. Creates a `ChatGroq` LLM instance (using API key from config)
  2. Loads tools from `mcp/tools.py`
  3. Creates a `create_react_agent(llm, tools, prompt=system_message)`
  4. Returns the agent
- System prompt that says: "You are a GCP assistant. Only use tool results. Never fabricate data."

**Reference:** [old main.py lines 44-60](file:///Users/shriyansh/Documents/project_gbot/src/server/main.py) — the `get_agent()` function

**New dependencies:** Add `langchain-groq`, `langgraph` to requirements.txt

---

### Step 7: `services/auth_service.py` — Auth Logic

**What it does:** Handles password hashing and JWT token creation/verification.

**What to put:**
- `hash_password(password)` → returns hashed string
- `verify_password(password, hash)` → returns bool
- `create_access_token(user_id, email)` → returns JWT string
- `decode_token(token)` → returns user data or raises error
- Use `passlib` for hashing, `python-jose` for JWT

**New dependencies:** Add `passlib[bcrypt]`, `python-jose[cryptography]` to requirements.txt

---

### Step 8: `server/routers/health.py` — Health Check

**What it does:** Simple endpoint to verify the server is running.

**What to put:**
- `GET /health` → returns `{"status": "ok", "service": "gbot-api"}`
- This is the simplest FastAPI router — good first one to write

---

### Step 9: `server/routers/auth.py` — Auth Endpoints

**What to put:**
- `POST /api/v1/auth/register` → create user in DB, return JWT
- `POST /api/v1/auth/login` → verify credentials, return JWT
- Use Pydantic models for request/response validation
- Call `auth_service` functions

---

### Step 10: `main.py` — Wire Everything Together

**What it does:** The FastAPI app factory that ties all routers together.

**What to put:**
- Create `FastAPI()` app with title, version
- Add CORS middleware (allow all origins for dev)
- Include routers: `health`, `auth`, `chat`, `sessions`
- Add lifespan event to initialize agent on startup

**Reference:** [old main.py](file:///Users/shriyansh/Documents/project_gbot/src/server/main.py) — similar but with routers instead of inline endpoints

---

### Step 11: `server/routers/chat.py` — The Main Chat Endpoint

**What to put:**
- `POST /api/v1/chat` — accepts message, session_id, model choice
- Requires JWT auth (middleware checks token)
- Calls the agent, saves message to DB, returns response
- This is the HEART of the app

---

## Key Differences from Old Project

| Old Project | New Project (yours) |
|-------------|---------------------|
| All endpoints in `main.py` (200 lines) | Split into routers (`health.py`, `auth.py`, `chat.py`) |
| No auth | JWT auth on every request |
| No DB saves | Every message saved to PostgreSQL |
| `from src.gcp.vm import ...` | `from app.gcp.vm import ...` |
| `config/settings.py` at root | `app/lib/config.py` inside app |
| Tools in `lib/tools.py` | Tools in `mcp/tools.py` |

---

## Updated requirements.txt

When you start each step, add the needed dependency. Full list:
```
fastapi
uvicorn
sqlalchemy
alembic
asyncpg
psycopg2-binary
python-dotenv
pydantic-settings
google-cloud-compute
langchain-core
langchain-groq
langgraph
passlib[bcrypt]
python-jose[cryptography]
mcp
```

---

## Your Next Action

1. **Create all the empty folders + `__init__.py`** (Step 1)
2. **Start with `lib/config.py`** (Step 2)
3. Go step by step. After each file, tell me "check" and I'll review.

> [!TIP]
> Don't try to build all 9 GCP services before testing the first one. 
> Get VM working end-to-end first (GCP call → tool → agent → API → response), 
> then adding the other 8 services is just copy-paste-modify.
