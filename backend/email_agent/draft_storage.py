"""
Email Draft Storage
JSON file-based storage for email drafts following hierarchical session structure
"""
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime

from .models import EmailDraft, DraftStatus

# Import session-aware utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from database_utils import get_session_email_drafts_dir


class DraftStorage:
    """Manage email draft persistence using session-based JSON files"""
    
    def __init__(self):
        logging.info("Draft storage initialized with session-based structure")
    
    def _get_draft_file(self, session_id: str, draft_id: str) -> Path:
        """Get file path for a specific draft in a session"""
        drafts_dir = get_session_email_drafts_dir(session_id)
        return drafts_dir / f"draft_{draft_id}.json"
    
    def _get_session_index_file(self, session_id: str) -> Path:
        """Get index file for session's drafts"""
        drafts_dir = get_session_email_drafts_dir(session_id)
        return drafts_dir / "index.json"
    
    async def save_draft(self, draft: EmailDraft) -> EmailDraft:
        """Save or update a draft"""
        try:
            draft.updated_at = datetime.utcnow()
            draft_file = self._get_draft_file(draft.session_id, draft.id)
            
            # Save draft file
            with open(draft_file, 'w', encoding='utf-8') as f:
                json.dump(draft.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Update session index
            await self._update_session_index(draft.session_id, draft.id)
            
            logging.info(f"Saved draft {draft.id} to session {draft.session_id}")
            return draft
            
        except Exception as e:
            logging.error(f"Failed to save draft {draft.id}: {e}")
            raise
    
    async def get_draft(self, draft_id: str, session_id: str = None) -> Optional[EmailDraft]:
        """
        Load a specific draft by ID
        If session_id is provided, looks only in that session (faster)
        If session_id is None, searches all sessions (slower but more flexible)
        """
        try:
            if session_id:
                # Direct lookup in specific session
                draft_file = self._get_draft_file(session_id, draft_id)
                if not draft_file.exists():
                    return None
                
                with open(draft_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return EmailDraft.from_dict(data)
            else:
                # Search across all sessions
                from database_utils import SESSIONS_DIR
                for session_dir in SESSIONS_DIR.glob("session-*"):
                    drafts_dir = session_dir / "email_drafts"
                    if not drafts_dir.exists():
                        continue
                    
                    draft_file = drafts_dir / f"draft_{draft_id}.json"
                    if draft_file.exists():
                        with open(draft_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        return EmailDraft.from_dict(data)
                
                return None
            
        except Exception as e:
            logging.error(f"Failed to load draft {draft_id}: {e}")
            return None
    
    async def get_drafts_by_session(self, session_id: str, status: Optional[DraftStatus] = None) -> List[EmailDraft]:
        """Get all drafts for a session, optionally filtered by status"""
        try:
            index_file = self._get_session_index_file(session_id)
            if not index_file.exists():
                return []
            
            with open(index_file, 'r', encoding='utf-8') as f:
                draft_ids = json.load(f)
            
            drafts = []
            for draft_id in draft_ids:
                draft = await self.get_draft(draft_id, session_id)
                if draft:
                    if status is None or draft.status == status:
                        drafts.append(draft)
            
            # Sort by creation time, newest first
            drafts.sort(key=lambda d: d.created_at, reverse=True)
            return drafts
            
        except Exception as e:
            logging.error(f"Failed to load drafts for session {session_id}: {e}")
            return []
    
    async def update_draft_status(self, draft_id: str, session_id: str = None, status: DraftStatus = None, **kwargs) -> Optional[EmailDraft]:
        """
        Update draft status and optional fields
        If session_id not provided, will search all sessions
        """
        try:
            draft = await self.get_draft(draft_id, session_id)
            if not draft:
                return None
            
            if status:
                draft.status = status
            draft.updated_at = datetime.utcnow()
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(draft, key):
                    setattr(draft, key, value)
            
            await self.save_draft(draft)
            return draft
            
        except Exception as e:
            logging.error(f"Failed to update draft {draft_id} status: {e}")
            return None
    
    async def delete_draft(self, draft_id: str, session_id: str = None) -> bool:
        """
        Delete a draft
        If session_id not provided, will search all sessions
        """
        try:
            # Get the draft first to find its session_id
            draft = await self.get_draft(draft_id, session_id)
            if not draft:
                return False
            
            # Use the draft's session_id for deletion
            draft_file = self._get_draft_file(draft.session_id, draft_id)
            if draft_file.exists():
                draft_file.unlink()
                
                # Remove from session index
                await self._remove_from_session_index(draft.session_id, draft_id)
                
                logging.info(f"Deleted draft {draft_id} from session {draft.session_id}")
                return True
            return False
            
        except Exception as e:
            logging.error(f"Failed to delete draft {draft_id}: {e}")
            return False
    
    async def _update_session_index(self, session_id: str, draft_id: str):
        """Update session index with new draft ID"""
        try:
            index_file = self._get_session_index_file(session_id)
            draft_ids = []
            
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    draft_ids = json.load(f)
            
            if draft_id not in draft_ids:
                draft_ids.append(draft_id)
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(draft_ids, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to update session index for {session_id}: {e}")
    
    async def _remove_from_session_index(self, session_id: str, draft_id: str):
        """Remove draft ID from session index"""
        try:
            index_file = self._get_session_index_file(session_id)
            if not index_file.exists():
                return
            
            with open(index_file, 'r', encoding='utf-8') as f:
                draft_ids = json.load(f)
            
            if draft_id in draft_ids:
                draft_ids.remove(draft_id)
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(draft_ids, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to remove from session index for {session_id}: {e}")
    
    async def get_all_pending_approvals(self) -> List[EmailDraft]:
        """Get all drafts pending approval across all sessions"""
        try:
            from database_utils import SESSIONS_DIR
            pending_drafts = []
            
            # Scan all session directories
            for session_dir in SESSIONS_DIR.glob("session-*"):
                drafts_dir = session_dir / "email_drafts"
                if not drafts_dir.exists():
                    continue
                
                # Check each draft file in the session
                for draft_file in drafts_dir.glob("draft_*.json"):
                    try:
                        with open(draft_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        draft = EmailDraft.from_dict(data)
                        if draft.status == DraftStatus.PENDING_APPROVAL:
                            pending_drafts.append(draft)
                    except Exception as e:
                        logging.warning(f"Failed to load draft file {draft_file}: {e}")
            
            return sorted(pending_drafts, key=lambda d: d.created_at)
            
        except Exception as e:
            logging.error(f"Failed to get pending approvals: {e}")
            return []
    
    async def cleanup_old_drafts(self, days: int = 30) -> int:
        """Delete drafts older than specified days (sent, rejected, or failed)"""
        try:
            cutoff = datetime.utcnow().timestamp() - (days * 86400)
            deleted = 0
            
            for draft_file in self.storage_dir.glob("draft_*.json"):
                try:
                    with open(draft_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    draft = EmailDraft.from_dict(data)
                    
                    # Only cleanup terminal states
                    if draft.status in [DraftStatus.SENT, DraftStatus.REJECTED, DraftStatus.FAILED]:
                        if draft.updated_at.timestamp() < cutoff:
                            draft_file.unlink()
                            deleted += 1
                            
                except Exception as e:
                    logging.warning(f"Failed to process draft file {draft_file}: {e}")
            
            logging.info(f"Cleaned up {deleted} old drafts")
            return deleted
            
        except Exception as e:
            logging.error(f"Failed to cleanup old drafts: {e}")
            return 0


# Global instance
draft_storage = DraftStorage()
