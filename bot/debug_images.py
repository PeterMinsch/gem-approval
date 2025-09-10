#!/usr/bin/env python3
"""
Debug script to see what images are on the Facebook page
"""

import sys
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def debug_page_images():
    """Debug what images are available on the page"""
    
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
        
        # Debug: Find ALL images on the page
        all_images = driver.find_elements(By.TAG_NAME, "img")
        logger.info(f"Found {len(all_images)} total img elements on page")
        
        print(f"\n{'='*80}")
        print("ALL IMAGES ON PAGE:")
        print(f"{'='*80}")
        
        for i, img in enumerate(all_images[:10]):  # Show first 10 images
            try:
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")
                width = img.get_attribute("width")
                height = img.get_attribute("height")
                
                print(f"Image {i+1}:")
                print(f"  src: {src[:100] if src else 'None'}...")
                print(f"  alt: {alt}")
                print(f"  size: {width}x{height}")
                print(f"  visible: {img.is_displayed()}")
                print()
                
            except Exception as e:
                print(f"Image {i+1}: Error - {e}")
        
        # Look for the main post element
        print("LOOKING FOR POST ELEMENTS:")
        print("-" * 40)
        
        selectors = [
            '[data-pagelet="FeedUnit_0"]',
            '[role="article"]', 
            '[data-ad-preview="message"]',
            '[data-testid="post_message"]',
            'div[class*="story_body"]'
        ]
        
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"Selector '{selector}': {len(elements)} elements")
            
            if elements:
                post_element = elements[0]
                post_images = post_element.find_elements(By.TAG_NAME, "img")
                print(f"  Images in first element: {len(post_images)}")
                
                for j, img in enumerate(post_images[:3]):
                    try:
                        src = img.get_attribute("src")
                        print(f"    Post Image {j+1}: {src[:80] if src else 'None'}...")
                    except:
                        print(f"    Post Image {j+1}: Error getting src")
        
        print(f"{'='*80}")
        
        # Take a screenshot for manual inspection
        driver.save_screenshot("debug_page.png")
        print("Saved screenshot as debug_page.png")
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            logger.info("Closing browser...")
            driver.quit()

if __name__ == "__main__":
    print("Debugging images on Facebook page...")
    debug_page_images()