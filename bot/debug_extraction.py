#!/usr/bin/env python3
"""
Debug script to see what elements are actually found by our selectors
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

def debug_selectors_on_page():
    """Debug what elements our selectors actually find"""
    
    bot = None
    try:
        logger.info("Initializing bot...")
        bot = FacebookAICommentBot()
        
        logger.info("Setting up browser driver...")
        bot.setup_driver()
        
        # Use a simpler URL that doesn't require login
        test_url = "https://m.facebook.com"  # Mobile version, simpler
        logger.info(f"Navigating to: {test_url}")
        bot.driver.get(test_url)
        
        import time
        time.sleep(3)
        
        # Get page source length to see if we loaded anything
        page_source = bot.driver.page_source
        logger.info(f"Page loaded, source length: {len(page_source)} characters")
        
        # Try a simple selector that should always work
        logger.info("Testing basic selectors...")
        
        # Test some basic elements
        try:
            all_divs = bot.driver.find_elements_by_xpath("//div")
            logger.info(f"Found {len(all_divs)} div elements on page")
            
            all_text_elements = bot.driver.find_elements_by_xpath("//*[text()]")
            logger.info(f"Found {len(all_text_elements)} elements with text")
            
            # Show first 3 text elements
            for i, elem in enumerate(all_text_elements[:3]):
                try:
                    text = elem.text.strip()[:50]
                    logger.info(f"  Text element {i}: '{text}...'")
                except:
                    logger.info(f"  Text element {i}: <error getting text>")
        
        except Exception as e:
            logger.error(f"Basic selector test failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if bot and bot.driver:
            logger.info("Closing browser...")
            bot.driver.quit()

if __name__ == "__main__":
    print("Debugging selector behavior...")
    debug_selectors_on_page()