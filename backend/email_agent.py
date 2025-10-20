"""
Enhanced Email Agent with collaboration capabilities
"""
import json
import os
from typing import Dict, Any
from openai import OpenAI

from .mock_graph_api import EnhancedMockGraphAPI


class EnhancedEmailAgent:
    def __init__(self):
        self.llm = OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY')
        )
        self.system_message = "You are an enhanced Email Agent with collaboration capabilities. Extract email details, meeting information, and coordinate with other agents for complex workflows."
        self.model = "gpt-4"

    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process email requests with enhanced collaboration capabilities"""
        user_message = state["user_request"]
        context = state.get("context", {})

        # Enhanced email processing with meeting integration
        extraction_prompt = f"""
        Analyze this request for email and meeting coordination: '{user_message}'
        Context from other agents: {context}

        Extract and return JSON with:
        {{
            "email_details": {{"to": "email", "subject": "subject", "body": "body"}},
            "meeting_required": true/false,
            "meeting_details": {{"title": "meeting title", "duration": "30 minutes", "agenda": "meeting agenda"}},
            "collaboration_needed": ["agent_names"],
            "priority": "high/medium/low"
        }}
        """

        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": extraction_prompt}
            ]
        )
        response_text = response.choices[0].message.content

        try:
            parsed_response = json.loads(response_text)
            email_details = parsed_response.get("email_details", {})
            meeting_details = parsed_response.get("meeting_details") if parsed_response.get("meeting_required") else None

            # Send enhanced email with optional meeting invite
            result = await EnhancedMockGraphAPI.send_email_with_invite(
                to=email_details.get("to", "unknown@example.com"),
                subject=email_details.get("subject", "Meeting Request"),
                body=email_details.get("body", "Let's schedule a meeting."),
                meeting_details=meeting_details
            )

            return {
                "status": "success",
                "result": result,
                "message": f"✅ Enhanced email sent to {result['to']} with subject '{result['subject']}'" +
                          (f" including meeting invite for {meeting_details.get('title', 'meeting')}" if meeting_details else ""),
                "collaboration_data": {
                    "meeting_required": parsed_response.get("meeting_required", False),
                    "meeting_details": meeting_details,
                    "next_agents": parsed_response.get("collaboration_needed", [])
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error processing enhanced email request: {str(e)}",
                "collaboration_data": {}
            }