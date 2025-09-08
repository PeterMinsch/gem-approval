"""
Test the optimized author extraction performance
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

import time
import logging

# Configure detailed logging to see the optimization in action
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_author_extraction_performance():
    """Test the optimized author extraction"""
    print("AUTHOR EXTRACTION OPTIMIZATION TEST")
    print("=" * 50)
    
    try:
        from facebook_comment_bot import FacebookAICommentBot
        
        # Initialize bot
        bot = FacebookAICommentBot()
        bot.setup_driver()
        
        # Navigate to the Facebook group with posts
        from bravo_config import CONFIG
        test_url = CONFIG.get('POST_URL', 'https://facebook.com/groups/5440421919361046')
        
        print(f"Testing with: {test_url}")
        bot.driver.get(test_url)
        time.sleep(3)  # Let page load
        
        # Find posts
        articles = bot.driver.find_elements("xpath", "//div[@role='article']")
        print(f"Found {len(articles)} posts to test")
        
        if not articles:
            print("No posts found for testing")
            return
        
        # Test author extraction on first 3 posts
        for i, article in enumerate(articles[:3]):
            print(f"\n--- Testing Post {i+1} ---")
            
            # Click on the post to navigate to it (if needed)
            try:
                # Look for a post link within the article
                post_links = article.find_elements("xpath", ".//a[contains(@href, '/posts/') or contains(@href, '/groups/')]")
                if post_links:
                    post_url = post_links[0].get_attribute('href')
                    print(f"Navigating to: {post_url}")
                    
                    # Navigate to individual post
                    bot.driver.get(post_url)
                    time.sleep(2)
                    
                    # Test author extraction with timing
                    start_time = time.time()
                    author = bot.get_post_author() if hasattr(bot, 'get_post_author') else bot.post_extractor.get_post_author()
                    extraction_time = time.time() - start_time
                    
                    print(f"Result: '{author}' in {extraction_time:.2f}s")
                    
                    if extraction_time > 5:
                        print("STILL TOO SLOW - needs further optimization")
                    elif extraction_time < 2:
                        print("GOOD - within acceptable range")
                    else:
                        print("ACCEPTABLE - could be improved")
                        
                else:
                    print("No post link found, testing in-place")
                    # Test with current article context
                    original_driver = bot.post_extractor.driver if bot.post_extractor else None
                    
                    # This won't work perfectly but gives us an idea
                    start_time = time.time()
                    spans = article.find_elements("xpath", ".//h2//span | .//h3//span")
                    author = spans[0].text if spans else "No author"
                    extraction_time = time.time() - start_time
                    
                    print(f"Quick test result: '{author}' in {extraction_time:.2f}s")
                    
            except Exception as e:
                print(f"Post {i+1} test failed: {e}")
                continue
                
    except Exception as e:
        print(f"Test failed: {e}")
        
    finally:
        try:
            if 'bot' in locals() and hasattr(bot, 'driver') and bot.driver:
                bot.driver.quit()
        except:
            pass
    
    print("\nAUTHOR EXTRACTION TEST COMPLETE")
    print("Check the logs above for detailed timing information")

if __name__ == "__main__":
    test_author_extraction_performance()