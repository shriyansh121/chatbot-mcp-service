from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any, List
import os
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

STRICTLY FORBIDDEN TOPICS (you must refuse these politely):
- Sexual content, sex education, adult content, NSFW material of any kind
- Medical or health advice (physical or mental)
- Legal advice, financial investment advice
- Politics, religion, philosophy, relationship advice
- Cooking, recipes, food, fitness, fashion, sports
- History, geography, literature, art, music (unless directly related to CS)  
- Homework help unrelated to CS/cloud topics
- Any topic not listed under ALLOWED TOPICS above
"""

REFUSAL_MESSAGE = (
    "I'm NexusAI — a cloud infrastructure and computer science assistant. "
    "I can only help with topics related to **Google Cloud Platform**, **cloud computing**, "
    "**programming**, **DevOps**, and **computer science** in general.\n\n"
    "This question falls outside my area of expertise. "
    "Please ask me something about your GCP infrastructure, coding, or cloud architecture, and I'll be happy to help! 🚀"
)


class AgentState(TypedDict):
    user_message: str
    route_decision: str
    simple_response: str
    gcp_response: str
    final_response: str
    session_id: str
    user_id: str
    history: List[Dict[str, str]]  # Conversation history from DB


def _build_langchain_history(history: List[Dict[str, str]]):
    """Convert DB history list into LangChain message objects."""
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
        self.router_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.simple_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.7,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.gcp_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Lightweight model for title generation
        self.title_model = ChatGroq(
            model_name="openai/gpt-oss-120b",
            temperature=0.3,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("route_query", self._route_query)
        workflow.add_node("simple_response", self._simple_response)
        workflow.add_node("gcp_response", self._gcp_response)
        workflow.add_node("blocked_response", self._blocked_response)
        workflow.add_node("final_response", self._final_response)
        
        # Add edges
        workflow.set_entry_point("route_query")
        workflow.add_conditional_edges(
            "route_query",
            self._decide_route,
            {
                "simple": "simple_response",
                "gcp": "gcp_response",
                "blocked": "blocked_response",
            }
        )
        workflow.add_edge("simple_response", "final_response")
        workflow.add_edge("gcp_response", "final_response")
        workflow.add_edge("blocked_response", "final_response")
        workflow.add_edge("final_response", END)
        
        return workflow.compile()
    
    def _route_query(self, state: AgentState) -> AgentState:
        """Decide whether to route to simple CS/cloud answer, GCP tools, or block."""
        router_prompt = """
{domain_rules}

You are a routing agent. Classify the user's query into EXACTLY ONE of these three categories:

1. "gcp" — The query asks about specific GCP resources (VMs, buckets, billing, networks, etc.) 
   that require fetching real data from Google Cloud Platform.
2. "simple" — The query is about computer science, cloud computing, programming, DevOps, 
   or general tech topics that can be answered conversationally WITHOUT GCP tool access.
   Also use "simple" for greetings like "hi", "hello", "how are you", and questions about 
   NexusAI's capabilities. Also use "simple" for follow-up questions that refer to previous 
   conversation context (e.g. "are these all?", "tell me more", "explain that").
3. "blocked" — The query is about a FORBIDDEN topic (sex, medical, legal, cooking, politics, 
   sports, relationships, or ANY topic not related to CS/cloud/GCP).

User query: {user_message}

Respond with ONLY one word: "simple", "gcp", or "blocked".
""".format(domain_rules=ALLOWED_DOMAINS, user_message=state["user_message"])
        
        response = self.router_model.invoke([HumanMessage(content=router_prompt)])
        route_decision = response.content.strip().lower().strip('"').strip("'")
        
        # Fallback: if the model returns something unexpected, default to blocked for safety
        if route_decision not in ("simple", "gcp", "blocked"):
            route_decision = "blocked"
        
        state["route_decision"] = route_decision
        return state
    
    def _decide_route(self, state: AgentState) -> str:
        return state["route_decision"]
    
    def _simple_response(self, state: AgentState) -> AgentState:
        """Generate a response for allowed CS/cloud/GCP conversational queries with history."""
        system_prompt = """
{domain_rules}

You are NexusAI, a specialized cloud infrastructure and computer science assistant.

INSTRUCTIONS:
- Answer the user's query helpfully and accurately.
- Stay strictly within your allowed domains (GCP, cloud computing, CS, programming, DevOps).
- If the user tries to sneak in an off-topic question disguised as a tech question, politely decline.
- For greetings, introduce yourself briefly as NexusAI — a GCP and CS assistant.
- Use markdown formatting for code, lists, and tables where appropriate.
- Be concise but thorough.
- You have access to the full conversation history. Use it to understand follow-up questions 
  and maintain context across messages.
""".format(domain_rules=ALLOWED_DOMAINS)
        
        # Build message chain: system + history + current user message
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(_build_langchain_history(state.get("history", [])))
        messages.append(HumanMessage(content=state["user_message"]))
        
        response = self.simple_model.invoke(messages)
        state["simple_response"] = response.content
        return state
    
    def _gcp_response(self, state: AgentState) -> AgentState:
        """Generate GCP-related response with tool calls and history."""
        system_prompt = """
{domain_rules}

You are NexusAI, a Google Cloud Platform assistant. The user is asking about GCP resources.
Analyze their query and determine what information they need, then use the appropriate GCP tools.

Available tools:
- VM operations (list, get details)
- VPC/network operations
- Storage/bucket operations
- GKE/cluster operations
- Cloud Functions
- Billing information
- Cloud SQL instances
- Load Balancers
- DNS zones and records

First, determine what they're asking for, then use the appropriate tools to get real data.
Provide a helpful response based on the actual GCP data.
Use proper markdown tables when displaying structured data (VMs, networks, buckets, etc.).
You have access to the full conversation history. Use it to understand follow-up questions.
""".format(domain_rules=ALLOWED_DOMAINS)
        
        # Build message chain: system + history + current user message
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(_build_langchain_history(state.get("history", [])))
        messages.append(HumanMessage(content=state["user_message"]))
        
        response = self.gcp_model.invoke(messages)
        state["gcp_response"] = response.content
        return state
    
    def _blocked_response(self, state: AgentState) -> AgentState:
        """Return a polite refusal for off-topic / inappropriate queries."""
        state["simple_response"] = REFUSAL_MESSAGE
        state["route_decision"] = "simple"  # Treat as simple for final_response logic
        return state
    
    def _final_response(self, state: AgentState) -> AgentState:
        """Prepare final response."""
        if state["route_decision"] == "simple":
            state["final_response"] = state["simple_response"]
        else:
            state["final_response"] = state["gcp_response"]
        return state
    
    async def generate_title(self, user_message: str) -> str:
        """Generate a short, descriptive title for a conversation based on the first message."""
        title_prompt = (
            "Generate a very short title (max 6 words) that summarizes the following user message. "
            "Return ONLY the title text, no quotes, no punctuation at the end, no explanation.\n\n"
            f"User message: {user_message}"
        )
        
        response = self.title_model.invoke([HumanMessage(content=title_prompt)])
        title = response.content.strip().strip('"').strip("'").strip(".")
        
        # Enforce max length
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title or "New Chat"
    
    async def process_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Process a message through the agent with conversation history."""
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
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "response": result["final_response"],
            "route_type": result["route_decision"],
            "session_id": session_id
        }