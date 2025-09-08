"""
Post Extractor Module
Handles extraction of post data, author information, and content from Facebook posts
"""

import logging
import time
import requests
from io import BytesIO
from PIL import Image
import pytesseract
from typing import List, Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException

logger = logging.getLogger(__name__)


class PostExtractor:
    """Extracts data from Facebook posts"""
    
    def __init__(self, driver, config: dict):
        """
        Initialize PostExtractor
        
        Args:
            driver: Selenium WebDriver instance
            config: Configuration dictionary
        """
        self.driver = driver
        self.config = config
    
    def scroll_and_collect_post_links(self, max_scrolls: int = 5) -> List[str]:
        """
        Scroll through the page and collect post links
        
        Args:
            max_scrolls: Maximum number of scrolls to perform
            
        Returns:
            List of post URLs
        """
        collected = set()
        empty_scroll_count = 0
        max_empty_scrolls = 2
        
        for scroll_num in range(max_scrolls):
            logger.info(f"Scroll {scroll_num + 1}/{max_scrolls}")
            
            # Wait for dynamic content to load
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//a[contains(@href, '/groups/') or contains(@href, '/photo/') or contains(@href, '/commerce/')]"))
                )
            except TimeoutException:
                logger.debug("No new elements appeared after wait")
            
            # Collect group posts, photo posts, and commerce listings
            post_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/groups/') and contains(@href, '/posts/') and not(contains(@href, 'comment_id')) and string-length(@href) > 60]" +
                " | //a[contains(@href, '/photo/?fbid=') and contains(@href, 'set=')]" +
                " | //a[contains(@href, '/commerce/listing/') and string-length(@href) > 80]"
            )
            
            hrefs = [link.get_attribute('href') for link in post_links if link.get_attribute('href')]
            logger.info(f"Found {len(hrefs)} post links on this scroll")
            
            # Filter and clean URLs
            valid_hrefs = []
            for href in hrefs:
                if '/photo/' in href and 'fbid=' in href:
                    # Keep photo URLs mostly intact
                    import re
                    clean_href = re.sub(r'&(__cft__|__tn__|notif_id|notif_t|ref)=[^&]*', '', href)
                    clean_href = re.sub(r'&context=[^&]*', '', clean_href)
                else:
                    clean_href = href.split('?')[0] if '?' in href else href
                
                if self.is_valid_post_url(clean_href) and clean_href not in collected:
                    valid_hrefs.append(clean_href)
            
            if valid_hrefs:
                empty_scroll_count = 0
            else:
                empty_scroll_count += 1
                if empty_scroll_count >= max_empty_scrolls:
                    logger.info(f"Stopping early - {max_empty_scrolls} consecutive scrolls with no new posts")
                    break
            
            collected.update(valid_hrefs)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        return list(collected)
    
    def is_valid_post_url(self, url: str) -> bool:
        """
        Check if a URL is a valid post URL
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not url or len(url) < 50:
            return False
        
        # Must be a Facebook URL
        if 'facebook.com' not in url:
            return False
        
        # Check for valid post patterns
        valid_patterns = [
            '/groups/',
            '/photo/',
            '/commerce/listing/'
        ]
        
        return any(pattern in url for pattern in valid_patterns)
    
    def get_post_text(self) -> str:
        """
        Extract the main text of the post for context or logging.
        
        Returns:
            Extracted post text or empty string
        """
        logger.info("Attempting to extract post text...")
        
        # Wait for page to load
        try:
            time.sleep(0.5)
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
            )
        except Exception as e:
            logger.debug(f"Page load wait failed: {e}")
        
        # Try extraction methods - FIXED: More specific selectors to avoid comment text
        extraction_methods = [
            # Primary selectors - most specific first
            ("//div[@data-testid='post_message']", "Facebook post message container"),
            ("//div[contains(@class, 'userContent')]", "Facebook user content container"),
            
            # More specific selectors to avoid comments
            ("//div[@role='article']/div[1]//div[@dir='auto' and not(ancestor::*[contains(@aria-label, 'Comment') or contains(@aria-label, 'comment')])]", "Post content excluding comment sections"),
            ("//div[@role='article']//div[contains(@class, 'x1iorvi4') and @dir='auto'][1]", "First post text container only"),
            ("//div[@role='article']//span[@dir='auto' and not(ancestor::*[@role='complementary'])][1]", "First post span excluding sidebar"),
            
            # Fallback - but limit to first occurrence only
            ("(//div[@role='article']//div[@dir='auto'])[1]", "First directional container only"),
        ]
        
        for xpath, method_name in extraction_methods:
            try:
                logger.debug(f"Trying method: {method_name}")
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                if elements:
                    logger.debug(f"Found {len(elements)} elements for {method_name}")
                    extracted_text = self.extract_text_from_elements(elements, method_name)
                    if extracted_text:
                        return extracted_text
                        
            except Exception as e:
                logger.debug(f"Method {method_name} failed: {e}")
                continue
        
        logger.warning("Could not extract post text")
        return ""
    
    def extract_text_from_elements(self, elements: List[WebElement], method_name: str) -> str:
        """
        Extract and clean text from elements - IMPROVED: Better filtering for post vs comment text
        
        Args:
            elements: List of WebElements
            method_name: Name of extraction method for logging
            
        Returns:
            Cleaned text or empty string
        """
        texts = []
        comment_indicators = [
            'reply', 'replies', 'like', 'likes', 'react', 'share', 'shares',
            'ago', 'minute', 'minutes', 'hour', 'hours', 'day', 'days',
            'comment by', 'commented', 'see more', 'hide', 'translate'
        ]
        
        for element in elements:
            try:
                text = element.text.strip()
                if text and len(text) > 10:
                    # Filter out obvious comment-related text
                    text_lower = text.lower()
                    is_comment_like = any(indicator in text_lower for indicator in comment_indicators)
                    
                    # Skip very short texts that are likely UI elements
                    if len(text) < 20 and any(word in text_lower for word in ['like', 'reply', 'share']):
                        continue
                        
                    # Prefer longer, more substantial text that doesn't look like comments
                    if not is_comment_like or len(text) > 50:
                        texts.append(text)
                        
                        # IMPORTANT: For post extraction, take the first good text we find
                        # This prevents comment text from being included
                        if len(text) > 30 and not is_comment_like:
                            logger.info(f"Successfully extracted post text using {method_name}: {text[:100]}...")
                            return text
                            
            except Exception as e:
                logger.debug(f"Failed to extract text from element: {e}")
        
        # If we have multiple texts, prefer the longest one that doesn't look like a comment
        if texts:
            # Sort by length descending, then filter out comment-like texts
            texts_filtered = [t for t in texts if not any(ind in t.lower() for ind in comment_indicators[:5])]
            best_text = texts_filtered[0] if texts_filtered else texts[0]
            
            logger.info(f"Successfully extracted text using {method_name}: {best_text[:100]}...")
            return best_text
        
        return ""
    
    def get_post_author(self) -> str:
        """
        Extract the post author name from Facebook post page.
        OPTIMIZED: Reduced selector attempts and improved performance
        
        Returns:
            Author name or empty string if not found
        """
        start_time = time.time()
        logger.info("🔍 Starting author extraction...")
        
        try:
            # OPTIMIZED: Try most likely selectors first, with time limits
            author_selectors = [
                # Most common patterns first
                ("//div[@role='article']//h2//a[@role='link']", "H2 link"),
                ("//div[@role='article']//h3//a[@role='link']", "H3 link"),
                ("//div[@role='article']//h2//span", "H2 span"),
                ("//div[@role='article']//h3//span", "H3 span"),
                # Fallback patterns
                ("//h2//a[contains(@href, '/')]", "Generic H2 link"),
                ("//div[@role='article']//a[contains(@href, 'facebook.com/') and @role='link'][1]", "FB profile link"),
            ]

            for i, (selector, description) in enumerate(author_selectors):
                selector_start = time.time()
                try:
                    # Set a reasonable timeout for element finding
                    elements = WebDriverWait(self.driver, 2).until(
                        lambda d: d.find_elements(By.XPATH, selector)
                    )
                    
                    selector_time = time.time() - selector_start
                    logger.debug(f"  Selector {i+1} ({description}): {len(elements)} elements in {selector_time:.2f}s")
                    
                    for element in elements[:3]:  # OPTIMIZED: Check max 3 elements per selector
                        try:
                            if element.tag_name == 'a':
                                name = element.text.strip()
                                href = element.get_attribute('href') or ""
                                
                                if name and self.is_valid_author_name(name) and 'facebook.com/' in href:
                                    total_time = time.time() - start_time
                                    logger.info(f"✅ Found author '{name}' using {description} in {total_time:.2f}s")
                                    return name
                            else:
                                name = element.text.strip()
                                if name and self.is_valid_author_name(name):
                                    total_time = time.time() - start_time
                                    logger.info(f"✅ Found author '{name}' using {description} in {total_time:.2f}s")
                                    return name
                        except Exception as e:
                            logger.debug(f"Element processing failed: {e}")
                            continue
                                
                except Exception as e:
                    selector_time = time.time() - selector_start
                    if selector_time > 3:
                        logger.warning(f"⚠️ Slow selector {i+1} ({description}): {selector_time:.2f}s - {e}")
                    else:
                        logger.debug(f"Selector {i+1} failed: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to extract author name: {e}")
        
        total_time = time.time() - start_time
        logger.warning(f"❌ No author found after {total_time:.2f}s")
        return ""
    
    def is_valid_author_name(self, name: str) -> bool:
        """
        Check if extracted text is a valid author name
        
        Args:
            name: Potential author name
            
        Returns:
            True if valid name, False otherwise
        """
        if not name or len(name) < 2 or len(name) > 100:
            return False
        
        # Filter out common non-name strings
        invalid_strings = ['Write a comment', 'Like', 'Comment', 'Share', 'Reply', 'View', 'See more']
        for invalid in invalid_strings:
            if invalid.lower() in name.lower():
                return False
        
        return True
    
    def extract_post_url(self, post_element: WebElement) -> str:
        """
        Extract permalink URL from a post element
        
        Args:
            post_element: Selenium WebElement of the post
            
        Returns:
            Post URL or current page URL
        """
        try:
            # Try to find permalink within the post
            permalink_selectors = [
                ".//a[contains(@href, '/groups/') and contains(@href, '/posts/')]",
                ".//a[contains(@href, '/permalink/')]",
                ".//a[contains(@href, '/photo/')]"
            ]
            
            for selector in permalink_selectors:
                try:
                    link = post_element.find_element(By.XPATH, selector)
                    href = link.get_attribute('href')
                    if href:
                        return href.split('?')[0]  # Remove query parameters
                except:
                    continue
            
            # Fallback to current URL
            return self.driver.current_url
            
        except Exception as e:
            logger.error(f"Failed to extract post URL: {e}")
            return self.driver.current_url
    
    def extract_first_image_url(self) -> Optional[str]:
        """
        Extract the first real image URL from the current Facebook post.
        
        Returns:
            Image URL or None if no image found
        """
        try:
            post_element = self.driver.find_element(By.XPATH, "//div[@role='article']")
            img_elements = post_element.find_elements(By.TAG_NAME, "img")
            
            for img in img_elements:
                src = img.get_attribute("src")
                if not src:
                    continue
                    
                # Skip emojis, SVGs, icons, and profile images
                if any(x in src for x in ["emoji", ".svg", "profile", "static"]):
                    continue
                    
                # Facebook CDN images are usually real post images
                if src.startswith("https://scontent") and src.endswith(".jpg"):
                    return src
                    
                # Accept other http(s) images that aren't SVGs or emojis
                if src.startswith("http") and not any(x in src for x in ["emoji", ".svg", "profile", "static"]):
                    return src
                    
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image: {e}")
            return None
    
    def get_existing_comments(self) -> List[str]:
        """
        Extract existing comments from the current post
        
        Returns:
            List of existing comment texts
        """
        try:
            comment_elements = self.driver.find_elements(By.XPATH, "//div[@aria-label='Comment']//span")
            return [el.text for el in comment_elements if el.text.strip()]
        except Exception as e:
            logger.error(f"Failed to extract comments: {e}")
            return []
    
    def check_post_validity(self, post_data: dict) -> bool:
        """
        Check if a post is valid for commenting
        
        Args:
            post_data: Dictionary containing post information
            
        Returns:
            True if post is valid, False otherwise
        """
        # Check if post has minimum required data
        if not post_data:
            return False
            
        # Must have either text or images
        has_text = post_data.get('text') and len(post_data['text']) > 10
        has_images = post_data.get('images') and len(post_data['images']) > 0
        
        if not has_text and not has_images:
            return False
            
        # Must have a valid URL
        if not post_data.get('url'):
            return False
            
        return True