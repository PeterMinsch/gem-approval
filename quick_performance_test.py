"""
Quick Performance Test Script
Run this to immediately identify performance bottlenecks in the Facebook Comment Bot
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

import time
import logging
from bot.performance_monitor import perf_monitor, diagnose_webdriver_performance, diagnose_network_performance
from bot.facebook_comment_bot import FacebookAICommentBot
from bot.bravo_config import CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_performance_diagnosis():
    """Run immediate performance diagnosis"""
    print("🚀 Starting Facebook Comment Bot Performance Diagnosis")
    print("=" * 60)
    
    # Network test first (no browser needed)
    diagnose_network_performance()
    
    bot = None
    try:
        # Initialize bot
        print("\n🤖 Initializing Bot...")
        start_time = time.time()
        bot = FacebookAICommentBot()
        init_time = time.time() - start_time
        print(f"Bot initialization: {init_time:.2f}s")
        
        # Setup driver
        print("\n🌐 Setting up WebDriver...")
        start_time = time.time()
        bot.setup_driver()
        driver_time = time.time() - start_time
        print(f"WebDriver setup: {driver_time:.2f}s")
        
        # Diagnose WebDriver
        diagnose_webdriver_performance(bot.driver)
        
        # Test Facebook login/access speed
        print("\n📱 Testing Facebook Access...")
        start_time = time.time()
        bot.driver.get(CONFIG['POST_URL'])
        page_load_time = time.time() - start_time
        print(f"Facebook page load: {page_load_time:.2f}s")
        
        if page_load_time > 15:
            print("🚨 WARNING: Facebook page loading very slowly!")
        
        # Test element finding speed
        print("\n🔍 Testing Element Finding Speed...")
        test_element_finding_performance(bot)
        
        # Test post processing if we can find posts
        print("\n📄 Testing Post Processing Speed...")
        test_post_processing_performance(bot)
        
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        
    finally:
        # Cleanup
        if bot and hasattr(bot, 'driver') and bot.driver:
            bot.driver.quit()
            
        # Print final summary
        perf_monitor.print_performance_summary()

def test_element_finding_performance(bot):
    """Test how long it takes to find common elements"""
    
    common_selectors = [
        ("Articles", "//div[@role='article']"),
        ("Buttons", "//div[@role='button']"),
        ("Links", "//a"),
        ("Images", "//img"),
        ("Text Areas", "//textarea"),
    ]
    
    for name, selector in common_selectors:
        start_time = time.time()
        try:
            elements = bot.driver.find_elements("xpath", selector)
            duration = time.time() - start_time
            print(f"  {name}: Found {len(elements)} in {duration:.2f}s")
            
            if duration > 3:
                print(f"    🚨 SLOW: {name} selector took {duration:.2f}s")
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"  {name}: FAILED after {duration:.2f}s - {e}")

def test_post_processing_performance(bot):
    """Test post processing speed if posts are available"""
    
    try:
        # Look for posts on current page
        start_time = time.time()
        articles = bot.driver.find_elements("xpath", "//div[@role='article']")
        find_time = time.time() - start_time
        
        print(f"  Found {len(articles)} posts in {find_time:.2f}s")
        
        if not articles:
            print("  ⚠️ No posts found on current page")
            return
        
        # Test processing first post
        article = articles[0]
        
        # Test text extraction
        start_time = time.time()
        try:
            # Simple text extraction test
            text_elements = article.find_elements("xpath", ".//div//span")
            text_content = " ".join([elem.text for elem in text_elements[:5]])  # First 5 spans
            text_time = time.time() - start_time
            print(f"  Post text extraction: {text_time:.2f}s")
            print(f"    Sample text: {text_content[:100]}...")
            
        except Exception as e:
            text_time = time.time() - start_time
            print(f"  Post text extraction FAILED after {text_time:.2f}s: {e}")
        
        # Test author extraction
        start_time = time.time()
        try:
            author_elements = article.find_elements("xpath", ".//h2//span | .//h3//span")
            author = author_elements[0].text if author_elements else "Unknown"
            author_time = time.time() - start_time
            print(f"  Author extraction: {author_time:.2f}s")
            print(f"    Author: {author}")
            
        except Exception as e:
            author_time = time.time() - start_time
            print(f"  Author extraction FAILED after {author_time:.2f}s: {e}")
        
        # Test image finding
        start_time = time.time()
        try:
            images = article.find_elements("xpath", ".//img")
            image_time = time.time() - start_time
            print(f"  Image finding: Found {len(images)} images in {image_time:.2f}s")
            
        except Exception as e:
            image_time = time.time() - start_time
            print(f"  Image finding FAILED after {image_time:.2f}s: {e}")
            
    except Exception as e:
        print(f"  Post processing test failed: {e}")

def analyze_current_page_performance(bot):
    """Analyze performance of current page state"""
    
    current_url = bot.driver.current_url
    page_title = bot.driver.title
    
    print(f"\n📄 Current Page Analysis:")
    print(f"  URL: {current_url}")
    print(f"  Title: {page_title}")
    
    # Check for performance-impacting elements
    start_time = time.time()
    all_elements = bot.driver.find_elements("xpath", "//*")
    element_count_time = time.time() - start_time
    
    print(f"  Total DOM elements: {len(all_elements)} (counted in {element_count_time:.2f}s)")
    
    if len(all_elements) > 5000:
        print("  🚨 WARNING: Very heavy DOM with 5000+ elements")
    
    # Check for loading indicators
    spinners = bot.driver.find_elements("css selector", "[role='progressbar']")
    if spinners:
        print(f"  🔄 Active loading spinners: {len(spinners)}")
    
    # Check for common anti-bot indicators
    if "checkpoint" in current_url.lower():
        print("  🚨 CRITICAL: Facebook checkpoint detected!")
    
    if "login" in current_url.lower():
        print("  🚨 CRITICAL: Redirected to login page!")

if __name__ == "__main__":
    print("🔍 Quick Performance Test for Facebook Comment Bot")
    print("This will identify performance bottlenecks without modifying your code")
    print("")
    
    try:
        quick_performance_diagnosis()
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        
    print("\n✅ Performance diagnosis complete!")
    print("Check the output above for slow operations and bottlenecks.")
    print("Refer to PERFORMANCE_DIAGNOSIS_PLAN.md for detailed optimization steps.")