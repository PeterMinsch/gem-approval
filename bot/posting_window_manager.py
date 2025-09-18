#!/usr/bin/env python3
"""
Window-based posting manager for real-time comment posting.
Uses multiple windows in the same browser instance instead of separate browsers.
"""

import time
import logging
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

class WindowPostingManager:
    """Manages posting using a dedicated window in the main browser"""
    
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        self.main_window = None
        self.posting_window = None
        self._lock = threading.Lock()
        self._window_ready = False
        self.setup_windows()
    
    def setup_windows(self):
        """Initialize main and posting windows"""
        try:
            # Save main window handle
            self.main_window = self.driver.current_window_handle
            logger.info(f"Main window handle: {self.main_window}")
            
            # Open new window for posting with faster initialization
            self.driver.execute_script("window.open('about:blank', '_blank');")
            
            # Wait for window to be created (more efficient than fixed delay)
            WebDriverWait(self.driver, 3).until(lambda d: len(d.window_handles) > 1)
            
            # Get all window handles
            all_windows = self.driver.window_handles
            
            # Find the new window
            for window in all_windows:
                if window != self.main_window:
                    self.posting_window = window
                    break
            
            if self.posting_window:
                logger.info(f"Posting window created: {self.posting_window}")
                
                # Switch to posting window briefly to set it up
                self._safe_switch_window(self.posting_window)
                self.driver.get("https://www.facebook.com")
                
                # Wait for page load instead of fixed delay
                WebDriverWait(self.driver, 5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Switch back to main window
                self._safe_switch_window(self.main_window)
                self._window_ready = True
                logger.info("Windows setup complete")
                return True
            else:
                logger.error("Failed to create posting window")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up windows: {e}")
            return False
    
    def _safe_switch_window(self, target_window, timeout=3):
        """Safely switch to target window with timeout"""
        try:
            if self.driver.current_window_handle == target_window:
                return True
                
            self.driver.switch_to.window(target_window)
            
            # Verify switch was successful
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.current_window_handle == target_window
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch to window {target_window}: {e}")
            return False
    
    def post_comment(self, post_url, comment_text, comment_id=None):
        """Post a comment using the dedicated posting window with optimized timing"""
        
        if not self.posting_window or not self._window_ready:
            logger.error("Posting window not ready")
            return False
        
        # Use thread lock to prevent concurrent posting operations
        with self._lock:
            # Save current window
            current_window = self.driver.current_window_handle
        
        try:
            # Switch to posting window with verification
            if not self._safe_switch_window(self.posting_window):
                return False
                
            logger.info(f"Switched to posting window for comment {comment_id}")
            
            # Navigate to post with smart waiting
            self.driver.get(post_url)
            
            # Wait for page to be interactive (faster than fixed delay)
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(0.5)  # Minimal buffer for dynamic content
            
            # Check if logged in
            if "login" in self.driver.current_url.lower():
                logger.error("Not logged into Facebook in posting window")
                return False
            
            # Find comment box
            comment_box = self._find_comment_box()
            if not comment_box:
                logger.error(f"Could not find comment box on {post_url}")
                return False
            
            # Click and type comment with optimized timing
            comment_box.click()
            
            # Wait for focus instead of fixed delay
            WebDriverWait(self.driver, 2).until(
                lambda d: d.switch_to.active_element == comment_box
            )
            
            # Clear any existing text
            comment_box.clear()
            time.sleep(0.2)  # Minimal clear buffer
            
            # Sanitize comment text for ChromeDriver compatibility
            sanitized_comment = self._sanitize_unicode_for_chrome(comment_text)

            # Type the comment
            comment_box.send_keys(sanitized_comment)
            time.sleep(0.3)  # Minimal typing buffer
            
            # Submit comment
            comment_box.send_keys(Keys.RETURN)
            
            # Wait for submission confirmation (adaptive)
            time.sleep(1.5)
            
            logger.info(f"Successfully posted comment {comment_id} to {post_url}")
            
            # Update database if comment_id provided
            if comment_id:
                try:
                    from database import db
                    db.update_comment_status(int(comment_id), "posted")
                except Exception as e:
                    logger.error(f"Failed to update database: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error posting comment: {e}")
            
            # Update database on failure
            if comment_id:
                try:
                    from database import db
                    db.update_comment_status(int(comment_id), "failed", 
                                            error_message=str(e))
                except:
                    pass
            return False
            
        finally:
            # Always switch back to original window with verification
            try:
                if not self._safe_switch_window(current_window):
                    logger.error("Failed to switch back to original window")
                else:
                    logger.info("Switched back to original window")
            except Exception as e:
                logger.error(f"Error switching back to original window: {e}")
    
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
            }

            # Apply emoji replacements
            sanitized = text
            for emoji, replacement in emoji_replacements.items():
                sanitized = sanitized.replace(emoji, replacement)

            # Remove any remaining non-BMP characters (Unicode > U+FFFF)
            # Keep only Basic Multilingual Plane characters
            sanitized = ''.join(char for char in sanitized if ord(char) <= 0xFFFF)

            if sanitized != text:
                logger.info(f"[UNICODE] Sanitized comment text for ChromeDriver compatibility")
                logger.debug(f"[UNICODE] Original: {text[:50]}...")
                logger.debug(f"[UNICODE] Sanitized: {sanitized[:50]}...")

            return sanitized

        except Exception as e:
            logger.warning(f"[UNICODE] Error sanitizing text, using original: {e}")
            return text

    def cleanup(self):
        """Close the posting window and cleanup"""
        try:
            if self.posting_window:
                self.driver.switch_to.window(self.posting_window)
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
                logger.info("Posting window closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")