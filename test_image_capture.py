#!/usr/bin/env python3
"""
Test script to verify the new canvas-based image capture system
"""

import sys
import logging
import json
from bot.facebook_comment_bot import FacebookAICommentBot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_image_capture():
    """Test the new base64 image capture functionality"""
    
    bot = None
    try:
        logger.info("Initializing bot...")
        bot = FacebookAICommentBot()
        
        logger.info("Setting up browser driver...")
        bot.setup_driver()
        
        # Test URL with images
        test_url = "https://www.facebook.com/groups/5440421919361046/permalink/31268419142801303/"
        
        logger.info(f"Navigating to: {test_url}")
        bot.driver.get(test_url)
        
        import time
        time.sleep(10)  # Wait for page to load
        
        # Check if we can access the page
        page_title = bot.driver.title
        logger.info(f"Page title: {page_title}")
        
        # Test the new image capture functionality
        logger.info("Testing base64 image capture...")
        
        from selenium.webdriver.common.by import By
        
        # Find the main post element
        try:
            # Look for the main post container
            post_elements = bot.driver.find_elements(By.CSS_SELECTOR, '[data-pagelet="FeedUnit_0"]')
            if not post_elements:
                post_elements = bot.driver.find_elements(By.CSS_SELECTOR, '[role="article"]')
            if not post_elements:
                post_elements = bot.driver.find_elements(By.CSS_SELECTOR, '[data-ad-preview="message"]')
            
            if post_elements:
                post_element = post_elements[0]
                logger.info("Found post element, testing image extraction...")
                
                # Test the new image handler
                from bot.modules.image_handler import ImageHandler
                
                config = {}
                image_handler = ImageHandler(bot.driver, config)
                
                # Extract images using new base64 method
                images = image_handler.extract_post_images(post_element)
                
                print(f"\n{'='*80}")
                print("IMAGE CAPTURE TEST RESULTS:")
                print(f"{'='*80}")
                print(f"Number of images captured: {len(images)}")
                
                if images:
                    for i, img_data in enumerate(images):
                        if img_data and img_data.startswith('data:image'):
                            print(f"Image {i+1}: ✅ Valid base64 data ({len(img_data)} chars)")
                            print(f"  Type: {img_data.split(',')[0]}")
                            print(f"  Data preview: {img_data[:100]}...")
                        else:
                            print(f"Image {i+1}: ❌ Invalid data: {img_data[:100] if img_data else 'None'}")
                else:
                    print("No images captured")
                
                # Test screenshot functionality
                logger.info("Testing post screenshot...")
                screenshot = bot.capture_post_screenshot()
                
                if screenshot:
                    print(f"Screenshot: ✅ Valid base64 data ({len(screenshot)} chars)")
                    print(f"  Data preview: {screenshot[:100]}...")
                else:
                    print("Screenshot: ❌ No screenshot captured")
                
                print(f"{'='*80}")
                
                return images, screenshot
                
            else:
                logger.error("Could not find post element on page")
                return [], None
                
        except Exception as extract_error:
            logger.error(f"Image extraction failed: {extract_error}")
            import traceback
            traceback.print_exc()
            return [], None
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return [], None
        
    finally:
        if bot and bot.driver:
            logger.info("Closing browser...")
            bot.driver.quit()

if __name__ == "__main__":
    print("Testing canvas-based image capture system...")
    images, screenshot = test_image_capture()
    
    if images or screenshot:
        print("\n✅ SUCCESS: Image capture functionality is working!")
    else:
        print("\n❌ FAILURE: Image capture functionality needs debugging")