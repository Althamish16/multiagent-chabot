"""
Secure Email Agent with human-in-the-loop approval
AI drafts emails, but only sends after user confirmation
"""
import json
import os
from typing import Dict, Any, Optional
from openai import AsyncAzureOpenAI

from google_auth import GoogleAPIClient


class SecureEmailAgent:
    def __init__(self):
        # Use Azure OpenAI like other agents
        from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        
        self.llm = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment_name = AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        self.system_message = "You are a Secure Email Agent. Draft professional emails based on user requests. Return only the email draft - never send emails directly. Always ask for user approval before sending."
        self.model = self.deployment_name

    async def draft_email(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Draft an email based on user request - returns draft for approval"""
        user_message = state["user_request"]
        context = state.get("context", {})
        conversation_history = state.get("conversation_history", [])

        # Enhanced email drafting with context awareness
        history_text = "\n".join(conversation_history) if conversation_history else "No previous conversation."
        draft_prompt = f"""
        Draft a professional email based on this request: '{user_message}'
        Context from other agents: {context}
        Recent conversation history: {history_text}

        Return JSON with:
        {{
            "to": "recipient@example.com",
            "subject": "Clear, concise subject line",
            "body": "Professional email body with proper greeting, content, and sign-off",
            "tone": "professional/friendly/formal",
            "priority": "high/medium/low"
        }}

        Guidelines:
        - Keep subject under 50 characters
        - Use professional language
        - Include appropriate greeting and sign-off
        - Make the email clear and actionable
        - Consider the conversation history for context and personalization
        """

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": draft_prompt}
            ]
        )
        response_text = response.choices[0].message.content

        try:
            draft = json.loads(response_text)

            return {
                "status": "draft_ready",
                "draft": draft,
                "message": f"📧 Email draft ready for review:\n\n**To:** {draft.get('to', 'N/A')}\n**Subject:** {draft.get('subject', 'N/A')}\n**Body:**\n{draft.get('body', 'N/A')}\n\nPlease confirm to send this email.",
                "requires_approval": True
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error drafting email: {str(e)}",
                "requires_approval": False
            }

    async def send_email(self, draft: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Send email after user approval using secure backend"""
        try:
            # Initialize Google API client with user's access token
            google_client = GoogleAPIClient(access_token)

            # Send email via Gmail API
            result = await google_client.send_email(
                to=draft["to"],
                subject=draft["subject"],
                body=draft["body"]
            )

            return {
                "status": "success",
                "result": result,
                "message": f"✅ Email sent successfully to {result['to']} with subject '{result['subject']}'",
                "email_id": result["id"]
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Failed to send email: {str(e)}"
            }

    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method - handles both drafting and sending"""
        action = state.get("action", "draft")

        if action == "draft":
            return await self.draft_email(state)
        elif action == "send":
            draft = state.get("draft")
            access_token = state.get("access_token")

            if not draft or not access_token:
                return {
                    "status": "error",
                    "message": "❌ Missing draft or access token for sending"
                }

            return await self.send_email(draft, access_token)
        else:
            return {
                "status": "error",
                "message": f"❌ Unknown action: {action}"
            }