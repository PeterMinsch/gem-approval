#!/usr/bin/env python3
"""
Create a test comment for safe Selenium automation testing
Uses your own Messenger URL so you can test without bothering anyone
Now includes: image pack integration, category detection, proper JSON formatting
"""

import sys
import os
import json
import logging

# Change to the bot directory where the database is located
bot_dir = os.path.join(os.path.dirname(__file__), 'bot')
os.chdir(bot_dir)
sys.path.append(bot_dir)

from database import db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_or_create_image_pack():
    """Get existing image pack or use default one"""
    try:
        image_packs = db.get_image_packs()
        if image_packs:
            # Use the first available image pack (preferably Generic Card)
            default_pack = next((pack for pack in image_packs if pack['is_default']), image_packs[0])
            logger.info(f"Using image pack: {default_pack['name']}")
            return default_pack['id']
        else:
            logger.warning("No image packs found")
            return None
    except Exception as e:
        logger.error(f"Error getting image pack: {e}")
        return None

def create_test_comment():
    """Create a modern test comment with all current features"""
    
    # Get image pack for test
    image_pack_id = get_or_create_image_pack()
    
    # Use proper JSON formatting for post_images (consistent with other scripts)
    test_images = ["uploads/image-packs/generic/test_ring.jpg"]  # Use existing verified file
    
    test_comment = {
        'post_url': 'https://www.facebook.com/test/post/selenium-test-modern',
        'post_text': 'Looking for a custom jewelry designer who can create beautiful engagement rings with CAD design. Need someone experienced with precious metals and gemstone setting. Also interested in stone setting services and custom manufacturing.',
        'generated_comment': "Hi there! Beautiful work! We're Bravo Creations, full-service B2B jewelry manufacturer specializing in CAD design, casting, and stone setting. We'd love to help bring your custom pieces to life! Check us out: https://welcome.bravocreations.com - Call us: (760) 431-9977 — ask for Eugene.",
        'post_type': 'service',
        'post_author': 'Test User (Your Account)',
        'post_author_url': 'https://www.facebook.com/messages/e2ee/t/1476291396736716',  # Your Messenger URL
        'post_engagement': '12 likes, 5 comments',
        'post_images': test_images,  # Use list format (will be JSON encoded by add_to_comment_queue)
        'post_screenshot': None,
        'image_pack_id': image_pack_id,
        'detected_categories': ['CAD', 'SETTING', 'GENERIC'],  # Modern category detection
        'status': 'pending'
    }
    
    try:
        # Insert the test comment using modern database function
        comment_id = db.add_to_comment_queue(
            post_url=test_comment['post_url'],
            post_text=test_comment['post_text'],
            comment_text=test_comment['generated_comment'],
            post_type=test_comment['post_type'],
            post_screenshot=test_comment['post_screenshot'],
            post_images=json.dumps(test_comment['post_images']),  # Proper JSON encoding
            post_author=test_comment['post_author'],
            post_engagement=test_comment['post_engagement'],
            image_pack_id=test_comment['image_pack_id'],
            detected_categories=test_comment['detected_categories'],
            post_author_url=test_comment['post_author_url']
        )
        
        print("\n" + "="*60)
        print("SUCCESS: MODERN TEST COMMENT CREATED")
        print("="*60)
        print(f"Comment ID: {comment_id}")
        print(f"Author: {test_comment['post_author']}")
        print(f"Messenger URL: {test_comment['post_author_url']}")
        print(f"Categories: {', '.join(test_comment['detected_categories'])}")
        print(f"Image Pack: {image_pack_id or 'None'}")
        print(f"Test Image: {test_comment['post_images'][0] if test_comment['post_images'] else 'None'}")
        print(f"Message: {test_comment['generated_comment'][:80]}...")
        
        print(f"\nTESTING WORKFLOW:")
        print(f"1. Open Comment Queue in browser (http://localhost:3000)")
        print(f"2. Find your test comment (ID: {comment_id})")
        print(f"3. Test user-selectable images:")
        print(f"   - Click 'Select Images' toggle")
        print(f"   - Choose from Generic Card image pack")
        print(f"   - Select multiple images if desired")
        print(f"4. Toggle to 'Full Automation (3-6s)'")
        print(f"5. Click 'Generate & Send Message'")
        print(f"6. Check your Messenger for the automated message!")
        print(f"\nFEATURES INCLUDED:")
        print(f"• Image pack integration")
        print(f"• Category detection")
        print(f"• Proper JSON formatting")
        print(f"• Modern database schema")
        print(f"• Verified image paths")
        print(f"• User-selectable images support")
        print("="*60)
        
        return comment_id
        
    except Exception as e:
        logger.error(f"Failed to create test comment: {e}")
        print(f"❌ Error: {e}")
        return None

def show_summary():
    """Show summary of pending comments"""
    try:
        pending = db.get_pending_comments(limit=5)
        print(f"\nCURRENT QUEUE STATUS:")
        print(f"Pending comments: {len(pending)}")
        if pending:
            print(f"\nRecent comments:")
            for comment in pending[:3]:
                print(f"  • ID {comment['id']}: {comment['post_author']} - {comment['post_type']}")
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")

if __name__ == "__main__":
    print("Creating Modern Test Comment for Selenium Automation...")
    print("=" * 60)
    
    result = create_test_comment()
    
    if result:
        show_summary()
        print(f"\nReady for testing! Comment ID: {result}")
    else:
        print(f"\nFailed to create test comment")
        sys.exit(1)