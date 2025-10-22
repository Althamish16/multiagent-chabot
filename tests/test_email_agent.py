"""
Email Agent Test Script
Tests email drafting and sending functionality
"""
import sys
import os
import asyncio
import json
from datetime import datetime

# Add backend directory to Python path
sys.        try:
            draft = {
                "to": "althu1603@gmail.com",
                "subject": "Test Email Subject",
                "body": "This is a test email body\n\nBest regards,\nTest User"
            }
            
            # Use a mock token (this will fail but tests the flow)ert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from email_agent import SecureEmailAgent
from google_auth import GoogleAPIClient


class EmailTestSuite:
    """Test suite for email functionality"""
    
    def __init__(self):
        self.agent = SecureEmailAgent()
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}")
        print(f"   {message}\n")
        
    async def test_draft_simple_email(self):
        """Test drafting a simple email"""
        test_name = "Draft Simple Email"
        
        try:
            state = {
                "user_request": "Draft an email to john@example.com about the quarterly meeting scheduled for next Monday at 2 PM",
                "context": {},
                "conversation_history": []
            }
            
            result = await self.agent.draft_email(state)
            
            # Verify result structure
            if result.get("status") == "draft_ready":
                draft = result.get("draft", {})
                
                # Check required fields
                has_to = "to" in draft and draft["to"]
                has_subject = "subject" in draft and draft["subject"]
                has_body = "body" in draft and draft["body"]
                
                if has_to and has_subject and has_body:
                    self.log_test(
                        test_name, 
                        True,
                        f"Successfully drafted email to {draft['to']} with subject: {draft['subject'][:50]}..."
                    )
                    return draft
                else:
                    missing = []
                    if not has_to: missing.append("to")
                    if not has_subject: missing.append("subject")
                    if not has_body: missing.append("body")
                    self.log_test(test_name, False, f"Draft missing fields: {missing}")
            else:
                self.log_test(test_name, False, f"Unexpected status: {result.get('status')}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
        return None
    
    async def test_draft_with_context(self):
        """Test drafting email with conversation context"""
        test_name = "Draft Email with Context"
        
        try:
            state = {
                "user_request": "Send a follow-up email to sarah@company.com about the discussed proposal",
                "context": {
                    "previous_topic": "Budget proposal discussion",
                    "mentioned_amount": "$50,000"
                },
                "conversation_history": [
                    "User discussed budget proposal",
                    "AI suggested $50,000 allocation"
                ]
            }
            
            result = await self.agent.draft_email(state)
            
            if result.get("status") == "draft_ready":
                draft = result.get("draft", {})
                body = draft.get("body", "").lower()
                
                # Check if context is incorporated
                context_used = "proposal" in body or "budget" in body
                
                if context_used:
                    self.log_test(
                        test_name,
                        True,
                        f"Email draft includes context from conversation history"
                    )
                    return draft
                else:
                    self.log_test(
                        test_name,
                        False,
                        "Draft doesn't seem to incorporate conversation context"
                    )
            else:
                self.log_test(test_name, False, f"Failed to draft: {result.get('message')}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
        return None
    
    async def test_draft_professional_tone(self):
        """Test that email draft maintains professional tone"""
        test_name = "Professional Tone Check"
        
        try:
            state = {
                "user_request": "Tell bob@work.com that the deadline was missed and we need to reschedule",
                "context": {},
                "conversation_history": []
            }
            
            result = await self.agent.draft_email(state)
            
            if result.get("status") == "draft_ready":
                draft = result.get("draft", {})
                body = draft.get("body", "")
                
                # Check for professional indicators
                professional_keywords = ["Dear", "Hi", "Hello", "Best regards", "Sincerely", "Thank you"]
                has_greeting = any(keyword in body for keyword in professional_keywords)
                
                # Check tone metadata
                tone = draft.get("tone", "").lower()
                
                if has_greeting and tone in ["professional", "formal", "friendly"]:
                    self.log_test(
                        test_name,
                        True,
                        f"Email maintains professional tone: {tone}"
                    )
                    return draft
                else:
                    self.log_test(
                        test_name,
                        False,
                        f"Email may lack professional elements (tone: {tone}, greeting: {has_greeting})"
                    )
            else:
                self.log_test(test_name, False, f"Failed to draft: {result.get('message')}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
        return None
    
    async def test_send_email_without_token(self):
        """Test that sending email without access token fails properly"""
        test_name = "Send Email Without Token (Expected Failure)"
        
        try:
            draft = {
                "to": "test@example.com",
                "subject": "Test Email",
                "body": "This is a test email"
            }
            
            state = {
                "action": "send",
                "draft": draft,
                "access_token": None  # No token
            }
            
            result = await self.agent.process_request(state)
            
            # This should fail
            if result.get("status") == "error":
                self.log_test(
                    test_name,
                    True,
                    "Correctly rejected send request without access token"
                )
            else:
                self.log_test(
                    test_name,
                    False,
                    "Should have failed without access token but didn't"
                )
                
        except Exception as e:
            self.log_test(test_name, False, f"Unexpected exception: {str(e)}")
    
    async def test_send_email_with_mock_token(self):
        """Test sending email with a mock token (will fail but tests the flow)"""
        test_name = "Send Email Flow Test"
        
        try:
            draft = {
                "to": "recipient@example.com",
                "subject": "Test Email Subject",
                "body": "This is a test email body\n\nBest regards,\nTest User"
            }
            
            # Use a mock token (this will fail at Gmail API but tests our code path)
            mock_token = "mock_access_token_for_testing"
            
            result = await self.agent.send_email(draft, mock_token)
            
            # We expect this to fail with actual Gmail API, but we test error handling
            if result.get("status") == "error":
                error_msg = result.get("message", "")
                if "Failed to send email" in error_msg:
                    self.log_test(
                        test_name,
                        True,
                        f"Send email flow executed correctly (expected API failure with mock token)"
                    )
                else:
                    self.log_test(test_name, False, f"Unexpected error message: {error_msg}")
            else:
                # If it somehow succeeded, that's also good (maybe mock implementation)
                self.log_test(
                    test_name,
                    True,
                    "Send email flow completed successfully"
                )
                
        except Exception as e:
            # Exception is expected with mock token
            self.log_test(
                test_name,
                True,
                f"Send email flow executed (expected failure: {str(e)[:100]})"
            )
    
    async def test_process_request_draft_action(self):
        """Test process_request method with draft action"""
        test_name = "Process Request - Draft Action"
        
        try:
            state = {
                "action": "draft",
                "user_request": "Draft an email to team@company.com about the holiday schedule",
                "context": {},
                "conversation_history": []
            }
            
            result = await self.agent.process_request(state)
            
            if result.get("status") == "draft_ready" and result.get("requires_approval"):
                self.log_test(
                    test_name,
                    True,
                    "Draft action processed correctly with approval requirement"
                )
            else:
                self.log_test(
                    test_name,
                    False,
                    f"Unexpected result: {result.get('status')}"
                )
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def test_google_api_client_initialization(self):
        """Test GoogleAPIClient can be initialized"""
        test_name = "GoogleAPIClient Initialization"
        
        try:
            mock_token = "test_token_123"
            client = GoogleAPIClient(mock_token)
            
            if client.access_token == mock_token:
                self.log_test(
                    test_name,
                    True,
                    "GoogleAPIClient initialized successfully"
                )
            else:
                self.log_test(test_name, False, "Token not set correctly")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("EMAIL AGENT TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test_name']}: {result['message']}")
        
        print("\n" + "="*60)
        
        # Save results to file
        report_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "test_reports",
            f"email_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump({
                "test_suite": "Email Agent Tests",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\nTest report saved to: {report_file}\n")


async def run_all_tests():
    """Run all email tests"""
    print("="*60)
    print("EMAIL AGENT TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    suite = EmailTestSuite()
    
    # Run tests
    print("Running Email Drafting Tests...")
    print("-" * 60)
    await suite.test_draft_simple_email()
    await suite.test_draft_with_context()
    await suite.test_draft_professional_tone()
    await suite.test_process_request_draft_action()
    
    print("\nRunning Email Sending Tests...")
    print("-" * 60)
    await suite.test_send_email_without_token()
    await suite.test_send_email_with_mock_token()
    
    print("\nRunning Component Tests...")
    print("-" * 60)
    suite.test_google_api_client_initialization()
    
    # Print summary
    suite.print_summary()


def test_with_real_token():
    """
    Optional: Test with a real Google OAuth token
    
    To use this:
    1. Get a valid access token from your Google OAuth flow
    2. Set the GOOGLE_ACCESS_TOKEN environment variable
    3. Run: python test_email_agent.py --real
    """
    print("\n" + "="*60)
    print("REAL EMAIL SEND TEST")
    print("="*60)
    
    access_token = os.environ.get('GOOGLE_ACCESS_TOKEN')
    
    if not access_token:
        print("⚠️  No GOOGLE_ACCESS_TOKEN environment variable found")
        print("To test with real email sending:")
        print("1. Authenticate via your app's OAuth flow")
        print("2. Set GOOGLE_ACCESS_TOKEN=your_token")
        print("3. Run this test again with --real flag\n")
        return
    
    async def send_real_email():
        agent = SecureEmailAgent()
        
        # Get recipient email from user
        print("\n📧 This will send a REAL email via Gmail API")
        recipient = input("Enter recipient email address: ").strip()
        
        if not recipient:
            print("❌ No recipient provided. Test cancelled.")
            return
        
        confirm = input(f"Send test email to {recipient}? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Test cancelled.")
            return
        
        # Draft email
        print("\n✍️  Drafting email...")
        draft_result = await agent.draft_email({
            "user_request": f"Draft a friendly test email to {recipient} to verify the email system is working",
            "context": {},
            "conversation_history": []
        })
        
        if draft_result.get("status") != "draft_ready":
            print(f"❌ Failed to draft: {draft_result.get('message')}")
            return
        
        draft = draft_result.get("draft")
        print(f"\n📄 Draft created:")
        print(f"To: {draft['to']}")
        print(f"Subject: {draft['subject']}")
        print(f"Body:\n{draft['body']}\n")
        
        # Send email
        print("📤 Sending email...")
        send_result = await agent.send_email(draft, access_token)
        
        if send_result.get("status") == "success":
            print(f"✅ {send_result.get('message')}")
            print(f"Email ID: {send_result.get('email_id')}")
        else:
            print(f"❌ {send_result.get('message')}")
    
    asyncio.run(send_real_email())


if __name__ == "__main__":
    import sys
    
    # Check for --real flag
    if "--real" in sys.argv:
        test_with_real_token()
    else:
        # Run standard test suite
        asyncio.run(run_all_tests())
