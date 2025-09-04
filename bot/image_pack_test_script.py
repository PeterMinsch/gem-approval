#!/usr/bin/env python3
"""
Image Pack Testing Script
Populates the comment approval queue with test data to test image attachment functionality
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict

# Test data for populating the approval queue
TEST_COMMENTS = [
    {
        "post_url": "https://www.facebook.com/groups/12345/posts/67890",
        "author_name": "Sarah Johnson",
        "post_text": "Looking for a beautiful engagement ring for my upcoming proposal!",
        "comment_text": "Congratulations on your upcoming engagement! We have some stunning engagement rings that would be perfect for your special moment. Would love to help you find the perfect piece!",
        "image_pack": "engagement_rings"
    },
    {
        "post_url": "https://www.facebook.com/groups/12345/posts/67891", 
        "author_name": "Michael Chen",
        "post_text": "Need some earrings to match my wife's necklace set",
        "comment_text": "That sounds like a lovely matching set! We specialize in coordinated jewelry pieces. I'd be happy to show you some earring options that would complement her necklace beautifully.",
        "image_pack": "earrings_collection"
    },
    {
        "post_url": "https://www.facebook.com/groups/12345/posts/67892",
        "author_name": "Emma Rodriguez", 
        "post_text": "My grandmother's vintage bracelet needs repair",
        "comment_text": "We'd be honored to help restore your grandmother's bracelet! Vintage pieces hold such special memories. Our skilled craftsmen specialize in delicate vintage jewelry repair.",
        "image_pack": "vintage_repair"
    },
    {
        "post_url": "https://www.facebook.com/groups/12345/posts/67893",
        "author_name": "David Wilson",
        "post_text": "Anniversary is coming up, need something special",
        "comment_text": "Anniversary jewelry is so meaningful! We have some beautiful pieces that celebrate lasting love. Would you like to see some options that would make this anniversary unforgettable?",
        "image_pack": "anniversary_collection"
    },
    {
        "post_url": "https://www.facebook.com/groups/12345/posts/67894",
        "author_name": "Lisa Thompson",
        "post_text": "Looking for custom wedding bands",
        "comment_text": "Custom wedding bands are such a beautiful way to make your ceremony unique! We specialize in creating personalized bands that tell your love story. Let's design something perfect for you both.",
        "image_pack": "wedding_bands"
    }
]

# Available image packs for testing
IMAGE_PACKS = {
    "engagement_rings": {
        "name": "Engagement Ring Collection",
        "description": "Stunning engagement rings for proposals",
        "images": [
            {"filename": "solitaire_diamond.jpg", "description": "Classic solitaire diamond ring"},
            {"filename": "vintage_halo.jpg", "description": "Vintage-inspired halo setting"},
            {"filename": "three_stone.jpg", "description": "Three stone engagement ring"}
        ]
    },
    "earrings_collection": {
        "name": "Earrings Collection", 
        "description": "Beautiful earrings to complement any outfit",
        "images": [
            {"filename": "diamond_studs.jpg", "description": "Classic diamond stud earrings"},
            {"filename": "pearl_drops.jpg", "description": "Elegant pearl drop earrings"},
            {"filename": "gold_hoops.jpg", "description": "Modern gold hoop earrings"}
        ]
    },
    "vintage_repair": {
        "name": "Vintage Restoration",
        "description": "Before and after vintage jewelry repairs",
        "images": [
            {"filename": "vintage_before.jpg", "description": "Vintage piece before restoration"},
            {"filename": "vintage_after.jpg", "description": "Beautiful restored vintage piece"},
            {"filename": "repair_process.jpg", "description": "Our careful restoration process"}
        ]
    },
    "anniversary_collection": {
        "name": "Anniversary Collection",
        "description": "Celebrate lasting love with these pieces",
        "images": [
            {"filename": "eternity_band.jpg", "description": "Diamond eternity band"},
            {"filename": "anniversary_pendant.jpg", "description": "Heart anniversary pendant"},
            {"filename": "matching_set.jpg", "description": "Matching anniversary set"}
        ]
    },
    "wedding_bands": {
        "name": "Wedding Band Collection",
        "description": "Custom wedding bands for your special day",
        "images": [
            {"filename": "his_hers_bands.jpg", "description": "His and hers wedding bands"},
            {"filename": "custom_engraving.jpg", "description": "Custom engraved bands"},
            {"filename": "unique_design.jpg", "description": "Unique custom design"}
        ]
    }
}

def get_database_connection():
    """Get connection to the bot's database"""
    db_path = "C:\\Users\\petem\\personal\\gem-approval\\bot\\bot_data.db"
    return sqlite3.connect(db_path)

def create_tables_if_not_exist(conn):
    """Create necessary tables if they don't exist"""
    cursor = conn.cursor()
    
    # Image packs table already exists with correct schema
    
    conn.commit()

def populate_image_packs(conn):
    """Populate the image_packs table with test data"""
    cursor = conn.cursor()
    
    print("Adding image packs...")
    for pack_id, pack_data in IMAGE_PACKS.items():
        cursor.execute("""
        INSERT OR REPLACE INTO image_packs (id, name, images)
        VALUES (?, ?, ?)
        """, (
            pack_id,
            pack_data["name"],
            json.dumps(pack_data["images"])
        ))
    
    conn.commit()
    print(f"Added {len(IMAGE_PACKS)} image packs")

def populate_comment_queue(conn):
    """Populate the comment_queue table with test data"""
    cursor = conn.cursor()
    
    print("Adding test comments to approval queue...")
    for comment in TEST_COMMENTS:
        cursor.execute("""
        INSERT INTO comment_queue (post_url, post_text, comment_text, post_type, post_author, image_pack_id, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (
            comment["post_url"],
            comment["post_text"],
            comment["comment_text"],
            "text",  # post_type
            comment["author_name"],  # post_author
            comment["image_pack"]  # image_pack_id
        ))
    
    conn.commit()
    print(f"Added {len(TEST_COMMENTS)} test comments")

def show_queue_status(conn):
    """Show current queue status"""
    cursor = conn.cursor()
    
    # Count comments by status
    cursor.execute("SELECT status, COUNT(*) FROM comment_queue GROUP BY status")
    status_counts = cursor.fetchall()
    
    print("\nCurrent queue status:")
    for status, count in status_counts:
        print(f"  {status}: {count} comments")
    
    # Show recent comments
    cursor.execute("""
    SELECT id, post_author, substr(comment_text, 1, 50), image_pack_id, status 
    FROM comment_queue 
    ORDER BY queued_at DESC 
    LIMIT 10
    """)
    recent_comments = cursor.fetchall()
    
    print("\nRecent comments:")
    for comment in recent_comments:
        comment_id, author, text, pack, status = comment
        print(f"  {comment_id}: {author} - {text}... [{pack}] ({status})")

def clear_test_data(conn):
    """Clear existing test data"""
    cursor = conn.cursor()
    
    print("Clearing existing test data...")
    cursor.execute("DELETE FROM comment_queue WHERE post_url LIKE '%/groups/12345/posts/%'")
    cursor.execute("DELETE FROM image_packs")
    
    conn.commit()
    print("Test data cleared")

def main():
    """Main function to populate test data"""
    print("Image Pack Testing Script")
    print("=" * 40)
    
    try:
        # Connect to database
        conn = get_database_connection()
        print("Connected to database")
        
        # Create tables
        create_tables_if_not_exist(conn)
        print("Database tables ready")
        
        # Clear any existing test data
        clear_test_data(conn)
        
        # Populate image packs
        populate_image_packs(conn)
        print("Image packs populated")
        
        # Populate comment queue
        populate_comment_queue(conn)
        print("Comment queue populated")
        
        # Show status
        show_queue_status(conn)
        
        print("\nTest data ready!")
        print("\nNow you can:")
        print("1. Open the frontend at http://localhost:8080")
        print("2. Navigate to the Comment Approval section")
        print("3. Test attaching images to comments")
        print("4. Each comment has a different image_pack assigned")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()