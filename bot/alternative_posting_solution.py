#!/usr/bin/env python3
"""
Alternative solution for real-time posting using the main browser.

Instead of using a separate headless browser (which Facebook blocks),
this solution uses the main browser instance to post comments when approved.

The key insight is that we can temporarily pause the scanning process,
navigate to the post URL, submit the comment, then return to scanning.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class PostingManager:
    """Manages posting comments using the main browser instance"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.driver = bot_instance.driver
        self.config = bot_instance.config
        
    def post_comment_now(self, post_url, comment_text, comment_id=None):
        """
        Post a comment immediately using the main browser.
        Saves current URL, navigates to post, comments, then returns.
        """
        # Save current URL to return to
        current_url = self.driver.current_url
        success = False
        
        try:
            # Navigate to the post
            self.driver.get(post_url)
            time.sleep(3)  # Wait for page load
            
            # Check if we're still logged in
            if "login" in self.driver.current_url.lower():
                raise Exception("Not logged into Facebook")
            
            # Find comment box
            comment_box = self._find_comment_box()
            if not comment_box:
                raise Exception("Could not find comment box")
            
            # Click and type comment
            comment_box.click()
            time.sleep(1)

            # Sanitize comment text for ChromeDriver compatibility
            sanitized_comment = self._sanitize_unicode_for_chrome(comment_text)
            comment_box.send_keys(sanitized_comment)
            time.sleep(1)
            
            # Submit comment
            comment_box.send_keys(Keys.RETURN)
            time.sleep(2)
            
            success = True
            print(f"Successfully posted comment to {post_url}")
            
        except Exception as e:
            print(f"Failed to post comment: {e}")
            success = False
            
        finally:
            # Return to original URL
            try:
                self.driver.get(current_url)
                time.sleep(2)
            except:
                pass
                
        return success
    
    def _find_comment_box(self):
        """Find the comment box on the current page"""
        # Try primary xpath
        elements = self.driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
        if elements:
            return elements[0]
            
        # Try fallback xpaths
        for xpath in self.config.get('COMMENT_BOX_FALLBACK_XPATHS', []):
            elements = self.driver.find_elements(By.XPATH, xpath)
            if elements:
                return elements[0]
                
        return None

    def _sanitize_unicode_for_chrome(self, text: str) -> str:
        """
        Sanitize Unicode characters that ChromeDriver can't handle (non-BMP characters).
        Converts problematic emojis and Unicode to safe alternatives.
        """
        try:
            # Replace common problematic emojis with text equivalents
            emoji_replacements = {
                '✨': '*',       # Sparkles
                '💎': 'diamond', # Diamond
                '💍': 'ring',    # Ring
                '👑': 'crown',   # Crown
                '🌟': '*',       # Star
                '⭐': '*',       # Star
                '💫': '*',       # Dizzy star
                '🔥': 'fire',    # Fire
                '❤️': 'love',    # Heart
                '💖': 'love',    # Sparkling heart
                '😍': ':)',      # Heart eyes
                '🤩': ':)',      # Star eyes
                '👍': 'thumbs up', # Thumbs up
                '💯': '100',     # 100 emoji
                '🎉': '!',       # Party
                '🏆': 'trophy',  # Trophy
                '🔍': '',        # Magnifying glass (search) - MISSING EMOJI
                '📝': '',        # Memo/note - MISSING EMOJI
                '🚀': '',        # Rocket - MISSING EMOJI
                '🎯': '',        # Direct hit/target - MISSING EMOJI
            }

            # Apply emoji replacements
            sanitized = text
            for emoji, replacement in emoji_replacements.items():
                sanitized = sanitized.replace(emoji, replacement)

            # Remove any remaining non-BMP characters (Unicode > U+FFFF)
            # Keep only Basic Multilingual Plane characters
            sanitized = ''.join(char for char in sanitized if ord(char) <= 0xFFFF)

            return sanitized

        except Exception as e:
            print(f"[UNICODE] Error sanitizing text, using original: {e}")
            return text


def integrate_with_api(bot_instance):
    """
    Integration point for the API to use this posting method.
    
    This would replace the current posting queue approach with
    direct posting using the main browser.
    """
    posting_manager = PostingManager(bot_instance)
    
    def post_comment_realtime(comment_id, post_url, comment_text):
        """Replacement for the current post_comment_realtime function"""
        success = posting_manager.post_comment_now(post_url, comment_text, comment_id)
        
        # Update database status
        if success:
            from database import db
            db.update_comment_status(int(comment_id), "posted")
        else:
            from database import db
            db.update_comment_status(int(comment_id), "failed", error_message="Posting failed")
            
        return success
    
    return post_comment_realtime


# Example usage
if __name__ == "__main__":
    print("Alternative Posting Solution")
    print("="*50)
    print()
    print("This module provides an alternative approach to real-time posting.")
    print("Instead of using a separate headless browser (which Facebook blocks),")
    print("it uses the main browser instance to post comments.")
    print()
    print("Key advantages:")
    print("- No authentication issues (uses existing logged-in session)")
    print("- No headless browser detection by Facebook")
    print("- Simpler architecture (one browser instead of two)")
    print()
    print("Key trade-off:")
    print("- Temporarily pauses scanning while posting")
    print("- But posting only takes 5-10 seconds per comment")
    print()
    print("To implement this solution:")
    print("1. Import this module in api.py")
    print("2. Replace the posting queue approach with direct posting")
    print("3. Modify the approve endpoint to use this method")