"""
Interaction Handler Module
Handles UI interactions, clicking, typing, and form submissions
"""

import time
import random
import logging
from typing import Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# Import performance timer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from performance_timer import time_method

logger = logging.getLogger(__name__)


class InteractionHandler:
    """Handles all UI interactions with Facebook"""
    
    def __init__(self, driver, config: dict):
        """
        Initialize InteractionHandler
        
        Args:
            driver: Selenium WebDriver instance
            config: Configuration dictionary
        """
        self.driver = driver
        self.config = config
    
    @time_method
    def click_element_safely(self, element: WebElement, use_js: bool = False, max_retries: int = 3) -> bool:
        """
        Safely click an element with retry logic
        
        Args:
            element: WebElement to click
            use_js: Whether to use JavaScript click
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if click successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Scroll element into view first
                self.scroll_to_element(element)
                time.sleep(0.2)
                
                if use_js:
                    # Use JavaScript click
                    self.driver.execute_script("arguments[0].click();", element)
                else:
                    # Use regular click with human-like mouse movement
                    self.human_mouse_jiggle(element)
                    element.click()
                
                logger.debug(f"Successfully clicked element on attempt {attempt + 1}")
                return True
                
            except ElementClickInterceptedException:
                logger.warning(f"Click intercepted on attempt {attempt + 1}, trying JavaScript click")
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception as e:
                    logger.warning(f"JavaScript click also failed: {e}")
                    
            except Exception as e:
                logger.warning(f"Click attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    
        logger.error(f"Failed to click element after {max_retries} attempts")
        return False
    
    def human_mouse_jiggle(self, element: WebElement, moves: int = 2):
        """
        Add human-like mouse movement before clicking
        
        Args:
            element: Element to move to
            moves: Number of micro-movements
        """
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            
            # Get configuration values or use defaults
            jiggle_range = random.randint(3, 8)
            
            for move_num in range(moves):
                x_offset = random.randint(-jiggle_range, jiggle_range)
                y_offset = random.randint(-jiggle_range, jiggle_range)
                
                actions.move_by_offset(x_offset, y_offset).perform()
                time.sleep(random.uniform(0.05, 0.15))
                
                # Return to center
                actions.move_by_offset(-x_offset, -y_offset).perform()
                time.sleep(random.uniform(0.02, 0.08))
                
        except Exception as e:
            logger.debug(f"Mouse jiggle failed: {e}")
    
    @time_method
    def type_text_human_like(self, element: WebElement, text: str, delay_range: tuple = (0.05, 0.15)) -> bool:
        """
        Type text with human-like delays
        
        Args:
            element: Input element
            text: Text to type
            delay_range: Min and max delay between keystrokes
            
        Returns:
            True if typing successful, False otherwise
        """
        try:
            # Clear the element first
            element.clear()
            time.sleep(0.2)
            
            # Simulate typing errors occasionally
            text = self.simulate_typing_errors(text)
            
            # Type each character with human-like delays
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(delay_range[0], delay_range[1]))
                
                # Occasional pauses at word boundaries
                if char == ' ' and random.random() < 0.1:
                    time.sleep(random.uniform(0.1, 0.3))
                    
            logger.debug(f"Successfully typed text: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def simulate_typing_errors(self, text: str) -> str:
        """
        Occasionally simulate human typing errors
        
        Args:
            text: Original text
            
        Returns:
            Text with possible typos (that are corrected)
        """
        if random.random() < 0.05:  # 5% chance of typo
            common_errors = [
                ('the', 'teh'), ('and', 'adn'), ('for', 'fro'),
                ('with', 'wth'), ('that', 'taht')
            ]
            for correct, error in common_errors:
                if correct in text.lower():
                    # Make error then correct it (human-like)
                    text = text.replace(correct, error)
                    time.sleep(0.1)  # Pause before correction
                    text = text.replace(error, correct)
                    break
        return text
    
    @time_method
    def find_and_click_comment_button(self, post_element: WebElement) -> bool:
        """
        Find and click the comment button on a post
        
        Args:
            post_element: WebElement of the post
            
        Returns:
            True if comment button clicked, False otherwise
        """
        comment_selectors = [
            ".//div[@aria-label='Leave a comment']",
            ".//div[@aria-label='Comment']",
            ".//span[contains(text(), 'Comment')]",
            ".//div[contains(@class, 'comment')]"
        ]
        
        for selector in comment_selectors:
            try:
                comment_button = post_element.find_element(By.XPATH, selector)
                if comment_button.is_displayed():
                    return self.click_element_safely(comment_button)
            except NoSuchElementException:
                continue
                
        logger.warning("Could not find comment button")
        return False
    
    @time_method
    def submit_comment_form(self) -> bool:
        """
        Submit the comment form
        
        Returns:
            True if submission successful, False otherwise
        """
        submit_selectors = [
            "//div[@aria-label='Comment' and @role='button']",
            "//button[contains(text(), 'Post')]",
            "//div[contains(@class, 'submit')]"
        ]
        
        for selector in submit_selectors:
            try:
                submit_button = self.driver.find_element(By.XPATH, selector)
                if submit_button.is_displayed():
                    return self.click_element_safely(submit_button)
            except NoSuchElementException:
                continue
                
        # Fallback: try pressing Enter key
        try:
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.RETURN)
            return True
        except Exception as e:
            logger.error(f"Failed to submit comment form: {e}")
            return False
    
    def handle_popups_and_dialogs(self) -> bool:
        """
        Handle any popups or dialogs that appear
        
        Returns:
            True if handled successfully, False otherwise
        """
        popup_selectors = [
            "//div[@aria-label='Close']",
            "//button[contains(text(), 'Not Now')]",
            "//button[contains(text(), 'Cancel')]",
            "//div[@role='dialog']//div[@aria-label='Close']"
        ]
        
        for selector in popup_selectors:
            try:
                popup_element = self.driver.find_element(By.XPATH, selector)
                if popup_element.is_displayed():
                    logger.info(f"Closing popup with selector: {selector}")
                    self.click_element_safely(popup_element)
                    time.sleep(0.5)
                    return True
            except NoSuchElementException:
                continue
                
        return False
    
    def upload_images(self, image_paths: List[str]) -> bool:
        """
        Upload images to a comment
        
        Args:
            image_paths: List of local image file paths to upload
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            # Find the image upload button
            upload_selectors = [
                "//div[@aria-label='Attach a photo or video']",
                "//input[@type='file' and @accept='image/*,video/*']",
                "//div[contains(@class, 'photo-upload')]"
            ]
            
            upload_element = None
            for selector in upload_selectors:
                try:
                    upload_element = self.driver.find_element(By.XPATH, selector)
                    if upload_element:
                        break
                except NoSuchElementException:
                    continue
            
            if not upload_element:
                logger.error("Could not find image upload element")
                return False
                
            # If it's a file input, send keys directly
            if upload_element.tag_name == 'input':
                # Join multiple paths with newline for multiple file selection
                file_paths = '\n'.join(image_paths)
                upload_element.send_keys(file_paths)
            else:
                # Click the button first to reveal file input
                self.click_element_safely(upload_element)
                time.sleep(1)
                
                # Find the actual file input
                file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                file_paths = '\n'.join(image_paths)
                file_input.send_keys(file_paths)
                
            logger.info(f"Uploaded {len(image_paths)} images")
            time.sleep(2)  # Wait for upload to complete
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload images: {e}")
            return False
    
    @time_method
    def scroll_to_element(self, element: WebElement) -> bool:
        """
        Scroll element into view
        
        Args:
            element: WebElement to scroll to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Failed to scroll to element: {e}")
            return False