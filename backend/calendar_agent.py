"""
Enhanced Calendar Agent with coordination capabilities
"""
import json
import os
from typing import Dict, Any, List
from openai import AsyncAzureOpenAI

from mock_graph_api import EnhancedMockGraphAPI


class EnhancedCalendarAgent:
    def __init__(self):
        # Use Azure OpenAI like other agents
        from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        
        self.llm = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment_name = AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        self.system_message = "You are an enhanced Calendar Agent with coordination capabilities. Schedule meetings, manage attendees, and collaborate with notes agents."
        self.model = self.deployment_name

    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process calendar requests with enhanced collaboration"""
        user_message = state["user_request"]
        context = state.get("context", {})
        conversation_history = state.get("conversation_history", [])

        # Regular calendar processing with AI enhancement
        history_text = "\n".join(conversation_history) if conversation_history else "No previous conversation."
        extraction_prompt = f"""
        Extract meeting details from: '{user_message}'
        Context from other agents: {context}
        Recent conversation history: {history_text}

        Return JSON with:
        {{
            "action": "create/view",
            "event_details": {{"title": "title", "start_date": "ISO date", "end_date": "ISO date", "description": "desc"}},
            "attendees": ["email1", "email2"],
            "collaboration_needed": ["agent_names"]
        }}
        """

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": extraction_prompt}
            ]
        )
        response_text = response.choices[0].message.content

        try:
            parsed_response = json.loads(response_text)

            if parsed_response.get("action") == "create":
                event_details = parsed_response.get("event_details", {})
                attendees = parsed_response.get("attendees", [])

                result = await EnhancedMockGraphAPI.create_calendar_event_with_attendees(
                    title=event_details.get("title", "New Meeting"),
                    start_date=event_details.get("start_date", "2024-01-16T10:00:00Z"),
                    end_date=event_details.get("end_date", "2024-01-16T11:00:00Z"),
                    description=event_details.get("description", ""),
                    attendees=attendees
                )

                return {
                    "status": "success",
                    "result": result,
                    "message": f"📅 Enhanced meeting '{result['title']}' created with {len(attendees)} attendees",
                    "collaboration_data": {
                        "meeting_link": result["meeting_link"],
                        "event_id": result["id"],
                        "next_agents": parsed_response.get("collaboration_needed", [])
                    }
                }
            else:
                # View calendar functionality
                events = await EnhancedMockGraphAPI.get_calendar_events()
                return {
                    "status": "success",
                    "result": {"events": events},
                    "message": "📅 Your enhanced calendar view with smart insights",
                    "collaboration_data": {}
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error in enhanced calendar processing: {str(e)}",
                "collaboration_data": {}
            }