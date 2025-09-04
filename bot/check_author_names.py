#!/usr/bin/env python3
"""Check if author names are being extracted properly"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import BotDatabase

def check_author_extraction():
    """Check recent database entries for author name extraction"""
    
    db = BotDatabase()
    history = db.get_comment_history()
    
    print("=== Recent Database Entries ===")
    print(f"Total entries: {len(history)}")
    
    for i, comment in enumerate(history[-10:]):  # Last 10 entries
        print(f"\n{i+1}. Entry ID: {comment.get('id')}")
        print(f"   Author: '{comment.get('post_author', 'None')}'")
        comment_text = comment.get('comment_text', '')
        print(f"   Comment: '{comment_text[:80]}...'")
        
        # Check if comment is personalized
        if 'Hi there' in comment_text:
            print("   -> Uses generic greeting")
        elif comment_text.startswith('Hi ') and '!' in comment_text:
            # Extract the name from the comment
            name_part = comment_text[3:comment_text.find('!')].strip()
            print(f"   -> Personalized with: '{name_part}'")
        else:
            print("   -> Other greeting format")

if __name__ == "__main__":
    check_author_extraction()