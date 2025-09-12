#!/usr/bin/env python3
"""
Simple test script to verify base64 image capture
"""

import sys
import logging
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from modules.image_handler import ImageHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_image_capture():
    """Test the new base64 image capture functionality"""
    
    driver = None
    try:
        logger.info("Setting up Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Test URL with images
        test_url = "https://www.facebook.com/groups/5440421919361046/permalink/31268419142801303/"
        
        logger.info(f"Navigating to: {test_url}")
        driver.get(test_url)
        
        time.sleep(10)  # Wait for page to load
        
        # Check if we can access the page
        page_title = driver.title
        logger.info(f"Page title: {page_title}")
        
        # Test the new image capture functionality
        logger.info("Testing base64 image capture...")
        
        # Find the main post element
        try:
            # Look for the main post container
            post_elements = driver.find_elements(By.CSS_SELECTOR, '[data-pagelet="FeedUnit_0"]')
            if not post_elements:
                post_elements = driver.find_elements(By.CSS_SELECTOR, '[role="article"]')
            if not post_elements:
                post_elements = driver.find_elements(By.CSS_SELECTOR, '[data-ad-preview="message"]')
            
            if post_elements:
                post_element = post_elements[0]
                logger.info("Found post element, testing image extraction...")
                
                # Test the new image handler
                config = {}
                image_handler = ImageHandler(driver, config)
                
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
                    
                    # Save first image to verify it works
                    if images[0] and images[0].startswith('data:image'):
                        import base64
                        import os
                        
                        try:
                            # Extract base64 data
                            header, data = images[0].split(',', 1)
                            image_bytes = base64.b64decode(data)
                            
                            # Save to file
                            with open('test_captured_image.png', 'wb') as f:
                                f.write(image_bytes)
                            
                            print(f"  ✅ Saved test image: test_captured_image.png ({len(image_bytes)} bytes)")
                        except Exception as save_error:
                            print(f"  ❌ Failed to save image: {save_error}")
                            
                else:
                    print("No images captured")
                
                print(f"{'='*80}")
                
                return images
                
            else:
                logger.error("Could not find post element on page")
                return []
                
        except Exception as extract_error:
            logger.error(f"Image extraction failed: {extract_error}")
            import traceback
            traceback.print_exc()
            return []
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        if driver:
            logger.info("Closing browser...")
            driver.quit()

if __name__ == "__main__":
    print("Testing canvas-based image capture system...")
    images = test_image_capture()
    
    if images:
        print("\n✅ SUCCESS: Image capture functionality is working!")
        print(f"Captured {len(images)} image(s) as base64 data")
    else:
        print("\n❌ FAILURE: Image capture functionality needs debugging")