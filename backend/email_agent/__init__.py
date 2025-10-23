"""
Email Agent Module
Secure AI-powered email drafting and sending with human-in-the-loop approval
"""
from .email_drafter import EmailDrafter, email_drafter
from .approval_workflow import ApprovalWorkflow, approval_workflow
from .gmail_connector import GmailConnector, gmail_connector
from .draft_storage import DraftStorage, draft_storage
from .safety_guard import SafetyGuard, safety_guard
from .send_worker import SendWorker, send_worker
from .enhanced_email_agent import EnhancedEmailAgent, enhanced_email_agent
from .models import (
    EmailDraft,
    DraftStatus,
    ApprovalRequest,
    ApprovalDecision,
    SendResult,
    EmailTone,
    EmailPriority,
    SafetyCheckResult,
    EmailAgentState
)

__all__ = [
    'EmailDrafter',
    'email_drafter',
    'ApprovalWorkflow',
    'approval_workflow',
    'GmailConnector',
    'gmail_connector',
    'DraftStorage',
    'draft_storage',
    'SafetyGuard',
    'safety_guard',
    'SendWorker',
    'send_worker',
    'EnhancedEmailAgent',
    'enhanced_email_agent',
    'EmailDraft',
    'DraftStatus',
    'ApprovalRequest',
    'ApprovalDecision',
    'SendResult',
    'EmailTone',
    'EmailPriority',
    'SafetyCheckResult',
    'EmailAgentState'
]
