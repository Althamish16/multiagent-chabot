"""
Database utilities for chat history and message storage using JSON files
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
import json
import os
import uuid
from pathlib import Path

# Global data directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

class ChatMessage(BaseModel):
    id: str
    message: str
    sender: str  # 'user' or 'agent'
    timestamp: datetime
    agent_type: Optional[str] = None
    session_id: str

def get_session_file(session_id: str) -> Path:
    """Get the JSON file path for a session"""
    return DATA_DIR / f"chat_{session_id}.json"

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
    """Get the JSON file path for notes"""
    return DATA_DIR / "notes.json"

async def save_note(note_doc: dict) -> str:
    """Save note to JSON file"""
    try:
        notes_file = get_notes_file()
        notes = []

        # Load existing notes if file exists
        if notes_file.exists():
            with open(notes_file, 'r', encoding='utf-8') as f:
                notes = json.load(f)

        # Add new note with ID
        note_id = str(uuid.uuid4())
        note_doc['id'] = note_id
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