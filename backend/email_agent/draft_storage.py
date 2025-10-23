"""
Email Draft Storage
JSON file-based storage for email drafts following database_utils.py patterns
"""
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime

from .models import EmailDraft, DraftStatus

# Draft storage directory
DRAFTS_DIR = Path(__file__).parent.parent / "data" / "email_drafts"
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


class DraftStorage:
    """Manage email draft persistence using JSON files"""
    
    def __init__(self, storage_dir: Path = DRAFTS_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Draft storage initialized at: {self.storage_dir}")
    
    def _get_draft_file(self, draft_id: str) -> Path:
        """Get file path for a specific draft"""
        return self.storage_dir / f"draft_{draft_id}.json"
    
    def _get_session_index_file(self, session_id: str) -> Path:
        """Get index file for session's drafts"""
        return self.storage_dir / f"session_{session_id}_index.json"
    
    async def save_draft(self, draft: EmailDraft) -> EmailDraft:
        """Save or update a draft"""
        try:
            draft.updated_at = datetime.utcnow()
            draft_file = self._get_draft_file(draft.id)
            
            # Save draft file
            with open(draft_file, 'w', encoding='utf-8') as f:
                json.dump(draft.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Update session index
            await self._update_session_index(draft.session_id, draft.id)
            
            logging.info(f"Saved draft {draft.id} to {draft_file}")
            return draft
            
        except Exception as e:
            logging.error(f"Failed to save draft {draft.id}: {e}")
            raise
    
    async def get_draft(self, draft_id: str) -> Optional[EmailDraft]:
        """Retrieve a draft by ID"""
        try:
            draft_file = self._get_draft_file(draft_id)
            if not draft_file.exists():
                return None
            
            with open(draft_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return EmailDraft.from_dict(data)
            
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
                draft = await self.get_draft(draft_id)
                if draft:
                    if status is None or draft.status == status:
                        drafts.append(draft)
            
            # Sort by creation time, newest first
            drafts.sort(key=lambda d: d.created_at, reverse=True)
            return drafts
            
        except Exception as e:
            logging.error(f"Failed to load drafts for session {session_id}: {e}")
            return []
    
    async def update_draft_status(self, draft_id: str, status: DraftStatus, **kwargs) -> Optional[EmailDraft]:
        """Update draft status and optional fields"""
        try:
            draft = await self.get_draft(draft_id)
            if not draft:
                return None
            
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
    
    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft"""
        try:
            draft_file = self._get_draft_file(draft_id)
            if draft_file.exists():
                draft_file.unlink()
                logging.info(f"Deleted draft {draft_id}")
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
    
    async def get_all_pending_approvals(self) -> List[EmailDraft]:
        """Get all drafts pending approval across all sessions"""
        try:
            pending_drafts = []
            
            # Scan all draft files
            for draft_file in self.storage_dir.glob("draft_*.json"):
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
