"""
Dynamic Multi-Agent Orchestrator using LangGraph and LLM
"""
from typing import Dict, Any, TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from datetime import datetime
import asyncio

from calendar_agent import EnhancedCalendarAgent
from notes_agent import EnhancedNotesAgent
from advanced_file_summarizer_agent import AdvancedFileSummarizerAgent
from email_agent import EnhancedEmailAgent
from general_agent import GeneralTaskAgent
from config import (
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)
import logging
from database_utils import get_chat_history_by_session


class OrchestratorState(TypedDict):
    """State for the dynamic orchestrator"""
    user_request: str
    session_id: str
    access_token: Optional[str]
    file_content: Optional[bytes]
    file_name: Optional[str]
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
        self.calendar_agent = EnhancedCalendarAgent()
        self.notes_agent = EnhancedNotesAgent()
        self.file_agent = AdvancedFileSummarizerAgent()
        self.email_agent = EnhancedEmailAgent()
        self.general_agent = GeneralTaskAgent()

        # Build the LangGraph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph for dynamic orchestration"""
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("route_agents", self._route_agents)
        workflow.add_node("execute_agent", self._execute_agent)
        workflow.add_node("check_next", self._check_next)
        workflow.add_node("compile_response", self._compile_response)

        # Define the flow
        workflow.set_entry_point("analyze_request")

        # Add edges
        workflow.add_edge("analyze_request", "route_agents")
        workflow.add_edge("route_agents", "execute_agent")
        workflow.add_edge("execute_agent", "check_next")

        workflow.add_conditional_edges(
            "check_next",
            self._should_continue,
            {
                "continue": "execute_agent",
                "done": "compile_response"
            }
        )

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

        # Load available files information
        file_context = ""
        try:
            from database_utils import get_session_files_dir
            
            # Check current session only
            files_dir = get_session_files_dir(state['session_id'])
            file_paths = []
            if files_dir.exists():
                file_paths.extend(list(files_dir.glob("*")))
            
            if file_paths:
                file_info = []
                for file_path in file_paths:
                    file_size = file_path.stat().st_size
                    file_info.append(f"- {file_path.name} ({file_size} bytes)")
                
                file_context = f"Available files in current session:\n" + "\n".join(file_info)
            else:
                file_context = "No files available in current session."
        except Exception as e:
            logging.warning(f"Failed to load file context: {e}")
            file_context = "File context unavailable."

        analysis_prompt = ChatPromptTemplate.from_template("""
        You are the Orchestrator for a multi-agent system. Decide which agents to run and in what order based on
        the current user request, recent conversation, and available files.

        Current date: {current_date}

        Available agents (use only what is needed):
        - calendar_agent — schedule/reschedule/cancel meetings, find availability, list events
        - notes_agent — create/update/search notes, action items, meeting minutes
        - file_agent — read/summarize/extract/analyze documents and files
        - email_agent — read inbox/unread/search, draft/approve/send/reply/forward emails
        - general_agent — handle general tasks, answer questions, create plans and strategies

        Guidance:
        - Select the minimal set of agents required to satisfy the request.
        - Order agents so dependencies are satisfied (e.g., file_agent → email_agent to email a summary;
            email_agent → calendar_agent to schedule from an email; file_agent → notes_agent to capture a summary).
        - If nothing actionable is required, return an empty list for agents_to_invoke.
        - Prefer single-agent workflows when possible.
        - Consider available files when deciding whether to invoke file_agent.
        - For email actions: use "approve" when user wants to approve a draft, "send" when user wants to send an already approved email.

        Output format (STRICT JSON only; no prose, no markdown, no code fences):
                {{
                    "agents_to_invoke": ["calendar_agent", "..."],
                    "reasoning": "one or two sentences explaining the choice",
                    "workflow_type": "short label like 'email_search' | 'file_summary' | 'schedule_meeting' | 'notes_capture' | 'multi_step' | 'no_action'",
                    "agent_actions": {{
                        "email_agent": {{"action": "read|draft|approve|send|list|update", "parameters": {{"query": "", "recipient": "", "subject": "", "tone": ""}}}},
                        "calendar_agent": {{"action": "create_event|list_events|find_time|reschedule|cancel", "parameters": {{"date": "", "time": "", "duration_min": 0, "attendees": []}}}},
                        "file_agent": {{"action": "summarize|extract|analyze", "parameters": {{"file_hint": "", "sections": []}}}},
                        "notes_agent": {{"action": "create|append|search|list", "parameters": {{"title": "", "content": ""}}}},
                        "general_agent": {{"action": "task_management|question_answer|planning|general_assistance", "parameters": {{"category": "", "priority": "", "timeline": ""}}}}
                    }},
                    "confidence": 0.0
                }}

        Constraints:
        - agents_to_invoke must only contain these exact values: ["calendar_agent", "notes_agent", "file_agent", "email_agent", "general_agent"].
        - Do not include agents that are not clearly relevant.
        - Do not include chain-of-thought. Return ONLY the JSON object.

        {file_context}

        Conversation (last messages):
        {conversation_history}

        Current user request:
                {user_request}
        """)

        conversation_text = "\n".join(state["conversation_history"]) if state["conversation_history"] else "No previous conversation."
        current_date = datetime.now().strftime("%Y-%m-%d")
        chain = analysis_prompt | self.llm | JsonOutputParser()
        result = await chain.ainvoke({
            "user_request": state["user_request"],
            "conversation_history": conversation_text,
            "file_context": file_context,
            "current_date": current_date
        })

        state["analysis_result"] = result
        state["agents_to_invoke"] = result.get("agents_to_invoke", [])
        
        # Fallbacks: If user mentions agent-related keywords and agent not included, add it
        # But don't override if LLM determined no action is needed
        workflow_type = result.get("workflow_type", "")
        if workflow_type == "no_action":
            logging.info("LLM determined no action needed, skipping keyword fallbacks")
        else:
            user_request_lower = state["user_request"].lower()
            keyword_map = {
                "email_agent": [
                    "email", "mail", "inbox", "message", "unread", "gmail", "latest email", "recent email",
                    "send email", "draft email", "compose"
                ],
                "calendar_agent": [
                    "calendar", "meeting", "schedule", "reschedule", "appointment", "event", "availability",
                    "time slot", "book", "invite"
                ],
                "file_agent": [
                    "file", "document", "pdf", "docx", "ppt", "slide", "slides", "summarize", "extract",
                    "analyze", "report"
                ],
                "notes_agent": [
                    "note", "notes", "notebook", "remember", "save this", "to-do", "todo", "task list",
                    "minutes"
                ],
                "general_agent": [
                    "task", "todo", "to-do", "reminder", "question", "answer", "explain", "help me",
                    "plan", "planning", "strategy", "goal", "how to", "what is", "why", "when", "where"
                ]
            }

            detected_agents = []
            for agent_name, keywords in keyword_map.items():
                if any(keyword in user_request_lower for keyword in keywords):
                    detected_agents.append(agent_name)

            for agent_name in detected_agents:
                if agent_name not in state["agents_to_invoke"]:
                    state["agents_to_invoke"].append(agent_name)
                    logging.info(f"Fallback triggered: Added {agent_name} due to keywords in request")
        
        logging.info(f"Analysis complete: {result}")
        logging.info(f"Final agents to invoke: {state['agents_to_invoke']}")

        return state

    def _route_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Route to the first agent in the list"""
        if state["agents_to_invoke"]:
            state["current_agent"] = state["agents_to_invoke"][0]
        else:
            state["workflow_complete"] = True
        return state

    async def _execute_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the current agent"""
        agent = state["current_agent"]
        if agent == "calendar_agent":
            return await self._execute_calendar_agent(state)
        elif agent == "notes_agent":
            return await self._execute_notes_agent(state)
        elif agent == "file_agent":
            return await self._execute_file_agent(state)
        elif agent == "email_agent":
            return await self._execute_email_agent(state)
        elif agent == "general_agent":
            return await self._execute_general_agent(state)
        else:
            # Unknown agent, skip
            return state

    async def _check_next(self, state: OrchestratorState) -> OrchestratorState:
        """Check if there are more agents to execute"""
        agents = state["agents_to_invoke"]
        current = state["current_agent"]
        if current in agents:
            index = agents.index(current)
            if index + 1 < len(agents):
                state["current_agent"] = agents[index + 1]
            else:
                state["workflow_complete"] = True
        else:
            state["workflow_complete"] = True
        return state

    def _should_continue(self, state: OrchestratorState) -> str:
        """Determine if to continue executing agents or done"""
        return "continue" if not state["workflow_complete"] else "done"

    async def _execute_calendar_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the calendar agent"""
        logging.info("Executing calendar agent")
        try:
            agent_state = {
                "user_request": state["user_request"],
                "access_token": state.get("access_token"),
                "context": state.get("agent_results", {}),
                "conversation_history": state.get("conversation_history", []),
                "calendar_parameters": state.get("analysis_result", {}).get("agent_actions", {}).get("calendar_agent", {}),
                "results": {}
            }

            result = await asyncio.wait_for(
                self.calendar_agent.process_request(agent_state),
                timeout=60.0
            )
            state["agent_results"]["calendar_agent"] = result
            return state
        except asyncio.TimeoutError:
            logging.error("Calendar agent timed out")
            state["agent_results"]["calendar_agent"] = {
                "status": "error",
                "message": "❌ Calendar agent timed out",
                "result": {},
                "collaboration_data": {"error": "timeout"}
            }
            return state
        except Exception as e:
            logging.error(f"Calendar agent error: {str(e)}")
            state["agent_results"]["calendar_agent"] = {
                "status": "error",
                "message": f"❌ Calendar agent failed: {str(e)}",
                "result": {},
                "collaboration_data": {"error": str(e)}
            }
            return state

    async def _execute_notes_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the notes agent"""
        logging.info("Executing notes agent")
        agent_state = {
            "user_request": state["user_request"],
            "access_token": state.get("access_token"),
            "context": state.get("agent_results", {}),
            "conversation_history": state.get("conversation_history", []),
            "results": {}
        }

        result = await self.notes_agent.process_request(agent_state)
        state["agent_results"]["notes_agent"] = result

        return state

    async def _execute_file_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the file agent"""
        logging.info("Executing file agent")
        
        file_content = state.get("file_content")
        if not file_content:
            result = {
                "status": "error",
                "message": "📄 No file content provided for analysis",
                "collaboration_data": {}
            }
        else:
            # Convert string to bytes if needed
            if isinstance(file_content, str):
                file_content_bytes = file_content.encode('utf-8')
            else:
                file_content_bytes = file_content
            
            # Extract file name from state or use default
            file_name = state.get("file_name", "uploaded_file.txt")
            
            # Determine summary mode from user request or default
            user_request = state["user_request"]
            summary_mode = "detailed"  # default
            if "brief" in user_request.lower():
                summary_mode = "brief"
            elif "executive" in user_request.lower():
                summary_mode = "executive"
            
            # Call the advanced file summarizer
            result = await self.file_agent.process_file(
                file_content=file_content_bytes,
                file_name=file_name,
                user_request=user_request,
                summary_mode=summary_mode,
                query=None,  # Could be extracted from user_request if it's a query
                conversation_history=state.get("conversation_history", [])
            )
            
            # Adapt the response format to match what the orchestrator expects
            if result["status"] == "success":
                adapted_result = {
                    "status": "success",
                    "result": {
                        "summary": result.get("summary", ""),
                        "key_insights": result.get("key_insights", []),
                        "metadata": result.get("metadata", {}),
                        "file_type": result.get("file_type", ""),
                        "query_response": result.get("query_response")
                    },
                    "message": f"📄 **Advanced Document Analysis Complete**\n\n**Summary:** {result.get('summary', '')[:200]}...\n\n**Key Insights:** {len(result.get('key_insights', []))} insights extracted",
                    "collaboration_data": {
                        "analysis": result,
                        "recommended_workflows": {},  # Could be enhanced later
                        "next_actions": result.get("key_insights", [])
                    }
                }
                result = adapted_result
            # If error, the format is already compatible
        
        state["agent_results"]["file_agent"] = result
        return state

    async def _execute_email_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the email agent"""
        logging.info("Executing email agent")
        try:
            agent_state = {
                "user_request": state["user_request"],
                "session_id": state["session_id"],
                "access_token": state.get("access_token"),
                "conversation_history": state.get("conversation_history", []),
                "context": state.get("agent_results", {}),
                "action": state.get("analysis_result", {}).get("agent_actions", {}).get("email_agent", {}).get("action"),
                "recipient": state.get("analysis_result", {}).get("agent_actions", {}).get("email_agent", {}).get("parameters", {}).get("recipient"),
                "subject": state.get("analysis_result", {}).get("agent_actions", {}).get("email_agent", {}).get("parameters", {}).get("subject"),
                "tone": state.get("analysis_result", {}).get("agent_actions", {}).get("email_agent", {}).get("parameters", {}).get("tone"),
                "query": state.get("analysis_result", {}).get("agent_actions", {}).get("email_agent", {}).get("parameters", {}).get("query"),
            }

            result = await asyncio.wait_for(
                self.email_agent.process_request(agent_state),
                timeout=60.0
            )
            state["agent_results"]["email_agent"] = result
            return state
        except asyncio.TimeoutError:
            logging.error("Email agent timed out")
            state["agent_results"]["email_agent"] = {
                "status": "error",
                "message": "❌ Email agent timed out",
                "result": {},
                "collaboration_data": {"error": "timeout"}
            }
            return state
        except Exception as e:
            logging.error(f"Email agent error: {str(e)}")
            state["agent_results"]["email_agent"] = {
                "status": "error",
                "message": f"❌ Email agent failed: {str(e)}",
                "result": {},
                "collaboration_data": {"error": str(e)}
            }
            return state

    async def _execute_general_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the general agent"""
        logging.info("Executing general agent")
        try:
            agent_state = {
                "user_request": state["user_request"],
                "access_token": state.get("access_token"),
                "context": state.get("agent_results", {}),
                "conversation_history": state.get("conversation_history", []),
                "results": {}
            }

            logging.info(f"Calling general agent with state: {agent_state.keys()}")
            
            # Add timeout wrapper
            result = await asyncio.wait_for(
                self.general_agent.process_request(agent_state),
                timeout=90.0  # 90 seconds timeout
            )
            
            logging.info(f"General agent result received: {result.get('status')}")
            
            state["agent_results"]["general_agent"] = result
            return state
        except asyncio.TimeoutError:
            logging.error("General agent execution timed out after 90 seconds")
            state["agent_results"]["general_agent"] = {
                "status": "error",
                "message": "❌ General agent timed out - please try a simpler request",
                "result": {},
                "collaboration_data": {"error": "timeout"}
            }
            return state
        except Exception as e:
            logging.error(f"General agent execution error: {str(e)}")
            # Fallback result
            state["agent_results"]["general_agent"] = {
                "status": "error",
                "message": f"❌ General agent failed: {str(e)}",
                "result": {},
                "collaboration_data": {"error": str(e)}
            }
            return state

    async def _compile_response(self, state: OrchestratorState) -> OrchestratorState:
        """Compile the final response from all agent results"""
        logging.info("Compiling final response")

        agent_results = state.get("agent_results", {})
        analysis = state.get("analysis_result", {})

        # Check if multiple agents were involved
        agents_used = list(agent_results.keys())
        
        # If multiple agents, compile all their results
        if len(agents_used) > 1:
            response_parts = []
            
            # Notes agent result
            if "notes_agent" in agent_results:
                notes_result = agent_results["notes_agent"]
                if notes_result.get("status") == "success":
                    response_parts.append(notes_result.get("message", "Notes saved successfully"))
            
            # Email agent result
            if "email_agent" in agent_results:
                email_result = agent_results["email_agent"]
                if email_result.get("status") == "success":
                    result_data = email_result.get("result", {})
                    if "draft_id" in result_data:
                        body_preview = result_data.get("body", "")[:300]
                        response_parts.append(
                            f"\n📧 **Email Draft Created**\n"
                            f"**To:** {result_data.get('to', 'N/A')}\n"
                            f"**Subject:** {result_data.get('subject', 'N/A')}\n"
                            f"**Preview:** {body_preview}..."
                        )
                    else:
                        response_parts.append(email_result.get("message", "Email processed"))
            
            # Calendar agent result
            if "calendar_agent" in agent_results:
                calendar_result = agent_results["calendar_agent"]
                if calendar_result.get("status") == "success":
                    response_parts.append(calendar_result.get("message", "Calendar updated"))
            
            # File agent result
            if "file_agent" in agent_results:
                file_result = agent_results["file_agent"]
                if file_result.get("status") == "success":
                    response_parts.append(file_result.get("message", "File processed"))
            
            # General agent result
            if "general_agent" in agent_results:
                general_result = agent_results["general_agent"]
                if general_result.get("status") == "success":
                    response_parts.append(general_result.get("message", "General assistance provided"))
            
            if response_parts:
                state["final_response"] = "\n\n".join(response_parts)
                return state

        # Special handling for single agent results
        single_agent_handlers = {
            "email_agent": self._handle_email_response,
            "general_agent": self._handle_general_response
        }
        
        if len(agents_used) == 1 and agents_used[0] in single_agent_handlers:
            return single_agent_handlers[agents_used[0]](state, agent_results)

        # Use LLM to compile a coherent response for other cases
        compile_prompt = ChatPromptTemplate.from_template("""
        You are an expert at synthesizing responses from multiple AI agents. Given the results from various agents
        and the original user request, create a comprehensive, helpful response.

        Original request: {user_request}
        Workflow type: {workflow_type}
        Agent results: {agent_results}

        Create a response that:
        1. Summarizes what was accomplished with SPECIFIC DETAILS from each agent
        2. Shows the ACTUAL CONTENT that was created (document titles, URLs, key information)
        3. If a document was created, include the document title and URL
        4. If notes were saved, show what was saved
        5. Provides clear information about each agent's contribution with REAL DATA
        6. Offers next steps or follow-up actions if relevant
        7. Maintains a professional, helpful tone

        IMPORTANT: Include actual content, not just generic descriptions like "2 agents" or "content saved".
        Show what was actually created or retrieved.

        Keep the response detailed but well-organized.
        """)

        chain = compile_prompt | self.llm
        response = await chain.ainvoke({
            "user_request": state["user_request"],
            "workflow_type": analysis.get("workflow_type", "general"),
            "agent_results": str(agent_results)
        })

        state["final_response"] = response.content
        return state

    async def process_request(self, user_request: str, session_id: str, access_token: str = None, file_content: bytes = None, file_name: str = None) -> Dict[str, Any]:
        """Process user request through the dynamic LangGraph orchestrator"""
        logging.info(f"Processing request: '{user_request}' for session {session_id}")

        try:
            # Initialize state
            initial_state: OrchestratorState = {
                "user_request": user_request,
                "session_id": session_id,
                "access_token": access_token,
                "file_content": file_content,
                "file_name": file_name,
                "conversation_history": [],
                "analysis_result": {},
                "agent_results": {},
                "final_response": "",
                "agents_to_invoke": [],
                "current_agent": "",
                "email_action": None,
                "workflow_complete": False
            }

            # Execute the graph
            final_state = await self.graph.ainvoke(initial_state)

            # Extract results
            agent_results = final_state.get("agent_results", {})
            analysis = final_state.get("analysis_result", {})
            draft_created = final_state.get("draft_created")

            result = {
                "response": final_state.get("final_response", "Request processed successfully"),
                "agent_used": "dynamic_langgraph_orchestrator",
                "workflow_type": analysis.get("workflow_type", "dynamic"),
                "agents_involved": list(agent_results.keys()),
                "collaboration_data": {
                    "analysis": analysis,
                    "agent_results": agent_results
                }
            }
            
            # Add draft info if email draft was created
            if draft_created:
                result["draft_created"] = draft_created
            
            return result

        except Exception as e:
            logging.error(f"Dynamic orchestrator error: {str(e)}")
            return {
                "response": f"❌ Dynamic orchestration error: {str(e)}",
                "agent_used": "error_handler",
                "workflow_type": "error",
                "agents_involved": [],
                "collaboration_data": {}
            }

    def _handle_email_response(self, state: OrchestratorState, agent_results: Dict[str, Any]) -> OrchestratorState:
        """Handle single email agent response"""
        email_result = agent_results["email_agent"]
        if email_result.get("status") == "success":
            result_data = email_result.get("result", {})
            
            # Check if this is an email send result (has gmail_message_id)
            if "gmail_message_id" in result_data and result_data["gmail_message_id"]:
                # Email was sent successfully - try to get draft details from agent results first
                sent_response = ["✅ **Email Sent Successfully**"]
                
                # Check if the email agent has draft info in its collaboration_data
                collaboration_data = email_result.get("collaboration_data", {})
                draft_info = collaboration_data.get("draft_info")
                
                if draft_info:
                    sent_response.extend([
                        f"**To:** {draft_info.get('to', 'N/A')}",
                        f"**Subject:** {draft_info.get('subject', 'N/A')}",
                        f"**Message ID:** {result_data.get('gmail_message_id', 'N/A')}"
                    ])
                    
                    # Add body preview if available
                    body = draft_info.get('body', '')
                    if body:
                        body_preview = body[:200]
                        sent_response.append(f"\n**Content Preview:** {body_preview}...")
                else:
                    # Fallback - basic info from result
                    sent_response.extend([
                        f"**Draft ID:** {result_data.get('draft_id', 'N/A')}",
                        f"**Message ID:** {result_data.get('gmail_message_id', 'N/A')}"
                    ])
                
                state["final_response"] = "\n".join(sent_response)
                return state
            
            # Check if this is a draft creation (only if not sent)
            elif "draft_id" in result_data:
                # Draft was created - store draft info in state for frontend
                state["draft_created"] = {
                    "draft_id": result_data.get("draft_id"),
                    "to": result_data.get("to"),
                    "subject": result_data.get("subject"),
                    "body": result_data.get("body"),
                    "status": result_data.get("status"),
                    "created_at": result_data.get("created_at")
                }
                
                # Create detailed response showing the actual draft content
                body_preview = result_data.get("body", "")[:500]
                draft_response = [
                    "📧 **Email Draft Created**",
                    f"**To:** {result_data.get('to', 'N/A')}",
                    f"**Subject:** {result_data.get('subject', 'N/A')}",
                    f"**Status:** {result_data.get('status', 'pending_approval')}",
                    "\n**Email Content:**",
                    body_preview
                ]
                
                if len(result_data.get("body", "")) > 500:
                    draft_response.append("\n... (content truncated)")
                
                draft_response.append("\n✅ The draft is awaiting your approval.")
                
                state["final_response"] = "\n".join(draft_response)
                return state
            
            # Email reading/listing
            elif "email_summaries" in result_data:
                email_summaries = result_data.get("email_summaries", [])
                total_count = result_data.get("total_count", 0)
                query = result_data.get("query", "")

                if email_summaries:
                    # Format email data into readable response
                    response_parts = [f"I found {total_count} email{'s' if total_count != 1 else ''}"]
                    if query:
                        response_parts[0] += f" matching '{query}'"
                    response_parts[0] += ":"

                    for i, email in enumerate(email_summaries[:5], 1):  # Show first 5
                        from_addr = email.get("from", "Unknown")
                        subject = email.get("subject", "(No Subject)")
                        snippet = email.get("snippet", "")[:100]
                        is_unread = " (unread)" if email.get("is_unread") else ""
                        response_parts.append(f"{i}. From: {from_addr}")
                        response_parts.append(f"   Subject: {subject}{is_unread}")
                        if snippet:
                            response_parts.append(f"   Preview: {snippet}...")
                        response_parts.append("")

                    if total_count > 5:
                        response_parts.append(f"... and {total_count - 5} more emails.")

                    state["final_response"] = "\n".join(response_parts)
                    return state
                else:
                    state["final_response"] = email_result.get("message", "No emails found.")
                    return state
            
            # Fallback to the message from the email agent
            else:
                state["final_response"] = email_result.get("message", "Email operation completed successfully.")
                return state
                
        elif email_result.get("status") == "error":
            error_msg = email_result.get("message", "Failed to process email request")
            if "Authentication required" in error_msg:
                state["final_response"] = "Please sign in with Google to access your emails."
            else:
                state["final_response"] = f"❌ {error_msg}"
            return state

    def _handle_general_response(self, state: OrchestratorState, agent_results: Dict[str, Any]) -> OrchestratorState:
        """Handle single general agent response"""
        general_result = agent_results["general_agent"]
        
        if general_result.get("status") == "success":
            state["final_response"] = general_result.get("message", "General assistance provided")
        else:
            state["final_response"] = general_result.get("message", "❌ General assistance failed")
        
        return state