"""Email Send Test Script"""
import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from email_agent import SecureEmailAgent

async def test_send_email():
    print("EMAIL SEND TEST")
    print("From: althamishnainamohamed@gmail.com")
    print("To: althu1603@gmail.com")
    
    agent = SecureEmailAgent()
    draft = {
        'to': 'althu1603@gmail.com',
        'subject': 'Test Email from Multi-Agent Chatbot',
        'body': 'This is a test email. If you receive this, email sending is working!'
    }
    
    print(f"Draft: {draft['to']} - {draft['subject']}")
    print("Note: Requires valid OAuth token to actually send")
    
    try:
        mock_token = "mock"
        result = await agent.send_email(draft, mock_token)
        if result.get('status') == 'success':
            print("SUCCESS: Email sent!")
        else:
            print(f"FAILED: {result.get('message')}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == '__main__':
    asyncio.run(test_send_email())
