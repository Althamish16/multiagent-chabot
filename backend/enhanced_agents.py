"""
Enhanced AI Agents with LangGraph Integration for Multi-Agent Collaboration
"""
from typing import Dict, Any, List, Optional, TypedDict

from langchain_core.messages import BaseMessage

from .mock_graph_api import EnhancedMockGraphAPI
from .email_agent import EnhancedEmailAgent
from .calendar_agent import EnhancedCalendarAgent
from .notes_agent import EnhancedNotesAgent
from .file_summarizer_agent import EnhancedFileSummarizerAgent
from .multi_agent_orchestrator import MultiAgentOrchestrator

# Enhanced State Management for Agent Collaboration
class AgentState(TypedDict):
    messages: List[BaseMessage]
    current_task: str
    context: Dict[str, Any]
    active_agents: List[str]
    workflow_type: str
    user_request: str
    results: Dict[str, Any]
    next_action: Optional[str]