#!/usr/bin/env python3
"""Simple test for posting with the specific Facebook link"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import requests
from database import BotDatabase

def test_specific_link():
    """Test with the user's specific Facebook link"""
    
    print("=== Testing Specific Facebook Link ===")
    
    # The specific link from the user
    test_url = "https://www.facebook.com/photo/?fbid=1263404155797914&set=g.5440421919361046"
    
    print(f"\nTesting with URL: {test_url}")
    
    # Check API health first
    print("Checking API health...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"API is healthy")
            print(f"Bot running: {health.get('bot_running')}")
            print(f"Comments queued: {health.get('comments_queued')}")
        else:
            print(f"API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Cannot reach API: {e}")
        return False
    
    # Create a test comment
    db = BotDatabase()
    
    # Use the comment generator for proper personalization
    from facebook_comment_bot import CommentGenerator
    from bravo_config import CONFIG
    
    generator = CommentGenerator(CONFIG)
    test_comment = generator.generate_comment("service", "Test diamond post for posting verification", "Test Jeweler")
    
    print("\nCreating test comment for specific URL...")
    queue_id = db.add_to_comment_queue(
        post_url=test_url,
        post_text="Test diamond post for posting verification",
        comment_text=test_comment,
        post_type="service",
        post_author="Test Jeweler",
        post_engagement="Diamond inquiry"
    )
    
    if not queue_id:
        print("Failed to create test comment")
        return False
    
    print(f"Created test comment with ID: {queue_id}")
    
    # Test the approve and post flow
    api_url = "http://localhost:8000/comments/approve"
    
    print(f"\nSending approval request...")
    try:
        response = requests.post(api_url, json={
            "comment_id": str(queue_id),
            "action": "approve"
        }, timeout=15)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nAPI Response:")
            print(f"  Success: {result.get('success')}")
            print(f"  Message: {result.get('message')}")
            
            if "queued for posting" in result.get('message', ''):
                print("\nSUCCESS: Comment queued for posting!")
                
                # Monitor the posting status
                print("\nMonitoring posting status...")
                for i in range(30):  # Check for 30 seconds
                    time.sleep(1)
                    
                    # Check database status
                    history = db.get_comment_history()
                    for comment in history:
                        if comment['id'] == queue_id:
                            current_status = comment['status']
                            print(f"\rStatus check {i+1}/30: {current_status}", end="", flush=True)
                            
                            if current_status == "posted":
                                print(f"\n\nSUCCESS! Comment posted to {test_url}")
                                print(f"Comment: {test_comment}")
                                return True
                            elif current_status == "failed":
                                error_msg = comment.get('error_message', 'Unknown error')
                                print(f"\n\nFAILED: Posting failed - {error_msg}")
                                return False
                            break
                    
                    if i == 29:  # Last check
                        print(f"\n\nTIMEOUT: Posting took longer than expected")
                        print("Check logs for more details")
                        return False
                        
                return False
            else:
                print(f"\nERROR: {result.get('message')}")
                return False
                
        else:
            print(f"\nAPI Error: {response.status_code}")
            try:
                error = response.json()
                print(f"Error details: {error}")
            except:
                print(f"Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\nRequest timed out")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False

if __name__ == "__main__":
    success = test_specific_link()
    
    if success:
        print("\nSPECIFIC LINK TEST PASSED!")
        print("Real-time posting is working with your Facebook link!")
    else:
        print("\nSPECIFIC LINK TEST FAILED")
        print("Check the logs for more details about what went wrong")