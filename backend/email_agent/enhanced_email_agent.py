"""
Enhanced Email Agent
Main agent interface for email operations, integrated with orchestrator
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from .email_drafter import email_drafter
from .approval_workflow import approval_workflow
from .gmail_connector import gmail_connector
from .draft_storage import draft_storage
from .send_worker import send_worker
from .safety_guard import safety_guard
from .models import (
    EmailDraft,
    EmailTone,
    EmailPriority,
    DraftStatus,
    ApprovalDecision,
    EmailAgentState
)


class EnhancedEmailAgent:
    """
    Enhanced Email Agent with AI drafting and human approval workflow
    Follows the same pattern as other agents (Calendar, Notes, File)
    """
    
    def __init__(self):
        self.drafter = email_drafter
        self.workflow = approval_workflow
        self.connector = gmail_connector
        self.storage = draft_storage
        self.worker = send_worker
        self.guard = safety_guard
        logging.info("EnhancedEmailAgent initialized")
    
    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email-related requests
        Matches signature of other agents: process_request(state) -> result_dict
        
        State fields:
            - user_request: str (required)
            - session_id: str (required)
            - access_token: str (optional, for Gmail API)
            - conversation_history: List[str] (optional)
            - user_id: str (optional)
            - action: str (optional: "draft", "approve", "send", "list")
            - draft_id: str (optional, for approve/send actions)
        """
        
        user_request = state.get("user_request", "")
        session_id = state.get("session_id")
        access_token = state.get("access_token")
        conversation_history = state.get("conversation_history", [])
        user_id = state.get("user_id")
        
        logging.info(f"Email agent processing request: {user_request[:50]}...")
        
        # Analyze request to determine action
        action = await self._determine_action(user_request, state)
        
        try:
            if action == "draft":
                return await self._handle_draft(state)
            elif action == "approve":
                return await self._handle_approve(state)
            elif action == "send":
                return await self._handle_send(state)
            elif action == "list":
                return await self._handle_list(state)
            elif action == "update":
                return await self._handle_update(state)
            elif action == "read":
                return await self._handle_read(state)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "result": {}
                }
        
        except Exception as e:
            logging.error(f"Email agent error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to process email request: {str(e)}",
                "result": {}
            }
    
    async def _determine_action(self, user_request: str, state: Dict[str, Any]) -> str:
        """Determine what action to take based on request"""
        
        # Explicit action provided
        if "action" in state:
            return state["action"]
        
        # Analyze request text
        request_lower = user_request.lower()
        
        if any(word in request_lower for word in ["approve", "accept", "confirm send"]):
            return "approve"
        elif any(word in request_lower for word in ["send email", "send the email", "send it"]):
            return "send"
        elif any(word in request_lower for word in ["list", "show", "drafts", "pending"]):
            return "list"
        elif any(word in request_lower for word in ["update", "change", "edit", "modify"]):
            return "update"
        elif any(word in request_lower for word in ["read", "fetch", "get", "inbox", "emails", "messages"]):
            return "read"
        else:
            # Default to drafting
            return "draft"
    
    async def _handle_draft(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email drafting request"""
        
        user_request = state.get("user_request", "")
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        conversation_history = state.get("conversation_history", [])
        
        # Extract parameters from request or state
        recipient = state.get("recipient")
        subject = state.get("subject")
        tone = state.get("tone", EmailTone.PROFESSIONAL)
        priority = state.get("priority", EmailPriority.MEDIUM)
        
        # Create draft
        draft = await self.drafter.draft_email(
            user_request=user_request,
            session_id=session_id,
            recipient=recipient,
            subject=subject,
            tone=tone,
            priority=priority,
            conversation_history=conversation_history,
            user_id=user_id
        )
        
        # Save draft
        await self.storage.save_draft(draft)
        
        # Request approval
        await self.workflow.request_approval(draft, user_id or "anonymous")
        
        # Build response
        safety_summary = ""
        if draft.safety_checks:
            flags = draft.safety_checks.get('flags', [])
            if flags:
                safety_summary = f"\n\n⚠️ Safety Checks: {len(flags)} issue(s) found:\n" + "\n".join(f"  - {flag}" for flag in flags[:3])
        
        return {
            "status": "success",
            "message": f"Email draft created and awaiting approval{safety_summary}",
            "result": {
                "draft_id": draft.id,
                "to": draft.to,
                "subject": draft.subject,
                "body": draft.body,
                "status": draft.status.value,
                "safety_checks": draft.safety_checks,
                "created_at": draft.created_at.isoformat()
            }
        }
    
    async def _handle_approve(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle draft approval"""
        
        draft_id = state.get("draft_id")
        user_id = state.get("user_id", "anonymous")
        
        if not draft_id:
            return {
                "status": "error",
                "message": "No draft_id provided for approval",
                "result": {}
            }
        
        # Create approval decision
        decision = ApprovalDecision(
            draft_id=draft_id,
            user_id=user_id,
            approved=True,
            feedback="Approved via agent"
        )
        
        # Process approval
        draft = await self.workflow.process_decision(decision)
        
        return {
            "status": "success",
            "message": f"Draft {draft_id} approved. Ready to send.",
            "result": {
                "draft_id": draft.id,
                "status": draft.status.value,
                "approved_at": draft.approved_at.isoformat() if draft.approved_at else None
            }
        }
    
    async def _handle_send(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email sending"""
        
        draft_id = state.get("draft_id")
        access_token = state.get("access_token")
        user_id = state.get("user_id", "anonymous")
        
        if not draft_id:
            return {
                "status": "error",
                "message": "No draft_id provided for sending",
                "result": {}
            }
        
        if not access_token:
            return {
                "status": "error",
                "message": "No access_token provided. Gmail API access required.",
                "result": {}
            }
        
        # Send the email
        result = await self.worker.send_approved_draft(
            draft_id=draft_id,
            access_token=access_token,
            user_id=user_id,
            auto_approve=False  # Require explicit approval
        )
        
        if result.success:
            return {
                "status": "success",
                "message": f"Email sent successfully to {result.gmail_message_id}",
                "result": {
                    "draft_id": result.draft_id,
                    "gmail_message_id": result.gmail_message_id,
                    "gmail_thread_id": result.gmail_thread_id,
                    "sent_at": result.sent_at.isoformat() if result.sent_at else None
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to send email: {result.error_message}",
                "result": {
                    "draft_id": result.draft_id,
                    "error": result.error_message,
                    "retry_count": result.retry_count
                }
            }
    
    async def _handle_list(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """List email drafts"""
        
        session_id = state.get("session_id")
        status_filter = state.get("status")  # Optional status filter
        
        if status_filter:
            try:
                status_filter = DraftStatus(status_filter)
            except ValueError:
                status_filter = None
        
        drafts = await self.storage.get_drafts_by_session(session_id, status=status_filter)
        
        draft_list = [
            {
                "draft_id": d.id,
                "to": d.to,
                "subject": d.subject,
                "status": d.status.value,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat()
            }
            for d in drafts
        ]
        
        return {
            "status": "success",
            "message": f"Found {len(draft_list)} draft(s)",
            "result": {
                "drafts": draft_list,
                "count": len(draft_list)
            }
        }
    
    async def _handle_update(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing draft"""
        
        draft_id = state.get("draft_id")
        user_request = state.get("user_request", "")
        modifications = state.get("modifications", {})
        
        if not draft_id:
            return {
                "status": "error",
                "message": "No draft_id provided for update",
                "result": {}
            }
        
        # Load draft
        draft = await self.storage.get_draft(draft_id)
        if not draft:
            return {
                "status": "error",
                "message": f"Draft {draft_id} not found",
                "result": {}
            }
        
        # Update draft
        updated_draft = await self.drafter.update_draft(
            draft=draft,
            modifications=modifications,
            user_request=user_request
        )
        
        # Save updated draft
        await self.storage.save_draft(updated_draft)
        
        return {
            "status": "success",
            "message": f"Draft {draft_id} updated successfully",
            "result": {
                "draft_id": updated_draft.id,
                "to": updated_draft.to,
                "subject": updated_draft.subject,
                "body": updated_draft.body,
                "updated_at": updated_draft.updated_at.isoformat()
            }
        }
    
    async def _handle_read(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email reading/fetching request"""
        
        access_token = state.get("access_token")
        if not access_token:
            return {
                "status": "error",
                "message": "Authentication required. Please sign in with Google to read emails.",
                "result": {"requires_auth": True}
            }
        
        user_request = state.get("user_request", "").lower()
        max_results = state.get("max_results", 10)
        query = state.get("query")
        message_id = state.get("message_id")
        
        try:
            # If specific message ID requested
            if message_id:
                email_data = await self.connector.get_email(access_token, message_id)
                if email_data:
                    return {
                        "status": "success",
                        "message": f"Fetched email: {email_data['subject']}",
                        "result": {
                            "email": email_data,
                            "action": "read_single"
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Email {message_id} not found",
                        "result": {}
                    }
            
            # List emails based on request
            # Parse query from natural language
            if not query:
                if "unread" in user_request:
                    query = "is:unread"
                elif "important" in user_request:
                    query = "is:important"
                elif "starred" in user_request:
                    query = "is:starred"
                # Check for sender filter
                if "from " in user_request:
                    # Extract email after "from"
                    import re
                    match = re.search(r'from\s+([^\s]+@[^\s]+)', user_request)
                    if match:
                        sender = match.group(1)
                        query = f"from:{sender}" if not query else f"{query} from:{sender}"
            
            # Fetch emails
            result = await self.connector.list_emails(
                access_token=access_token,
                max_results=max_results,
                query=query
            )
            
            if 'error' in result:
                return {
                    "status": "error",
                    "message": f"Failed to fetch emails: {result['error']}",
                    "result": {}
                }
            
            emails = result.get('emails', [])
            total = result.get('total_count', 0)
            
            # Format response
            if total == 0:
                message = "No emails found" + (f" matching '{query}'" if query else " in inbox")
            else:
                message = f"Found {total} email{'s' if total != 1 else ''}" + (f" matching '{query}'" if query else "")
            
            # Create formatted summary for display
            email_summaries = []
            for email in emails[:10]:  # Show first 10
                summary = {
                    "from": email.get("from", "Unknown"),
                    "subject": email.get("subject", "(No Subject)"),
                    "date": email.get("date", ""),
                    "snippet": email.get("snippet", "")[:100],
                    "is_unread": email.get("is_unread", False),
                    "id": email.get("id")
                }
                email_summaries.append(summary)
            
            return {
                "status": "success",
                "message": message,
                "result": {
                    "emails": emails,
                    "email_summaries": email_summaries,
                    "total_count": total,
                    "query": query,
                    "action": "read_list"
                }
            }
            
        except Exception as e:
            logging.error(f"Error reading emails: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to read emails: {str(e)}",
                "result": {}
            }


# Global instance
enhanced_email_agent = EnhancedEmailAgent()
