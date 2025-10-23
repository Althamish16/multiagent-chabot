"""
Email Safety Guard
Policy checks for email content before sending
"""
from typing import Dict, Any, List
import re
import logging

from .models import EmailDraft, SafetyCheckResult


class SafetyGuard:
    """Performs safety and policy checks on email drafts"""
    
    # Sensitive patterns to flag
    SENSITIVE_PATTERNS = {
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        'password': r'\b(password|pwd|passwd)[\s:=]+[\w!@#$%^&*]+',
    }
    
    # Toxic language indicators (basic)
    TOXIC_KEYWORDS = [
        'hate', 'kill', 'die', 'stupid', 'idiot', 'moron',
        'damn', 'hell', 'crap', 'shut up'
    ]
    
    # Blocklisted domains/recipients
    BLOCKED_DOMAINS = [
        'example.com',
        'test.com',
        'spam.com'
    ]
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        logging.info(f"SafetyGuard initialized (strict_mode={strict_mode})")
    
    async def check_draft(self, draft: EmailDraft) -> SafetyCheckResult:
        """Run all safety checks on a draft"""
        checks = {}
        flags = []
        recommendations = []
        
        # 1. PII Detection
        pii_check = self._check_pii(draft)
        checks['pii_check'] = pii_check['passed']
        flags.extend(pii_check['flags'])
        recommendations.extend(pii_check['recommendations'])
        
        # 2. Toxic Content Detection
        toxic_check = self._check_toxic_content(draft)
        checks['toxic_check'] = toxic_check['passed']
        flags.extend(toxic_check['flags'])
        recommendations.extend(toxic_check['recommendations'])
        
        # 3. Recipient Validation
        recipient_check = self._check_recipients(draft)
        checks['recipient_check'] = recipient_check['passed']
        flags.extend(recipient_check['flags'])
        recommendations.extend(recipient_check['recommendations'])
        
        # 4. Content Length Check
        length_check = self._check_content_length(draft)
        checks['length_check'] = length_check['passed']
        flags.extend(length_check['flags'])
        recommendations.extend(length_check['recommendations'])
        
        # 5. Subject Line Check
        subject_check = self._check_subject(draft)
        checks['subject_check'] = subject_check['passed']
        flags.extend(subject_check['flags'])
        recommendations.extend(subject_check['recommendations'])
        
        # Determine overall pass/fail and risk level
        passed = all(checks.values())
        risk_level = self._calculate_risk_level(checks, flags)
        
        result = SafetyCheckResult(
            passed=passed,
            checks=checks,
            flags=flags,
            risk_level=risk_level,
            recommendations=recommendations
        )
        
        logging.info(f"Safety check for draft {draft.id}: passed={passed}, risk={risk_level}, flags={len(flags)}")
        return result
    
    def _check_pii(self, draft: EmailDraft) -> Dict[str, Any]:
        """Check for personally identifiable information"""
        flags = []
        recommendations = []
        combined_text = f"{draft.subject} {draft.body}"
        
        for pii_type, pattern in self.SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                flags.append(f"Potential {pii_type.upper()} detected: {len(matches)} occurrence(s)")
                recommendations.append(f"Review and remove {pii_type.upper()} before sending")
        
        passed = len(flags) == 0 or not self.strict_mode
        return {
            'passed': passed,
            'flags': flags,
            'recommendations': recommendations
        }
    
    def _check_toxic_content(self, draft: EmailDraft) -> Dict[str, Any]:
        """Check for toxic or inappropriate language"""
        flags = []
        recommendations = []
        combined_text = f"{draft.subject} {draft.body}".lower()
        
        found_toxic = [word for word in self.TOXIC_KEYWORDS if word in combined_text]
        
        if found_toxic:
            flags.append(f"Potentially inappropriate language detected: {', '.join(found_toxic[:3])}")
            recommendations.append("Review tone and language for professionalism")
        
        # Check for all caps (shouting)
        if draft.subject.isupper() and len(draft.subject) > 10:
            flags.append("Subject line in ALL CAPS may appear aggressive")
            recommendations.append("Consider using title case for subject")
        
        passed = len(flags) == 0 or not self.strict_mode
        return {
            'passed': passed,
            'flags': flags,
            'recommendations': recommendations
        }
    
    def _check_recipients(self, draft: EmailDraft) -> Dict[str, Any]:
        """Validate recipient email addresses"""
        flags = []
        recommendations = []
        
        # Check main recipient
        if not self._is_valid_email(draft.to):
            flags.append(f"Invalid recipient email: {draft.to}")
            return {'passed': False, 'flags': flags, 'recommendations': ['Provide a valid recipient email']}
        
        # Check for blocked domains
        domain = draft.to.split('@')[-1] if '@' in draft.to else ''
        if domain in self.BLOCKED_DOMAINS:
            flags.append(f"Blocked domain: {domain}")
            recommendations.append(f"Cannot send to {domain} domain")
        
        # Check CC/BCC
        for cc_email in (draft.cc or []):
            if not self._is_valid_email(cc_email):
                flags.append(f"Invalid CC email: {cc_email}")
        
        for bcc_email in (draft.bcc or []):
            if not self._is_valid_email(bcc_email):
                flags.append(f"Invalid BCC email: {bcc_email}")
        
        # Warn if sending to many recipients
        total_recipients = 1 + len(draft.cc or []) + len(draft.bcc or [])
        if total_recipients > 10:
            flags.append(f"Large recipient count: {total_recipients}")
            recommendations.append("Consider using a mailing list for bulk emails")
        
        passed = len([f for f in flags if 'Invalid' in f or 'Blocked' in f]) == 0
        return {
            'passed': passed,
            'flags': flags,
            'recommendations': recommendations
        }
    
    def _check_content_length(self, draft: EmailDraft) -> Dict[str, Any]:
        """Check email content length"""
        flags = []
        recommendations = []
        
        body_length = len(draft.body)
        
        if body_length < 10:
            flags.append("Email body is very short (< 10 characters)")
            recommendations.append("Consider adding more context to your message")
        elif body_length > 5000:
            flags.append("Email body is very long (> 5000 characters)")
            recommendations.append("Consider breaking into multiple emails or attaching a document")
        
        passed = True  # Length warnings don't block sending
        return {
            'passed': passed,
            'flags': flags,
            'recommendations': recommendations
        }
    
    def _check_subject(self, draft: EmailDraft) -> Dict[str, Any]:
        """Check subject line"""
        flags = []
        recommendations = []
        
        if not draft.subject or len(draft.subject.strip()) == 0:
            flags.append("Subject line is empty")
            recommendations.append("Add a descriptive subject line")
            return {'passed': False, 'flags': flags, 'recommendations': recommendations}
        
        if len(draft.subject) < 5:
            flags.append("Subject line is very short")
            recommendations.append("Consider a more descriptive subject")
        elif len(draft.subject) > 100:
            flags.append("Subject line is very long (> 100 characters)")
            recommendations.append("Shorten subject line for better readability")
        
        # Check for spam indicators
        spam_words = ['free', 'click here', 'act now', '$$$', 'winner']
        subject_lower = draft.subject.lower()
        found_spam = [word for word in spam_words if word in subject_lower]
        if found_spam:
            flags.append(f"Subject contains spam-like words: {', '.join(found_spam)}")
            recommendations.append("Avoid spam trigger words in subject")
        
        passed = draft.subject and len(draft.subject.strip()) > 0
        return {
            'passed': passed,
            'flags': flags,
            'recommendations': recommendations
        }
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email format validation"""
        if not email or '@' not in email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _calculate_risk_level(self, checks: Dict[str, bool], flags: List[str]) -> str:
        """Calculate overall risk level"""
        failed_checks = sum(1 for passed in checks.values() if not passed)
        flag_count = len(flags)
        
        if failed_checks >= 2 or flag_count >= 5:
            return "high"
        elif failed_checks == 1 or flag_count >= 3:
            return "medium"
        else:
            return "low"


# Global instance
safety_guard = SafetyGuard(strict_mode=False)
