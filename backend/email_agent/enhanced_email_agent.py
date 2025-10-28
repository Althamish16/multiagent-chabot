"""
Enhanced Email Agent
Main agent interface for email operations, integrated with orchestrator
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from openai import AsyncAzureOpenAI
from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)

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
        self.llm = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment_name = AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        
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
        """Determine what action to take based on request using LLM analysis"""
        
        # Explicit action provided (highest priority)
        if "action" in state:
            return state["action"]
        
        # Try LLM-based analysis first
        try:
            llm_action = await self._determine_action_llm(user_request, state)
            if llm_action and llm_action != "unknown":
                logging.info(f"LLM determined action: {llm_action}")
                return llm_action
        except Exception as e:
            logging.warning(f"LLM action determination failed: {e}, falling back to keyword matching")
        
        # Fallback to keyword matching
        return await self._determine_action_keywords(user_request, state)
    
    async def _determine_action_llm(self, user_request: str, state: Dict[str, Any]) -> str:
        """Use LLM to intelligently determine the appropriate email action"""
        
        conversation_history = state.get("conversation_history", [])
        session_id = state.get("session_id")
        
        # Get recent conversation context (last 3 messages)
        recent_context = ""
        if conversation_history:
            recent_messages = conversation_history[-3:]
            recent_context = "\n".join([f"- {msg}" for msg in recent_messages])
        
        # Check for existing drafts in session to provide context
        draft_context = ""
        if session_id:
            try:
                drafts = await self.storage.get_drafts_by_session(session_id)
                if drafts:
                    draft_statuses = {}
                    for draft in drafts[-3:]:  # Last 3 drafts
                        status = draft.status.value if hasattr(draft.status, 'value') else draft.status
                        draft_statuses[draft.id] = status
                    
                    draft_context = f"Recent drafts: {draft_statuses}"
            except Exception as e:
                logging.debug(f"Could not load draft context: {e}")
        
        analysis_prompt = f"""
        Analyze this user request and determine the most appropriate email action.

        Available actions:
        - draft: Create a new email draft
        - approve: Approve a pending email draft
        - send: Send an approved email draft
        - list: Show/list email drafts
        - update: Modify an existing draft
        - read: Read/fetch emails from inbox

        Context:
        - Recent conversation: {recent_context}
        - Draft status: {draft_context}

        User request: "{user_request}"

        Respond with ONLY the action name (draft/approve/send/list/update/read). If unclear, respond with "draft".
        """
        
        try:
            response = await self.llm.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an email action classifier. Respond with only the action name."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            action = response.choices[0].message.content.strip().lower()
            
            # Validate the action is one of our expected actions
            valid_actions = ["draft", "approve", "send", "list", "update", "read"]
            if action in valid_actions:
                return action
            else:
                logging.warning(f"LLM returned invalid action: {action}")
                return "unknown"
                
        except Exception as e:
            logging.error(f"LLM action determination error: {e}")
            return "unknown"
    
    async def _determine_action_keywords(self, user_request: str, state: Dict[str, Any]) -> str:
        """Fallback keyword-based action determination"""
        
        # Analyze request text
        request_lower = user_request.lower()
        
        if any(word in request_lower for word in ["approve", "accept", "confirm send"]):
            return "approve"
        elif any(phrase in request_lower for phrase in ["send email", "send the email", "send it", "send mail", "send the mail"]):
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
                "status": draft.status.value if hasattr(draft.status, 'value') else draft.status,
                "safety_checks": draft.safety_checks,
                "created_at": draft.created_at.isoformat()
            }
        }
    
    async def _handle_approve(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle draft approval"""
        
        draft_id = state.get("draft_id")
        user_id = state.get("user_id", "anonymous")
        session_id = state.get("session_id")
        
        # If no draft_id provided, find the most recent pending draft
        if not draft_id and session_id:
            drafts = await self.storage.get_drafts_by_session(session_id, status=DraftStatus.PENDING_APPROVAL)
            if drafts:
                # Get the most recent pending draft
                draft_id = max(drafts, key=lambda d: d.created_at).id
                logging.info(f"Using most recent pending draft for approval: {draft_id}")
            else:
                return {
                    "status": "error",
                    "message": "No pending drafts found to approve.",
                    "result": {}
                }
        
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
                "status": draft.status.value if hasattr(draft.status, 'value') else draft.status,
                "approved_at": draft.approved_at.isoformat() if draft.approved_at else None
            }
        }
    
    async def _handle_send(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email sending"""
        
        draft_id = state.get("draft_id")
        access_token = state.get("access_token")
        user_id = state.get("user_id", "anonymous")
        session_id = state.get("session_id")
        
        # If no draft_id provided, find the most recent draft (approved or pending)
        if not draft_id and session_id:
            # First try approved drafts
            drafts = await self.storage.get_drafts_by_session(session_id, status=DraftStatus.APPROVED)
            if drafts:
                # Get the most recent approved draft
                draft_id = max(drafts, key=lambda d: d.created_at).id
                logging.info(f"Using most recent approved draft: {draft_id}")
            else:
                # If no approved drafts, check for pending approval drafts
                drafts = await self.storage.get_drafts_by_session(session_id, status=DraftStatus.PENDING_APPROVAL)
                if drafts:
                    draft_id = max(drafts, key=lambda d: d.created_at).id
                    logging.info(f"Using most recent pending draft: {draft_id}")
                else:
                    return {
                        "status": "error",
                        "message": "No drafts found to send. Please create an email draft first.",
                        "result": {}
                    }
        
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
        
        # Load the draft to check its status
        draft = await self.storage.get_draft(draft_id)
        if not draft:
            return {
                "status": "error",
                "message": f"Draft {draft_id} not found",
                "result": {}
            }
        
        # Auto-approve if the draft is pending approval
        current_status = draft.status.value if hasattr(draft.status, 'value') else draft.status
        if current_status == "pending_approval":
            logging.info(f"Auto-approving pending draft {draft_id} before sending")
            try:
                # Create approval decision
                decision = ApprovalDecision(
                    draft_id=draft_id,
                    user_id=user_id,
                    approved=True,
                    feedback="Auto-approved for sending"
                )
                
                # Process approval
                draft = await self.workflow.process_decision(decision)
                logging.info(f"Draft {draft_id} auto-approved successfully")
            except Exception as e:
                logging.error(f"Failed to auto-approve draft {draft_id}: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to approve draft before sending: {str(e)}",
                    "result": {}
                }
        
        # Now send the approved draft
        result = await self.worker.send_approved_draft(
            draft_id=draft_id,
            access_token=access_token,
            user_id=user_id,
            auto_approve=False  # Already approved above
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
                "status": d.status.value if hasattr(d.status, 'value') else d.status,
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
    
    def _parse_email_count(self, user_request: str) -> Optional[int]:
        """Parse the number of emails requested from natural language"""
        import re
        
        # Look for patterns like "get 5 emails", "latest 3 emails", "show 10 emails"
        patterns = [
            r'(\d+)\s+emails?',  # "5 emails"
            r'(\d+)\s+latest',    # "3 latest"
            r'latest\s+(\d+)',    # "latest 2"
            r'get\s+(\d+)',       # "get 1"
            r'show\s+(\d+)',      # "show 5"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_request, re.IGNORECASE)
            if match:
                try:
                    count = int(match.group(1))
                    return min(count, 100)  # Cap at 100
                except ValueError:
                    continue
        
        # Check for singular forms that imply 1
        if any(word in user_request for word in ['latest email', 'recent email', 'new email', 'last email']):
            return 1
        
        return None  # No specific count found, use default
    
    def _parse_message_id(self, user_request: str) -> Optional[str]:
        """Parse message ID from natural language request"""
        import re
        
        # Look for Gmail message ID patterns
        # Gmail message IDs are typically long alphanumeric strings
        patterns = [
            r'id\s+([a-zA-Z0-9]{10,})',  # "id 1234567890abcdef"
            r'message\s+id\s+([a-zA-Z0-9]{10,})',  # "message id 1234567890abcdef"
            r'email\s+id\s+([a-zA-Z0-9]{10,})',  # "email id 1234567890abcdef"
            r'message\s+([a-zA-Z0-9]{10,})',  # "message 1234567890abcdef"
            r'email\s+([a-zA-Z0-9]{10,})',  # "email 1234567890abcdef"
            r'([a-zA-Z0-9]{16,})',  # Just a long alphanumeric string (likely message ID)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_request, re.IGNORECASE)
            if match:
                message_id = match.group(1)
                # Basic validation - Gmail message IDs are usually 16+ characters
                if len(message_id) >= 10:
                    return message_id
        
        return None  # No message ID found
    
    def _extract_search_keywords(self, user_request: str) -> List[str]:
        """Extract meaningful keywords from user request for email search"""
        import re
        
        # Common stop words to filter out
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'while', 'at', 'by', 'for', 'with', 
            'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 
            'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 
            'very', 'can', 'will', 'just', 'should', 'now', 'get', 'show', 'list', 'find',
            'search', 'look', 'check', 'see', 'mail', 'email', 'emails', 'message', 'messages',
            'received', 'sent', 'got', 'have', 'has', 'had', 'do', 'does', 'did', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
            'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves'
        }
        
        # Split into words and filter
        words = re.findall(r'\b\w+\b', user_request.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Prioritize proper nouns, organizations, and specific terms
        priority_keywords = []
        for keyword in keywords:
            # Capitalized words (likely proper nouns)
            if keyword[0].isupper():
                priority_keywords.append(keyword)
            # Numbers (like account numbers, dates)
            elif keyword.isdigit() and len(keyword) > 3:
                priority_keywords.append(keyword)
            # All caps (likely acronyms like ICICI, HSBC)
            elif keyword.isupper() and len(keyword) > 2:
                priority_keywords.append(keyword)
        
        # If we have priority keywords, use them; otherwise use all filtered keywords
        if priority_keywords:
            return priority_keywords[:3]  # Limit to top 3 to avoid too broad search
        else:
            return keywords[:3]  # Limit to 3 keywords max
    
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
        max_results = state.get("max_results", 5)
        query = state.get("query")
        message_id = state.get("message_id")
        
        # Parse dynamic max_results from user request
        parsed_max_results = self._parse_email_count(user_request)
        if parsed_max_results is not None:
            max_results = min(parsed_max_results, 100)  # Cap at 100
        
        # Parse message_id from user request if not provided
        if not message_id:
            message_id = self._parse_message_id(user_request)
        
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
                query_parts = []
                
                # Handle status filters
                if "unread" in user_request:
                    query_parts.append("is:unread")
                elif "important" in user_request:
                    query_parts.append("is:important")
                elif "starred" in user_request:
                    query_parts.append("is:starred")
                
                # Handle time-based filters
                if any(word in user_request for word in ["recent", "latest", "new", "today"]):
                    # For recent emails, we could add date filters, but Gmail search is limited
                    # Just rely on the natural ordering from Gmail API
                    pass
                
                # Check for sender filter - more flexible parsing
                import re
                sender_patterns = [
                    r'from\s+([^\s]+@[^\s]+)',  # "from email@domain.com"
                    r'from\s+([^\s]+)',         # "from John" or "from ICICI"
                ]
                for pattern in sender_patterns:
                    match = re.search(pattern, user_request, re.IGNORECASE)
                    if match:
                        sender = match.group(1)
                        # If it looks like an email address, use from: filter
                        if '@' in sender:
                            query_parts.append(f"from:{sender}")
                        else:
                            # For names/organizations, search in from field
                            query_parts.append(f"from:{sender}")
                        break
                
                # Extract keywords for subject/body search
                # Remove common words and extract potential search terms
                keywords = self._extract_search_keywords(user_request)
                if keywords:
                    # Add keywords to search in subject and body
                    keyword_query = " OR ".join(keywords)
                    query_parts.append(f"subject:({keyword_query}) OR {keyword_query}")
                
                # Combine all query parts
                if query_parts:
                    query = " ".join(query_parts)
            
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
