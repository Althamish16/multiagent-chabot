"""
General Purpose Agent for Tasks, Q&A, and Planning
"""
from typing import Dict, Any, List
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
import logging
from config import (
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)


class GeneralTaskAgent:
    """Agent for handling general tasks, Q&A, and planning"""

    def __init__(self):
        try:
            self.llm = AzureChatOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                azure_deployment=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                api_version=AZURE_OPENAI_API_VERSION,
                api_key=AZURE_OPENAI_API_KEY,
                temperature=0.3,
                timeout=60,  # 60 second timeout
                max_retries=2
            )
            logging.info("GeneralTaskAgent initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize GeneralTaskAgent: {str(e)}")
            raise

    async def process_request(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """Process general tasks, questions, and planning requests"""
        try:
            user_request = agent_state.get("user_request", "")
            conversation_history = agent_state.get("conversation_history", [])
            context = agent_state.get("context", {})

            logging.info(f"General agent processing: {user_request}")

            # Determine the type of request
            request_type = self._classify_request(user_request)
            logging.info(f"Classified as: {request_type}")

            if request_type == "task_management":
                logging.info("Routing to task management handler")
                return await self._handle_task_management(user_request, conversation_history)
            elif request_type == "question_answer":
                logging.info("Routing to question answer handler")
                return await self._handle_question_answer(user_request, conversation_history, context)
            elif request_type == "planning":
                logging.info("Routing to planning handler")
                return await self._handle_planning(user_request, conversation_history)
            else:
                logging.info("Routing to general assistance handler")
                return await self._handle_general_assistance(user_request, conversation_history)
        
        except Exception as e:
            logging.error(f"General agent error: {str(e)}")
            return {
                "status": "error",
                "result": {},
                "message": f"❌ General agent failed: {str(e)}",
                "collaboration_data": {
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
            }

    def _classify_request(self, user_request: str) -> str:
        """Classify the type of request"""
        request_lower = user_request.lower()

        # Task management keywords
        task_keywords = [
            "task", "todo", "to-do", "reminder", "schedule", "deadline", "complete",
            "finish", "done", "add task", "create task", "manage tasks"
        ]

        # Planning keywords
        planning_keywords = [
            "plan", "planning", "goal", "strategy", "roadmap", "timeline",
            "project plan", "organize", "structure", "break down"
        ]

        # Question keywords
        question_keywords = [
            "what", "how", "why", "when", "where", "who", "explain", "tell me",
            "help me understand", "can you", "do you know"
        ]

        if any(keyword in request_lower for keyword in task_keywords):
            return "task_management"
        elif any(keyword in request_lower for keyword in planning_keywords):
            return "planning"
        elif any(keyword in request_lower for keyword in question_keywords) or user_request.endswith("?"):
            return "question_answer"
        else:
            return "general_assistance"

    async def _handle_task_management(self, user_request: str, conversation_history: List[str]) -> Dict[str, Any]:
        """Handle task creation, management, and tracking"""
        try:
            logging.info("Starting task management handler")
            task_prompt = ChatPromptTemplate.from_template("""
            You are a task management assistant. Help the user organize and track their tasks.

            Current date: {current_date}
            User request: {user_request}

            Recent conversation:
            {conversation_history}

            Analyze the request and provide:
            1. Task identification and categorization
            2. Priority assessment (high/medium/low)
            3. Suggested deadlines if not specified
            4. Action items or subtasks
            5. Any dependencies or prerequisites

            Format your response as a structured task list with clear priorities and timelines.
            Be proactive in suggesting task breakdowns for complex requests.
            """)

            chain = task_prompt | self.llm
            logging.info("Invoking LLM for task management response")
            
            response = await chain.ainvoke({
                "user_request": user_request,
                "conversation_history": "\n".join(conversation_history[-5:]) if conversation_history else "No previous conversation",
                "current_date": datetime.now().strftime("%Y-%m-%d")
            })
            
            logging.info("LLM response received for task management")

            return {
                "status": "success",
                "result": {
                    "task_analysis": response.content,
                    "request_type": "task_management"
                },
                "message": f"📋 **Task Management**\n\n{response.content}",
                "collaboration_data": {
                    "task_type": "general_task",
                    "created_at": datetime.now().isoformat(),
                    "priority_suggestions": True
                }
            }
        except Exception as e:
            logging.error(f"Task management handler error: {str(e)}")
            return {
                "status": "error",
                "result": {},
                "message": f"❌ Task management failed: {str(e)}",
                "collaboration_data": {
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
            }

    async def _handle_question_answer(self, user_request: str, conversation_history: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general questions and provide answers"""
        try:
            logging.info("Starting question answer handler")
            qa_prompt = ChatPromptTemplate.from_template("""
            You are a knowledgeable assistant that provides clear, accurate answers to questions.
            Use the conversation context and any available information to give comprehensive responses.

            Current date: {current_date}
            User question: {user_request}

            Recent conversation context:
            {conversation_history}

            Available context from other agents:
            {context}

            Provide a clear, well-structured answer that:
            1. Directly addresses the question
            2. Uses available context when relevant
            3. Breaks down complex topics into understandable parts
            4. Offers additional relevant information when helpful
            5. Suggests follow-up questions or actions if appropriate

            Keep responses conversational but informative.
            """)

            chain = qa_prompt | self.llm
            logging.info("Invoking LLM for Q&A response")
            
            response = await chain.ainvoke({
                "user_request": user_request,
                "conversation_history": "\n".join(conversation_history[-5:]) if conversation_history else "No previous conversation",
                "context": str(context) if context else "No additional context available",
                "current_date": datetime.now().strftime("%Y-%m-%d")
            })
            
            logging.info("LLM response received for Q&A")

            return {
                "status": "success",
                "result": {
                    "answer": response.content,
                    "request_type": "question_answer"
                },
                "message": f"🤔 **Question & Answer**\n\n{response.content}",
                "collaboration_data": {
                    "qa_type": "general_knowledge",
                    "answered_at": datetime.now().isoformat(),
                    "context_used": bool(context)
                }
            }
        except Exception as e:
            logging.error(f"Q&A handler error: {str(e)}")
            return {
                "status": "error",
                "result": {},
                "message": f"❌ Q&A failed: {str(e)}",
                "collaboration_data": {
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
            }

    async def _handle_planning(self, user_request: str, conversation_history: List[str]) -> Dict[str, Any]:
        """Handle planning requests including project planning and goal setting"""
        try:
            logging.info("Starting planning handler")
            planning_prompt = ChatPromptTemplate.from_template("""
            You are a planning specialist. Help users create structured plans for projects, goals, and activities.

            Current date: {current_date}
            Planning request: {user_request}

            Recent conversation:
            {conversation_history}

            Create a comprehensive plan that includes:
            1. Clear objectives and goals
            2. Step-by-step action plan
            3. Timeline with milestones
            4. Required resources or prerequisites
            5. Potential challenges and mitigation strategies
            6. Success metrics or completion criteria
            7. Regular check-in points

            Structure the plan clearly with phases, timelines, and actionable steps.
            Make the plan realistic and achievable.
            """)

            chain = planning_prompt | self.llm
            logging.info("Invoking LLM for planning response")
            
            response = await chain.ainvoke({
                "user_request": user_request,
                "conversation_history": "\n".join(conversation_history[-5:]) if conversation_history else "No previous conversation",
                "current_date": datetime.now().strftime("%Y-%m-%d")
            })
            
            logging.info("LLM response received for planning")

            return {
                "status": "success",
                "result": {
                    "plan": response.content,
                    "request_type": "planning"
                },
                "message": f"📅 **Planning & Strategy**\n\n{response.content}",
                "collaboration_data": {
                    "plan_type": "structured_plan",
                    "created_at": datetime.now().isoformat(),
                    "includes_timeline": True,
                    "includes_milestones": True
                }
            }
        except Exception as e:
            logging.error(f"Planning handler error: {str(e)}")
            return {
                "status": "error",
                "result": {},
                "message": f"❌ Planning failed: {str(e)}",
                "collaboration_data": {
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
            }

    async def _handle_general_assistance(self, user_request: str, conversation_history: List[str]) -> Dict[str, Any]:
        """Handle general assistance requests that don't fit other categories"""
        try:
            logging.info("Starting general assistance handler")
            general_prompt = ChatPromptTemplate.from_template("""
            You are a helpful general assistant. Provide useful, actionable responses to user requests.

            Current date: {current_date}
            User request: {user_request}

            Recent conversation:
            {conversation_history}

            Provide helpful assistance that:
            1. Understands the user's intent
            2. Offers practical advice or solutions
            3. Suggests next steps or related actions
            4. Uses conversation context appropriately
            5. Maintains a supportive, professional tone

            Focus on being genuinely helpful and proactive.
            """)

            chain = general_prompt | self.llm
            logging.info("Invoking LLM for general assistance response")
            
            response = await chain.ainvoke({
                "user_request": user_request,
                "conversation_history": "\n".join(conversation_history[-5:]) if conversation_history else "No previous conversation",
                "current_date": datetime.now().strftime("%Y-%m-%d")
            })
            
            logging.info("LLM response received for general assistance")

            return {
                "status": "success",
                "result": {
                    "assistance": response.content,
                    "request_type": "general_assistance"
                },
                "message": f"💡 **General Assistance**\n\n{response.content}",
                "collaboration_data": {
                    "assistance_type": "general_help",
                    "provided_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logging.error(f"General assistance handler error: {str(e)}")
            return {
                "status": "error",
                "result": {},
                "message": f"❌ General assistance failed: {str(e)}",
                "collaboration_data": {
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
            }