"""
Enhanced Notes Agent with intelligent categorization and cross-referencing
"""
import json
import os
from typing import Dict, Any, List
from openai import AsyncAzureOpenAI

from mock_graph_api import EnhancedMockGraphAPI


class EnhancedNotesAgent:
    def __init__(self):
        # Use Azure OpenAI like other agents
        from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        
        self.llm = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment_name = AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        self.system_message = "You are an enhanced Notes Agent with intelligent categorization and cross-referencing. Take notes, categorize them, and coordinate with other agents for follow-up actions."
        self.model = self.deployment_name

    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process notes with enhanced structure and collaboration"""
        user_message = state["user_request"]
        context = state.get("context", {})
        conversation_history = state.get("conversation_history", [])

        # Enhanced note processing with conversation context
        history_text = "\n".join(conversation_history) if conversation_history else "No previous conversation."
        note_prompt = f"""
        Create a comprehensive note from: '{user_message}'
        Context from other agents: {context}
        Recent conversation history: {history_text}

        Consider the conversation context when creating the note - it might be a follow-up, clarification, or related to previous discussions.
        """

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": note_prompt}
            ]
        )
        response_text = response.choices[0].message.content

        try:
            # Save note
            result = await EnhancedMockGraphAPI.save_note(
                title="Note",
                content=user_message,
                category="General"
            )

            return {
                "status": "success",
                "result": result,
                "message": "Note saved successfully",
                "collaboration_data": {}
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing note request: {str(e)}",
                "collaboration_data": {}
            }
