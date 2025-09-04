#!/usr/bin/env python3
"""
Quick diagnostic script to test Facebook DOM stability
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bravo_config import CONFIG

def test_facebook_dom():
    print("Setting up Chrome driver...")
    
    # Setup Chrome with same options as bot
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--user-data-dir=C:\\Users\\petem\\AppData\\Local\\Google\\Chrome\\User Data")
    chrome_options.add_argument("--profile-directory=Default")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("Navigating to Facebook group...")
        driver.get(CONFIG['POST_URL'])
        time.sleep(5)  # Wait for page to load
        
        print("Testing XPath selectors...")
        
        # Test the main XPath used by the bot
        main_xpath = ("//a[contains(@href, '/groups/') and contains(@href, '/posts/') and not(contains(@href, 'comment_id')) and string-length(@href) > 60]" +
                     " | //a[contains(@href, '/photo/?fbid=') and contains(@href, 'set=')]" +
                     " | //a[contains(@href, '/commerce/listing/') and string-length(@href) > 80]")
        
        for attempt in range(3):
            print(f"\n--- Attempt {attempt + 1} ---")
            
            try:
                # Find elements
                elements = driver.find_elements(By.XPATH, main_xpath)
                print(f"Found {len(elements)} elements")
                
                if elements:
                    print("Testing element stability...")
                    for i, element in enumerate(elements[:3]):  # Test first 3 elements
                        try:
                            href = element.get_attribute('href')
                            print(f"Element {i+1}: {href[:100]}...")
                            
                            # Test immediate re-access
                            href2 = element.get_attribute('href')
                            if href == href2:
                                print(f"  ✓ Element {i+1} is stable")
                            else:
                                print(f"  ⚠ Element {i+1} changed: {href2[:100]}...")
                                
                        except StaleElementReferenceException:
                            print(f"  ✗ Element {i+1} became stale immediately")
                        except Exception as e:
                            print(f"  ✗ Element {i+1} error: {e}")
                            
                else:
                    print("No elements found with main XPath")
                    
                # Test simpler fallback
                simple_xpath = "//a[contains(@href, '/groups/')]"
                simple_elements = driver.find_elements(By.XPATH, simple_xpath)
                print(f"Simple XPath found {len(simple_elements)} elements")
                
            except Exception as e:
                print(f"Error in attempt {attempt + 1}: {e}")
            
            if attempt < 2:
                print("Waiting 3 seconds before next attempt...")
                time.sleep(3)
        
        print("\nTesting page refresh impact...")
        driver.refresh()
        time.sleep(5)
        
        elements = driver.find_elements(By.XPATH, main_xpath)
        print(f"After refresh: Found {len(elements)} elements")
        
    finally:
        print("Closing driver...")
        driver.quit()

if __name__ == "__main__":
    test_facebook_dom()