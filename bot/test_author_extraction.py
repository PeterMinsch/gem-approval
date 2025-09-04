#!/usr/bin/env python3
"""
Test script to verify author name extraction on a specific Facebook post
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from facebook_comment_bot import FacebookAICommentBot
import logging

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def test_author_extraction():
    """Test author name extraction with a real post"""
    logger.info("🧪 Testing author name extraction...")
    
    # Initialize bot (but don't start it)
    bot = FacebookAICommentBot()
    
    try:
        # Start browser and login
        logger.info("🚀 Starting browser and logging in...")
        bot.setup_driver()
        
        # Navigate to the test post
        test_post_url = "https://www.facebook.com/photo/?fbid=24358671130457313&set=pcb.30915708561405698"
        
        logger.info(f"🔗 Navigating to test post: {test_post_url}")
        bot.driver.get(test_post_url)
        
        # Wait a moment for page to load
        import time
        time.sleep(10)  # Give extra time for Facebook to load
        
        # Extract author name
        logger.info("👤 Extracting post author name...")
        author_name = bot.get_post_author()
        
        print("\n" + "="*80)
        print("EXTRACTED AUTHOR NAME:")
        print("="*80)
        if author_name:
            print(f"Raw author name: '{author_name}'")
            
            # Test first name extraction
            first_name = bot.comment_generator.extract_first_name(author_name)
            print(f"Extracted first name: '{first_name}'")
            
            # Test personalization
            template = "Hi {{author_name}}! Great post!"
            personalized = bot.comment_generator.personalize_comment(template, author_name)
            print(f"Personalized comment: '{personalized}'")
            
            print("\n✅ SUCCESS: Author name extraction working!")
        else:
            print("FAILED: Could not extract author name")
            
            # Debug: Try to find author elements manually
            logger.info("🔍 Debugging author element detection...")
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Try different selectors
                selectors = [
                    "//h2//a[contains(@href, '/')]",
                    "//h3//a[contains(@href, '/')]", 
                    "//strong//a[contains(@href, '/')]",
                    "//a[contains(@href, '/') and contains(@role, 'link')]",
                    "//div[@data-ad-preview='message']//a",
                    "//div[contains(@class, 'author')]//a"
                ]
                
                for i, selector in enumerate(selectors, 1):
                    try:
                        elements = bot.driver.find_elements(By.XPATH, selector)
                        logger.info(f"Selector {i}: Found {len(elements)} elements")
                        for j, elem in enumerate(elements[:3]):  # Show first 3
                            try:
                                text = elem.text.strip()
                                href = elem.get_attribute('href')
                                logger.info(f"  Element {j+1}: text='{text}', href='{href}'")
                            except:
                                pass
                    except Exception as e:
                        logger.info(f"Selector {i} failed: {e}")
                        
            except Exception as debug_error:
                logger.error(f"Debug failed: {debug_error}")
                
        print("="*80)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            bot.cleanup()
        except:
            pass

if __name__ == "__main__":
    logger.info("🚀 Starting author extraction test...")
    
    print("\n" + "="*60)
    print("AUTHOR NAME EXTRACTION TEST")
    print("="*60)
    print("This test will:")
    print("1. Open a browser and login to Facebook")
    print("2. Navigate to the specific post URL")
    print("3. Extract the post author name using current selectors")
    print("4. Test first name extraction and personalization")
    print("5. Debug selector issues if extraction fails")
    print("="*60 + "\n")
    
    test_author_extraction()
    logger.info("✅ Test complete!")