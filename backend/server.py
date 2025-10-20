from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import json
import uuid
from datetime import datetime, timezone
import json

# Import configuration
from config import (
    MONGO_URL, DB_NAME, CORS_ORIGINS, 
    HAS_LLM_KEYS, HAS_GOOGLE_CONFIG, USE_DATABASE,
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)

# Conditional imports based on configuration
if HAS_LLM_KEYS:
    try:
        from openai import AzureOpenAI
        print("✅ Azure OpenAI integration loaded")
    except ImportError:
        print("⚠️ Azure OpenAI package not available, using mock responses")
        HAS_LLM_KEYS = False

if HAS_GOOGLE_CONFIG:
    try:
        from google_auth import (
            GoogleOAuth, UserProfile, AuthToken, 
            get_current_user, session_manager, 
            is_authenticated_request, get_user_from_request, GoogleAPIClient
        )
        print("✅ Google OAuth authentication loaded")
    except ImportError as e:
        print(f"⚠️ Google OAuth authentication not available: {e}")
        HAS_GOOGLE_CONFIG = False

# Try to import enhanced agents separately
enhanced_orchestrator = None
if HAS_GOOGLE_CONFIG and HAS_LLM_KEYS:
    try:
        from enhanced_agents import MultiAgentOrchestrator
        enhanced_orchestrator = MultiAgentOrchestrator()
        print("✅ Enhanced agents loaded")
    except ImportError as e:
        print(f"⚠️ Enhanced agents not available: {e}")
        enhanced_orchestrator = None

# Initialize Google OAuth auth if configured
google_auth = None
if HAS_GOOGLE_CONFIG:
    try:
        google_auth = GoogleOAuth()
        print("✅ Google OAuth auth initialized")
    except Exception as e:
        print(f"⚠️ Google OAuth auth initialization failed: {e}")
        google_auth = None

# MongoDB connection (optional for POC)
client = None
db = None

def init_database():
    """Initialize database connection if configured"""
    global client, db
    if USE_DATABASE and MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=3000)
            db = client[DB_NAME]
            print(f"✅ MongoDB configured for: {DB_NAME}")
        except Exception as e:
            print(f"⚠️ MongoDB connection failed: {e}")
            print("💡 Falling back to in-memory storage")
            client = None
            db = None
    else:
        print("✅ POC Mode: Using in-memory storage (no database required)")

# Initialize database
init_database()

# In-memory storage for POC mode
in_memory_messages = []
print("📝 Message storage ready (DB or in-memory for POC)")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    if client:
        client.close()

# Create the main app with lifespan
app = FastAPI(title="AI Agents POC", version="1.0.0", lifespan=lifespan)

# Create API router
api_router = APIRouter(prefix="/api")

# Mock classes for demo mode
class MockUserMessage:
    def __init__(self, text: str):
        self.text = text

class MockLlmChat:
    def __init__(self, api_key: str = None, session_id: str = None, system_message: str = None):
        self.session_id = session_id
        self.system_message = system_message
    
    def with_model(self, provider: str, model: str):
        return self
    
    async def send_message(self, message):
        """Mock LLM response based on input"""
        text = message.text.lower()
        
        # Route based on keywords
        if any(word in text for word in ['email', 'send', 'mail']):
            if 'extract' in text and 'json' in text:
                return '{"to": "user@example.com", "subject": "Hello", "body": "This is a test email."}'
            return "I'll help you send an email. Please provide the recipient, subject, and message content."
        elif any(word in text for word in ['calendar', 'meeting', 'schedule']):
            if 'extract' in text and 'json' in text:
                return '{"title": "Team Meeting", "start_date": "2024-01-16T14:00:00Z", "end_date": "2024-01-16T15:00:00Z", "description": "Weekly team sync"}'
            return "I'll help you manage your calendar. What would you like to schedule?"
        elif any(word in text for word in ['note', 'remember', 'save']):
            if 'extract' in text and 'json' in text:
                return '{"title": "Important Note", "content": "This is an important reminder.", "category": "Work"}'
            return "I'll help you take notes. What would you like to remember?"
        elif any(word in text for word in ['summarize', 'analyze', 'document']):
            return "This document contains important information about the project. Key points include project objectives, timeline, and deliverables. Action items: review requirements, schedule next meeting, and prepare status report."
        elif 'route' in text or 'agent' in text:
            if 'email' in text:
                return '{"agent": "email_agent", "action": "send_email", "parameters": {}}'
            elif 'calendar' in text or 'meeting' in text:
                return '{"agent": "calendar_agent", "action": "manage_calendar", "parameters": {}}'
            elif 'note' in text:
                return '{"agent": "notes_agent", "action": "create_note", "parameters": {}}'
            elif 'file' in text or 'document' in text:
                return '{"agent": "file_summarizer_agent", "action": "summarize", "parameters": {}}'
        
        return "Hello! I'm your AI assistant running in demo mode. I can help you with emails, calendar, notes, and file analysis. Try asking me to send an email or schedule a meeting!"

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
    
    def with_model(self, provider: str, model: str):
        # For Azure, model is deployment name
        return self
    
    async def send_message(self, message):
        self.messages.append({"role": "user", "content": message.text})
        response = await self.client.chat.completions.create(
            model=self.deployment_name,
            messages=self.messages
        )
        content = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": content})
        return content

# Initialize LLM Chat (with fallback to mock)
if HAS_LLM_KEYS and 'AzureOpenAI' in globals():
    try:
        llm_chat = AzureLlmChat(
            api_key=AZURE_OPENAI_API_KEY,
            endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            session_id="ai-agents-orchestrator",
            system_message="You are an AI Agent Orchestrator. Analyze user requests and determine which specialized agent should handle the task: email_agent, calendar_agent, file_summarizer_agent, or notes_agent. Respond with JSON format: {'agent': 'agent_name', 'action': 'action_description', 'parameters': {...}}"
        )
        UserMessage = MockUserMessage  # Use MockUserMessage as it's compatible
        print("✅ Azure OpenAI Chat initialized")
    except Exception as e:
        print(f"⚠️ Azure OpenAI initialization failed, using mock: {e}")
        llm_chat = MockLlmChat()
        UserMessage = MockUserMessage
else:
    print("ℹ️ Using mock LLM for demo mode")
    llm_chat = MockLlmChat()
    UserMessage = MockUserMessage

# Pydantic Models
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    sender: str  # 'user' or 'agent'
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_type: Optional[str] = None
    session_id: str

class ChatMessageCreate(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    agent_used: str
    timestamp: datetime
    session_id: str

class EmailAction(BaseModel):
    to: str
    subject: str
    body: str
    action: str = "send_email"

class CalendarAction(BaseModel):
    title: str
    start_date: str
    end_date: str
    description: Optional[str] = None
    action: str

class NotesAction(BaseModel):
    content: str
    title: Optional[str] = None
    category: Optional[str] = "General"
    action: str

# Helper functions for POC storage
async def save_message(message_doc: ChatMessage):
    """Save message to database or in-memory storage"""
    if db:
        try:
            await db.chat_messages.insert_one(message_doc.dict())
        except Exception as e:
            print(f"DB save failed, using memory: {e}")
            in_memory_messages.append(message_doc.dict())
    else:
        # POC mode: store in memory
        in_memory_messages.append(message_doc.dict())
        # Keep only last 100 messages to prevent memory issues
        if len(in_memory_messages) > 100:
            in_memory_messages.pop(0)

async def get_chat_history_by_session(session_id: str):
    """Get chat history from database or in-memory storage"""
    if db:
        try:
            messages = await db.chat_messages.find(
                {"session_id": session_id}
            ).sort("timestamp", 1).to_list(100)
            return [ChatMessage(**msg) for msg in messages]
        except Exception as e:
            print(f"DB read failed, using memory: {e}")
            # Fallback to memory
    
    # POC mode: filter in-memory messages
    session_messages = [
        ChatMessage(**msg) for msg in in_memory_messages 
        if msg.get("session_id") == session_id
    ]
    return sorted(session_messages, key=lambda x: x.timestamp)

# Mock Microsoft Graph API responses
class MockGraphAPI:
    @staticmethod
    async def send_email(to: str, subject: str, body: str):
        """Mock email sending"""
        await asyncio.sleep(0.5)  # Simulate API delay
        return {
            "id": f"mock-email-{uuid.uuid4()}",
            "status": "sent",
            "to": to,
            "subject": subject,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    async def get_calendar_events():
        """Mock calendar events"""
        await asyncio.sleep(0.3)
        return [
            {
                "id": "1",
                "title": "Team Standup",
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T09:30:00Z",
                "description": "Daily team sync"
            },
            {
                "id": "2", 
                "title": "Client Demo",
                "start": "2024-01-15T14:00:00Z",
                "end": "2024-01-15T15:00:00Z",
                "description": "Product demonstration for key client"
            }
        ]
    
    @staticmethod
    async def create_calendar_event(title: str, start_date: str, end_date: str, description: str = ""):
        """Mock calendar event creation"""
        await asyncio.sleep(0.4)
        return {
            "id": f"mock-event-{uuid.uuid4()}",
            "title": title,
            "start": start_date,
            "end": end_date,
            "description": description,
            "status": "created"
        }
    
    @staticmethod
    async def save_note(title: str, content: str, category: str = "General"):
        """Mock OneNote saving"""
        await asyncio.sleep(0.3)
        return {
            "id": f"mock-note-{uuid.uuid4()}",
            "title": title,
            "content": content,
            "category": category,
            "created": datetime.now(timezone.utc).isoformat()
        }

# Specialized Agents
class EmailAgent:
    def __init__(self):
        if HAS_LLM_KEYS and 'AzureOpenAI' in globals():
            try:
                self.llm = AzureLlmChat(
                    api_key=AZURE_OPENAI_API_KEY,
                    endpoint=AZURE_OPENAI_ENDPOINT,
                    api_version=AZURE_OPENAI_API_VERSION,
                    deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                    session_id="email-agent",
                    system_message="You are an Email Agent. Help users compose and send emails. Extract recipient, subject, and body from user requests."
                )
            except:
                self.llm = MockLlmChat(session_id="email-agent")
        else:
            self.llm = MockLlmChat(session_id="email-agent")
    
    async def process_request(self, user_message: str, parameters: Dict[str, Any]):
        # Use AI to extract email details if not provided
        if not all(k in parameters for k in ['to', 'subject', 'body']):
            extraction_prompt = f"Extract email details from: '{user_message}'. Return JSON with 'to', 'subject', 'body' fields."
            user_msg = UserMessage(text=extraction_prompt)
            response = await self.llm.send_message(user_msg)
            
            try:
                email_details = json.loads(response)
                parameters.update(email_details)
            except:
                return "Sorry, I couldn't extract the email details. Please provide recipient, subject, and message content."
        
        # Send email using mock API
        result = await MockGraphAPI.send_email(
            to=parameters['to'],
            subject=parameters['subject'], 
            body=parameters['body']
        )
        
        return f"✅ Email sent successfully to {result['to']} with subject '{result['subject']}'"

class CalendarAgent:
    def __init__(self):
        if HAS_LLM_KEYS and 'AzureOpenAI' in globals():
            try:
                self.llm = AzureLlmChat(
                    api_key=AZURE_OPENAI_API_KEY,
                    endpoint=AZURE_OPENAI_ENDPOINT,
                    api_version=AZURE_OPENAI_API_VERSION,
                    deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                    session_id="calendar-agent",
                    system_message="You are a Calendar Agent. Help users manage their calendar - view, create, or modify events."
                )
            except:
                self.llm = MockLlmChat(session_id="calendar-agent")
        else:
            self.llm = MockLlmChat(session_id="calendar-agent")
    
    async def process_request(self, user_message: str, parameters: Dict[str, Any]):
        action = parameters.get('action', 'view')
        
        if action == 'view' or 'schedule' in user_message.lower() or 'calendar' in user_message.lower():
            events = await MockGraphAPI.get_calendar_events()
            events_text = "📅 Your upcoming events:\n\n"
            for event in events:
                events_text += f"• {event['title']}\n  Time: {event['start']} to {event['end']}\n  {event['description']}\n\n"
            return events_text
            
        elif action == 'create' or 'add' in user_message.lower() or 'meeting' in user_message.lower():
            # Extract event details using AI
            extraction_prompt = f"Extract meeting details from: '{user_message}'. Return JSON with 'title', 'start_date', 'end_date', 'description'."
            user_msg = UserMessage(text=extraction_prompt)
            response = await self.llm.send_message(user_msg)
            
            try:
                event_details = json.loads(response)
                result = await MockGraphAPI.create_calendar_event(
                    title=event_details.get('title', 'New Meeting'),
                    start_date=event_details.get('start_date', '2024-01-16T10:00:00Z'),
                    end_date=event_details.get('end_date', '2024-01-16T11:00:00Z'),
                    description=event_details.get('description', '')
                )
                return f"📅 Event '{result['title']}' created successfully for {result['start']}"
            except:
                return "Sorry, I couldn't extract the meeting details. Please provide title, date, and time."

class FileSummarizerAgent:
    def __init__(self):
        if HAS_LLM_KEYS and 'AzureOpenAI' in globals():
            try:
                self.llm = AzureLlmChat(
                    api_key=AZURE_OPENAI_API_KEY,
                    endpoint=AZURE_OPENAI_ENDPOINT,
                    api_version=AZURE_OPENAI_API_VERSION,
                    deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                    session_id="file-summarizer-agent",
                    system_message="You are a File Summarizer Agent. Analyze and summarize document content. Provide key summaries, main points, and action items."
                )
            except:
                self.llm = MockLlmChat(session_id="file-summarizer-agent")
        else:
            self.llm = MockLlmChat(session_id="file-summarizer-agent")
    
    async def process_request(self, user_message: str, file_content: str = None):
        if not file_content:
            return "📄 Please upload a file to summarize. I support PDF, DOCX, TXT, and other common formats."
        
        summary_prompt = f"Analyze and summarize this document content:\n\n{file_content}\n\nProvide: 1) Key summary, 2) Main points, 3) Action items (if any)"
        user_msg = UserMessage(text=summary_prompt)
        response = await self.llm.send_message(user_msg)
        
        return f"📄 **Document Summary:**\n\n{response}"

class NotesAgent:
    def __init__(self):
        if HAS_LLM_KEYS and 'AzureOpenAI' in globals():
            try:
                self.llm = AzureLlmChat(
                    api_key=AZURE_OPENAI_API_KEY,
                    endpoint=AZURE_OPENAI_ENDPOINT,
                    api_version=AZURE_OPENAI_API_VERSION,
                    deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                    session_id="notes-agent",
                    system_message="You are a Notes Agent. Help users take, organize, and retrieve notes. Extract key information and categorize appropriately."
                )
            except:
                self.llm = MockLlmChat(session_id="notes-agent")
        else:
            self.llm = MockLlmChat(session_id="notes-agent")
    
    async def process_request(self, user_message: str, parameters: Dict[str, Any]):
        action = parameters.get('action', 'create')
        
        if action == 'create' or 'note' in user_message.lower() or 'remember' in user_message.lower():
            # Extract note details using AI
            extraction_prompt = f"Extract note details from: '{user_message}'. Return JSON with 'title', 'content', 'category'."
            user_msg = UserMessage(text=extraction_prompt)
            response = await self.llm.send_message(user_msg)
            
            try:
                note_details = json.loads(response)
                result = await MockGraphAPI.save_note(
                    title=note_details.get('title', 'Quick Note'),
                    content=note_details.get('content', user_message),
                    category=note_details.get('category', 'General')
                )
                return f"📝 Note '{result['title']}' saved successfully in {result['category']} category"
            except:
                # Fallback to simple note creation
                result = await MockGraphAPI.save_note(
                    title="Quick Note",
                    content=user_message,
                    category="General"
                )
                return f"📝 Note saved: '{result['title']}'"
        
        return "📝 Note functionality ready. Tell me what you'd like to remember!"

# Legacy agents for backward compatibility
email_agent = EmailAgent()
calendar_agent = CalendarAgent()
file_summarizer_agent = FileSummarizerAgent()
notes_agent = NotesAgent()

# Agent Orchestrator
class AgentOrchestrator:
    @staticmethod
    async def route_request(user_message: str) -> Dict[str, Any]:
        """Determine which agent should handle the request"""
        
        # Simple keyword-based routing with AI fallback
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['email', 'send', 'mail', 'message']):
            return {'agent': 'email_agent', 'action': 'send_email', 'parameters': {}}
        elif any(word in message_lower for word in ['calendar', 'meeting', 'schedule', 'event', 'appointment']):
            return {'agent': 'calendar_agent', 'action': 'manage_calendar', 'parameters': {}}
        elif any(word in message_lower for word in ['note', 'remember', 'save', 'write down']):
            return {'agent': 'notes_agent', 'action': 'create_note', 'parameters': {}}
        elif any(word in message_lower for word in ['summarize', 'summary', 'analyze', 'document', 'file']):
            return {'agent': 'file_summarizer_agent', 'action': 'summarize', 'parameters': {}}
        else:
            # Use AI orchestrator for complex requests
            try:
                user_msg = UserMessage(text=f"Route this request to appropriate agent: {user_message}")
                response = await llm_chat.send_message(user_msg)
                return json.loads(response)
            except:
                return {'agent': 'general', 'action': 'help', 'parameters': {}}

# Enhanced API Routes with Authentication

# Authentication endpoints
@api_router.get("/auth/login")
async def login_redirect(redirect_uri: str = "http://localhost:5000/auth/google/callback"):
    """Initiate Google OAuth login flow"""
    if not google_auth:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth authentication not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file"
        )
    
    try:
        auth_data = google_auth.get_auth_url()
        return {
            "auth_url": auth_data["auth_url"],
            "state": auth_data["state"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GoogleAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str = "http://localhost:5000/auth/google/callback"

@api_router.post("/auth/callback")
async def auth_callback(auth_request: GoogleAuthCallbackRequest):
    """Handle OAuth callback from Google"""
    if not google_auth:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth authentication not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file"
        )
    
    try:
        token_data = await google_auth.handle_auth_callback(auth_request.code, auth_request.redirect_uri)
        
        # Create session
        session_id = session_manager.create_session(
            user_id=token_data.user_profile.id,
            token_data=token_data.dict()
        )
        
        return {
            "access_token": token_data.access_token,
            "token_type": token_data.token_type,
            "expires_in": token_data.expires_in,
            "user_profile": token_data.user_profile,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/auth/logout")
async def logout(session_id: str = None):
    """Logout user and invalidate session"""
    if session_id and 'session_manager' in globals():
        session_manager.delete_session(session_id)
    
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: UserProfile = Depends(get_current_user)):
    """Get current authenticated user information"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "picture": current_user.picture,
        "verified_email": current_user.verified_email
    }

# Main API Routes
@api_router.get("/")
async def root():
    """API root endpoint with enhanced features"""
    return {
        "message": "🚀 Multiagent Chatbot Backend Ready",
        "version": "2.0.0",
        "status": {
            "storage": "in_memory" if not db else "database",
            "ai_responses": "configured" if HAS_LLM_KEYS else "not_configured",
            "authentication": "google_oauth" if HAS_GOOGLE_CONFIG else "not_configured",
            "ready": HAS_GOOGLE_CONFIG and HAS_LLM_KEYS
        },
        "features": {
            "agents": ["email_agent", "calendar_agent", "file_summarizer_agent", "notes_agent"],
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
            message=chat_input.message,
            sender="user", 
            session_id=chat_input.session_id
        )
        
        await save_message(user_message_doc)
        
        # Process with enhanced orchestrator if available
        if enhanced_orchestrator:
            result = await enhanced_orchestrator.process_request(
                user_request=chat_input.message,
                session_id=chat_input.session_id
            )
        else:
            # Fallback to basic processing
            routing_info = await AgentOrchestrator.route_request(chat_input.message)
            agent_name = routing_info.get('agent', 'general')
            
            if agent_name == 'email_agent':
                response = await email_agent.process_request(chat_input.message, routing_info.get('parameters', {}))
            elif agent_name == 'calendar_agent':
                response = await calendar_agent.process_request(chat_input.message, routing_info.get('parameters', {}))
            elif agent_name == 'file_summarizer_agent':
                response = await file_summarizer_agent.process_request(chat_input.message)
            elif agent_name == 'notes_agent':
                response = await notes_agent.process_request(chat_input.message, routing_info.get('parameters', {}))
            else:
                response = "🤖 Hello! I'm your AI assistant running in demo mode. I can help you with emails, calendar, notes, and file analysis."
            
            result = {
                "response": response,
                "agent_used": agent_name,
                "workflow_type": "basic",
                "agents_involved": [agent_name],
                "collaboration_data": {}
            }
        
        # Save agent response with enhanced metadata
        agent_message_doc = ChatMessage(
            message=result["response"],
            sender="agent",
            session_id=chat_input.session_id,
            agent_type=result["agent_used"]
        )
        
        await save_message(agent_message_doc)
        
        return {
            "response": result["response"],
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
            message=chat_input.message,
            sender="user",
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
        
        # Process with specific agent
        if agent_name == 'email_agent':
            response = await email_agent.process_request(chat_input.message, routing_info.get('parameters', {}))
        elif agent_name == 'calendar_agent':
            response = await calendar_agent.process_request(chat_input.message, routing_info.get('parameters', {}))
        elif agent_name == 'file_summarizer_agent':
            response = await file_summarizer_agent.process_request(chat_input.message)
        elif agent_name == 'notes_agent':
            response = await notes_agent.process_request(chat_input.message, routing_info.get('parameters', {}))
        else:
            response = "🤖 Hello! I'm your AI Agents assistant. I can help you with:\n\n📧 **Email** - Send emails to anyone\n📅 **Calendar** - Manage your schedule and events\n📄 **File Summarization** - Analyze and summarize documents\n📝 **Notes** - Take and organize your notes\n\n💡 **Try saying:**\n• \"Send an email to john@company.com about the meeting\"\n• \"What's on my calendar today?\"\n• \"Take a note about project deadlines\"\n• Upload a document for analysis\n\n🚀 **New!** Sign in for enhanced multi-agent collaboration features!\n\nWhat would you like to do?"
        
        # Save agent response
        agent_message_doc = ChatMessage(
            message=response,
            sender="agent",
            session_id=chat_input.session_id,
            agent_type=agent_name
        )
        
        await save_message(agent_message_doc)
        
        return ChatResponse(
            response=response,
            agent_used=agent_name,
            timestamp=datetime.now(timezone.utc),
            session_id=chat_input.session_id
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

# Include router
app.include_router(api_router)

# OAuth callback route (must be before CORS middleware)
@app.get("/auth/google/callback")
async def google_oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback"""
    if not google_auth:
        return HTMLResponse("""
        <html>
        <body>
        <script>
        window.opener.postMessage({type: 'auth-error', error: 'Google OAuth not configured'}, '*');
        window.close();
        </script>
        </body>
        </html>
        """)
    
    if error:
        return HTMLResponse(f"""
        <html>
        <body>
        <script>
        window.opener.postMessage({{type: 'auth-error', error: '{error}'}}, '*');
        window.close();
        </script>
        </body>
        </html>
        """)
    
    if not code:
        return HTMLResponse("""
        <html>
        <body>
        <script>
        window.opener.postMessage({type: 'auth-error', error: 'No authorization code received'}, '*');
        window.close();
        </script>
        </body>
        </html>
        """)
    
    try:
        # Exchange code for tokens
        token_data = await google_auth.handle_auth_callback(code, google_auth.config.REDIRECT_URI)
        
        # Create session
        session_id = session_manager.create_session(
            user_id=token_data.user_profile.id,
            token_data=token_data.dict()
        )
        
        # Return HTML that sends the token data to the parent window
        import json
        user_profile_json = json.dumps(token_data.user_profile.dict())
        return HTMLResponse(f"""
        <html>
        <body>
        <script>
        window.opener.postMessage({{
            type: 'auth-success',
            access_token: '{token_data.access_token}',
            user_profile: {user_profile_json},
            session_id: '{session_id}'
        }}, '*');
        window.close();
        </script>
        </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
        <html>
        <body>
        <script>
        window.opener.postMessage({{type: 'auth-error', error: '{str(e)}'}}, '*');
        window.close();
        </script>
        </body>
        </html>
        """)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS.split(',') if CORS_ORIGINS else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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