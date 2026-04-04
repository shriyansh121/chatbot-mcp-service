from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any, List, AsyncGenerator
import os
import json
from app.gcp import vm, vpc, storage, gke, functions, billing, cloudsql, loadbalancer, dns


# ── Guardrail: Domain scope definition ──────────────────────────
ALLOWED_DOMAINS = """
You are NexusAI, a specialized cloud infrastructure and computer science assistant. 
You ONLY answer questions within these domains:

ALLOWED TOPICS:
- Google Cloud Platform (GCP): VMs, VPCs, Storage, GKE, Cloud Functions, Billing, Cloud SQL, Load Balancers, DNS, IAM, Pub/Sub, BigQuery, Cloud Run, App Engine, etc.
- Cloud Computing: AWS, Azure, general cloud architecture, DevOps, CI/CD, Docker, Kubernetes, Terraform, Infrastructure as Code
- Computer Science: programming, algorithms, data structures, databases, networking, operating systems, system design, software engineering, web development, APIs, security best practices
- NexusAI itself: questions about your own capabilities, how to use this assistant, greetings, and farewells

CONCISENESS RULES:
- For general questions (non-GCP tool calls): Limit your response to 5-6 lines maximum. 
- Be incredibly precise and high-density. Avoid fluff.
- If a GCP tool is called: Provide a clear, structured summary but keep text brief. Use tables for resources.
"""

REFUSAL_MESSAGE = (
    "I'm NexusAI — a cloud infrastructure and computer science assistant. "
    "I can only help with topics related to **Google Cloud Platform**, **cloud computing**, "
    "**programming**, **DevOps**, and **computer science**.\n\n"
    "This question falls outside my area of expertise. "
    "Please ask me something about your GCP infrastructure or coding! 🚀"
)


class AgentState(TypedDict):
    user_message: str
    route_decision: str
    simple_response: str
    gcp_response: str
    final_response: str
    session_id: str
    user_id: str
    history: List[Dict[str, str]]


def _build_langchain_history(history: List[Dict[str, str]]):
    messages = []
    for entry in history:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


class ChatAgent:
    def __init__(self):
        # Initialize models
        # Note: We use streaming=True for models we want to stream
        self.router_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.simple_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.7,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            streaming=True
        )
        
        self.gcp_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            streaming=True
        )
        
        self.title_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.3,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("route_query", self._route_query)
        workflow.add_node("simple_response", self._simple_response)
        workflow.add_node("gcp_response", self._gcp_response)
        workflow.add_node("blocked_response", self._blocked_response)
        workflow.add_node("final_response", self._final_response)
        
        workflow.set_entry_point("route_query")
        workflow.add_conditional_edges(
            "route_query",
            self._decide_route,
            {"simple": "simple_response", "gcp": "gcp_response", "blocked": "blocked_response"}
        )
        workflow.add_edge("simple_response", "final_response")
        workflow.add_edge("gcp_response", "final_response")
        workflow.add_edge("blocked_response", "final_response")
        workflow.add_edge("final_response", END)
        
        return workflow.compile()
    
    async def _route_query(self, state: AgentState) -> AgentState:
        router_prompt = f"""
{ALLOWED_DOMAINS}
Classify the user's query into: "gcp", "simple", or "blocked".
User query: {state['user_message']}
Respond with ONLY one word.
"""
        response = await self.router_model.ainvoke([HumanMessage(content=router_prompt)])
        state["route_decision"] = response.content.strip().lower().strip('"').strip("'")
        if state["route_decision"] not in ("simple", "gcp", "blocked"):
            state["route_decision"] = "blocked"
        return state
    
    def _decide_route(self, state: AgentState) -> str:
        return state["route_decision"]
    
    async def _simple_response(self, state: AgentState) -> AgentState:
        system_prompt = f"""
{ALLOWED_DOMAINS}
Respond precisely and briefly (max 5-6 lines). 
Use markdown headers (###) for structure only if necessary.
"""
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(_build_langchain_history(state.get("history", [])))
        messages.append(HumanMessage(content=state["user_message"]))
        
        # When using streaming, we still need to wait for the final content for the state
        response = await self.simple_model.ainvoke(messages)
        state["simple_response"] = response.content
        return state
    
    async def _gcp_response(self, state: AgentState) -> AgentState:
        system_prompt = f"""
{ALLOWED_DOMAINS}
You have tool access. Provide a short textual summary and use tables for data.
Keep your total response concise.
"""
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(_build_langchain_history(state.get("history", [])))
        messages.append(HumanMessage(content=state["user_message"]))
        
        response = await self.gcp_model.ainvoke(messages)
        state["gcp_response"] = response.content
        return state
    
    async def _blocked_response(self, state: AgentState) -> AgentState:
        state["simple_response"] = REFUSAL_MESSAGE
        state["route_decision"] = "simple"
        return state
    
    async def _final_response(self, state: AgentState) -> AgentState:
        state["final_response"] = state["simple_response"] if state["route_decision"] == "simple" else state["gcp_response"]
        return state

    async def generate_title(self, user_message: str) -> str:
        title_prompt = f"Summarize in max 6 words: {user_message}. Return ONLY text."
        response = await self.title_model.ainvoke([HumanMessage(content=title_prompt)])
        title = response.content.strip().strip('"').strip("'").strip(".")
        return title[:57] + "..." if len(title) > 60 else title or "New Chat"

    async def stream_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Streams tokens from the agent using astream_events."""
        initial_state = {
            "user_message": user_message,
            "route_decision": "",
            "simple_response": "",
            "gcp_response": "",
            "final_response": "",
            "session_id": session_id,
            "user_id": user_id,
            "history": history or [],
        }

        # Use astream_events to catch token streams
        async for event in self.graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            
            # Send route info if available
            if kind == "on_chain_end" and event["name"] == "route_query":
                route = event["data"]["output"]["route_decision"]
                yield f"data: {json.dumps({'type': 'route', 'content': route})}\n\n"

            # Stream tokens from chat models
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            
            # Final state for metadata
            if kind == "on_chain_end" and event["name"] == "LangGraph":
                 yield f"data: {json.dumps({'type': 'done'})}\n\n"