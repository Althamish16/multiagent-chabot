import requests
import sys
import json
import time
from datetime import datetime
from pathlib import Path

class AIAgentsAPITester:
    def __init__(self, base_url="https://ai-agent-poc.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = f"test-session-{int(time.time())}"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'} if not files else {}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    print(f"   Response: {response.text[:200]}...")
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}...")
                self.failed_tests.append({
                    'test': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:300]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'test': name,
                'error': str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )

    def test_chat_general_message(self):
        """Test general chat message"""
        return self.run_test(
            "General Chat Message",
            "POST",
            "chat",
            200,
            data={
                "message": "Hello, what can you help me with?",
                "session_id": self.session_id
            }
        )

    def test_email_agent(self):
        """Test Email Agent functionality"""
        return self.run_test(
            "Email Agent - Send Email",
            "POST",
            "chat",
            200,
            data={
                "message": "Send an email to john@example.com with subject 'Test Meeting' and message 'Let's schedule a meeting for tomorrow'",
                "session_id": self.session_id
            }
        )

    def test_calendar_agent_view(self):
        """Test Calendar Agent - View Events"""
        return self.run_test(
            "Calendar Agent - View Events",
            "POST",
            "chat",
            200,
            data={
                "message": "What's on my calendar today?",
                "session_id": self.session_id
            }
        )

    def test_calendar_agent_create(self):
        """Test Calendar Agent - Create Event"""
        return self.run_test(
            "Calendar Agent - Create Event",
            "POST",
            "chat",
            200,
            data={
                "message": "Schedule a team meeting for tomorrow at 2 PM for 1 hour about project review",
                "session_id": self.session_id
            }
        )

    def test_notes_agent(self):
        """Test Notes Agent functionality"""
        return self.run_test(
            "Notes Agent - Create Note",
            "POST",
            "chat",
            200,
            data={
                "message": "Take a note: Remember to follow up on the client proposal by Friday",
                "session_id": self.session_id
            }
        )

    def test_file_upload_txt(self):
        """Test File Upload with TXT file"""
        # Create a test file
        test_content = "This is a test document for the AI Agents POC system. It contains important information about project requirements and specifications."
        
        files = {
            'file': ('test_document.txt', test_content, 'text/plain')
        }
        data = {
            'session_id': self.session_id
        }
        
        return self.run_test(
            "File Upload - TXT File",
            "POST",
            "upload",
            200,
            data=data,
            files=files
        )

    def test_file_upload_pdf(self):
        """Test File Upload with PDF file (simulated)"""
        # Simulate PDF content
        files = {
            'file': ('test_document.pdf', b'%PDF-1.4 fake pdf content for testing', 'application/pdf')
        }
        data = {
            'session_id': self.session_id
        }
        
        return self.run_test(
            "File Upload - PDF File",
            "POST",
            "upload",
            200,
            data=data,
            files=files
        )

    def test_chat_history(self):
        """Test Chat History retrieval"""
        return self.run_test(
            "Chat History Retrieval",
            "GET",
            f"chat/{self.session_id}",
            200
        )

    def test_file_summarizer_agent_direct(self):
        """Test File Summarizer Agent via chat"""
        return self.run_test(
            "File Summarizer Agent - Direct Request",
            "POST",
            "chat",
            200,
            data={
                "message": "Please summarize any documents I've uploaded",
                "session_id": self.session_id
            }
        )

    def test_agent_orchestration(self):
        """Test complex request that requires agent orchestration"""
        return self.run_test(
            "Agent Orchestration - Complex Request",
            "POST",
            "chat",
            200,
            data={
                "message": "I need to send an email about tomorrow's meeting, add it to my calendar, and take a note to prepare the agenda",
                "session_id": self.session_id
            }
        )

def main():
    print("🚀 Starting AI Agents POC Backend API Tests")
    print("=" * 60)
    
    tester = AIAgentsAPITester()
    
    # Test sequence
    tests = [
        tester.test_root_endpoint,
        tester.test_chat_general_message,
        tester.test_email_agent,
        tester.test_calendar_agent_view,
        tester.test_calendar_agent_create,
        tester.test_notes_agent,
        tester.test_file_upload_txt,
        tester.test_file_upload_pdf,
        tester.test_chat_history,
        tester.test_file_summarizer_agent_direct,
        tester.test_agent_orchestration
    ]
    
    # Run all tests
    for test in tests:
        try:
            success, response = test()
            if success:
                # Add small delay between tests to avoid overwhelming the API
                time.sleep(1)
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            tester.failed_tests.append({
                'test': test.__name__,
                'error': str(e)
            })
    
    # Print results summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {len(tester.failed_tests)}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.failed_tests:
        print("\n❌ FAILED TESTS:")
        for i, failure in enumerate(tester.failed_tests, 1):
            print(f"\n{i}. {failure.get('test', 'Unknown')}")
            if 'error' in failure:
                print(f"   Error: {failure['error']}")
            if 'expected' in failure:
                print(f"   Expected: {failure['expected']}, Got: {failure['actual']}")
            if 'response' in failure:
                print(f"   Response: {failure['response']}")
    
    # Return appropriate exit code
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())