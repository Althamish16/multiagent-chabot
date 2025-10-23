from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import asyncio
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import json

# Import configuration
from config import (
    MONGO_URL, DB_NAME, CORS_ORIGINS,
    HAS_LLM_KEYS, HAS_GOOGLE_CONFIG, USE_DATABASE,
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)

# Import database utilities
from database_utils import save_message, get_chat_history_by_session, set_database_connection, ChatMessage, save_note

# Required imports - no fallbacks
try:
    from openai import AzureOpenAI
    print("✅ Azure OpenAI integration loaded")
except ImportError as e:
    raise RuntimeError(f"❌ Azure OpenAI package not available: {e}")

# Import new auth system
try:
    from auth_new import (
        google_auth,
        get_current_user,
        get_google_token,
        get_optional_user,
        session_store,
        UserProfile
    )
    from auth_routes import auth_router, create_callback_html
    print("✅ Google OAuth authentication loaded")
except ImportError as e:
    raise RuntimeError(f"❌ Google OAuth authentication not available: {e}")

try:
    from enhanced_agents import DynamicMultiAgentOrchestrator
    enhanced_orchestrator = DynamicMultiAgentOrchestrator()
    print("✅ Enhanced agents loaded")
except ImportError as e:
    raise RuntimeError(f"❌ Enhanced agents not available: {e}")

# JSON file storage (no MongoDB needed for POC)
print("📝 Using JSON file storage for chat messages")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    pass

# Create the main app with lifespan
app = FastAPI(title="AI Agents POC", version="1.0.0", lifespan=lifespan)

# CORS middleware (MUST be added before routers)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS.split(',') if CORS_ORIGINS else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router
api_router = APIRouter(prefix="/api")

# Mock classes for demo mode
class MockUserMessage:
    def __init__(self, text: str):
        self.text = text

# Removed MockLlmChat - using real Azure OpenAI only

# Azure OpenAI wrapper class
class AzureLlmChat:
    def __init__(self, api_key, endpoint, api_version, deployment_name, session_id=None, system_message=None):
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self.deployment_name = deployment_name
        self.system_message = system_message
        self.session_id = session_id
        self.messages = []
        if system_message:
            self.messages.append({"role": "system", "content": system_message})

    async def load_conversation_history(self, session_id: str):
        """Load conversation history for the session"""
        try:
            # Get recent messages from the session (limit to last 20 for context window)
            messages = await get_chat_history_by_session(session_id)
            recent_messages = messages[-20:]  # Keep only recent messages

            # Convert to OpenAI message format
            conversation_messages = []
            if self.system_message:
                conversation_messages.append({"role": "system", "content": self.system_message})

            for msg in recent_messages:
                role = "user" if msg.sender == "user" else "assistant"
                conversation_messages.append({
                    "role": role,
                    "content": msg.message
                })

            self.messages = conversation_messages
            logging.info(f"Loaded {len(recent_messages)} messages for session {session_id}")
        except Exception as e:
            logging.warning(f"Failed to load conversation history: {e}")
            # Fallback to system message only
            self.messages = []
            if self.system_message:
                self.messages.append({"role": "system", "content": self.system_message})

    async def send_message(self, message):
        # Load conversation history if session_id is provided and messages not loaded yet
        if self.session_id and len(self.messages) <= 1:  # Only system message or empty
            await self.load_conversation_history(self.session_id)

        self.messages.append({"role": "user", "content": message.text})
        response = await self.client.chat.completions.create(
            model=self.deployment_name,
            messages=self.messages
        )
        content = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": content})
        return content

# Initialize UserMessage for compatibility
UserMessage = MockUserMessage

# Pydantic Models
class ChatMessageCreate(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    agent_used: str
    timestamp: datetime
    session_id: str
    html_response: Optional[str] = None

# HTML formatting and streaming utilities
def format_response_as_html(text: str, agent_type: str = "general") -> str:
    """Format LLM response as HTML with proper styling"""
    import re

    # Escape HTML characters
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Convert markdown-style formatting to HTML
    # Headers
    text = re.sub(r'^### (.*)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)

    # Code blocks
    text = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Lists
    text = re.sub(r'^\* (.*)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\. (.*)$', r'<li>\1</li>', text, flags=re.MULTILINE)

    # Wrap in paragraphs
    paragraphs = []
    for para in text.split('\n\n'):
        if para.strip():
            if para.startswith('<h') or para.startswith('<li') or para.startswith('<pre'):
                paragraphs.append(para)
            else:
                paragraphs.append(f'<p>{para}</p>')

    text = '\n'.join(paragraphs)

    # Add agent-specific styling
    agent_colors = {
        "calendar_agent": "#28a745",
        "notes_agent": "#ffc107",
        "file_summarizer_agent": "#dc3545",
        "general": "#6c757d"
    }

    color = agent_colors.get(agent_type, agent_colors["general"])

    return f'<div class="agent-response" style="border-left: 4px solid {color}; padding-left: 10px; margin: 10px 0;">{text}</div>'

async def stream_llm_response(message: str, session_id: str, agent_type: str = "general"):
    """Stream LLM response with HTML formatting via SSE"""
    try:
        # Save user message first
        user_message_doc = ChatMessage(
            id=str(uuid.uuid4()),
            message=message,
            sender="user",
            timestamp=datetime.now(timezone.utc),
            session_id=session_id
        )
        await save_message(user_message_doc)

        # Create session-aware LLM chat instance
        session_llm_chat = AzureLlmChat(
            api_key=AZURE_OPENAI_API_KEY,
            endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            session_id=session_id,
            system_message="You are a helpful AI assistant. Provide clear, well-formatted responses."
        )

        # Load conversation history
        await session_llm_chat.load_conversation_history(session_id)

        # Add current user message
        session_llm_chat.messages.append({"role": "user", "content": message})

        # Stream the response
        response = await session_llm_chat.client.chat.completions.create(
            model=session_llm_chat.deployment_name,
            messages=session_llm_chat.messages,
            stream=True
        )

        accumulated_text = ""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                accumulated_text += content

                # Format partial response as HTML
                html_content = format_response_as_html(accumulated_text, agent_type)

                # Send SSE event
                yield f"data: {json.dumps({'html': html_content, 'text': accumulated_text})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for smooth streaming

        # Add final response to conversation history
        session_llm_chat.messages.append({"role": "assistant", "content": accumulated_text})

        # Save agent response
        agent_message_doc = ChatMessage(
            id=str(uuid.uuid4()),
            message=accumulated_text,
            sender="agent",
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            agent_type=agent_type
        )
        await save_message(agent_message_doc)

        # Send completion event
        yield f"data: {json.dumps({'complete': True, 'final_text': accumulated_text})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

# Removed MockGraphAPI - using Google APIs instead

# Specialized Agents
class CalendarAgent:
    def __init__(self):
        try:
            self.llm = AzureLlmChat(
                api_key=AZURE_OPENAI_API_KEY,
                endpoint=AZURE_OPENAI_ENDPOINT,
                api_version=AZURE_OPENAI_API_VERSION,
                deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                session_id="calendar-agent",
                system_message="You are a Calendar Agent. Help users manage their calendar - view, create, or modify events."
            )
        except Exception as e:
            raise RuntimeError(f"❌ Calendar agent LLM initialization failed: {e}")

    async def process_request(self, user_message: str, parameters: Dict[str, Any], access_token: str = None):
        if not access_token:
            raise RuntimeError("❌ Access token required for calendar operations")

        action = parameters.get('action', 'view')

        if action == 'view' or 'schedule' in user_message.lower() or 'calendar' in user_message.lower():
            try:
                google_client = GoogleAPIClient(access_token)
                events = await google_client.get_calendar_events()
                events_text = "📅 Your upcoming events:\n\n"
                for event in events:
                    events_text += f"• {event['title']}\n  Time: {event['start']} to {event['end']}\n  {event.get('description', 'No description')}\n\n"
                return events_text
            except Exception as e:
                raise RuntimeError(f"❌ Failed to get calendar events: {e}")

        elif action == 'create' or 'add' in user_message.lower() or 'meeting' in user_message.lower():
            try:
                # Extract event details using AI
                extraction_prompt = f"Extract meeting details from: '{user_message}'. Return JSON with 'title', 'start_date', 'end_date', 'description'."
                user_msg = UserMessage(text=extraction_prompt)
                response = await self.llm.send_message(user_msg)

                event_details = json.loads(response)
                google_client = GoogleAPIClient(access_token)
                result = await google_client.create_calendar_event(
                    title=event_details.get('title', 'New Meeting'),
                    start=event_details.get('start_date', '2024-01-16T10:00:00Z'),
                    end=event_details.get('end_date', '2024-01-16T11:00:00Z'),
                    description=event_details.get('description', '')
                )
                return f"📅 Event '{result['title']}' created successfully for {result['start']}"
            except json.JSONDecodeError:
                return "❌ Sorry, I couldn't extract the meeting details. Please provide title, date, and time."
            except Exception as e:
                raise RuntimeError(f"❌ Failed to create calendar event: {e}")
        else:
            return "❌ Unknown calendar action"

class FileSummarizerAgent:
    def __init__(self):
        try:
            self.llm = AzureLlmChat(
                api_key=AZURE_OPENAI_API_KEY,
                endpoint=AZURE_OPENAI_ENDPOINT,
                api_version=AZURE_OPENAI_API_VERSION,
                deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                session_id="file-summarizer-agent",
                system_message="You are a File Summarizer Agent. Analyze and summarize document content. Provide key summaries, main points, and action items."
            )
        except Exception as e:
            raise RuntimeError(f"❌ File summarizer agent LLM initialization failed: {e}")
    
    async def process_request(self, user_message: str, parameters: Dict[str, Any], access_token: str = None):
        file_content = parameters.get('file_content')
        if not file_content:
            return "📄 Please upload a file to summarize. I support PDF, DOCX, TXT, and other common formats."

        summary_prompt = f"Analyze and summarize this document content:\n\n{file_content}\n\nProvide: 1) Key summary, 2) Main points, 3) Action items (if any)"
        user_msg = UserMessage(text=summary_prompt)
        response = await self.llm.send_message(user_msg)

        return f"📄 **Document Summary:**\n\n{response}"

class NotesAgent:
    def __init__(self):
        try:
            self.llm = AzureLlmChat(
                api_key=AZURE_OPENAI_API_KEY,
                endpoint=AZURE_OPENAI_ENDPOINT,
                api_version=AZURE_OPENAI_API_VERSION,
                deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                session_id="notes-agent",
                system_message="You are a Notes Agent. Help users take, organize, and retrieve notes. Extract key information and categorize appropriately."
            )
        except Exception as e:
            raise RuntimeError(f"❌ Notes agent LLM initialization failed: {e}")

    async def process_request(self, user_message: str, parameters: Dict[str, Any], access_token: str = None):
        action = parameters.get('action', 'create')

        if action == 'create' or 'note' in user_message.lower() or 'remember' in user_message.lower():
            try:
                # Extract note details using AI
                extraction_prompt = f"Extract note details from: '{user_message}'. Return JSON with 'title', 'content', 'category'."
                user_msg = UserMessage(text=extraction_prompt)
                response = await self.llm.send_message(user_msg)

                note_details = json.loads(response)

                # Save to JSON file
                note_doc = {
                    "title": note_details.get('title', 'Quick Note'),
                    "content": note_details.get('content', user_message),
                    "category": note_details.get('category', 'General'),
                    "created_at": datetime.now(timezone.utc),
                    "user_id": parameters.get('user_id', 'anonymous')
                }

                note_id = await save_note(note_doc)
                print(f"📝 Note stored in JSON: {note_id}")

                return f"📝 Note '{note_details.get('title', 'Quick Note')}' saved successfully in {note_details.get('category', 'General')} category"
            except json.JSONDecodeError:
                # Fallback to simple note creation
                note_doc = {
                    "title": "Quick Note",
                    "content": user_message,
                    "category": "General",
                    "created_at": datetime.now(timezone.utc),
                    "user_id": parameters.get('user_id', 'anonymous')
                }

                note_id = await save_note(note_doc)
                print(f"📝 Note stored in JSON: {note_id}")

                return f"📝 Note saved: 'Quick Note'"
            except Exception as e:
                raise RuntimeError(f"❌ Failed to save note: {e}")
        else:
            return "❌ Unknown notes action"
        
        return "📝 Note functionality ready. Tell me what you'd like to remember!"

# Legacy agents for backward compatibility
calendar_agent = CalendarAgent()
file_summarizer_agent = FileSummarizerAgent()
notes_agent = NotesAgent()

# Agent registry for scalable processing
agents = {
    'calendar_agent': calendar_agent,
    'file_summarizer_agent': file_summarizer_agent,
    'notes_agent': notes_agent
}

# Helper function for agent processing
async def process_agent_request(agent_name: str, user_message: str, parameters: Dict[str, Any] = None, access_token: str = None) -> str:
    """Process request with specified agent"""
    if parameters is None:
        parameters = {}

    if agent_name in agents:
        try:
            # All agents now require access_token for Google API operations
            return await agents[agent_name].process_request(user_message, parameters, access_token)
        except Exception as e:
            logging.error(f"Error processing {agent_name} request: {str(e)}")
            raise RuntimeError(f"❌ Error processing {agent_name.replace('_', ' ')} request: {str(e)}")
    elif agent_name == 'general':
        return "🤖 Hello! I'm your AI Agents assistant. I can help you with:\n\n **Calendar** - Manage your schedule and events\n📄 **File Summarization** - Analyze and summarize documents\n📝 **Notes** - Take and organize your notes\n\n💡 **Try saying:**\n• \"What's on my calendar today?\"\n• \"Take a note about project deadlines\"\n• Upload a document for analysis\n\nWhat would you like to do?"
    else:
        raise RuntimeError(f"❌ Unknown agent: {agent_name}")

# Agent Orchestrator
class AgentOrchestrator:
    @staticmethod
    async def route_request(user_message: str) -> Dict[str, Any]:
        """Determine which agent should handle the request"""
        
        message_lower = user_message.lower().strip()
        
        # Simple keyword-based routing with AI fallback
        if any(word in message_lower for word in ['calendar', 'meeting', 'schedule', 'event', 'appointment']):
            return {'agent': 'calendar_agent', 'action': 'manage_calendar', 'parameters': {}}
        elif any(word in message_lower for word in ['note', 'remember', 'save', 'write down']):
            return {'agent': 'notes_agent', 'action': 'create_note', 'parameters': {}}
        elif any(word in message_lower for word in ['summarize', 'summary', 'analyze', 'document', 'file']):
            return {'agent': 'file_summarizer_agent', 'action': 'summarize', 'parameters': {}}
        else:
            # Use AI orchestrator for complex requests with conversation context
            try:
                # Create session-aware LLM chat instance
                session_llm_chat = AzureLlmChat(
                    api_key=AZURE_OPENAI_API_KEY,
                    endpoint=AZURE_OPENAI_ENDPOINT,
                    api_version=AZURE_OPENAI_API_VERSION,
                    deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                    session_id="routing_orchestrator",  # Use a generic session for routing
                    system_message="You are an AI Agent Orchestrator. Analyze user requests and determine which specialized agent should handle the task: calendar_agent, file_summarizer_agent, or notes_agent. Respond with JSON format: {'agent': 'agent_name', 'action': 'action_description', 'parameters': {...}}"
                )
                user_msg = UserMessage(text=f"Route this request to appropriate agent: {user_message}")
                response = await session_llm_chat.send_message(user_msg)
                return json.loads(response)
            except Exception as e:
                logging.error(f"AI routing failed: {e}")
                return {'agent': 'general', 'action': 'help', 'parameters': {}}

# Enhanced API Routes with Authentication
# Note: Auth endpoints (/auth/login, /auth/callback, /auth/logout, /auth/me) 
# are now provided by auth_router (imported from auth_routes.py)

# Main API Routes
@api_router.get("/")
async def root():
    """API root endpoint with enhanced features"""
    return {
        "message": "🚀 Multiagent Chatbot Backend Ready",
        "version": "2.0.0",
        "status": {
            "storage": "json_files",
            "ai_responses": "configured" if HAS_LLM_KEYS else "not_configured",
            "authentication": "google_oauth" if HAS_GOOGLE_CONFIG else "not_configured",
            "ready": HAS_GOOGLE_CONFIG and HAS_LLM_KEYS
        },
        "features": {
            "agents": ["calendar_agent", "file_summarizer_agent", "notes_agent"],
            "collaboration": ["multi_agent_workflows"] if enhanced_orchestrator else ["basic_routing"],
            "authentication": ["google_oauth"] if google_auth else ["not_configured"],
            "file_processing": ["pdf", "docx", "txt", "md"]
        },
        "endpoints": {
            "auth": ["/auth/login", "/auth/callback", "/auth/logout", "/auth/me"],
            "chat": ["/chat", "/chat/{session_id}", "/enhanced-chat"],
            "files": ["/upload", "/upload-legacy"]
        },
        "setup_requirements": {
            "google_oauth": "Required: Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET in .env",
            "llm_api": "Required: Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT in .env for AI responses",
            "database": "Optional: Set MONGO_URL in .env for persistent storage (uses in-memory by default)"
        }
    }

# Enhanced Chat Endpoint with LangGraph Integration
@api_router.post("/enhanced-chat")
async def enhanced_chat_with_agents(
    chat_input: ChatMessageCreate,
    request: Request,
    current_user: UserProfile = Depends(get_current_user)
):
    """Enhanced chat with multi-agent collaboration via LangGraph"""
    try:
        # Save user message with user context
        user_message_doc = ChatMessage(
            id=str(uuid.uuid4()),
            message=chat_input.message,
            sender="user", 
            timestamp=datetime.now(timezone.utc),
            session_id=chat_input.session_id
        )
        
        await save_message(user_message_doc)
        
        logging.info("Processing with enhanced orchestrator")
        
        # Get Google access token for the user
        access_token = None
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                # Get Google token from session
                from auth_new import session_store, GoogleAuth
                auth = GoogleAuth()
                payload = auth.verify_jwt_token(token)
                session_id = payload.get('session_id')
                if session_id:
                    session = session_store.get(session_id)
                    if session:
                        access_token = session.get('google_access_token')
        except Exception as e:
            logging.warning(f"Could not get Google access token: {e}")
        
        # Process with enhanced orchestrator
        result = await enhanced_orchestrator.process_request(
            user_request=chat_input.message,
            session_id=chat_input.session_id,
            access_token=access_token
        )

        # Validate result structure
        if not isinstance(result, dict) or "response" not in result:
            raise ValueError("Invalid result structure from orchestrator")

        # Ensure required keys with defaults
        result.setdefault("agent_used", "unknown")
        result.setdefault("workflow_type", "single_agent")
        result.setdefault("agents_involved", [])
        result.setdefault("collaboration_data", {})
        
        # Save agent response with enhanced metadata
        agent_message_doc = ChatMessage(
            id=str(uuid.uuid4()),
            message=result["response"],
            sender="agent",
            timestamp=datetime.now(timezone.utc),
            session_id=chat_input.session_id,
            agent_type=result["agent_used"]
        )
        
        await save_message(agent_message_doc)
        
        # Format response as HTML
        html_response = format_response_as_html(result["response"], result["agent_used"])
        
        return {
            "response": result["response"],
            "html_response": html_response,
            "agent_used": result["agent_used"], 
            "workflow_type": result.get("workflow_type", "single_agent"),
            "agents_involved": result.get("agents_involved", []),
            "collaboration_data": result.get("collaboration_data", {}),
            "timestamp": datetime.now(timezone.utc),
            "session_id": chat_input.session_id,
            "user": "demo-user",
            "enhanced": bool(enhanced_orchestrator),
            "demo_mode": not HAS_LLM_KEYS
        }
        
    except Exception as e:
        logging.error(f"Enhanced chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing enhanced request: {str(e)}")

# Legacy Chat Endpoint (for backward compatibility)
@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_agents(chat_input: ChatMessageCreate, request: Request, current_user: UserProfile = Depends(get_current_user)):
    """Legacy chat endpoint with authentication"""
    try:
        # Legacy processing for all requests
        user_message_doc = ChatMessage(
            id=str(uuid.uuid4()),
            message=chat_input.message,
            sender="user",
            timestamp=datetime.now(timezone.utc),
            session_id=chat_input.session_id
        )
        
        await save_message(user_message_doc)
        
        # Add processing delay to simulate real AI thinking
        await asyncio.sleep(0.5)
        
        # Route to appropriate agent
        routing_info = await AgentOrchestrator.route_request(chat_input.message)
        agent_name = routing_info.get('agent', 'general')
        
        # Add agent-specific processing delay
        await asyncio.sleep(0.3)
        
        # Get access token for authenticated requests
        access_token = None
        if current_user:
            # Get Google token from current user's session
            try:
                from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
                from auth import get_google_token
                # The get_google_token dependency will extract it from the session
                # For now, we'll try to get it from the user's token directly
                access_token = None  # Will be None if not available
            except:
                access_token = None
        
        # Process with specific agent
        response = await process_agent_request(agent_name, chat_input.message, routing_info.get('parameters', {}), access_token or "")
        
        # Save agent response
        agent_message_doc = ChatMessage(
            id=str(uuid.uuid4()),
            message=response,
            sender="agent",
            timestamp=datetime.now(timezone.utc),
            session_id=chat_input.session_id,
            agent_type=agent_name
        )
        
        await save_message(agent_message_doc)
        
        # Format response as HTML
        html_response = format_response_as_html(response, agent_name)
        
        return ChatResponse(
            response=response,
            agent_used=agent_name,
            timestamp=datetime.now(timezone.utc),
            session_id=chat_input.session_id,
            html_response=html_response
        )
        
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@api_router.get("/chat/{session_id}")
async def get_chat_history(session_id: str, current_user: UserProfile = Depends(get_current_user)):
    try:
        messages = await get_chat_history_by_session(session_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SSE Streaming Chat Endpoint - Authentication temporarily disabled for testing
@api_router.get("/chat/stream/{session_id}")
async def stream_chat_response(
    session_id: str,
    message: str,
    agent_type: str = "general"
    # TODO: Re-enable authentication: current_user: UserProfile = Depends(get_current_user)
):
    """Stream chat response with HTML formatting via Server-Sent Events"""
    try:
        # Return streaming response
        return StreamingResponse(
            stream_llm_response(message, session_id, agent_type),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            }
        )

    except Exception as e:
        logging.error(f"Streaming chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error streaming response: {str(e)}")

# Enhanced File Upload with Authentication
@api_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    session_id: str = "default",
    current_user: UserProfile = Depends(get_current_user)
):
    """Enhanced file upload with multi-agent processing"""
    try:
        # Read file content
        content = await file.read()
        
        # Process based on file type
        if file.filename.endswith(('.txt', '.md')):
            file_content = content.decode('utf-8')
        elif file.filename.endswith('.pdf'):
            file_content = f"[PDF content simulation for: {file.filename}]\nThis is a sample PDF content for demonstration. In production, this would contain the actual extracted PDF text with smart OCR processing."
        elif file.filename.endswith(('.docx', '.doc')):
            file_content = f"[Document content simulation for: {file.filename}]\nThis is a sample document content for demonstration. In production, this would contain the actual extracted document text with advanced parsing."
        else:
            file_content = f"[File uploaded: {file.filename}]\nFile type: {file.content_type}\nSize: {len(content)} bytes"
        
        # Use enhanced file processing if available, otherwise use basic
        if enhanced_orchestrator:
            state = {
                "user_request": f"Analyze and process the uploaded file: {file.filename} with enhanced collaboration features",
                "context": {"file_name": file.filename, "file_size": len(content)},
                "workflow_type": "document_workflow",
                "results": {}
            }
            
            result = await enhanced_orchestrator.file_agent.process_request(state, file_content)
            summary = result.get("message", "File processed with enhanced features")
            processing_type = "enhanced_multi_agent"
        else:
            # Basic file processing
            summary = await file_summarizer_agent.process_request(
                f"Please summarize the uploaded file: {file.filename}",
                file_content
            )
            processing_type = "basic"
        
        return JSONResponse(content={
            "filename": file.filename,
            "size": len(content),
            "summary": summary,
            "session_id": session_id,
            "processing_type": processing_type,
            "demo_mode": not HAS_LLM_KEYS
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")

# Legacy file upload for non-authenticated users
@api_router.post("/upload-legacy")
async def legacy_upload_file(file: UploadFile = File(...), session_id: str = "default"):
    """Legacy file upload for backward compatibility"""
    try:
        content = await file.read()
        
        if file.filename.endswith(('.txt', '.md')):
            file_content = content.decode('utf-8')
        elif file.filename.endswith('.pdf'):
            file_content = f"[PDF content simulation for: {file.filename}]\nThis is a sample PDF content for demonstration."
        elif file.filename.endswith(('.docx', '.doc')):
            file_content = f"[Document content simulation for: {file.filename}]\nThis is a sample document content for demonstration."
        else:
            file_content = f"[File uploaded: {file.filename}]\nFile type: {file.content_type}\nSize: {len(content)} bytes"
        
        summary = await file_summarizer_agent.process_request(
            f"Please summarize the uploaded file: {file.filename}",
            file_content
        )
        
        return JSONResponse(content={
            "filename": file.filename,
            "size": len(content),
            "summary": summary,
            "session_id": session_id,
            "note": "Sign in for enhanced multi-agent file processing features!"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")


# ========================================
# EMAIL AGENT API ROUTES
# ========================================

# Import email agent components
try:
    from email_agent import (
        enhanced_email_agent,
        draft_storage,
        approval_workflow,
        send_worker,
        EmailDraft,
        DraftStatus,
        ApprovalDecision,
        EmailTone,
        EmailPriority
    )
    print("✅ Email agent loaded")
except ImportError as e:
    print(f"⚠️  Email agent not available: {e}")
    enhanced_email_agent = None


# Email API models
class DraftEmailRequest(BaseModel):
    user_request: str
    session_id: str
    recipient: Optional[str] = None
    subject: Optional[str] = None
    tone: Optional[str] = "professional"
    priority: Optional[str] = "medium"


class ApproveEmailRequest(BaseModel):
    draft_id: str
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, str]] = None


class SendEmailRequest(BaseModel):
    draft_id: str


@api_router.post("/email/draft")
async def draft_email(
    request: DraftEmailRequest,
    user: UserProfile = Depends(get_current_user),
    google_token: str = Depends(get_google_token)
):
    """Create an email draft using AI"""
    if not enhanced_email_agent:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        state = {
            "action": "draft",
            "user_request": request.user_request,
            "session_id": request.session_id,
            "user_id": user.id,
            "recipient": request.recipient,
            "subject": request.subject,
            "tone": request.tone,
            "priority": request.priority,
            "access_token": google_token
        }
        
        result = await enhanced_email_agent.process_request(state)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Email draft error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/email/approve")
async def approve_email(
    request: ApproveEmailRequest,
    user: UserProfile = Depends(get_current_user)
):
    """Approve an email draft for sending"""
    if not enhanced_email_agent:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        decision = ApprovalDecision(
            draft_id=request.draft_id,
            user_id=user.id,
            approved=True,
            feedback=request.feedback,
            modifications_requested=request.modifications
        )
        
        draft = await approval_workflow.process_decision(decision)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Email draft approved",
            "draft_id": draft.id,
            "draft_status": draft.status.value
        })
        
    except Exception as e:
        logging.error(f"Email approval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/email/send")
async def send_email(
    request: SendEmailRequest,
    user: UserProfile = Depends(get_current_user),
    google_token: str = Depends(get_google_token)
):
    """Send an approved email draft"""
    if not enhanced_email_agent:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        state = {
            "action": "send",
            "draft_id": request.draft_id,
            "session_id": "api_send",
            "user_id": user.id,
            "access_token": google_token
        }
        
        result = await enhanced_email_agent.process_request(state)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Email send error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/email/drafts/{session_id}")
async def list_drafts(
    session_id: str,
    status: Optional[str] = None,
    user: UserProfile = Depends(get_current_user)
):
    """List email drafts for a session"""
    if not enhanced_email_agent:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        state = {
            "action": "list",
            "session_id": session_id,
            "user_id": user.id,
            "status": status
        }
        
        result = await enhanced_email_agent.process_request(state)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"List drafts error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/email/draft/{draft_id}")
async def get_draft(
    draft_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """Get details of a specific draft"""
    if not draft_storage:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        draft = await draft_storage.get_draft(draft_id)
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        return JSONResponse(content=draft.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get draft error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/email/draft/{draft_id}")
async def delete_draft(
    draft_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """Delete an email draft"""
    if not draft_storage:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        success = await draft_storage.delete_draft(draft_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Draft deleted",
            "draft_id": draft_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Delete draft error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/email/inbox")
async def get_inbox_emails(
    max_results: int = 10,
    query: Optional[str] = None,
    user: UserProfile = Depends(get_current_user),
    google_token: str = Depends(get_google_token)
):
    """
    List emails from Gmail inbox
    
    Query params:
    - max_results: Number of emails to fetch (1-100, default 10)
    - query: Gmail search query (e.g., "is:unread", "from:someone@gmail.com")
    """
    if not enhanced_email_agent:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        # Get access token from dependency
        access_token = google_token
        if not access_token:
            raise HTTPException(status_code=401, detail="Google authentication required")
        
        # Call email agent to fetch emails
        result = await enhanced_email_agent._handle_read({
            "user_request": f"list emails {query or ''}",
            "session_id": user.email,
            "access_token": access_token,
            "max_results": min(max_results, 100),
            "query": query
        })
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return JSONResponse(content={
            "status": "success",
            "emails": result["result"].get("email_summaries", []),
            "total_count": result["result"].get("total_count", 0),
            "query": result["result"].get("query")
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"List inbox error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/email/message/{message_id}")
async def get_email_message(
    message_id: str,
    user: UserProfile = Depends(get_current_user),
    google_token: str = Depends(get_google_token)
):
    """Get full details of a specific email message"""
    if not enhanced_email_agent:
        raise HTTPException(status_code=503, detail="Email agent not available")
    
    try:
        # Get access token from dependency
        access_token = google_token
        if not access_token:
            raise HTTPException(status_code=401, detail="Google authentication required")
        
        # Call email agent to fetch single email
        result = await enhanced_email_agent._handle_read({
            "user_request": f"get email {message_id}",
            "session_id": user.email,
            "access_token": access_token,
            "message_id": message_id
        })
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return JSONResponse(content={
            "status": "success",
            "email": result["result"].get("email")
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get email error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Add middleware to set security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # For OAuth callback, use same-origin-allow-popups to allow popup communication
    if "/auth/google/callback" in str(request.url):
        response.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
    else:
        # For other routes, use same-origin-allow-popups for better security
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    
    return response

# Include routers (must be after middleware and route definitions)
app.include_router(api_router)
app.include_router(auth_router)

# Mount static files from frontend build (LAST - catches all remaining routes)
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
if os.path.exists(frontend_build_path):
    app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="frontend")
    print(f"✅ Frontend static files mounted from: {frontend_build_path}")
else:
    print(f"⚠️  Frontend build not found at: {frontend_build_path}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Server startup
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )