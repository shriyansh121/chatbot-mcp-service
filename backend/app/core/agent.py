from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any
import os
from app.gcp import vm, vpc, storage, gke, functions, billing, cloudsql, loadbalancer, dns

class AgentState(TypedDict):
    user_message: str
    route_decision: str
    simple_response: str
    gcp_response: str
    final_response: str
    session_id: str
    user_id: str

class ChatAgent:
    def __init__(self):
        # Initialize models
        self.router_model = ChatGroq(
            model_name="llama3-70b-8192",
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.simple_model = ChatGroq(
            model_name="llama3-70b-8192",
            temperature=0.7,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.gcp_model = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("route_query", self._route_query)
        workflow.add_node("simple_response", self._simple_response)
        workflow.add_node("gcp_response", self._gcp_response)
        workflow.add_node("final_response", self._final_response)
        
        # Add edges
        workflow.set_entry_point("route_query")
        workflow.add_conditional_edges(
            "route_query",
            self._decide_route,
            {
                "simple": "simple_response",
                "gcp": "gcp_response"
            }
        )
        workflow.add_edge("simple_response", "final_response")
        workflow.add_edge("gcp_response", "final_response")
        workflow.add_edge("final_response", END)
        
        return workflow.compile()
    
    def _route_query(self, state: AgentState) -> AgentState:
        """Decide whether to use simple or GCP model"""
        router_prompt = """
        You are a routing agent. Your job is to decide whether a user query is:
        1. A simple conversational query that doesn't require GCP tools
        2. A GCP-related query that needs access to Google Cloud Platform resources
        
        User query: {user_message}
        
        Respond with ONLY "simple" or "gcp" based on your decision.
        - Use "simple" for: greetings, general questions, casual conversation, help requests
        - Use "gcp" for: any questions about Google Cloud Platform, VMs, storage, billing, etc.
        """.format(user_message=state["user_message"])
        
        response = self.router_model.invoke([HumanMessage(content=router_prompt)])
        route_decision = response.content.strip().lower()
        
        state["route_decision"] = route_decision
        return state
    
    def _decide_route(self, state: AgentState) -> str:
        return state["route_decision"]
    
    def _simple_response(self, state: AgentState) -> AgentState:
        """Generate simple conversational response"""
        simple_prompt = """
        You are a helpful AI assistant. Provide a friendly, conversational response to the user's query.
        
        User query: {user_message}
        
        Respond naturally and helpfully.
        """.format(user_message=state["user_message"])
        
        response = self.simple_model.invoke([HumanMessage(content=simple_prompt)])
        state["simple_response"] = response.content
        return state
    
    def _gcp_response(self, state: AgentState) -> AgentState:
        """Generate GCP-related response with tool calls"""
        gcp_prompt = """
        You are a Google Cloud Platform assistant. The user is asking about GCP resources.
        Analyze their query and determine what information they need, then use the appropriate GCP tools.
        
        User query: {user_message}
        
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
        """.format(user_message=state["user_message"])
        
        # For now, we'll simulate tool calls. In a real implementation,
        # you would integrate with LangChain tools
        response = self.gcp_model.invoke([HumanMessage(content=gcp_prompt)])
        state["gcp_response"] = response.content
        return state
    
    def _final_response(self, state: AgentState) -> AgentState:
        """Prepare final response"""
        if state["route_decision"] == "simple":
            state["final_response"] = state["simple_response"]
        else:
            state["final_response"] = state["gcp_response"]
        return state
    
    async def process_message(self, user_message: str, session_id: str, user_id: str) -> Dict[str, Any]:
        """Process a message through the agent"""
        initial_state = {
            "user_message": user_message,
            "route_decision": "",
            "simple_response": "",
            "gcp_response": "",
            "final_response": "",
            "session_id": session_id,
            "user_id": user_id
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "response": result["final_response"],
            "route_type": result["route_decision"],
            "session_id": session_id
        }