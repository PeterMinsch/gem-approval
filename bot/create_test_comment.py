#!/usr/bin/env python3
"""Create a test comment in the database for testing posting"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import BotDatabase

def create_test_comment():
    """Create a test comment for posting verification"""
    
    db = BotDatabase()
    
    # Use a real Facebook post URL from the group
    test_url = "https://www.facebook.com/photo/?fbid=122143481480825821&set=g.5440421919361046"
    test_comment = "Hi! This is a test comment from Bravo Creations. Testing the new window-based posting system. (760) 431-9977 • welcome.bravocreations.com"
    test_post_text = "Test post for verifying real-time comment posting"
    
    print("Creating test comment in database...")
    print(f"URL: {test_url}")
    print(f"Comment: {test_comment[:50]}...")
    
    queue_id = db.add_to_comment_queue(
        post_url=test_url,
        post_text=test_post_text,
        comment_text=test_comment,
        post_type="service",
        post_author="Test Author",
        post_engagement="Test engagement"
    )
    
    if queue_id:
        print(f"\n[SUCCESS] Test comment created with ID: {queue_id}")
        print("\nNext steps:")
        print("1. Go to http://localhost:3000 to view the comment queue")
        print("2. Click 'Approve' on the test comment")
        print("3. Watch the browser window to see the comment being posted")
        return queue_id
    else:
        print("\n[FAIL] Failed to create test comment")
        return None

if __name__ == "__main__":
    queue_id = create_test_comment()
    
    if queue_id:
        print(f"\n[SUCCESS] Test comment ID: {queue_id}")
    else:
        print("\n[FAIL] Failed to create test comment")