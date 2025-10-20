"""
Enhanced Multi-Agent Orchestrator for collaborative workflows
"""
from typing import Dict, Any

from .email_agent import EnhancedEmailAgent
from .calendar_agent import EnhancedCalendarAgent
from .notes_agent import EnhancedNotesAgent
from .file_summarizer_agent import EnhancedFileSummarizerAgent


class MultiAgentOrchestrator:
    def __init__(self):
        self.email_agent = EnhancedEmailAgent()
        self.calendar_agent = EnhancedCalendarAgent()
        self.notes_agent = EnhancedNotesAgent()
        self.file_agent = EnhancedFileSummarizerAgent()

    async def route_request(self, user_request: str) -> Dict[str, Any]:
        """Enhanced routing with multi-agent workflow detection"""
        message = user_request.lower()

        # Multi-agent workflow detection
        if any(word in message for word in ["meeting", "schedule", "invite"]) and any(word in message for word in ["email", "send", "notify"]):
            return {"workflow_type": "meeting_coordination", "agents": ["email", "calendar", "notes"]}
        elif any(word in message for word in ["document", "file", "analyze"]) and any(word in message for word in ["summarize", "notes", "save"]):
            return {"workflow_type": "document_workflow", "agents": ["file", "notes"]}
        elif any(word in message for word in ["email"]):
            return {"workflow_type": "email_task", "agents": ["email"]}
        elif any(word in message for word in ["calendar", "schedule"]):
            return {"workflow_type": "calendar_task", "agents": ["calendar"]}
        elif any(word in message for word in ["note", "remember"]):
            return {"workflow_type": "notes_task", "agents": ["notes"]}
        else:
            return {"workflow_type": "general", "agents": ["general"]}

    async def meeting_coordination_workflow(self, user_request: str, session_id: str) -> Dict[str, Any]:
        """Enhanced workflow: Email + Calendar + Notes coordination"""
        results = {}
        agents_used = []

        # Step 1: Process with Email Agent
        state = {
            "user_request": user_request,
            "context": {},
            "results": {}
        }

        email_result = await self.email_agent.process_request(state)
        results["email"] = email_result
        agents_used.append("email_agent")

        # Step 2: If meeting required, process with Calendar Agent
        if email_result.get("collaboration_data", {}).get("meeting_required"):
            state["context"]["email_agent"] = email_result.get("collaboration_data", {})
            calendar_result = await self.calendar_agent.process_request(state)
            results["calendar"] = calendar_result
            agents_used.append("calendar_agent")

            # Step 3: Create meeting notes template
            state["context"]["calendar_agent"] = calendar_result.get("collaboration_data", {})
            state["user_request"] = f"Create meeting notes template for the scheduled meeting"
            notes_result = await self.notes_agent.process_request(state)
            results["notes"] = notes_result
            agents_used.append("notes_agent")

        # Compile collaborative response
        response_parts = []
        for agent, result in results.items():
            if result.get("message"):
                response_parts.append(result["message"])

        return {
            "response": "\n\n".join(response_parts) if response_parts else "✅ Multi-agent workflow completed successfully!",
            "agent_used": "enhanced_multi_agent",
            "workflow_type": "meeting_coordination",
            "agents_involved": agents_used,
            "collaboration_data": results
        }

    async def document_workflow(self, user_request: str, session_id: str, file_content: str = None) -> Dict[str, Any]:
        """Enhanced workflow: File Analysis + Notes collaboration"""
        results = {}
        agents_used = []

        # Step 1: Process with File Agent
        state = {
            "user_request": user_request,
            "context": {},
            "results": {}
        }

        file_result = await self.file_agent.process_request(state, file_content or user_request)
        results["file_analysis"] = file_result
        agents_used.append("file_summarizer_agent")

        # Step 2: Create structured notes from analysis
        if file_result.get("status") == "success":
            state["context"]["file_agent"] = file_result.get("collaboration_data", {})
            analysis = file_result.get("collaboration_data", {}).get("analysis", {})
            state["user_request"] = f"Save analysis notes: {analysis.get('summary', 'Document analysis completed')}"
            notes_result = await self.notes_agent.process_request(state)
            results["notes"] = notes_result
            agents_used.append("notes_agent")

        # Compile collaborative response
        response_parts = []
        for agent, result in results.items():
            if result.get("message"):
                response_parts.append(result["message"])

        return {
            "response": "\n\n".join(response_parts) if response_parts else "✅ Document workflow completed successfully!",
            "agent_used": "enhanced_multi_agent",
            "workflow_type": "document_workflow",
            "agents_involved": agents_used,
            "collaboration_data": results
        }

    async def process_request(self, user_request: str, session_id: str) -> Dict[str, Any]:
        """Process user request through enhanced multi-agent workflow"""

        try:
            # Route the request
            routing_info = await self.route_request(user_request)
            workflow_type = routing_info["workflow_type"]

            # Execute appropriate workflow
            if workflow_type == "meeting_coordination":
                return await self.meeting_coordination_workflow(user_request, session_id)
            elif workflow_type == "document_workflow":
                return await self.document_workflow(user_request, session_id)
            elif workflow_type == "email_task":
                state = {"user_request": user_request, "context": {}, "results": {}}
                result = await self.email_agent.process_request(state)
                return {
                    "response": result.get("message", "Email task completed"),
                    "agent_used": "email_agent",
                    "workflow_type": "email_task",
                    "agents_involved": ["email_agent"],
                    "collaboration_data": result.get("collaboration_data", {})
                }
            elif workflow_type == "calendar_task":
                state = {"user_request": user_request, "context": {}, "results": {}}
                result = await self.calendar_agent.process_request(state)
                return {
                    "response": result.get("message", "Calendar task completed"),
                    "agent_used": "calendar_agent",
                    "workflow_type": "calendar_task",
                    "agents_involved": ["calendar_agent"],
                    "collaboration_data": result.get("collaboration_data", {})
                }
            elif workflow_type == "notes_task":
                state = {"user_request": user_request, "context": {}, "results": {}}
                result = await self.notes_agent.process_request(state)
                return {
                    "response": result.get("message", "Notes task completed"),
                    "agent_used": "notes_agent",
                    "workflow_type": "notes_task",
                    "agents_involved": ["notes_agent"],
                    "collaboration_data": result.get("collaboration_data", {})
                }
            else:
                # General help
                return {
                    "response": "🚀 Hello! I'm your enhanced AI Agents assistant with advanced collaboration capabilities!\n\n🔗 **Multi-Agent Collaboration Features:**\n\n📧 **Smart Email Agent** - Send emails with meeting invites\n📅 **Intelligent Calendar Agent** - Advanced scheduling with attendee management\n📝 **Enhanced Notes Agent** - Smart categorization and cross-referencing\n📄 **Advanced File Analyzer** - Deep insights with workflow recommendations\n\n⚡ **Enhanced Workflows Available:**\n• \"Schedule a meeting with John about project review and send him an invite\"\n• \"Analyze this document and save the key points to my notes\"\n• \"Create a team meeting, invite everyone, and prepare meeting notes\"\n\nWhat enhanced workflow would you like me to help with?",
                    "agent_used": "enhanced_orchestrator",
                    "workflow_type": "general",
                    "agents_involved": [],
                    "collaboration_data": {}
                }

        except Exception as e:
            return {
                "response": f"❌ Enhanced orchestration error: {str(e)}",
                "agent_used": "error_handler",
                "workflow_type": "error",
                "agents_involved": [],
                "collaboration_data": {}
            }