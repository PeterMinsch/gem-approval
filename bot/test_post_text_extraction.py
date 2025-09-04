#!/usr/bin/env python3
"""
Test script to verify post text extraction is getting post content, not comments
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

def test_post_text_extraction():
    """Test post text extraction with a real post"""
    logger.info("🧪 Testing post text extraction...")
    
    # Initialize bot (but don't start it)
    bot = FacebookAICommentBot()
    
    try:
        # Start browser and login
        logger.info("🚀 Starting browser and logging in...")
        bot.start_driver()
        
        # Navigate to a test post
        test_post_url = input("Please enter a Facebook post URL to test: ").strip()
        
        if not test_post_url:
            logger.warning("No URL provided, exiting...")
            return
            
        logger.info(f"🔗 Navigating to test post: {test_post_url}")
        bot.driver.get(test_post_url)
        
        # Wait a moment for page to load
        import time
        time.sleep(5)
        
        # Extract post text
        logger.info("📝 Extracting post text...")
        post_text = bot.get_post_text()
        
        print("\n" + "="*80)
        print("EXTRACTED POST TEXT:")
        print("="*80)
        if post_text:
            print(post_text)
            print(f"\nText length: {len(post_text)} characters")
            
            # Check text quality and content type
            words = post_text.split()
            single_chars = len([word for word in words if len(word) == 1])
            word_ratio = single_chars / len(words) if words else 1
            
            print(f"Text analysis:")
            print(f"- Word count: {len(words)}")
            print(f"- Single character ratio: {word_ratio:.1%}")
            
            # Check if text is scrambled (character fragments)
            if word_ratio > 0.5:
                print("\n❌ WARNING: Text appears to be SCRAMBLED (character fragments)!")
            elif len(words) < 3:
                print("\n⚠️  WARNING: Text is very short, might be incomplete")
            else:
                # Check for comment indicators
                comment_indicators = [
                    post_text.strip().startswith(("@", "Reply to", "Replying to")),
                    len(post_text.strip()) < 20 and any(word in post_text.lower() for word in ["yes", "no", "thanks", "lol", "haha", "great", "nice", "wow", "cool"]),
                    " replied " in post_text.lower() or " commented " in post_text.lower(),
                    "Write a comment" in post_text,
                    "Add a comment" in post_text
                ]
                
                if any(comment_indicators):
                    print("\n⚠️  WARNING: This text appears to be a COMMENT, not the post content!")
                else:
                    print("\n✅ SUCCESS: This appears to be clean POST CONTENT!")
                    print("✅ Text is not scrambled")
                    print("✅ Text doesn't match comment patterns")
                
        else:
            print("❌ FAILED: Could not extract any post text")
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
    logger.info("🚀 Starting post text extraction test...")
    
    print("\n" + "="*60)
    print("POST TEXT EXTRACTION TEST")
    print("="*60)
    print("This test will:")
    print("1. Open a browser and login to Facebook")
    print("2. Navigate to a post URL you provide")
    print("3. Extract the post text using updated selectors")
    print("4. Analyze if the text is post content vs comment")
    print("="*60 + "\n")
    
    test_post_text_extraction()
    logger.info("✅ Test complete!")