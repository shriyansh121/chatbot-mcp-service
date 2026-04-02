# 🚀 GBot SaaS — Getting Started Guide (Solo Developer)

## What You Already Have

| Item | Location | Status |
|------|----------|--------|
| Old working prototype | `/Users/shriyansh/Documents/project_gbot` | AI-generated, 9 GCP modules, FastAPI + Streamlit, MCP server |
| Improvement plan | `gbot_saas_improvement_plan.md` | 950-line detailed SaaS roadmap |
| New repo | `chatbot-mcp-service` | Empty (git initialized) |
| Excalidraw workflow | `workflow.excalidraw` | Empty/starter file |

---

## Q1: Do I Need Branches or Just Push to Main?

**Solo dev → Keep it simple:**

```
main           ← always working/deployable code
feature/*      ← your active work (optional but recommended)
```

### My recommendation: **Work directly on `main` for now**

**Why:**
- You're alone, no merge conflicts possible
- Adding branching overhead when you're learning the codebase slows you down
- Start using `feature/` branches later when you have a working MVP and want to experiment without breaking things

**One rule:** Commit often with meaningful messages. Think of commits as save points.

```bash
git add .
git commit -m "feat: add base project structure with FastAPI skeleton"
```

---

## Q2: Where Do I Start?

### The Engineering Process (in order):

```
1. System Design (High Level)     ← You are HERE
2. Requirements Document
3. Project Structure
4. Build Phase 1
5. Test → Iterate
```

---

## Step 1: System Design (Do This NOW)

Open your `workflow.excalidraw` and draw these 3 things:

### Box 1 — Core Components
```
┌──────────────────────────────────────────────┐
│                  GBot SaaS                    │
│                                               │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐ │
│  │ React   │───▶│ FastAPI  │───▶│ LangGraph│ │
│  │ Frontend│◀───│ Backend  │◀───│ Agent    │ │
│  └─────────┘    └────┬─────┘    └────┬─────┘ │
│                      │               │        │
│                 ┌────▼─────┐    ┌────▼─────┐ │
│                 │PostgreSQL│    │ GCP APIs  │ │
│                 │ + Redis  │    │ (9+ svcs) │ │
│                 └──────────┘    └──────────┘ │
└──────────────────────────────────────────────┘
```

### Box 2 — Request Flow
```
User types message
  → Frontend sends to /api/v1/chat
    → Router classifies intent (GCP? General? Off-topic?)
      → Agent picks tools & calls GCP APIs
        → Formatter makes it pretty
          → Stream response back to user
```

### Box 3 — What's Different from Old Project
| Old (project_gbot) | New (chatbot-mcp-service) |
|---------------------|---------------------------|
| Streamlit UI | React frontend |
| No auth | User auth + sessions |
| Single model (Groq) | Multi-model support |
| No persistence | PostgreSQL for chat history |
| No caching | Redis cache |
| Raw API responses | Formatted rich responses |
| Monolithic agent | Router + specialized agents |

---

## Step 2: Create Your Requirements (Next)

Before writing ANY code, answer these questions (I'll help you):

1. **MVP scope** — What is the MINIMUM version you want working first?
2. **Which GCP services** — Start with all 9 or just 2-3?  
3. **Auth** — Do you need login/signup in v1 or skip it?
4. **Frontend** — React from day 1 or start with Streamlit again and migrate later?
5. **Database** — PostgreSQL from day 1 or skip for now?

> [!TIP]
> **My recommendation for MVP:** Start with FastAPI backend + 3 GCP services (VMs, Storage, Billing) + Streamlit UI + no auth + no DB. Get the core agent working clean FIRST, then layer everything else on top.

---

## Step 3: Set Up Project Structure (After Requirements)

Once we agree on scope, we'll create the folder structure in the new repo and start building.

---

## Summary — Your Action Items Right Now

1. ✅ **Git strategy**: Work on `main` for now, branch later
2. 📝 **Draw system design** in Excalidraw (the 3 boxes above)
3. 💬 **Answer the 5 MVP questions** above and tell me
4. 🚀 Then we start coding together

