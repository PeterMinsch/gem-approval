#!/usr/bin/env python3
"""
Backfill categories for existing comments that don't have them
"""

import sys
import os
sys.path.append('bot')

from bot.database import BotDatabase
from bot.classifier import PostClassifier
from bot.bravo_config import CONFIG
import json

def backfill_categories():
    """Backfill categories for existing comments"""
    
    print("🔄 Starting category backfill for existing comments...")
    
    # Initialize database and classifier
    db = BotDatabase()
    classifier = PostClassifier()
    
    # Get comments with empty categories
    import sqlite3
    conn = sqlite3.connect('bot/bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, post_text, detected_categories 
        FROM comment_queue 
        WHERE detected_categories = '[]' OR detected_categories IS NULL
        LIMIT 10
    """)
    
    comments = cursor.fetchall()
    print(f"📋 Found {len(comments)} comments without categories")
    
    updated_count = 0
    
    for comment_id, post_text, current_categories in comments:
        print(f"\n🔍 Processing comment {comment_id}:")
        print(f"   Text: {post_text[:100]}...")
        
        try:
            # Create a mock classification object
            class MockClassification:
                def __init__(self):
                    self.post_type = "SERVICE"  # Default
                    self.matched_keywords = []
                    self.intent = "SERVICE"
            
            mock_classification = MockClassification()
            
            # Detect categories using the classifier
            detected_categories = classifier.detect_jewelry_categories(post_text, mock_classification)
            
            if detected_categories:
                print(f"   ✅ Detected: {detected_categories}")
                
                # Update the database
                categories_json = json.dumps(detected_categories)
                cursor.execute("""
                    UPDATE comment_queue 
                    SET detected_categories = ? 
                    WHERE id = ?
                """, (categories_json, comment_id))
                
                updated_count += 1
            else:
                print(f"   ❌ No categories detected")
                
        except Exception as e:
            print(f"   ⚠️ Error processing comment {comment_id}: {e}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Backfill complete!")
    print(f"   Updated {updated_count} comments with categories")
    print(f"   You can now test Smart Mode in the UI")
    
    # Show some examples
    print(f"\n📋 Sample results:")
    conn = sqlite3.connect('bot/bot_data.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, post_text, detected_categories 
        FROM comment_queue 
        WHERE detected_categories != '[]' AND detected_categories IS NOT NULL
        LIMIT 3
    """)
    
    results = cursor.fetchall()
    for comment_id, post_text, categories in results:
        print(f"   💎 Comment {comment_id}: {json.loads(categories)} | {post_text[:50]}...")
    
    conn.close()

if __name__ == "__main__":
    backfill_categories()