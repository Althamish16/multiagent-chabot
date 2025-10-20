"""
Enhanced Mock Microsoft Graph API with sophisticated operations
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class EnhancedMockGraphAPI:
    @staticmethod
    async def send_email_with_invite(to: str, subject: str, body: str, meeting_details: Optional[Dict] = None):
        """Enhanced email sending with optional meeting invite"""
        await asyncio.sleep(0.5)
        result = {
            "id": f"enhanced-email-{uuid.uuid4()}",
            "status": "sent",
            "to": to,
            "subject": subject,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "contains_meeting_invite": bool(meeting_details),
            "meeting_link": f"https://teams.microsoft.com/meet/{uuid.uuid4()}" if meeting_details else None
        }

        if meeting_details:
            result["meeting_details"] = meeting_details

        return result

    @staticmethod
    async def create_calendar_event_with_attendees(title: str, start_date: str, end_date: str,
                                                 description: str = "", attendees: List[str] = None):
        """Enhanced calendar event creation with attendee management"""
        await asyncio.sleep(0.4)
        return {
            "id": f"enhanced-event-{uuid.uuid4()}",
            "title": title,
            "start": start_date,
            "end": end_date,
            "description": description,
            "attendees": attendees or [],
            "meeting_link": f"https://teams.microsoft.com/meet/{uuid.uuid4()}",
            "status": "created",
            "notifications_sent": len(attendees or []) > 0
        }

    @staticmethod
    async def save_structured_note(title: str, content: str, category: str = "General",
                                 tags: List[str] = None, related_items: Dict = None):
        """Enhanced note saving with structured data and relationships"""
        await asyncio.sleep(0.3)
        return {
            "id": f"enhanced-note-{uuid.uuid4()}",
            "title": title,
            "content": content,
            "category": category,
            "tags": tags or [],
            "related_items": related_items or {},
            "created": datetime.now(timezone.utc).isoformat(),
            "ai_processed": True
        }