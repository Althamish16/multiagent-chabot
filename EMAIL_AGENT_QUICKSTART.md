# Email Agent - Quick Start Guide

## 🚀 Getting Started

The Email Agent is now fully integrated into your multi-agent chatbot. Here's how to use it:

---

## 1️⃣ **Prerequisites**

✅ **Already Configured:**
- Azure OpenAI credentials (for AI drafting)
- Google OAuth 2.0 (for Gmail API)
- Backend server running on port 5000
- User authenticated via Google OAuth

---

## 2️⃣ **Using via Chat Interface**

### **Example 1: Simple Email Draft**
```
User: "Draft an email to john@example.com about the project status update"
```

**Agent Response:**
```
Email draft created and awaiting approval

📧 Draft Details:
To: john@example.com
Subject: Project Status Update
Body: Dear John, [AI-generated content]...

Draft ID: abc-123-def
Status: pending_approval

✅ Ready for review and approval
```

### **Example 2: Email with Tone**
```
User: "Write a friendly email to the team thanking them for their hard work"
```

### **Example 3: Formal Email**
```
User: "Draft a formal email to praveen@company.com requesting sick leave for tomorrow"
```

---

## 3️⃣ **Using via API**

### **Step 1: Create Draft**
```bash
curl -X POST http://localhost:5000/api/email/draft \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Draft email to john@example.com about meeting tomorrow",
    "session_id": "my_session_123",
    "tone": "professional"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Email draft created and awaiting approval",
  "result": {
    "draft_id": "abc-123-def-456",
    "to": "john@example.com",
    "subject": "Meeting Tomorrow",
    "body": "Dear John,\n\nI wanted to discuss...",
    "status": "pending_approval",
    "created_at": "2025-10-23T15:30:00Z",
    "safety_checks": {
      "passed": true,
      "risk_level": "low"
    }
  }
}
```

### **Step 2: Review & Approve**
```bash
curl -X POST http://localhost:5000/api/email/approve \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "draft_id": "abc-123-def-456"
  }'
```

### **Step 3: Send Email**
```bash
curl -X POST http://localhost:5000/api/email/send \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "draft_id": "abc-123-def-456"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Email sent successfully",
  "result": {
    "draft_id": "abc-123-def-456",
    "gmail_message_id": "17a1b2c3d4e5f6",
    "gmail_thread_id": "17a1b2c3d4e5f6",
    "sent_at": "2025-10-23T15:35:00Z"
  }
}
```

---

## 4️⃣ **Managing Drafts**

### **List All Drafts**
```bash
curl http://localhost:5000/api/email/drafts/my_session_123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### **Filter by Status**
```bash
curl "http://localhost:5000/api/email/drafts/my_session_123?status=pending_approval" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### **Get Specific Draft**
```bash
curl http://localhost:5000/api/email/draft/abc-123-def-456 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### **Delete Draft**
```bash
curl -X DELETE http://localhost:5000/api/email/draft/abc-123-def-456 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 5️⃣ **Advanced Features**

### **Tone Control**
Available tones: `professional`, `friendly`, `formal`, `casual`

```json
{
  "user_request": "Draft email...",
  "tone": "friendly"
}
```

### **Priority Levels**
Available priorities: `low`, `medium`, `high`, `urgent`

```json
{
  "user_request": "Draft email...",
  "priority": "high"
}
```

### **Explicit Recipients**
```json
{
  "user_request": "Draft email about quarterly report",
  "recipient": "manager@company.com",
  "subject": "Q4 2025 Report"
}
```

### **Modify During Approval**
```json
{
  "draft_id": "abc-123",
  "modifications": {
    "subject": "Updated Subject Line",
    "body": "Updated email body..."
  }
}
```

---

## 6️⃣ **Safety Features**

The Email Agent performs automatic safety checks:

✅ **PII Detection** - Flags SSN, credit cards, passwords  
✅ **Toxic Language** - Detects inappropriate content  
✅ **Recipient Validation** - Checks email format  
✅ **Subject Validation** - Ensures subject is present  
✅ **Content Length** - Warns on very short/long emails  

**Safety Check Response:**
```json
{
  "safety_checks": {
    "passed": false,
    "checks": {
      "pii_check": false,
      "toxic_check": true,
      "recipient_check": true
    },
    "flags": [
      "Potential SSN detected: 1 occurrence(s)"
    ],
    "risk_level": "medium",
    "recommendations": [
      "Review and remove SSN before sending"
    ]
  }
}
```

---

## 7️⃣ **Workflow States**

```
┌─────────┐
│ DRAFTED │ ──→ Initial creation
└─────────┘
     ↓
┌──────────────────┐
│ PENDING_APPROVAL │ ──→ Awaiting human review
└──────────────────┘
     ↓
  ┌─────────┐
  │ APPROVED│ ──→ Ready to send
  └─────────┘
     ↓
  ┌──────┐
  │ SENT │ ──→ Successfully sent
  └──────┘

Alternate paths:
PENDING_APPROVAL → REJECTED (user rejects)
APPROVED → FAILED (send error after retries)
```

---

## 8️⃣ **Error Handling**

### **Common Errors:**

**"Email agent not available"** (503)
- Email agent module not imported
- Check backend logs for import errors

**"Draft not found"** (404)
- Invalid draft_id
- Draft may have been deleted

**"Draft must be approved before sending"** (error in result)
- Trying to send unapproved draft
- Call `/api/email/approve` first

**"Gmail API error"** (error in result)
- Token expired - re-authenticate
- Insufficient Gmail scopes
- Network/API issue

**"No access_token provided"** (error in result)
- User not authenticated
- Missing Google OAuth token

---

## 9️⃣ **Debugging**

### **Check Backend Logs**
```bash
# Look for email agent initialization
✅ Email agent loaded

# Check for draft operations
Drafting email for session my_session_123: Draft email...
Draft abc-123 created successfully (status: pending_approval)
Safety check for draft abc-123: passed=True, risk=low, flags=0
```

### **Verify Storage**
```bash
ls backend/data/email_drafts/
# Should show:
# draft_{uuid}.json
# session_{session_id}_index.json
```

### **Test Module Import**
```bash
cd backend
python -c "from email_agent import enhanced_email_agent; print('✅ Import successful')"
```

---

## 🔟 **Tips & Best Practices**

1. **Always Review Drafts** - Even AI-generated content should be reviewed
2. **Use Descriptive Requests** - More context = better drafts
3. **Check Safety Flags** - Review any flagged issues before approving
4. **Provide Explicit Recipients** - When email address isn't in request
5. **Delete Old Drafts** - Keep session clean
6. **Monitor Gmail Quotas** - Gmail API has daily send limits
7. **Test with Safe Recipients** - Use test accounts first

---

## 📞 **Support**

If you encounter issues:

1. Check backend logs (`uvicorn` output)
2. Verify Google OAuth authentication
3. Ensure Gmail API scopes are authorized
4. Review safety check flags in draft
5. Check `backend/data/email_drafts/` for stored drafts

---

## ✨ **Examples**

### **Business Email**
```
User: "Draft a professional email to client@company.com with a project proposal"
```

### **Internal Communication**
```
User: "Send a friendly email to the team about tomorrow's standup"
```

### **Meeting Request**
```
User: "Write a formal email to schedule a meeting with director@company.com"
```

### **Follow-up**
```
User: "Draft a follow-up email to john@example.com about our previous discussion"
```

---

**🎉 You're all set! Start drafting emails with AI assistance now.**
