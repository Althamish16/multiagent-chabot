"""
Data models for Email Agent
Pydantic schemas for email drafts, approvals, and workflow states
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from enum import Enum
import uuid


class EmailTone(str, Enum):
    """Email tone options"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CASUAL = "casual"


class EmailPriority(str, Enum):
    """Email priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DraftStatus(str, Enum):
    """Email draft lifecycle states"""
    DRAFTED = "drafted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"


class EmailDraft(BaseModel):
    """Email draft model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: Optional[str] = None
    to: str  # Primary recipient
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    subject: str
    body: str
    tone: EmailTone = EmailTone.PROFESSIONAL
    priority: EmailPriority = EmailPriority.MEDIUM
    status: DraftStatus = DraftStatus.DRAFTED
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    
    # Context
    conversation_context: Optional[List[str]] = None
    ai_reasoning: Optional[str] = None
    safety_checks: Optional[Dict[str, Any]] = None
    
    # Gmail integration
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @validator('to', 'cc', 'bcc')
    def validate_emails(cls, v):
        """Basic email validation"""
        if v is None:
            return v
        if isinstance(v, str):
            # Basic check for @ symbol
            if '@' not in v:
                raise ValueError(f"Invalid email format: {v}")
            return v
        # For lists
        for email in v:
            if '@' not in email:
                raise ValueError(f"Invalid email format: {email}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        data = self.dict()
        # Convert datetime objects to ISO strings
        for key in ['created_at', 'updated_at', 'approved_at', 'sent_at']:
            if data.get(key):
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailDraft':
        """Create from dictionary (JSON deserialization)"""
        # Convert ISO strings back to datetime
        for key in ['created_at', 'updated_at', 'approved_at', 'sent_at']:
            if data.get(key) and isinstance(data[key], str):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except ValueError:
                    pass
        return cls(**data)


class ApprovalRequest(BaseModel):
    """Request for human approval of email draft"""
    draft_id: str
    user_id: str
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    notification_sent: bool = False


class ApprovalDecision(BaseModel):
    """Human decision on email draft approval"""
    draft_id: str
    user_id: str
    approved: bool
    feedback: Optional[str] = None
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    modifications_requested: Optional[Dict[str, str]] = None  # Field -> new value


class SendResult(BaseModel):
    """Result of email send operation"""
    draft_id: str
    success: bool
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    retry_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SafetyCheckResult(BaseModel):
    """Result of safety policy checks"""
    passed: bool
    checks: Dict[str, bool] = {}  # check_name -> passed
    flags: List[str] = []  # Issues found
    risk_level: str = "low"  # low, medium, high
    recommendations: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return self.dict()


class EmailAgentState(BaseModel):
    """State for email agent in orchestrator"""
    draft_id: Optional[str] = None
    action: Optional[str] = None  # "draft", "approve", "send", "list", "read"
    user_request: str
    session_id: str
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    
    # Draft creation inputs
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body_intent: Optional[str] = None
    tone: Optional[EmailTone] = None
    
    # Results
    draft: Optional[EmailDraft] = None
    send_result: Optional[SendResult] = None
    emails: Optional[List[Dict[str, Any]]] = None  # For list/read operations
    error: Optional[str] = None
    
    class Config:
        use_enum_values = True


class EmailMessage(BaseModel):
    """Received email message from Gmail"""
    id: str  # Gmail message ID
    thread_id: str  # Gmail thread ID
    from_address: str = Field(alias="from")
    to: str
    cc: Optional[str] = None
    subject: str
    date: str
    snippet: str  # Short preview
    body: str  # Full body content
    labels: Optional[List[str]] = None
    is_unread: bool = False
    
    class Config:
        populate_by_name = True


class EmailListRequest(BaseModel):
    """Request to list emails from inbox"""
    max_results: int = Field(default=10, ge=1, le=100)
    query: Optional[str] = None  # Gmail search query (e.g., "is:unread", "from:example@gmail.com")
    label_ids: Optional[List[str]] = None  # Default: ['INBOX']
    include_spam_trash: bool = False


class EmailListResponse(BaseModel):
    """Response containing list of emails"""
    emails: List[EmailMessage]
    total_count: int
    next_page_token: Optional[str] = None
