"""
Email Drafter
AI-powered email drafting using Azure OpenAI with context awareness
"""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from openai import AsyncAzureOpenAI
from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)

from .models import EmailDraft, EmailTone, EmailPriority, DraftStatus
from .safety_guard import safety_guard


class EmailDrafter:
    """AI-powered email draft generation"""
    
    TONE_GUIDELINES = {
        EmailTone.PROFESSIONAL: "Use professional, business-appropriate language. Be polite and clear.",
        EmailTone.FRIENDLY: "Use warm, friendly language while maintaining professionalism. Be conversational.",
        EmailTone.FORMAL: "Use formal, traditional business language. Be respectful and reserved.",
        EmailTone.CASUAL: "Use relaxed, informal language. Be personable and direct."
    }
    
    def __init__(self):
        self.llm = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment_name = AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        logging.info("EmailDrafter initialized with Azure OpenAI")
    
    async def draft_email(
        self,
        user_request: str,
        session_id: str,
        recipient: Optional[str] = None,
        subject: Optional[str] = None,
        tone: EmailTone = EmailTone.PROFESSIONAL,
        priority: EmailPriority = EmailPriority.MEDIUM,
        conversation_history: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> EmailDraft:
        """Generate an email draft from user request"""
        
        logging.info(f"Drafting email for session {session_id}: {user_request[:50]}...")
        
        # Build context
        context = self._build_context(user_request, conversation_history)
        
        # Generate email content
        email_data = await self._generate_email_content(
            user_request=user_request,
            context=context,
            tone=tone,
            recipient=recipient,
            subject=subject
        )
        
        # Create draft object
        draft = EmailDraft(
            session_id=session_id,
            user_id=user_id,
            to=email_data['to'],
            subject=email_data['subject'],
            body=email_data['body'],
            tone=tone,
            priority=priority,
            status=DraftStatus.DRAFTED,
            conversation_context=conversation_history[-5:] if conversation_history else None,
            ai_reasoning=email_data.get('reasoning', '')
        )
        
        # Run safety checks
        safety_result = await safety_guard.check_draft(draft)
        draft.safety_checks = safety_result.to_dict()
        
        # Update status based on safety
        if not safety_result.passed:
            logging.warning(f"Draft {draft.id} failed safety checks: {safety_result.flags}")
            draft.status = DraftStatus.PENDING_APPROVAL  # Still needs review
        else:
            draft.status = DraftStatus.PENDING_APPROVAL
        
        logging.info(f"Draft {draft.id} created successfully (status: {draft.status})")
        return draft
    
    async def update_draft(
        self,
        draft: EmailDraft,
        modifications: Dict[str, str],
        user_request: Optional[str] = None
    ) -> EmailDraft:
        """Update an existing draft with modifications"""
        
        logging.info(f"Updating draft {draft.id} with modifications: {list(modifications.keys())}")
        
        # Apply direct field updates
        for field, value in modifications.items():
            if hasattr(draft, field) and field in ['to', 'subject', 'body', 'cc', 'bcc']:
                setattr(draft, field, value)
        
        # If there's a user request for AI-assisted update
        if user_request:
            updated_content = await self._regenerate_content(
                draft=draft,
                user_request=user_request,
                modifications=modifications
            )
            draft.body = updated_content['body']
            if 'subject' in updated_content:
                draft.subject = updated_content['subject']
        
        draft.updated_at = datetime.utcnow()
        
        # Re-run safety checks
        safety_result = await safety_guard.check_draft(draft)
        draft.safety_checks = safety_result.to_dict()
        
        logging.info(f"Draft {draft.id} updated successfully")
        return draft
    
    def _build_context(self, user_request: str, conversation_history: Optional[List[str]]) -> str:
        """Build context string from conversation history"""
        if not conversation_history:
            return "No previous conversation context."
        
        # Take last 5 messages for context
        recent = conversation_history[-5:]
        return "\n".join(recent)
    
    async def _generate_email_content(
        self,
        user_request: str,
        context: str,
        tone: EmailTone,
        recipient: Optional[str],
        subject: Optional[str]
    ) -> Dict[str, Any]:
        """Use LLM to generate email content"""
        
        tone_guide = self.TONE_GUIDELINES.get(tone, self.TONE_GUIDELINES[EmailTone.PROFESSIONAL])
        
        system_prompt = f"""You are an expert email writer. Generate professional email drafts based on user requests.

TONE: {tone_guide}

INSTRUCTIONS:
1. Extract or infer the recipient email if not explicitly provided
2. Create a clear, concise subject line if not provided
3. Write a well-structured email body with proper greeting and closing
4. Maintain the requested tone throughout
5. Be specific and actionable

Return JSON with:
{{
    "to": "recipient@example.com",
    "subject": "Clear subject line",
    "body": "Full email body with greeting, content, and closing",
    "reasoning": "Brief explanation of your approach"
}}"""

        user_prompt = f"""User Request: {user_request}

Conversation Context:
{context}

{f"Recipient: {recipient}" if recipient else "Infer recipient from request"}
{f"Subject: {subject}" if subject else "Generate appropriate subject"}

Generate the email draft as JSON."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            import json
            # Extract JSON from response (handle markdown code blocks)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            email_data = json.loads(content)
            
            # Validate required fields
            if 'to' not in email_data or 'subject' not in email_data or 'body' not in email_data:
                raise ValueError("LLM response missing required fields")
            
            # Use provided recipient if available
            if recipient:
                email_data['to'] = recipient
            if subject:
                email_data['subject'] = subject
            
            return email_data
            
        except Exception as e:
            logging.error(f"Failed to generate email content: {e}")
            # Fallback to basic template
            return {
                'to': recipient or 'recipient@example.com',
                'subject': subject or 'Email from AI Assistant',
                'body': f"[Generated from request: {user_request}]\n\nPlease review and edit as needed.",
                'reasoning': f"Fallback due to error: {str(e)}"
            }
    
    async def _regenerate_content(
        self,
        draft: EmailDraft,
        user_request: str,
        modifications: Dict[str, str]
    ) -> Dict[str, str]:
        """Regenerate email content with modifications"""
        
        system_prompt = f"""You are updating an email draft based on user feedback.

Current Email:
To: {draft.to}
Subject: {draft.subject}
Body: {draft.body}

User's Update Request: {user_request}

Requested Modifications: {modifications}

Generate the updated email content as JSON with "subject" and "body" fields."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Update the email as requested."}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            import json
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            updated = json.loads(content)
            return updated
            
        except Exception as e:
            logging.error(f"Failed to regenerate content: {e}")
            return {'body': draft.body, 'subject': draft.subject}


# Global instance
email_drafter = EmailDrafter()
