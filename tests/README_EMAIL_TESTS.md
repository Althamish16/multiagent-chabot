# Email Testing Suite

This directory contains comprehensive test scripts for validating email functionality in the multi-agent chatbot system.

## Test Scripts Overview

### 1. `test_email_agent.py` - Comprehensive Unit Tests
**Purpose**: Full automated test suite covering all email agent functionality

**Features**:
- ✅ Email drafting tests (simple, context-aware, professional tone)
- ✅ Email sending flow tests
- ✅ Error handling validation
- ✅ Component initialization tests
- ✅ Process request method tests
- ✅ Detailed JSON test reports

**Usage**:
```powershell
# Run standard automated tests
python tests/test_email_agent.py

# Test with real Gmail API (requires valid token)
python tests/test_email_agent.py --real
```

**Test Coverage**:
- Draft simple email
- Draft email with conversation context
- Professional tone verification
- Send email without token (expected failure)
- Send email flow with mock token
- Process request actions
- GoogleAPIClient initialization

**Output**: 
- Console output with pass/fail status
- JSON test report in `test_reports/` directory
- Success rate calculation

---

### 2. `quick_email_test.py` - Interactive Testing
**Purpose**: Quick manual testing with interactive menu

**Features**:
- 🚀 Quick automated tests (2 sample drafts)
- 💬 Interactive mode (enter your own requests)
- ℹ️ Email agent information display
- 📝 Real-time draft preview

**Usage**:
```powershell
python tests/quick_email_test.py
```

**Menu Options**:
1. Quick automated test - Runs 2 pre-defined draft scenarios
2. Interactive test - Enter your own email requests
3. Show email agent info - Display capabilities and features
4. Exit

**Example Interactive Session**:
```
📝 Your request: Draft an email to john@company.com about Q4 results

⏳ Drafting email...

📧 EMAIL DRAFT
==============================================================
📬 To: john@company.com
📋 Subject: Q4 Results Summary
🎯 Tone: professional
⚡ Priority: medium

💬 Body:
--------------------------------------------------------------
Dear John,

I hope this email finds you well...
```

---

### 3. `e2e_email_test.py` - End-to-End Gmail API Test
**Purpose**: Complete integration testing with real Gmail API

**Features**:
- 📧 Full draft → send flow with Gmail API
- 🔄 Multiple draft scenarios testing
- ⚠️ Error handling validation
- ✅ Real email delivery confirmation

**Usage**:
```powershell
# With command line arguments
python tests/e2e_email_test.py --token YOUR_ACCESS_TOKEN --to recipient@example.com

# With environment variables
set GOOGLE_ACCESS_TOKEN=your_token
set TEST_RECIPIENT_EMAIL=recipient@example.com
python tests/e2e_email_test.py

# Run specific test types
python tests/e2e_email_test.py --test full    # Full send test only
python tests/e2e_email_test.py --test draft   # Draft scenarios only
python tests/e2e_email_test.py --test errors  # Error handling only
python tests/e2e_email_test.py --test all     # All tests (default)
```

**Prerequisites**:
1. Valid Google OAuth access token
2. Gmail API enabled in Google Cloud Console
3. OAuth scopes: `https://www.googleapis.com/auth/gmail.send`

**Test Scenarios**:
- Complete draft and send flow
- Meeting invitation draft
- Project update draft
- Thank you note draft
- Invalid token handling
- Missing fields handling

---

## Getting a Google Access Token

### For Testing Purposes:

1. **Run your app and authenticate**:
   ```powershell
   cd backend
   python server.py
   ```

2. **Authenticate via Google OAuth**:
   - Open http://localhost:5000 in browser
   - Click "Login with Google"
   - Complete OAuth flow

3. **Extract token from browser**:
   - Open browser DevTools (F12)
   - Go to Application → Local Storage
   - Find `google_access_token`
   - Copy the token value

4. **Set environment variable**:
   ```powershell
   set GOOGLE_ACCESS_TOKEN=ya29.a0...your_token_here
   ```

5. **Run tests**:
   ```powershell
   python tests/e2e_email_test.py --to your-email@gmail.com
   ```

---

## Test Comparison Matrix

| Feature | test_email_agent.py | quick_email_test.py | e2e_email_test.py |
|---------|-------------------|-------------------|------------------|
| **Automated** | ✅ Yes | ⚠️ Optional | ⚠️ Optional |
| **Interactive** | ❌ No | ✅ Yes | ⚠️ Partial |
| **Real Email Sending** | ⚠️ Optional | ❌ No | ✅ Yes |
| **Detailed Reports** | ✅ JSON | ❌ Console only | ❌ Console only |
| **Error Testing** | ✅ Yes | ❌ No | ✅ Yes |
| **No Dependencies** | ✅ Yes | ✅ Yes | ❌ Needs token |
| **Best For** | CI/CD, Unit Tests | Development, Debug | Integration Test |

---

## Quick Start Guide

### For Developers (No Gmail API):
```powershell
# Quick automated test
python tests/test_email_agent.py

# Interactive testing
python tests/quick_email_test.py
```

### For Integration Testing (With Gmail API):
```powershell
# 1. Get access token (see instructions above)
set GOOGLE_ACCESS_TOKEN=your_token

# 2. Run end-to-end test
python tests/e2e_email_test.py --to test@example.com
```

---

## Test Results

### test_email_agent.py Output:
```
==============================================================
EMAIL AGENT TEST SUMMARY
==============================================================

Total Tests: 7
Passed: 7 ✅
Failed: 0 ❌
Success Rate: 100.0%

Test report saved to: test_reports/email_test_20250121_143052.json
```

### Test Report Structure (JSON):
```json
{
  "test_suite": "Email Agent Tests",
  "timestamp": "2025-01-21T14:30:52",
  "summary": {
    "total": 7,
    "passed": 7,
    "failed": 0,
    "success_rate": "100.0%"
  },
  "results": [
    {
      "test_name": "Draft Simple Email",
      "passed": true,
      "message": "Successfully drafted email...",
      "timestamp": "2025-01-21T14:30:53"
    }
  ]
}
```

---

## Environment Variables

### Required for Full Testing:
```powershell
# Azure OpenAI (for email drafting)
set AZURE_OPENAI_API_KEY=your_key
set AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
set AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4

# Google OAuth (for email sending)
set GOOGLE_CLIENT_ID=your_client_id
set GOOGLE_CLIENT_SECRET=your_client_secret
set GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# Testing (for e2e tests)
set GOOGLE_ACCESS_TOKEN=your_access_token
set TEST_RECIPIENT_EMAIL=recipient@example.com
```

---

## Troubleshooting

### Common Issues:

**1. "Failed to draft email" Error**
- ✅ Check Azure OpenAI credentials in `.env`
- ✅ Verify API key is valid and deployment exists
- ✅ Check internet connection

**2. "Failed to send email" Error**
- ✅ Verify access token is valid (not expired)
- ✅ Check Gmail API is enabled in Google Cloud Console
- ✅ Verify OAuth scopes include `gmail.send`
- ✅ Ensure token has not been revoked

**3. "Import Error" for Google Libraries**
- ✅ Install Google API client: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

**4. Token Expired**
- ✅ Tokens typically expire in 1 hour
- ✅ Re-authenticate through your app
- ✅ Get a fresh access token

---

## CI/CD Integration

### GitHub Actions Example:
```yaml
- name: Run Email Tests
  run: |
    python tests/test_email_agent.py
  env:
    AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
    AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: ${{ secrets.DEPLOYMENT_NAME }}
```

### Jenkins Pipeline:
```groovy
stage('Email Tests') {
    steps {
        bat 'python tests/test_email_agent.py'
    }
}
```

---

## Contributing

When adding new email features, please:
1. Add corresponding tests to `test_email_agent.py`
2. Update this README with new test scenarios
3. Ensure all tests pass before committing
4. Add test coverage for error cases

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test output and error messages
3. Verify all prerequisites are met
4. Check `test_reports/` for detailed JSON logs

---

## License

Part of the Multi-Agent Chatbot project.
