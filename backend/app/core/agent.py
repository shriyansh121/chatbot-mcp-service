from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any, List, AsyncGenerator
import os
import json
from app.gcp import vm, vpc, storage, gke, functions, billing, cloudsql, loadbalancer, dns

# ── System Prompt (concise = fewer hallucinations) ──────────────
SYSTEM_PROMPT = """You are NexusAI, a GCP infrastructure & CS assistant.

RULES:
1. For GCP resource queries ("list VMs", "show buckets"), call the matching tool.
2. For CS/coding/DevOps questions, answer concisely (max 6 lines).
3. Use markdown tables for resource listings. Keep text brief.
4. Refuse off-topic queries (medical, politics, NSFW) politely.
5. NEVER invent resource names, IPs, or data. Only report what tools return.
6. If a tool returns empty, say "No resources found."

AVAILABLE TOOLS: list_vms, get_vm_details, list_networks, list_buckets, list_clusters, list_functions, list_billing_accounts, list_sql_instances, list_load_balancers, list_dns_zones"""


# ── Tool registry (maps tool name → actual Python function) ─────
TOOL_REGISTRY = {
    "list_vms": vm.list_vms,
    "get_vm_details": vm.get_vm_details,
    "list_networks": vpc.list_networks,
    "list_buckets": storage.list_buckets,
    "list_clusters": gke.list_clusters,
    "list_functions": functions.list_functions,
    "list_billing_accounts": billing.list_billing_accounts,
    "list_sql_instances": cloudsql.list_instances,
    "list_load_balancers": loadbalancer.list_load_balancers,
    "list_dns_zones": dns.list_zones,
}

# ── Simple keyword → tool mapper (no extra LLM call needed) ────
TOOL_KEYWORDS = {
    "list_vms":              ["vm", "vms", "virtual machine", "instances", "running vms", "compute"],
    "list_networks":         ["vpc", "network", "networks", "subnets"],
    "list_buckets":          ["bucket", "buckets", "storage", "gcs"],
    "list_clusters":         ["gke", "cluster", "clusters", "kubernetes"],
    "list_functions":        ["function", "functions", "cloud function", "serverless"],
    "list_billing_accounts": ["billing", "bill", "cost", "budget", "spending"],
    "list_sql_instances":    ["sql", "cloud sql", "database", "databases", "cloudsql"],
    "list_load_balancers":   ["load balancer", "lb", "balancer"],
    "list_dns_zones":        ["dns", "zone", "zones", "domain"],
}


def detect_tool(query: str) -> str | None:
    """Match user query to a tool using keyword detection. Returns tool name or None."""
    q = query.lower()
    for tool_name, keywords in TOOL_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return tool_name
    return None


class AgentState(TypedDict):
    messages: List[Any]


class ChatAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.2,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            streaming=True,
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("process", self._process)
        workflow.set_entry_point("process")
        workflow.add_edge("process", END)
        return workflow.compile()

    async def _process(self, state: AgentState) -> AgentState:
        """Single-node processor: detect tool → call it → inject data → LLM."""
        messages = state["messages"]

        # Extract the latest user message
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_msg = m.content
                break

        # Check if a GCP tool should be called
        tool_name = detect_tool(user_msg)
        if tool_name and tool_name in TOOL_REGISTRY:
            try:
                tool_fn = TOOL_REGISTRY[tool_name]
                tool_result = tool_fn()  # Call the actual GCP function
                tool_data = json.dumps(tool_result, indent=2, default=str)

                # Inject tool result as a system message so the LLM formats it
                inject_msg = SystemMessage(
                    content=f"TOOL RESULT from `{tool_name}`:\n```json\n{tool_data}\n```\n\nFormat this data nicely for the user using a markdown table. Be concise."
                )
                messages.append(inject_msg)
            except Exception as e:
                messages.append(SystemMessage(
                    content=f"TOOL ERROR: `{tool_name}` failed with: {str(e)}. Tell the user."
                ))

        res = await self.llm.ainvoke(messages)
        state["messages"].append(res)
        return state

    async def generate_title(self, msg: str) -> str:
        """Generate a short title for a chat session."""
        prompt = [HumanMessage(
            content=f"Generate a 3-5 word title for this message. Return ONLY the title, nothing else:\n\n{msg[:150]}"
        )]
        res = await self.llm.ainvoke(prompt)
        title = res.content.strip().strip('"').strip("'").strip(".")
        return title[:60] if title else "New Chat"

    async def stream_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the agent via SSE."""
        # Build message chain: system + history + current
        msgs = [SystemMessage(content=SYSTEM_PROMPT)]
        for h in (history or []):
            if h["role"] == "user":
                msgs.append(HumanMessage(content=h["content"]))
            else:
                msgs.append(AIMessage(content=h["content"]))
        msgs.append(HumanMessage(content=user_message))

        state = {"messages": msgs}

        async for event in self.graph.astream_events(state, version="v2"):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and chunk.content:
                    payload = json.dumps({"type": "token", "content": chunk.content})
                    yield f"data: {payload}\n\n"

            elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"