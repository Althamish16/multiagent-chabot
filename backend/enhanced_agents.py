"""
Enhanced AI Agents for Multi-Agent Collaboration
"""
from typing import Dict, Any, List, Optional, TypedDict

from mock_graph_api import EnhancedMockGraphAPI
from email_agent import SecureEmailAgent
from calendar_agent import EnhancedCalendarAgent
from notes_agent import EnhancedNotesAgent
from file_summarizer_agent import EnhancedFileSummarizerAgent
from dynamic_orchestrator import DynamicMultiAgentOrchestrator

# Enhanced State Management for Agent Collaboration
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    current_task: str
    context: Dict[str, Any]
    active_agents: List[str]
    workflow_type: str
    user_request: str
    results: Dict[str, Any]
    next_action: Optional[str]