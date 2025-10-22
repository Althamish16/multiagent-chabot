"""
Quick Email Test - Interactive Testing Script
Use this for quick manual testing of email functionality
"""
import sys
import os
import asyncio
import json

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from email_agent import SecureEmailAgent


async def quick_test_draft():
    """Quick test for email drafting"""
    print("\n" + "="*60)
    print("QUICK EMAIL DRAFT TEST")
    print("="*60 + "\n")
    
    agent = SecureEmailAgent()
    
    # Test 1: Simple draft
    print("Test 1: Drafting a simple meeting invitation email...")
    result = await agent.draft_email({
        "user_request": "Draft an email to john.doe@company.com inviting him to a product demo meeting next Tuesday at 3 PM",
        "context": {},
        "conversation_history": []
    })
    
    if result.get("status") == "draft_ready":
        draft = result.get("draft")
        print("\n✅ Email Draft Created Successfully!")
        print("-" * 60)
        print(f"To: {draft.get('to')}")
        print(f"Subject: {draft.get('subject')}")
        print(f"Tone: {draft.get('tone')}")
        print(f"Priority: {draft.get('priority')}")
        print(f"\nBody:\n{draft.get('body')}")
        print("-" * 60)
    else:
        print(f"\n❌ Failed: {result.get('message')}")
    
    # Test 2: Email with context
    print("\n\nTest 2: Drafting a follow-up email with context...")
    result = await agent.draft_email({
        "user_request": "Send a thank you email to sarah@partner.com for the collaboration",
        "context": {
            "project_name": "Q4 Marketing Campaign",
            "collaboration_result": "Exceeded targets by 25%"
        },
        "conversation_history": [
            "User discussed successful Q4 campaign",
            "Partner company helped achieve 25% above target"
        ]
    })
    
    if result.get("status") == "draft_ready":
        draft = result.get("draft")
        print("\n✅ Email Draft Created Successfully!")
        print("-" * 60)
        print(f"To: {draft.get('to')}")
        print(f"Subject: {draft.get('subject')}")
        print(f"\nBody:\n{draft.get('body')}")
        print("-" * 60)
    else:
        print(f"\n❌ Failed: {result.get('message')}")
    
    print("\n✨ Quick test completed!\n")


async def interactive_test():
    """Interactive email drafting test"""
    print("\n" + "="*60)
    print("INTERACTIVE EMAIL DRAFT TEST")
    print("="*60 + "\n")
    
    agent = SecureEmailAgent()
    
    print("Enter your email request (or 'quit' to exit):")
    print("Example: Draft an email to bob@company.com about the quarterly report\n")
    
    while True:
        user_input = input("📝 Your request: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye! 👋\n")
            break
        
        if not user_input:
            print("Please enter a request.\n")
            continue
        
        print("\n⏳ Drafting email...")
        
        result = await agent.draft_email({
            "user_request": user_input,
            "context": {},
            "conversation_history": []
        })
        
        if result.get("status") == "draft_ready":
            draft = result.get("draft")
            print("\n" + "="*60)
            print("📧 EMAIL DRAFT")
            print("="*60)
            print(f"\n📬 To: {draft.get('to')}")
            print(f"📋 Subject: {draft.get('subject')}")
            print(f"🎯 Tone: {draft.get('tone')}")
            print(f"⚡ Priority: {draft.get('priority')}")
            print(f"\n💬 Body:")
            print("-" * 60)
            print(draft.get('body'))
            print("-" * 60 + "\n")
        else:
            print(f"\n❌ Error: {result.get('message')}\n")


def show_menu():
    """Show test menu"""
    print("\n" + "="*60)
    print("EMAIL AGENT QUICK TEST")
    print("="*60)
    print("\nChoose a test mode:")
    print("1. Quick automated test (2 sample drafts)")
    print("2. Interactive test (enter your own requests)")
    print("3. Show email agent info")
    print("4. Exit")
    print()


async def show_info():
    """Show email agent information"""
    print("\n" + "="*60)
    print("EMAIL AGENT INFORMATION")
    print("="*60 + "\n")
    
    print("📧 Email Agent Features:")
    print("  • Draft professional emails based on natural language requests")
    print("  • Context-aware email generation from conversation history")
    print("  • Automatic tone adjustment (professional/friendly/formal)")
    print("  • Priority setting (high/medium/low)")
    print("  • Human-in-the-loop approval before sending")
    print("  • Integration with Gmail API for actual sending")
    
    print("\n🔧 Technical Details:")
    print("  • Uses Azure OpenAI for intelligent draft generation")
    print("  • Secure OAuth 2.0 authentication with Google")
    print("  • Async/await for non-blocking operations")
    print("  • Structured JSON output for easy integration")
    
    print("\n✅ What This Test Covers:")
    print("  • Email drafting functionality")
    print("  • Context integration")
    print("  • Error handling")
    print("  • Response format validation")
    
    print("\n⚠️  Note for Full Testing:")
    print("  • To test actual sending, you need:")
    print("    1. Valid Google OAuth access token")
    print("    2. Gmail API enabled")
    print("    3. Proper OAuth scopes configured")
    print("  • Use the full test suite (test_email_agent.py --real)")
    print()


async def main():
    """Main test runner"""
    while True:
        show_menu()
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            await quick_test_draft()
        elif choice == '2':
            await interactive_test()
        elif choice == '3':
            await show_info()
        elif choice == '4':
            print("\n👋 Goodbye!\n")
            break
        else:
            print("\n❌ Invalid choice. Please enter 1-4.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted. Goodbye!\n")
