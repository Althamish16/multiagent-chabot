from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="AI Agents POC", version="1.0.0")

# Create API router
api_router = APIRouter(prefix="/api")

# Initialize LLM Chat
llm_chat = LlmChat(
    api_key=os.environ['EMERGENT_LLM_KEY'],
    session_id="ai-agents-orchestrator",
    system_message="You are an AI Agent Orchestrator. Analyze user requests and determine which specialized agent should handle the task: email_agent, calendar_agent, file_summarizer_agent, or notes_agent. Respond with JSON format: {'agent': 'agent_name', 'action': 'action_description', 'parameters': {...}}"
).with_model("openai", "gpt-5")

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
        self.llm = LlmChat(
            api_key=os.environ['EMERGENT_LLM_KEY'],
            session_id="email-agent",
            system_message="You are an Email Agent. Help users compose and send emails. Extract recipient, subject, and body from user requests."
        ).with_model("openai", "gpt-5")
    
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
        self.llm = LlmChat(
            api_key=os.environ['EMERGENT_LLM_KEY'],
            session_id="calendar-agent",
            system_message="You are a Calendar Agent. Help users manage their calendar - view, create, or modify events."
        ).with_model("openai", "gpt-5")
    
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
        self.llm = LlmChat(
            api_key=os.environ['EMERGENT_LLM_KEY'],
            session_id="file-summarizer",
            system_message="You are a File Summarizer Agent. Analyze and summarize document content, extract key points and action items."
        ).with_model("openai", "gpt-5")
    
    async def process_request(self, user_message: str, file_content: str = None):
        if not file_content:
            return "📄 Please upload a file to summarize. I support PDF, DOCX, TXT, and other common formats."
        
        summary_prompt = f"Analyze and summarize this document content:\n\n{file_content}\n\nProvide: 1) Key summary, 2) Main points, 3) Action items (if any)"
        user_msg = UserMessage(text=summary_prompt)
        response = await self.llm.send_message(user_msg)
        
        return f"📄 **Document Summary:**\n\n{response}"

class NotesAgent:
    def __init__(self):
        self.llm = LlmChat(
            api_key=os.environ['EMERGENT_LLM_KEY'],
            session_id="notes-agent",
            system_message="You are a Notes Agent. Help users take, organize, and retrieve notes. Extract key information and categorize appropriately."
        ).with_model("openai", "gpt-5")
    
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

# Initialize agents
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

# API Routes
@api_router.get("/")
async def root():
    return {"message": "AI Agents POC Backend Ready", "agents": ["email", "calendar", "file_summarizer", "notes"]}

@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_agents(chat_input: ChatMessageCreate):
    try:
        # Save user message
        user_message_doc = ChatMessage(
            message=chat_input.message,
            sender="user",
            session_id=chat_input.session_id
        )
        await db.chat_messages.insert_one(user_message_doc.dict())
        
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
            response = "🤖 Hello! I'm your AI Agents assistant. I can help you with:\n\n📧 **Email** - Send emails to anyone\n📅 **Calendar** - Manage your schedule and events\n📄 **File Summarization** - Analyze and summarize documents\n📝 **Notes** - Take and organize your notes\n\n💡 **Try saying:**\n• \"Send an email to john@company.com about the meeting\"\n• \"What's on my calendar today?\"\n• \"Take a note about project deadlines\"\n• Upload a document for analysis\n\nWhat would you like to do?"
        
        # Save agent response
        agent_message_doc = ChatMessage(
            message=response,
            sender="agent",
            session_id=chat_input.session_id,
            agent_type=agent_name
        )
        await db.chat_messages.insert_one(agent_message_doc.dict())
        
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
async def get_chat_history(session_id: str):
    try:
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(100)
        
        return [ChatMessage(**msg) for msg in messages]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/upload")
async def upload_file(file: UploadFile = File(...), session_id: str = "default"):
    try:
        # Read file content
        content = await file.read()
        
        # Process based on file type
        if file.filename.endswith(('.txt', '.md')):
            file_content = content.decode('utf-8')
        elif file.filename.endswith('.pdf'):
            file_content = f"[PDF content simulation for: {file.filename}]\nThis is a sample PDF content for demonstration. In production, this would contain the actual extracted PDF text."
        elif file.filename.endswith(('.docx', '.doc')):
            file_content = f"[Document content simulation for: {file.filename}]\nThis is a sample document content for demonstration. In production, this would contain the actual extracted document text."
        else:
            file_content = f"[File uploaded: {file.filename}]\nFile type: {file.content_type}\nSize: {len(content)} bytes"
        
        # Summarize using File Summarizer Agent
        summary = await file_summarizer_agent.process_request(
            f"Please summarize the uploaded file: {file.filename}",
            file_content
        )
        
        return JSONResponse(content={
            "filename": file.filename,
            "size": len(content),
            "summary": summary,
            "session_id": session_id
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()