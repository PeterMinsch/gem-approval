"""
Simple Performance Test - No external dependencies
Quick diagnosis of Facebook Comment Bot performance issues
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_network_performance():
    """Test network connectivity to Facebook without external deps"""
    print("\nNETWORK DIAGNOSIS")
    print("-" * 40)
    
    try:
        # Test with basic urllib (no requests dependency)
        import urllib.request
        import socket
        
        # Test DNS resolution
        start_time = time.time()
        ip = socket.gethostbyname("facebook.com")
        dns_time = time.time() - start_time
        print(f"DNS Resolution: {dns_time:.2f}s -> {ip}")
        
        # Test HTTP connection
        start_time = time.time()
        try:
            response = urllib.request.urlopen("https://facebook.com", timeout=10)
            http_time = time.time() - start_time
            print(f"HTTP Request: {http_time:.2f}s -> Status: {response.getcode()}")
        except Exception as e:
            http_time = time.time() - start_time
            print(f"HTTP Request FAILED: {http_time:.2f}s -> {e}")
            
    except Exception as e:
        print(f"Network test failed: {e}")

def test_bot_initialization():
    """Test bot initialization speed"""
    print("\nBOT INITIALIZATION TEST")
    print("-" * 40)
    
    try:
        # Import and time bot initialization
        start_time = time.time()
        from facebook_comment_bot import FacebookAICommentBot
        import_time = time.time() - start_time
        print(f"Bot import: {import_time:.2f}s")
        
        # Initialize bot
        start_time = time.time()
        bot = FacebookAICommentBot()
        init_time = time.time() - start_time
        print(f"Bot __init__: {init_time:.2f}s")
        
        return bot
        
    except Exception as e:
        print(f"Bot initialization failed: {e}")
        return None

def test_webdriver_performance(bot):
    """Test WebDriver setup and basic operations"""
    print("\nWEBDRIVER PERFORMANCE TEST")
    print("-" * 40)
    
    try:
        # Test driver setup
        start_time = time.time()
        bot.setup_driver()
        setup_time = time.time() - start_time
        print(f"WebDriver setup: {setup_time:.2f}s")
        
        if setup_time > 30:
            print("WARNING: WebDriver setup is very slow!")
        
        # Test basic navigation
        start_time = time.time()
        bot.driver.get("https://facebook.com")
        nav_time = time.time() - start_time
        print(f"Navigate to Facebook: {nav_time:.2f}s")
        
        if nav_time > 15:
            print("WARNING: Facebook navigation is very slow!")
        
        # Test current page analysis
        analyze_facebook_page(bot)
        
        return True
        
    except Exception as e:
        print(f"WebDriver test failed: {e}")
        return False

def analyze_facebook_page(bot):
    """Analyze the current Facebook page for performance issues"""
    print("\nFACEBOOK PAGE ANALYSIS")
    print("-" * 40)
    
    try:
        current_url = bot.driver.current_url
        page_title = bot.driver.title
        
        print(f"URL: {current_url}")
        print(f"Title: {page_title}")
        
        # Check for common issues
        if "checkpoint" in current_url.lower():
            print("CRITICAL: Facebook checkpoint detected!")
            
        if "login" in current_url.lower():
            print("CRITICAL: Redirected to login page!")
            
        # Test element finding speed
        test_element_finding_speed(bot)
        
    except Exception as e:
        print(f"Page analysis failed: {e}")

def test_element_finding_speed(bot):
    """Test how long common element selections take"""
    print("\nELEMENT FINDING SPEED TEST")
    print("-" * 35)
    
    test_selectors = [
        ("Articles", "//div[@role='article']"),
        ("Buttons", "//div[@role='button']"),  
        ("Links", "//a"),
        ("Images", "//img"),
        ("Divs", "//div"),
    ]
    
    total_slow_operations = 0
    
    for name, selector in test_selectors:
        start_time = time.time()
        try:
            elements = bot.driver.find_elements("xpath", selector)
            duration = time.time() - start_time
            print(f"  {name}: {len(elements)} elements in {duration:.2f}s")
            
            if duration > 3:
                print(f"    SLOW: {name} took {duration:.2f}s")
                total_slow_operations += 1
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"  {name}: FAILED after {duration:.2f}s - {str(e)[:50]}")
            total_slow_operations += 1
    
    if total_slow_operations > 2:
        print(f"\nWARNING: {total_slow_operations} slow element operations detected!")

def test_post_processing_simulation(bot):
    """Simulate post processing to identify bottlenecks"""
    print("\nPOST PROCESSING SIMULATION")
    print("-" * 40)
    
    try:
        # Navigate to the configured POST_URL
        from bravo_config import CONFIG
        post_url = CONFIG.get('POST_URL', 'https://facebook.com')
        
        print(f"Testing with URL: {post_url}")
        
        start_time = time.time()
        bot.driver.get(post_url)
        load_time = time.time() - start_time
        print(f"Page load time: {load_time:.2f}s")
        
        # Look for posts
        start_time = time.time()
        articles = bot.driver.find_elements("xpath", "//div[@role='article']")
        find_posts_time = time.time() - start_time
        print(f"Find posts: {len(articles)} found in {find_posts_time:.2f}s")
        
        if not articles:
            print("WARNING: No posts found - may indicate login issues or page changes")
            return
        
        # Test processing first post
        article = articles[0]
        print(f"\nTesting processing of first post...")
        
        # Test text extraction
        start_time = time.time()
        try:
            text_spans = article.find_elements("xpath", ".//span")
            text_content = " ".join([span.text for span in text_spans[:10]])
            text_time = time.time() - start_time
            print(f"  Text extraction: {text_time:.2f}s")
            print(f"  Sample: {text_content[:100]}...")
            
        except Exception as e:
            text_time = time.time() - start_time
            print(f"  Text extraction FAILED: {text_time:.2f}s - {e}")
        
        # Test author finding
        start_time = time.time()
        try:
            author_elements = article.find_elements("xpath", ".//h2//span | .//h3//span")
            author = author_elements[0].text if author_elements else "Unknown"
            author_time = time.time() - start_time
            print(f"  Author extraction: {author_time:.2f}s -> {author}")
            
        except Exception as e:
            author_time = time.time() - start_time
            print(f"  Author extraction FAILED: {author_time:.2f}s - {e}")
            
    except Exception as e:
        print(f"Post processing simulation failed: {e}")

def main():
    """Main diagnosis function"""
    print("Facebook Comment Bot Performance Diagnosis")
    print("=" * 55)
    print("Identifying why the bot takes 3+ minutes per post...")
    print("")
    
    # Track total test time
    total_start = time.time()
    
    # Test 1: Network
    test_network_performance()
    
    # Test 2: Bot initialization  
    bot = test_bot_initialization()
    if not bot:
        print("\nCannot continue - bot initialization failed")
        return
    
    # Test 3: WebDriver performance
    webdriver_ok = test_webdriver_performance(bot)
    if not webdriver_ok:
        print("\nWebDriver issues detected")
    
    # Test 4: Post processing simulation
    if webdriver_ok:
        test_post_processing_simulation(bot)
    
    # Cleanup
    try:
        if bot and hasattr(bot, 'driver') and bot.driver:
            bot.driver.quit()
    except:
        pass
    
    # Summary
    total_time = time.time() - total_start
    print(f"\nDIAGNOSIS SUMMARY")
    print("=" * 30)
    print(f"Total test time: {total_time:.2f}s")
    print("")
    print("NEXT STEPS:")
    print("1. Check the output above for any operations taking >10s")
    print("2. Look for CRITICAL warnings (checkpoints, login issues)")  
    print("3. Note any SLOW operations or FAILED element finding")
    print("4. If Facebook access is slow, check internet/VPN")
    print("5. If element finding is slow, Facebook may have changed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    
    print("\nPerformance diagnosis complete!")
    print("Share the output above to identify the root cause.")