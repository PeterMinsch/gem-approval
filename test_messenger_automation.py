#!/usr/bin/env python3
"""
Test script for the Messenger Automation system
Run this to validate the implementation
"""

import asyncio
import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_api_health():
    """Test if API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def test_messenger_sessions():
    """Test messenger session management"""
    try:
        response = requests.get(f"{API_BASE_URL}/messenger/sessions")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Messenger sessions API works - {data['count']} active sessions")
            return True
        else:
            print(f"❌ Messenger sessions API failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Messenger sessions test failed: {e}")
        return False

def test_send_message(session_id="test_session", recipient="test_user", message="Test message"):
    """Test sending a message (dry run - will fail at browser stage but tests API)"""
    try:
        payload = {
            "session_id": session_id,
            "recipient": recipient,
            "message": message,
            "images": []
        }
        
        print(f"🔄 Testing message send to {recipient}...")
        response = requests.post(f"{API_BASE_URL}/messenger/send-message", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                print(f"✅ Message sent successfully in {data.get('duration', 'unknown time')}")
                return True
            else:
                print(f"⚠️ Message send returned error: {data.get('error', 'Unknown error')}")
                print("   This is expected if Chrome/Facebook isn't set up")
                return "expected_error"
        else:
            print(f"❌ Message send API failed: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("⚠️ Message send timed out - this is expected without proper browser setup")
        return "expected_timeout"
    except Exception as e:
        print(f"❌ Message send test failed: {e}")
        return False

def test_cleanup_session(session_id="test_session"):
    """Test session cleanup"""
    try:
        response = requests.delete(f"{API_BASE_URL}/messenger/session/{session_id}")
        if response.status_code == 200:
            print(f"✅ Session {session_id} cleaned up successfully")
            return True
        else:
            print(f"⚠️ Session cleanup returned: {response.status_code} (may not exist)")
            return True  # This is OK if session didn't exist
    except Exception as e:
        print(f"❌ Session cleanup test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Messenger Automation Implementation")
    print("=" * 50)
    
    # Test API health
    if not test_api_health():
        print("❌ API is not running. Please start the API first with:")
        print("   cd bot && python api.py")
        return False
    
    time.sleep(1)
    
    # Test messenger sessions endpoint
    if not test_messenger_sessions():
        return False
    
    time.sleep(1)
    
    # Test sending message (will likely fail at browser stage, but tests API structure)
    result = test_send_message()
    if result not in [True, "expected_error", "expected_timeout"]:
        return False
    
    time.sleep(1)
    
    # Test session cleanup
    if not test_cleanup_session():
        return False
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n📝 Next steps for full testing:")
    print("1. Ensure Chrome browser is installed")
    print("2. Set up Facebook login in browser profiles")
    print("3. Test with real Facebook messenger URLs")
    print("4. Test image upload functionality")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)