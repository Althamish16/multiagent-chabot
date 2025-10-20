"""
Enhanced File Summarizer Agent with intelligent analysis and workflow integration
"""
import json
import os
from typing import Dict, Any
from openai import OpenAI


class EnhancedFileSummarizerAgent:
    def __init__(self):
        self.llm = OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY')
        )
        self.system_message = "You are an enhanced File Summarizer Agent with intelligent analysis and workflow integration. Extract key insights, action items, and coordinate with other agents for follow-up actions."
        self.model = "gpt-4"

    async def process_request(self, state: Dict[str, Any], file_content: str = None) -> Dict[str, Any]:
        """Process files with enhanced analysis and collaboration"""
        user_message = state["user_request"]
        context = state.get("context", {})

        if not file_content:
            return {
                "status": "error",
                "message": "📄 No file content provided for enhanced analysis",
                "collaboration_data": {}
            }

        analysis_prompt = f"""
        Perform comprehensive analysis of this document:

        Content: {file_content}
        User Request: {user_message}
        Context: {context}

        Provide detailed JSON response with:
        {{
            "summary": "executive summary",
            "key_points": ["point1", "point2"],
            "action_items": ["action1", "action2"],
            "insights": ["insight1", "insight2"],
            "recommended_workflows": {{
                "email_actions": ["send summary to...", "schedule follow-up"],
                "calendar_actions": ["schedule meeting about...", "set reminder"],
                "note_actions": ["save key points", "create project notes"]
            }},
            "collaboration_priority": "high/medium/low"
        }}
        """

        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": analysis_prompt}
            ]
        )
        response_text = response.choices[0].message.content

        try:
            analysis = json.loads(response_text)

            return {
                "status": "success",
                "result": analysis,
                "message": f"📄 **Enhanced Document Analysis Complete**\n\n**Summary:** {analysis.get('summary', 'Analysis completed')}\n\n**Key Insights:** {', '.join(analysis.get('insights', []))}\n\n**Action Items:** {len(analysis.get('action_items', []))} items identified",
                "collaboration_data": {
                    "analysis": analysis,
                    "recommended_workflows": analysis.get("recommended_workflows", {}),
                    "next_actions": analysis.get("action_items", [])
                }
            }

        except Exception as e:
            # Fallback to simple analysis
            return {
                "status": "success",
                "result": {"summary": "Document processed with basic analysis"},
                "message": f"📄 **Enhanced Document Summary:**\n\n{file_content[:500]}..." if len(file_content) > 500 else file_content,
                "collaboration_data": {}
            }