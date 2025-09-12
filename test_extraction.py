#!/usr/bin/env python3
"""
Test the Facebook ID extraction function
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from modules.post_extractor import PostExtractor

def test_extraction():
    url = "https://www.facebook.com/messages/e2ee/t/1476291396736716"
    result = PostExtractor.extract_facebook_id_from_profile_url(url)
    print(f"URL: {url}")
    print(f"Extracted ID: {result}")
    print(f"Expected: 1476291396736716")
    
    # Test if the condition is working
    print(f"URL contains '/messages/': {'/messages/' in url}")
    print(f"URL contains '/messages/e2ee/t/': {'/messages/e2ee/t/' in url}")

if __name__ == "__main__":
    test_extraction()