"""
End-to-End Email Test with Real Gmail API
This script tests the complete email flow including actual sending via Gmail API

Prerequisites:
1. Valid Google OAuth credentials in .env file
2. Gmail API enabled in Google Cloud Console
3. Proper OAuth scopes: https://www.googleapis.com/auth/gmail.send

Usage:
    python e2e_email_test.py --token YOUR_ACCESS_TOKEN --to recipient@example.com
    
Or set environment variables:
    set GOOGLE_ACCESS_TOKEN=your_token
    set TEST_RECIPIENT_EMAIL=recipient@example.com
    python e2e_email_test.py
"""
import sys
import os
import asyncio
import argparse
from datetime import datetime

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from email_agent import SecureEmailAgent
from google_auth import GoogleAPIClient


class E2EEmailTest:
    """End-to-end email testing with real Gmail API"""
    
    def __init__(self, access_token: str, recipient_email: str = None):
        self.access_token = access_token
        self.recipient_email = recipient_email
        self.agent = SecureEmailAgent()
        
    async def test_complete_flow(self):
        """Test complete email draft and send flow"""
        print("\n" + "="*70)
        print("END-TO-END EMAIL TEST WITH GMAIL API")
        print("="*70 + "\n")
        
        if not self.recipient_email:
            self.recipient_email = input("Enter recipient email address: ").strip()
            if not self.recipient_email:
                print("❌ No recipient provided. Test cancelled.")
                return False
        
        print(f"📧 Testing email flow to: {self.recipient_email}")
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Step 1: Draft the email
        print("Step 1: Drafting test email...")
        print("-" * 70)
        
        draft_result = await self.agent.draft_email({
            "user_request": f"Draft a test email to {self.recipient_email} to verify the email system is working correctly. Mention that this is an automated test.",
            "context": {
                "test_type": "End-to-end email functionality test",
                "timestamp": datetime.now().isoformat()
            },
            "conversation_history": []
        })
        
        if draft_result.get("status") != "draft_ready":
            print(f"❌ Failed to draft email: {draft_result.get('message')}")
            return False
        
        draft = draft_result.get("draft")
        print("✅ Email drafted successfully!")
        print(f"\nDraft Details:")
        print(f"  To: {draft.get('to')}")
        print(f"  Subject: {draft.get('subject')}")
        print(f"  Tone: {draft.get('tone')}")
        print(f"  Priority: {draft.get('priority')}")
        print(f"\n  Body Preview:")
        body_preview = draft.get('body', '')[:200] + "..." if len(draft.get('body', '')) > 200 else draft.get('body', '')
        print(f"  {body_preview}\n")
        
        # Step 2: Confirm sending
        print("\nStep 2: Sending email via Gmail API...")
        print("-" * 70)
        
        confirm = input(f"Send this email to {draft.get('to')}? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Test cancelled by user.")
            return False
        
        # Step 3: Send the email
        send_result = await self.agent.send_email(draft, self.access_token)
        
        if send_result.get("status") == "success":
            print("✅ Email sent successfully!")
            print(f"\nSend Details:")
            print(f"  Email ID: {send_result.get('email_id')}")
            print(f"  Recipient: {draft.get('to')}")
            print(f"  Subject: {draft.get('subject')}")
            print(f"  Status: {send_result.get('message')}")
            print("\n" + "="*70)
            print("✅ END-TO-END TEST PASSED!")
            print("="*70 + "\n")
            return True
        else:
            print(f"❌ Failed to send email: {send_result.get('message')}")
            print("\n" + "="*70)
            print("❌ END-TO-END TEST FAILED!")
            print("="*70 + "\n")
            return False
    
    async def test_multiple_drafts(self):
        """Test drafting multiple different types of emails"""
        print("\n" + "="*70)
        print("MULTIPLE DRAFT SCENARIOS TEST")
        print("="*70 + "\n")
        
        scenarios = [
            {
                "name": "Meeting Invitation",
                "request": f"Draft an email to {self.recipient_email or 'colleague@example.com'} inviting them to a team meeting next Monday at 2 PM"
            },
            {
                "name": "Project Update",
                "request": f"Draft an email to {self.recipient_email or 'manager@example.com'} providing an update on the Q4 project status"
            },
            {
                "name": "Thank You Note",
                "request": f"Draft a thank you email to {self.recipient_email or 'client@example.com'} for their collaboration on the recent project"
            }
        ]
        
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\nScenario {i}: {scenario['name']}")
            print("-" * 70)
            
            result = await self.agent.draft_email({
                "user_request": scenario['request'],
                "context": {},
                "conversation_history": []
            })
            
            if result.get("status") == "draft_ready":
                draft = result.get("draft")
                print(f"✅ Draft created")
                print(f"   Subject: {draft.get('subject')}")
                print(f"   Tone: {draft.get('tone')}")
                results.append(True)
            else:
                print(f"❌ Failed: {result.get('message')}")
                results.append(False)
        
        print("\n" + "="*70)
        print(f"Results: {sum(results)}/{len(results)} scenarios passed")
        print("="*70 + "\n")
        
        return all(results)
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n" + "="*70)
        print("ERROR HANDLING TEST")
        print("="*70 + "\n")
        
        tests_passed = []
        
        # Test 1: Invalid access token
        print("Test 1: Invalid Access Token")
        print("-" * 70)
        try:
            result = await self.agent.send_email(
                {"to": "test@example.com", "subject": "Test", "body": "Test"},
                "invalid_token_12345"
            )
            if result.get("status") == "error":
                print("✅ Correctly handled invalid token")
                tests_passed.append(True)
            else:
                print("❌ Should have failed with invalid token")
                tests_passed.append(False)
        except Exception as e:
            print(f"✅ Exception caught as expected: {str(e)[:100]}")
            tests_passed.append(True)
        
        # Test 2: Missing draft fields
        print("\nTest 2: Missing Required Fields")
        print("-" * 70)
        state = {
            "action": "send",
            "draft": None,  # Missing draft
            "access_token": self.access_token
        }
        result = await self.agent.process_request(state)
        if result.get("status") == "error":
            print("✅ Correctly handled missing draft")
            tests_passed.append(True)
        else:
            print("❌ Should have failed with missing draft")
            tests_passed.append(False)
        
        print("\n" + "="*70)
        print(f"Results: {sum(tests_passed)}/{len(tests_passed)} error handling tests passed")
        print("="*70 + "\n")
        
        return all(tests_passed)


def validate_token(token: str) -> bool:
    """Basic validation of access token format"""
    if not token or len(token) < 20:
        return False
    return True


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(
        description="End-to-end email testing with Gmail API"
    )
    parser.add_argument(
        "--token",
        help="Google OAuth access token",
        default=os.environ.get('GOOGLE_ACCESS_TOKEN')
    )
    parser.add_argument(
        "--to",
        help="Recipient email address",
        default=os.environ.get('TEST_RECIPIENT_EMAIL')
    )
    parser.add_argument(
        "--test",
        choices=['full', 'draft', 'errors', 'all'],
        default='all',
        help="Type of test to run"
    )
    
    args = parser.parse_args()
    
    # Validate token
    if not args.token:
        print("❌ Error: No access token provided")
        print("\nPlease provide a Google OAuth access token using one of these methods:")
        print("1. Command line: python e2e_email_test.py --token YOUR_TOKEN")
        print("2. Environment variable: set GOOGLE_ACCESS_TOKEN=YOUR_TOKEN")
        print("\nTo get an access token:")
        print("1. Run your app and authenticate via Google OAuth")
        print("2. Get the access token from the authentication response")
        print("3. Use that token for testing\n")
        return
    
    if not validate_token(args.token):
        print("⚠️  Warning: Access token appears to be invalid (too short)")
        confirm = input("Continue anyway? (yes/no): ").strip().lower()
        if confirm != 'yes':
            return
    
    # Create test instance
    tester = E2EEmailTest(args.token, args.to)
    
    # Run tests based on selection
    if args.test in ['full', 'all']:
        await tester.test_complete_flow()
    
    if args.test in ['draft', 'all']:
        await tester.test_multiple_drafts()
    
    if args.test in ['errors', 'all']:
        await tester.test_error_handling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user. Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}\n")
        import traceback
        traceback.print_exc()
