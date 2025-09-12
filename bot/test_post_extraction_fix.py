#!/usr/bin/env python3
"""
Test script to verify post text extraction stops before comments
"""

import sys
import logging
from facebook_comment_bot import FacebookAICommentBot

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_post_extraction(post_url):
    """Test post text extraction on a specific URL"""
    
    bot = None
    try:
        logger.info("Initializing bot...")
        bot = FacebookAICommentBot()
        
        logger.info("Setting up browser driver...")
        bot.setup_driver()
        
        logger.info(f"Navigating to: {post_url}")
        bot.driver.get(post_url)
        
        import time
        time.sleep(8)  # Wait longer for page to load
        
        # Check if we can access the page
        page_title = bot.driver.title
        logger.info(f"Page title: {page_title}")
        
        # Take a screenshot for debugging
        logger.info("Taking screenshot for debugging...")
        bot.driver.save_screenshot("debug_page.png")
        
        logger.info("Extracting post text...")
        post_text = bot.get_post_text()
        
        print("\n" + "="*80)
        print("EXTRACTED POST TEXT (should NOT include comments):")
        print("-"*80)
        print(post_text)
        print("-"*80)
        
        # Check if common comment indicators are present
        comment_indicators = ['replied', 'commented', 'write a comment', 'most relevant']
        found_comment_text = any(indicator in post_text.lower() for indicator in comment_indicators)
        
        if found_comment_text:
            print("⚠️  WARNING: Post text may contain comment data!")
        else:
            print("✅ SUCCESS: Post text appears clean (no obvious comment markers)")
        
        return post_text
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if bot and bot.driver:
            logger.info("Closing browser...")
            bot.driver.quit()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        # Default test URL (you can change this)
        test_url = "https://www.facebook.com/photo/?fbid=10162065334448575&set=gm.31268419142801303&idorvanity=5440421919361046"
    
    print(f"Testing post extraction on: {test_url}")
    test_post_extraction(test_url)