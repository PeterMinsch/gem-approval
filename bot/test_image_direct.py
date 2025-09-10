#!/usr/bin/env python3
"""
Direct test of image capture functionality using existing comment data
"""

import sqlite3
import json
from modules.message_generator import MessageGenerator
from bravo_config import CONFIG

async def test_image_capture_direct():
    """Test image capture using a real comment from database"""
    
    # Get a real comment from the database
    conn = sqlite3.connect('comments.db')
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()
    
    # Find a comment with a Facebook URL
    cursor.execute("""
        SELECT * FROM comments 
        WHERE post_url LIKE '%facebook.com%' 
        LIMIT 1
    """)
    
    db_comment = cursor.fetchone()
    conn.close()
    
    if not db_comment:
        print("X No Facebook comments found in database")
        return False
    
    print(f"Found comment: {db_comment['id']}")
    print(f"Post URL: {db_comment['post_url']}")
    print(f"Author: {db_comment['author_name']}")
    print(f"Post text: {db_comment['post_text'][:100]}...")
    
    # Convert to dict
    comment_dict = {
        'id': db_comment['id'],
        'post_url': db_comment['post_url'],
        'post_author': db_comment['author_name'],
        'post_text': db_comment['post_text'],
        'comment_text': db_comment['comment_text'],
        'status': db_comment['status']
    }
    
    try:
        # Test the message generator with image capture
        print(f"\n{'='*60}")
        print("TESTING IMAGE CAPTURE...")
        print(f"{'='*60}")
        
        generator = MessageGenerator(CONFIG)
        
        # This should trigger image capture
        result = await generator.generate_dm_message(comment_dict)
        
        if result:
            print(f"+ Message generated successfully!")
            print(f"Message: {result['message'][:100]}...")
            
            # Check if images were captured
            if result.get('post_images'):
                print(f"Images captured: {len(result['post_images'])}")
                for i, img_data in enumerate(result['post_images']):
                    if img_data and img_data.startswith('data:image'):
                        print(f"  Image {i+1}: + Valid base64 ({len(img_data)} chars)")
                    else:
                        print(f"  Image {i+1}: X Invalid: {img_data[:50] if img_data else 'None'}...")
            else:
                print("No images captured")
            
            # Check screenshot
            if result.get('post_screenshot'):
                print(f"Screenshot captured: + ({len(result['post_screenshot'])} chars)")
            else:
                print("No screenshot captured")
            
            return True
        else:
            print("X Message generation failed")
            return False
            
    except Exception as e:
        print(f"X Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    print("Testing image capture with real comment data...")
    success = asyncio.run(test_image_capture_direct())
    
    if success:
        print("\n+ SUCCESS: Image capture functionality is working!")
    else:
        print("\nX FAILURE: Image capture needs debugging")