# 🗓️ GBot SaaS — 3-Day Build Plan

> **Goal:** Full SaaS chatbot with auth, React UI, PostgreSQL, MCP tools, multi-model agent — deployed.

---

## Day 1 — Foundation (Backend + DB + Auth + First GCP Tool)

### Morning: Project Setup & Database
- [ ] Project structure (monorepo: `backend/` + `frontend/`)
- [ ] FastAPI skeleton with API versioning (`/api/v1/`)
- [ ] PostgreSQL setup (Docker) + SQLAlchemy models + Alembic migrations
- [ ] Tables: `users`, `sessions`, `messages`
- [ ] Redis setup (Docker) for caching later

### Afternoon: Auth + First MCP Tool
- [ ] Auth system (register/login with JWT tokens)
- [ ] Auth middleware on protected routes
- [ ] MCP Core Tool Server setup
- [ ] First GCP tool: **VM instances** (list, get details)
- [ ] Wire it: API endpoint → Agent → MCP → GCP API → response

### Evening: Agent Core
- [ ] LangGraph agent with Groq (single model first)
- [ ] Router/intent classifier (basic)
- [ ] Response formatter (clean output, not raw JSON)
- [ ] Test end-to-end via API: login → chat → get VM data back

**Day 1 Checkpoint:** You can hit `/api/v1/chat` with a token and ask "list my VMs" and get a clean response stored in DB.

---

## Day 2 — Frontend + More GCP Services + Features

### Morning: React Frontend
- [ ] Vite + React setup with routing
- [ ] Login/Register pages
- [ ] Chat interface (message input, response display, streaming)
- [ ] Session sidebar (conversation history)
- [ ] Model selector dropdown (UI ready, wire later)

### Afternoon: GCP Services (in this order)
- [ ] **Storage** (buckets) — simple, good second tool
- [ ] **VPC** (networks) — straightforward
- [ ] **Cloud SQL** — similar pattern to VMs
- [ ] **GKE** (clusters) — slightly more complex
- [ ] Wire all into MCP server as tools

### Evening: Polish + More Services
- [ ] **Cloud Functions** — serverless listing
- [ ] **DNS** — zone management
- [ ] **Load Balancers** — networking
- [ ] Response formatters for each service
- [ ] Chat history persistence (load old sessions in UI)

**Day 2 Checkpoint:** Full React UI working. Login, chat, see formatted GCP data, switch between sessions. 8 GCP services integrated.

---

## Day 3 — Multi-Model + Billing + Deploy

### Morning: Multi-Model Support
- [ ] Provider abstraction (base class)
- [ ] Add OpenAI / Anthropic / Google providers
- [ ] Model selector wired in UI → backend
- [ ] Model config (YAML registry with costs, limits)

### Afternoon: Billing + Guardrails
- [ ] **Billing** GCP service (the tricky one, last as requested)
- [ ] Guardrails: block destructive queries, hallucination checks
- [ ] Input validation & safety layer
- [ ] Streaming responses (SSE)

### Evening: Docker + Deploy
- [ ] Docker Compose (API + Frontend + Postgres + Redis)
- [ ] Test full stack in containers
- [ ] Deploy to Cloud Run / Railway / Render
- [ ] Final smoke test on live URL

**Day 3 Checkpoint:** Deployed SaaS. Auth, React UI, 9 GCP services via MCP, multi-model, streaming, guardrails. Live URL.

---

## GCP Service Order (easiest → hardest)

| Order | Service | Why This Order |
|-------|---------|----------------|
| 1 | VM Instances | Most intuitive, great first tool |
| 2 | Storage (Buckets) | Simple list/detail pattern |
| 3 | VPC Networks | Same pattern, networking basics |
| 4 | Cloud SQL | Slightly more fields |
| 5 | GKE Clusters | More complex objects |
| 6 | Cloud Functions | Serverless, different shape |
| 7 | DNS Zones | Straightforward |
| 8 | Load Balancers | More nested data |
| 9 | Billing | Tricky API, different auth, last |

---

## Project Structure

```
chatbot-mcp-service/
├── backend/
│   ├── src/
│   │   ├── core/               # Business logic
│   │   │   ├── agents/         # LangGraph agent, orchestration
│   │   │   ├── providers/      # LLM providers (Groq, OpenAI, etc.)
│   │   │   └── tools/          # Tool registry
│   │   ├── mcp/                # MCP Core Tool Server
│   │   │   ├── server.py       # MCP server setup
│   │   │   └── gcp_tools/      # GCP tools exposed via MCP
│   │   │       ├── vm.py
│   │   │       ├── storage.py
│   │   │       ├── vpc.py
│   │   │       ├── cloudsql.py
│   │   │       ├── gke.py
│   │   │       ├── functions.py
│   │   │       ├── dns.py
│   │   │       ├── loadbalancer.py
│   │   │       └── billing.py
│   │   ├── server/             # FastAPI transport
│   │   │   ├── app.py          # FastAPI app factory
│   │   │   ├── routers/        # API route handlers
│   │   │   │   ├── auth.py
│   │   │   │   ├── chat.py
│   │   │   │   └── sessions.py
│   │   │   └── middleware/     # Auth, CORS, rate limiting
│   │   ├── db/                 # Database layer
│   │   │   ├── models.py       # SQLAlchemy models
│   │   │   ├── database.py     # Connection setup
│   │   │   └── migrations/     # Alembic
│   │   ├── services/           # Business services
│   │   │   ├── auth_service.py
│   │   │   ├── chat_service.py
│   │   │   └── session_service.py
│   │   └── lib/                # Utilities
│   │       ├── formatters/     # Response formatters
│   │       ├── guardrails/     # Safety & validation
│   │       └── cache/          # Redis caching
│   ├── config/
│   │   ├── settings.py         # Pydantic settings
│   │   └── models.yaml         # Model registry
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Login, Chat, Settings
│   │   ├── hooks/              # Custom hooks
│   │   ├── services/           # API client
│   │   └── store/              # Zustand state
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── Documentation/
│   └── gbot_saas_improvement_plan.md
├── workflow.excalidraw
└── README.md
```

---

## Next Step: Start Building

**Action right now:** Tell me "let's go" and we scaffold the entire project structure + Docker setup.
