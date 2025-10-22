# Quick Start: Email Testing

## Your Configuration
- **From**: althamishnainamohamed@gmail.com
- **To**: althu1603@gmail.com

## Quickest Way to Test

### Step 1: Install Dependencies
```powershell
cd ..\backend
pip install -r requirements.txt
```

### Step 2: Run Test
```powershell
cd ..\tests
python test_email_send.py
```

## What to Expect

 **Draft Creation** - Should PASS (no auth needed)
 **Email Sending** - Will FAIL without real auth token (expected)

## To Actually Send Emails

1. Start server: `python ..\backend\server.py`
2. Authenticate via OAuth URL shown
3. Run: `python e2e_email_test.py`
4. Check althu1603@gmail.com inbox

## Available Tests

| Script | Purpose | Auth Required |
|--------|---------|---------------|
| test_email_simple.py | Quick basic test | No |
| test_email_send.py | Comprehensive test | No |
| test_email_agent.py | Full test suite (9 tests) | No |
| e2e_email_test.py | Real email send | Yes |

## Troubleshooting

**Missing modules?**  Run `pip install -r ..\backend\requirements.txt`
**Auth errors?**  Run `python ..\backend\server.py` and authenticate
**No email received?**  Check spam folder in althu1603@gmail.com

---
For full details, see EMAIL_TEST_GUIDE.md
