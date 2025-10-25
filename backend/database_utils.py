"""
Database utilities for chat history and message storage using JSON files
Organized by session with hierarchical folder structure
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
import json
import os
import uuid
from pathlib import Path

# Global data directory with sessions subfolder
DATA_DIR = Path(__file__).parent / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
GLOBAL_DIR = DATA_DIR / "global"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
GLOBAL_DIR.mkdir(exist_ok=True)

class ChatMessage(BaseModel):
    id: str
    message: str
    sender: str  # 'user' or 'agent'
    timestamp: datetime
    agent_type: Optional[str] = None
    session_id: str

def get_session_dir(session_id: str) -> Path:
    """Get the directory for a specific session"""
    session_dir = SESSIONS_DIR / f"session-{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def get_session_file(session_id: str) -> Path:
    """Get the chat JSON file path for a session"""
    session_dir = get_session_dir(session_id)
    return session_dir / "chat.json"

def get_session_email_drafts_dir(session_id: str) -> Path:
    """Get the email drafts directory for a session"""
    drafts_dir = get_session_dir(session_id) / "email_drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    return drafts_dir

def get_session_files_dir(session_id: str) -> Path:
    """Get the uploaded files directory for a session"""
    files_dir = get_session_dir(session_id) / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    return files_dir

def get_session_notes_file(session_id: str) -> Path:
    """Get the notes file for a specific session"""
    session_dir = get_session_dir(session_id)
    return session_dir / "notes.json"

async def save_message(message_doc: ChatMessage):
    """Save message to JSON file"""
    try:
        session_file = get_session_file(message_doc.session_id)
        messages = []

        # Load existing messages if file exists
        if session_file.exists():
            with open(session_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)

        # Add new message
        message_dict = message_doc.dict()
        # Convert datetime to ISO string for JSON serialization
        message_dict['timestamp'] = message_dict['timestamp'].isoformat()
        messages.append(message_dict)

        # Save back to file
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

    except Exception as e:
        logging.error(f"Failed to save message to JSON: {e}")
        raise

async def get_chat_history_by_session(session_id: str) -> List[ChatMessage]:
    """Get chat history from JSON file"""
    try:
        session_file = get_session_file(session_id)
        if not session_file.exists():
            return []

        with open(session_file, 'r', encoding='utf-8') as f:
            messages_data = json.load(f)

        # Convert back to ChatMessage objects
        messages = []
        for msg_data in messages_data:
            # Convert ISO timestamp back to datetime
            if 'timestamp' in msg_data:
                msg_data['timestamp'] = datetime.fromisoformat(msg_data['timestamp'])
            messages.append(ChatMessage(**msg_data))

        return sorted(messages, key=lambda x: x.timestamp)

    except Exception as e:
        logging.error(f"Failed to load chat history from JSON: {e}")
        return []

def get_notes_file() -> Path:
    """Get the JSON file path for global notes (backward compatibility)"""
    return GLOBAL_DIR / "notes.json"

async def save_note(note_doc: dict, session_id: str = None) -> str:
    """Save note to JSON file (session-specific or global)"""
    try:
        # Use session-specific notes if session_id provided, otherwise global
        if session_id:
            notes_file = get_session_notes_file(session_id)
        else:
            notes_file = get_notes_file()
        
        notes = []

        # Load existing notes if file exists
        if notes_file.exists():
            with open(notes_file, 'r', encoding='utf-8') as f:
                notes = json.load(f)

        # Add new note with ID
        note_id = str(uuid.uuid4())
        note_doc['id'] = note_id
        note_doc['session_id'] = session_id  # Track which session created the note
        # Convert datetime to ISO string for JSON serialization
        if 'created_at' in note_doc and isinstance(note_doc['created_at'], datetime):
            note_doc['created_at'] = note_doc['created_at'].isoformat()
        notes.append(note_doc)

        # Save back to file
        with open(notes_file, 'w', encoding='utf-8') as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)

        return note_id

    except Exception as e:
        logging.error(f"Failed to save note to JSON: {e}")
        raise

def set_database_connection(database):
    """No-op for JSON file storage - kept for compatibility"""
    pass