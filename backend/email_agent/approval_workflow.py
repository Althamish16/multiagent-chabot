"""
Approval Workflow
State machine for email draft approval lifecycle
"""
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from .models import (
    EmailDraft,
    DraftStatus,
    ApprovalRequest,
    ApprovalDecision
)
from .draft_storage import draft_storage


class ApprovalWorkflow:
    """Manages email draft approval lifecycle"""
    
    # Approval timeout (hours)
    APPROVAL_TIMEOUT_HOURS = 24
    
    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        logging.info("ApprovalWorkflow initialized")
    
    async def request_approval(
        self,
        draft: EmailDraft,
        user_id: str,
        send_notification: bool = True
    ) -> ApprovalRequest:
        """Request human approval for a draft"""
        
        logging.info(f"Requesting approval for draft {draft.id}")
        
        # Update draft status
        draft.status = DraftStatus.PENDING_APPROVAL
        await draft_storage.save_draft(draft)
        
        # Create approval request
        approval_request = ApprovalRequest(
            draft_id=draft.id,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=self.APPROVAL_TIMEOUT_HOURS),
            notification_sent=False
        )
        
        self.pending_approvals[draft.id] = approval_request
        
        # TODO: Send notification (email, webhook, etc.)
        if send_notification:
            await self._send_approval_notification(draft, user_id)
            approval_request.notification_sent = True
        
        logging.info(f"Approval requested for draft {draft.id}, expires at {approval_request.expires_at}")
        return approval_request
    
    async def process_decision(
        self,
        decision: ApprovalDecision
    ) -> EmailDraft:
        """Process human approval decision"""
        
        logging.info(f"Processing approval decision for draft {decision.draft_id}: approved={decision.approved}")
        
        # Load draft
        draft = await draft_storage.get_draft(decision.draft_id)
        if not draft:
            raise ValueError(f"Draft {decision.draft_id} not found")
        
        # Validate current status
        if draft.status != DraftStatus.PENDING_APPROVAL:
            raise ValueError(f"Draft {decision.draft_id} is not pending approval (status: {draft.status})")
        
        # Apply decision
        if decision.approved:
            draft.status = DraftStatus.APPROVED
            draft.approved_at = decision.decided_at
            
            # Apply any modifications
            if decision.modifications_requested:
                for field, value in decision.modifications_requested.items():
                    if hasattr(draft, field):
                        setattr(draft, field, value)
            
            logging.info(f"Draft {draft.id} approved")
        else:
            draft.status = DraftStatus.REJECTED
            logging.info(f"Draft {draft.id} rejected: {decision.feedback}")
        
        # Save updated draft
        await draft_storage.save_draft(draft)
        
        # Remove from pending approvals
        self.pending_approvals.pop(decision.draft_id, None)
        
        return draft
    
    async def auto_approve(self, draft_id: str) -> EmailDraft:
        """Auto-approve a draft (for testing or low-risk scenarios)"""
        
        logging.warning(f"Auto-approving draft {draft_id} (bypass human review)")
        
        decision = ApprovalDecision(
            draft_id=draft_id,
            user_id="system",
            approved=True,
            feedback="Auto-approved by system"
        )
        
        return await self.process_decision(decision)
    
    async def check_expired_approvals(self) -> int:
        """Check for and expire timed-out approval requests"""
        
        now = datetime.utcnow()
        expired_count = 0
        
        for draft_id, approval in list(self.pending_approvals.items()):
            if approval.expires_at and now > approval.expires_at:
                # Expire the approval
                draft = await draft_storage.get_draft(draft_id)
                if draft and draft.status == DraftStatus.PENDING_APPROVAL:
                    draft.status = DraftStatus.REJECTED
                    await draft_storage.save_draft(draft)
                    
                self.pending_approvals.pop(draft_id)
                expired_count += 1
                logging.info(f"Expired approval request for draft {draft_id}")
        
        if expired_count > 0:
            logging.info(f"Expired {expired_count} approval requests")
        
        return expired_count
    
    async def get_pending_approvals(self, user_id: Optional[str] = None) -> list[ApprovalRequest]:
        """Get all pending approval requests, optionally filtered by user"""
        
        if user_id:
            return [
                req for req in self.pending_approvals.values()
                if req.user_id == user_id
            ]
        return list(self.pending_approvals.values())
    
    async def cancel_approval(self, draft_id: str) -> bool:
        """Cancel a pending approval request"""
        
        if draft_id in self.pending_approvals:
            self.pending_approvals.pop(draft_id)
            
            # Update draft status
            draft = await draft_storage.get_draft(draft_id)
            if draft:
                draft.status = DraftStatus.DRAFTED
                await draft_storage.save_draft(draft)
            
            logging.info(f"Cancelled approval request for draft {draft_id}")
            return True
        
        return False
    
    async def _send_approval_notification(self, draft: EmailDraft, user_id: str):
        """Send notification about pending approval (stub for future implementation)"""
        
        # TODO: Implement notification system
        # Options: Email, webhook, push notification, etc.
        
        logging.info(f"[NOTIFICATION] Approval needed for draft {draft.id}")
        logging.info(f"  To: {draft.to}")
        logging.info(f"  Subject: {draft.subject}")
        logging.info(f"  User: {user_id}")
        
        # For now, just log. In production:
        # - Send email to user
        # - Trigger webhook
        # - Create in-app notification
        # - Send SMS/push notification
    
    def get_approval_status(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Get current approval status for a draft"""
        
        if draft_id not in self.pending_approvals:
            return None
        
        approval = self.pending_approvals[draft_id]
        return {
            'draft_id': approval.draft_id,
            'user_id': approval.user_id,
            'requested_at': approval.requested_at.isoformat(),
            'expires_at': approval.expires_at.isoformat() if approval.expires_at else None,
            'notification_sent': approval.notification_sent,
            'time_remaining': (approval.expires_at - datetime.utcnow()).total_seconds() if approval.expires_at else None
        }


# Global instance
approval_workflow = ApprovalWorkflow()
