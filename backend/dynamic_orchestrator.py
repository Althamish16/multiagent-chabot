"""
Dynamic Multi-Agent Orchestrator using LangGraph and LLM
"""
from typing import Dict, Any, TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from email_agent import SecureEmailAgent
from calendar_agent import EnhancedCalendarAgent
from notes_agent import EnhancedNotesAgent
from file_summarizer_agent import EnhancedFileSummarizerAgent
from config import (
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)
import logging
from database_utils import get_chat_history_by_session


class OrchestratorState(TypedDict):
    """State for the dynamic orchestrator"""
    user_request: str
    session_id: str
    file_content: Optional[str]
    conversation_history: List[Dict[str, Any]]
    analysis_result: Dict[str, Any]
    agent_results: Dict[str, Any]
    final_response: str
    agents_to_invoke: List[str]
    current_agent: str
    workflow_complete: bool


class DynamicMultiAgentOrchestrator:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_deployment=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            api_version=AZURE_OPENAI_API_VERSION,
            api_key=AZURE_OPENAI_API_KEY,
            temperature=0.1
        )
        self.email_agent = SecureEmailAgent()
        self.calendar_agent = EnhancedCalendarAgent()
        self.notes_agent = EnhancedNotesAgent()
        self.file_agent = EnhancedFileSummarizerAgent()

        # Build the LangGraph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph for dynamic orchestration"""
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("route_agents", self._route_agents)
        workflow.add_node("execute_email_agent", self._execute_email_agent)
        workflow.add_node("execute_calendar_agent", self._execute_calendar_agent)
        workflow.add_node("execute_notes_agent", self._execute_notes_agent)
        workflow.add_node("execute_file_agent", self._execute_file_agent)
        workflow.add_node("compile_response", self._compile_response)

        # Define the flow
        workflow.set_entry_point("analyze_request")

        # Add edges
        workflow.add_edge("analyze_request", "route_agents")

        # Conditional routing based on agents to invoke
        workflow.add_conditional_edges(
            "route_agents",
            self._should_execute_email,
            {
                True: "execute_email_agent",
                False: "compile_response"
            }
        )

        workflow.add_conditional_edges(
            "execute_email_agent",
            self._should_execute_calendar,
            {
                True: "execute_calendar_agent",
                False: "compile_response"
            }
        )

        workflow.add_conditional_edges(
            "execute_calendar_agent",
            self._should_execute_notes,
            {
                True: "execute_notes_agent",
                False: "compile_response"
            }
        )

        workflow.add_conditional_edges(
            "execute_notes_agent",
            self._should_execute_file,
            {
                True: "execute_file_agent",
                False: "compile_response"
            }
        )

        workflow.add_edge("execute_file_agent", "compile_response")
        workflow.add_edge("compile_response", END)

        return workflow.compile()

    async def _analyze_request(self, state: OrchestratorState) -> OrchestratorState:
        """Use LLM to analyze the user request and determine required agents"""
        logging.info(f"Analyzing request: {state['user_request']}")

        # Load conversation history
        try:
            messages = await get_chat_history_by_session(state['session_id'])
            # Convert to simple format for context
            conversation_context = []
            for msg in messages[-10:]:  # Last 10 messages for context
                role = "User" if msg.sender == "user" else "Assistant"
                conversation_context.append(f"{role}: {msg.message}")
            state["conversation_history"] = conversation_context
        except Exception as e:
            logging.warning(f"Failed to load conversation history: {e}")
            state["conversation_history"] = []

        analysis_prompt = ChatPromptTemplate.from_template("""
        You are an expert AI orchestrator. Analyze this user request and determine which agents should be invoked
        and in what order. Available agents:
        - email_agent: For sending emails, creating invites, email-related tasks
        - calendar_agent: For scheduling meetings, calendar management, time coordination
        - notes_agent: For taking notes, saving information, note management
        - file_agent: For analyzing documents, summarizing files, content extraction

        Conversation History:
        {conversation_history}

        Current User Request: {user_request}

        Respond with a JSON object containing:
        {{
            "agents_to_invoke": ["agent1", "agent2", ...] (in execution order),
            "reasoning": "brief explanation of why these agents",
            "workflow_type": "descriptive name for the workflow"
        }}

        Only include agents that are clearly needed based on the request and conversation context.
        """)

        conversation_text = "\n".join(state["conversation_history"]) if state["conversation_history"] else "No previous conversation."
        chain = analysis_prompt | self.llm | JsonOutputParser()
        result = await chain.ainvoke({
            "user_request": state["user_request"],
            "conversation_history": conversation_text
        })

        state["analysis_result"] = result
        state["agents_to_invoke"] = result.get("agents_to_invoke", [])
        logging.info(f"Analysis complete: {result}")

        return state

    def _route_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Route to the first agent in the list"""
        if state["agents_to_invoke"]:
            state["current_agent"] = state["agents_to_invoke"][0]
        else:
            state["workflow_complete"] = True
        return state

    def _should_execute_email(self, state: OrchestratorState) -> bool:
        """Check if email agent should be executed"""
        return "email_agent" in state["agents_to_invoke"] and state["current_agent"] == "email_agent"

    def _should_execute_calendar(self, state: OrchestratorState) -> bool:
        """Check if calendar agent should be executed"""
        return "calendar_agent" in state["agents_to_invoke"] and state["current_agent"] == "calendar_agent"

    def _should_execute_notes(self, state: OrchestratorState) -> bool:
        """Check if notes agent should be executed"""
        return "notes_agent" in state["agents_to_invoke"] and state["current_agent"] == "notes_agent"

    def _should_execute_file(self, state: OrchestratorState) -> bool:
        """Check if file agent should be executed"""
        return "file_agent" in state["agents_to_invoke"] and state["current_agent"] == "file_agent"

    async def _execute_email_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the email agent"""
        logging.info("Executing email agent")
        agent_state = {
            "user_request": state["user_request"],
            "context": state.get("agent_results", {}),
            "conversation_history": state.get("conversation_history", []),
            "results": {}
        }

        result = await self.email_agent.process_request(agent_state)
        state["agent_results"]["email_agent"] = result

        # Move to next agent
        current_index = state["agents_to_invoke"].index("email_agent")
        if current_index + 1 < len(state["agents_to_invoke"]):
            state["current_agent"] = state["agents_to_invoke"][current_index + 1]
        else:
            state["workflow_complete"] = True

        return state

    async def _execute_calendar_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the calendar agent"""
        logging.info("Executing calendar agent")
        agent_state = {
            "user_request": state["user_request"],
            "context": state.get("agent_results", {}),
            "conversation_history": state.get("conversation_history", []),
            "results": {}
        }

        result = await self.calendar_agent.process_request(agent_state)
        state["agent_results"]["calendar_agent"] = result

        # Move to next agent
        current_index = state["agents_to_invoke"].index("calendar_agent")
        if current_index + 1 < len(state["agents_to_invoke"]):
            state["current_agent"] = state["agents_to_invoke"][current_index + 1]
        else:
            state["workflow_complete"] = True

        return state

    async def _execute_notes_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the notes agent"""
        logging.info("Executing notes agent")
        agent_state = {
            "user_request": state["user_request"],
            "context": state.get("agent_results", {}),
            "conversation_history": state.get("conversation_history", []),
            "results": {}
        }

        result = await self.notes_agent.process_request(agent_state)
        state["agent_results"]["notes_agent"] = result

        # Move to next agent
        current_index = state["agents_to_invoke"].index("notes_agent")
        if current_index + 1 < len(state["agents_to_invoke"]):
            state["current_agent"] = state["agents_to_invoke"][current_index + 1]
        else:
            state["workflow_complete"] = True

        return state

    async def _execute_file_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the file agent"""
        logging.info("Executing file agent")
        agent_state = {
            "user_request": state["user_request"],
            "context": state.get("agent_results", {}),
            "conversation_history": state.get("conversation_history", []),
            "results": {}
        }

        result = await self.file_agent.process_request(agent_state, state.get("file_content"))
        state["agent_results"]["file_agent"] = result
        state["workflow_complete"] = True

        return state

    async def _compile_response(self, state: OrchestratorState) -> OrchestratorState:
        """Compile the final response from all agent results"""
        logging.info("Compiling final response")

        agent_results = state.get("agent_results", {})
        analysis = state.get("analysis_result", {})

        # Use LLM to compile a coherent response
        compile_prompt = ChatPromptTemplate.from_template("""
        You are an expert at synthesizing responses from multiple AI agents. Given the results from various agents
        and the original user request, create a comprehensive, helpful response.

        Original request: {user_request}
        Workflow type: {workflow_type}
        Agent results: {agent_results}

        Create a response that:
        1. Summarizes what was accomplished
        2. Provides clear information about each agent's contribution
        3. Offers next steps or follow-up actions if relevant
        4. Maintains a professional, helpful tone

        Keep the response concise but comprehensive.
        """)

        chain = compile_prompt | self.llm
        response = await chain.ainvoke({
            "user_request": state["user_request"],
            "workflow_type": analysis.get("workflow_type", "general"),
            "agent_results": str(agent_results)
        })

        state["final_response"] = response.content
        return state

    async def process_request(self, user_request: str, session_id: str, file_content: str = None) -> Dict[str, Any]:
        """Process user request through the dynamic LangGraph orchestrator"""
        logging.info(f"Processing request: '{user_request}' for session {session_id}")

        try:
            # Initialize state
            initial_state: OrchestratorState = {
                "user_request": user_request,
                "session_id": session_id,
                "file_content": file_content,
                "conversation_history": [],
                "analysis_result": {},
                "agent_results": {},
                "final_response": "",
                "agents_to_invoke": [],
                "current_agent": "",
                "workflow_complete": False
            }

            # Execute the graph
            final_state = await self.graph.ainvoke(initial_state)

            # Extract results
            agent_results = final_state.get("agent_results", {})
            analysis = final_state.get("analysis_result", {})

            return {
                "response": final_state.get("final_response", "Request processed successfully"),
                "agent_used": "dynamic_langgraph_orchestrator",
                "workflow_type": analysis.get("workflow_type", "dynamic"),
                "agents_involved": list(agent_results.keys()),
                "collaboration_data": {
                    "analysis": analysis,
                    "agent_results": agent_results
                }
            }

        except Exception as e:
            logging.error(f"Dynamic orchestrator error: {str(e)}")
            return {
                "response": f"❌ Dynamic orchestration error: {str(e)}",
                "agent_used": "error_handler",
                "workflow_type": "error",
                "agents_involved": [],
                "collaboration_data": {}
            }