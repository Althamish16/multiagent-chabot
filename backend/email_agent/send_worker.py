"""
Send Worker
Background email sending with retry logic and queue management
"""
from typing import Optional
import logging
import asyncio
from datetime import datetime

from .models import EmailDraft, DraftStatus, SendResult
from .draft_storage import draft_storage
from .gmail_connector import gmail_connector
from .approval_workflow import approval_workflow


class SendWorker:
    """Background worker for sending approved emails"""
    
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5
    
    def __init__(self, use_queue: bool = False):
        """
        Initialize send worker
        
        Args:
            use_queue: If True, use Redis queue (requires redis). If False, send immediately.
        """
        self.use_queue = use_queue
        self.queue = None
        
        if use_queue:
            try:
                import redis
                # TODO: Configure Redis connection from environment
                # self.queue = redis.Redis(host='localhost', port=6379, db=0)
                logging.warning("Redis queue not configured, falling back to immediate send")
                self.use_queue = False
            except ImportError:
                logging.warning("Redis not installed, using immediate send mode")
                self.use_queue = False
        
        logging.info(f"SendWorker initialized (queue_mode={self.use_queue})")
    
    async def queue_send(
        self,
        draft_id: str,
        access_token: str,
        user_id: str
    ) -> SendResult:
        """Queue an approved email for sending"""
        
        # Load draft
        draft = await draft_storage.get_draft(draft_id)
        if not draft:
            return SendResult(
                draft_id=draft_id,
                success=False,
                error_message="Draft not found"
            )
        
        # Verify draft is approved
        if draft.status != DraftStatus.APPROVED:
            return SendResult(
                draft_id=draft_id,
                success=False,
                error_message=f"Draft not approved (status: {draft.status})"
            )
        
        # Send immediately (no queue configured)
        if not self.use_queue:
            return await self._send_email(draft, access_token)
        
        # TODO: Queue implementation with Redis
        # For now, send immediately
        return await self._send_email(draft, access_token)
    
    async def _send_email(
        self,
        draft: EmailDraft,
        access_token: str,
        retry_count: int = 0
    ) -> SendResult:
        """Send email with retry logic"""
        
        logging.info(f"Sending email {draft.id} (attempt {retry_count + 1}/{self.MAX_RETRIES + 1})")
        
        try:
            # Send via Gmail connector
            result = await gmail_connector.send_email(draft, access_token)
            
            if result.success:
                # Update draft status (using draft's session_id)
                await draft_storage.update_draft_status(
                    draft.id,
                    draft.session_id,
                    DraftStatus.SENT,
                    sent_at=result.sent_at,
                    gmail_message_id=result.gmail_message_id,
                    gmail_thread_id=result.gmail_thread_id
                )
                logging.info(f"Email {draft.id} sent successfully")
                return result
            else:
                # Send failed, retry if possible
                if retry_count < self.MAX_RETRIES:
                    logging.warning(f"Send failed, retrying in {self.RETRY_DELAY_SECONDS}s: {result.error_message}")
                    await asyncio.sleep(self.RETRY_DELAY_SECONDS)
                    return await self._send_email(draft, access_token, retry_count + 1)
                else:
                    # Max retries reached
                    logging.error(f"Email {draft.id} failed after {retry_count + 1} attempts")
                    await draft_storage.update_draft_status(draft.id, draft.session_id, DraftStatus.FAILED)
                    result.retry_count = retry_count
                    return result
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(f"Failed to send email {draft.id}: {error_msg}")
            
            # Retry on exception
            if retry_count < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_DELAY_SECONDS)
                return await self._send_email(draft, access_token, retry_count + 1)
            else:
                await draft_storage.update_draft_status(draft.id, draft.session_id, DraftStatus.FAILED)
                return SendResult(
                    draft_id=draft.id,
                    success=False,
                    error_message=error_msg,
                    retry_count=retry_count
                )
    
    async def send_approved_draft(
        self,
        draft_id: str,
        access_token: str,
        user_id: str,
        auto_approve: bool = False
    ) -> SendResult:
        """
        Send an approved draft (or auto-approve and send)
        
        Args:
            draft_id: Draft to send
            access_token: Google OAuth access token
            user_id: User requesting send
            auto_approve: If True, auto-approve before sending (for testing)
        """
        
        # Load draft
        draft = await draft_storage.get_draft(draft_id)
        if not draft:
            return SendResult(
                draft_id=draft_id,
                success=False,
                error_message="Draft not found"
            )
        
        # Auto-approve if requested
        if auto_approve and draft.status == DraftStatus.PENDING_APPROVAL:
            draft = await approval_workflow.auto_approve(draft_id)
        
        # Verify approved status
        if draft.status != DraftStatus.APPROVED:
            return SendResult(
                draft_id=draft_id,
                success=False,
                error_message=f"Draft must be approved before sending (current status: {draft.status})"
            )
        
        # Queue/send the email
        return await self.queue_send(draft_id, access_token, user_id)
    
    async def process_queue(self):
        """Process queued emails (for background worker mode)"""
        
        if not self.use_queue:
            logging.warning("Queue processing called but queue mode is disabled")
            return
        
        # TODO: Implement Redis queue processing
        # while True:
        #     job = self.queue.blpop('email_send_queue', timeout=5)
        #     if job:
        #         await self._process_job(job)
        
        logging.info("Queue processing not implemented (Redis not configured)")


# Global instance
send_worker = SendWorker(use_queue=False)
