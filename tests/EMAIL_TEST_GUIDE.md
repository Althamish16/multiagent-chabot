# Email Send Test Guide

This guide explains how to test email sending functionality in the Multi-Agent Chatbot.

## Test Configuration

**From:** althamishnainamohamed@gmail.com  
**To:** althu1603@gmail.com

## Prerequisites

1. **Install Dependencies**
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

2. **Google OAuth Setup**
   - Ensure you have valid Google OAuth credentials
   - The credentials should be configured in `backend/config.py`
   - Gmail API must be enabled in your Google Cloud Project

3. **Authentication**
   - Start the backend server: `python backend/server.py`
   - Visit the provided OAuth URL to authenticate
   - This will generate access tokens needed for sending emails

## Available Test Scripts

### 1. test_email_send.py (Comprehensive Test)
Full test suite with multiple scenarios including draft creation, sending, and CC/BCC.

**Run:**
```powershell
cd tests
python test_email_send.py
```

**What it tests:**
- Email draft creation
- Email sending flow (expects failure without real auth token)
- CC/BCC functionality
- Error handling

### 2. test_email_simple.py (Quick Test)
Simple, quick test to verify basic email functionality.

**Run:**
```powershell
cd tests
python test_email_simple.py
```

### 3. test_email_agent.py (Full Test Suite)
Complete test suite with 9+ different test cases.

**Run:**
```powershell
cd tests
python test_email_agent.py
```

**What it tests:**
- Draft simple email
- Draft with CC/BCC
- Email validation
- Parse email requests
- Attachments handling
- Send email flow
- Format validation
- Multiple recipients
- HTML content

### 4. e2e_email_test.py (Real Email Send)
End-to-end test that actually sends a real email using Gmail API.

**Run:**
```powershell
cd tests
python e2e_email_test.py
```

**⚠️ Important:** This requires a valid OAuth access token.

## Test Scenarios

### Scenario 1: Test Draft Creation (No Authentication Required)
```powershell
python test_email_agent.py
```
This will test the email drafting logic without requiring authentication.

### Scenario 2: Test with Mock Token
```powershell
python test_email_send.py
```
This tests the full flow with a mock token. It will fail at the Gmail API call but verifies all the code paths work correctly.

### Scenario 3: Send Real Email (Requires Authentication)
```powershell
# First, get your access token from the OAuth flow
# Then run:
python e2e_email_test.py
```

## Understanding Test Results

### ✅ Expected Results (Without Real Authentication)

```
✅ PASS - Draft Simple Email
   Successfully drafted email to althu1603@gmail.com

❌ FAIL - Send Email Flow Test  
   Failed to send email (Expected - using mock token)
```

The draft creation should pass, but actual sending will fail without a real OAuth token. This is **expected behavior**.

### ✅ Success (With Real Authentication)

```
✅ PASS - Draft Simple Email
   Successfully drafted email to althu1603@gmail.com

✅ PASS - Send Email Flow Test
   Email sent successfully
   Message ID: abc123xyz
```

When you have proper authentication, emails will actually be sent.

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'openai'"

**Solution:**
```powershell
cd backend
pip install -r requirements.txt
```

### Error: "Failed to send email: Invalid credentials"

**Solution:**
1. Check that Google OAuth is properly configured
2. Ensure Gmail API is enabled in Google Cloud Console
3. Verify your `backend/config.py` has correct credentials
4. Re-authenticate by running `python backend/server.py`

### Error: "Request had insufficient authentication scopes"

**Solution:**
1. Delete the token cache file
2. Re-authenticate with the correct scopes
3. Ensure Gmail send scope is included: `https://www.googleapis.com/auth/gmail.send`

## Verifying Email Was Sent

After running a test with real authentication:

1. **Check the terminal output** for a Message ID
2. **Check the recipient inbox** (althu1603@gmail.com) for the test email
3. **Check the sender's Sent folder** (althamishnainamohamed@gmail.com)
4. **Review test reports** in `test_reports/` directory

## Test Reports

All tests generate JSON reports saved to:
```
test_reports/email_agent_test_report.json
test_reports/iteration_1.json
```

These reports include:
- Timestamp
- Total tests run
- Pass/fail counts
- Detailed results for each test
- Success rate

## Example Output

```
======================================================================
EMAIL SEND TEST
======================================================================
From: althamishnainamohamed@gmail.com
To: althu1603@gmail.com
Time: 2025-10-21 14:30:15
======================================================================

Draft created:
  To: althu1603@gmail.com
  Subject: Test Email from Multi-Agent Chatbot
  Body length: 456 characters

⚠️  NOTE: To actually send this email, you need:
   1. Valid Google OAuth credentials
   2. An active access token
   3. Gmail API enabled

Attempting to send email (with mock token)...
❌ FAILED: Could not send email
   Error: Failed to send email: Invalid Credentials

   This is expected when using a mock token.
   The email draft was created successfully,
   but actual sending requires real authentication.

======================================================================
TEST COMPLETE
======================================================================
```

## Next Steps

1. **Without Authentication**: Run `python test_email_send.py` to test email drafting
2. **With Authentication**: 
   - Start server: `python backend/server.py`
   - Authenticate via OAuth
   - Run: `python e2e_email_test.py`
3. **Check results**: Look for the email in althu1603@gmail.com inbox

## Quick Reference

```powershell
# Install dependencies
cd backend
pip install -r requirements.txt

# Run comprehensive test
cd tests
python test_email_send.py

# Run quick test
python test_email_simple.py

# Run full test suite
python test_email_agent.py

# Send real email (requires auth)
python e2e_email_test.py
```

---

**Note:** All test scripts are configured to send emails FROM `althamishnainamohamed@gmail.com` TO `althu1603@gmail.com`.
