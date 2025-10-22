"""
Email Send Test Script
Tests sending emails from althamishnainamohamed@gmail.com to althu1603@gmail.com
"""
import sys
import os
import asyncio
from datetime import datetime

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from email_agent import SecureEmailAgent


async def test_send_email():
    """Test sending an email"""
    print("=" * 70)
    print("EMAIL SEND TEST")
    print("=" * 70)
    print(f"From: althamishnainamohamed@gmail.com")
    print(f"To: althu1603@gmail.com")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Initialize agent
    agent = SecureEmailAgent()
    
    # Email draft
    draft = {
        'to': 'althu1603@gmail.com',
        'subject': 'Test Email from Multi-Agent Chatbot',
        'body': '''Hello,

This is a test email sent from the Multi-Agent Chatbot system.

If you receive this email, it confirms that:
1. The email agent is properly configured
2. Authentication is working correctly
3. Email sending functionality is operational

Test Details:
- Sent at: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''
- From: althamishnainamohamed@gmail.com
- To: althu1603@gmail.com

Best regards,
Multi-Agent Chatbot System'''
    }
    
    print("Draft created:")
    print(f"  To: {draft['to']}")
    print(f"  Subject: {draft['subject']}")
    print(f"  Body length: {len(draft['body'])} characters")
    print()
    
    # Note: You need proper authentication to actually send
    print("  NOTE: To actually send this email, you need:")
    print("   1. Valid Google OAuth credentials")
    print("   2. An active access token")
    print("   3. Gmail API enabled")
    print()
    
    try:
        # For testing purposes, use a mock token
        # In production, you'd get this from the OAuth flow
        mock_token = "mock_access_token"
        
        print("Attempting to send email (with mock token)...")
        result = await agent.send_email(draft, mock_token)
        
        if result.get('status') == 'success':
            print(" SUCCESS: Email sent!")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
        else:
            print(" FAILED: Could not send email")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            print()
            print("   This is expected when using a mock token.")
            print("   The email draft was created successfully,")
            print("   but actual sending requires real authentication.")
            
    except Exception as e:
        print(f" EXCEPTION: {type(e).__name__}")
        print(f"   {str(e)}")
        print()
        print("   This is expected without proper authentication.")
        
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(test_send_email())
