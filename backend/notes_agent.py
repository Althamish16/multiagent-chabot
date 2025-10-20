"""
Enhanced Notes Agent with intelligent categorization and cross-referencing
"""
import json
import os
from typing import Dict, Any, List
from openai import OpenAI

from .mock_graph_api import EnhancedMockGraphAPI


class EnhancedNotesAgent:
    def __init__(self):
        self.llm = OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY')
        )
        self.system_message = "You are an enhanced Notes Agent with intelligent categorization and cross-referencing capabilities. Create structured notes with tags, categories, and relationships to other agents' data."
        self.model = "gpt-4"

    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process notes with enhanced structure and collaboration"""
        user_message = state["user_request"]
        context = state.get("context", {})

        # Enhanced note processing with AI categorization
        processing_prompt = f"""
        Analyze this for intelligent note creation: '{user_message}'
        Context from other agents: {context}

        Extract and return JSON with:
        {{
            "note_details": {{"title": "smart title", "content": "structured content", "category": "intelligent category"}},
            "tags": ["tag1", "tag2"],
            "related_items": {{"meetings": ["event_ids"], "emails": ["email_ids"], "files": ["file_names"]}},
            "action_items": ["item1", "item2"],
            "collaboration_data": {{"linked_agents": ["agent_names"]}}
        }}
        """

        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": processing_prompt}
            ]
        )
        response_text = response.choices[0].message.content

        try:
            parsed_response = json.loads(response_text)
            note_details = parsed_response.get("note_details", {})

            # Add context from other agents to related items
            related_items = parsed_response.get("related_items", {})
            if context:
                if context.get("calendar_agent", {}).get("event_id"):
                    related_items.setdefault("meetings", []).append(context["calendar_agent"]["event_id"])
                if context.get("email_agent", {}).get("email_id"):
                    related_items.setdefault("emails", []).append(context["email_agent"]["email_id"])

            result = await EnhancedMockGraphAPI.save_structured_note(
                title=note_details.get("title", "Smart Note"),
                content=note_details.get("content", user_message),
                category=note_details.get("category", "AI Generated"),
                tags=parsed_response.get("tags", []),
                related_items=related_items
            )

            return {
                "status": "success",
                "result": result,
                "message": f"📝 Enhanced note '{result['title']}' created with smart categorization and {len(result['tags'])} tags",
                "collaboration_data": {
                    "note_id": result["id"],
                    "action_items": parsed_response.get("action_items", []),
                    "linked_data": related_items
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error in enhanced note processing: {str(e)}",
                "collaboration_data": {}
            }