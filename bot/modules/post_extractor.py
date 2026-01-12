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
from modules.url_normalizer import normalize_url
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from modules.stale_element_handler import (
    extract_hrefs_safely,
    collect_links_with_extraction,
    safe_get_text,
    safe_get_attribute,
    retry_on_stale
)

# Import performance timer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from performance_timer import time_method

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
    
    @time_method
    def scroll_and_collect_post_links(self, max_scrolls: int = 5) -> List[str]:
        """
        Scroll through the page and collect post links.
        Uses safe extraction to handle stale elements.

        Args:
            max_scrolls: Maximum number of scrolls to perform

        Returns:
            List of post URLs
        """
        collected = set()
        empty_scroll_count = 0
        max_empty_scrolls = 2

        xpath_query = (
            "//a[contains(@href, '/groups/') and contains(@href, '/posts/') and not(contains(@href, 'comment_id')) and string-length(@href) > 60]"
            " | //a[contains(@href, '/photo/?fbid=') and contains(@href, 'set=')]"
            " | //a[contains(@href, '/commerce/listing/') and string-length(@href) > 80]"
        )

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

            # OPTION 1+2: Use safe extraction with retry - extracts data immediately
            hrefs = collect_links_with_extraction(self.driver, xpath_query, max_retries=3)
            logger.info(f"Found {len(hrefs)} post links on this scroll")

            # Filter and normalize URLs
            valid_hrefs = []
            for href in hrefs:
                # Use centralized URL normalization
                clean_href = normalize_url(href)

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
            time.sleep(0.5)  # Reduced from 2s for faster scrolling

        return list(collected)
    
    def is_valid_post_url(self, url: str) -> bool:
        """
        Check if a URL is a valid GROUP post URL (not personal feed)

        Args:
            url: URL to validate

        Returns:
            True if valid group post, False otherwise
        """
        if not url or len(url) < 50:
            return False

        # Must be a Facebook URL
        if 'facebook.com' not in url:
            return False

        # Group posts - always valid
        if '/groups/' in url:
            return True

        # Photo posts - only accept GROUP photos (set=gm.), reject personal feed photos (set=a.)
        if '/photo/' in url:
            # Group media photos have set=gm. in the URL
            if 'set=gm.' in url:
                return True
            # Personal feed photos have set=a. - reject these
            if 'set=a.' in url:
                logger.debug(f"Rejecting personal feed photo: {url[:80]}...")
                return False
            # Other photo patterns - reject to be safe
            return False

        # Commerce listings
        if '/commerce/listing/' in url:
            return True

        return False
    
    @time_method
    def get_post_text(self) -> str:
        """
        Extract the main text of the post for context or logging.
        ENHANCED: Better detection to stop before comments section
        
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
        
        # Try extraction methods - HYBRID: Structure-aware + content analysis
        extraction_methods = [
            # TIER 1: Specific working selectors (keep what works)
            ("//span[contains(text(), 'Trying to find') or contains(text(), 'trying to find') or contains(text(), 'engagement ring')][string-length(text()) > 50]", "Direct match for photo post content"),
            
            # TIER 2: Generic structural selectors for main content areas
            ("//div[@role='main']//span[string-length(text()) > 50 and not(ancestor::*[contains(@aria-label, 'Comment')]) and not(ancestor::form)]", "Main content area - long text"),
            ("//div[contains(@class, 'x1iorvi4') or contains(@class, 'x1y1aw1k')]//span[string-length(text()) > 30]", "Post sidebar/content areas"),
            ("//div[@role='main']//span[string-length(text()) > 20 and not(ancestor::*[@role='button']) and not(ancestor::a)]", "Main content - medium text"),
            
            # TIER 3: Content-pattern based selectors (any post type)
            ("//span[string-length(text()) > 40 and (contains(text(), '?') or contains(text(), '.') or contains(text(), '!')) and not(ancestor::*[contains(@class, 'comment')]) and not(ancestor::form)]", "Question or sentence patterns"),
            ("//span[string-length(text()) > 30 and (contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'iso ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'wtb ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'looking ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'need ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'want '))]", "Common post keywords"),
            
            # TIER 4: Traditional selectors (improved)
            ("//div[@data-testid='post_message']", "Facebook post message container"),
            ("//div[contains(@class, 'userContent')]", "Facebook user content container"),
            
            # ENHANCED: Target actual post content, avoiding author names and comments
            ("//div[@role='article']//span[@dir='auto' and not(ancestor::*[.//h2[contains(text(), 'Comments')]]) and not(ancestor::*[contains(@class, 'x1heor9g')]) and not(ancestor::*[@role='link']) and string-length(text()) > 10]", "Post content excluding author names and comments"),
            
            ("//div[@role='article']//span[@dir='auto' and not(ancestor::form) and not(ancestor::*[contains(@aria-label, 'comment')]) and not(ancestor::*[contains(@href, '/user/') or contains(@href, 'facebook.com/')]) and string-length(text()) > 5]", "Post text excluding profile links"),
            
            ("//div[@role='article']//div[@dir='auto' and not(ancestor::*[.//h2[contains(text(), 'Comments')]]) and not(contains(@class, 'x1heor9g')) and not(ancestor::*[@role='link']) and string-length(text()) > 10]", "Post div content excluding author sections"),
            
            # Target content that looks like actual post text (contains common post keywords)
            ("//div[@role='article']//span[@dir='auto' and (contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'iso ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'wtb ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ring ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'looking ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'need ') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sell '))]", "Post content with jewelry keywords"),
            
            # More conservative fallbacks with author name exclusion
            ("//div[@role='article']//span[@dir='auto' and not(ancestor::*[contains(@class, 'comment')]) and not(preceding-sibling::*//img[contains(@src, 'scontent')]) and string-length(text()) > 3]", "Text not following profile images"),
            
            ("//div[@role='article']//div[@dir='auto' and not(ancestor::*[contains(@class, 'comment')]) and not(contains(text(), ' · ')) and string-length(text()) > 10]", "Content without author metadata markers"),
        ]
        
        for xpath, method_name in extraction_methods:
            try:
                logger.debug(f"Trying method: {method_name}")
                # PERFORMANCE FIX: Use explicit timeout to avoid implicit wait delays
                # Save original implicit wait
                original_wait = self.driver.implicitly_wait
                self.driver.implicitly_wait(0)  # Disable implicit wait temporarily
                
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                # Restore original implicit wait
                self.driver.implicitly_wait(1)
                
                if elements:
                    logger.debug(f"Found {len(elements)} elements for {method_name}")
                    # Log first element content for debugging
                    if elements[0]:
                        try:
                            first_text = elements[0].text.strip()[:100] if elements[0].text else "No text"
                            logger.debug(f"First element preview: {first_text}")
                        except:
                            pass
                    
                    # ENHANCED: Use new stop-before-comments extraction
                    extracted_text = self.extract_post_text_only(elements, method_name)
                    if extracted_text:
                        return extracted_text
                    else:
                        logger.debug(f"extract_post_text_only returned empty for {method_name}")
                        
            except Exception as e:
                logger.debug(f"Method {method_name} failed: {e}")
                # Ensure implicit wait is restored even on error
                self.driver.implicitly_wait(1)
                continue
        
        logger.warning("Could not extract post text")
        return ""
    
    def extract_post_text_only(self, elements: List[WebElement], method_name: str) -> str:
        """
        Extract ONLY the main post text, stopping before any comments.
        
        Args:
            elements: List of WebElements
            method_name: Name of extraction method for logging
            
        Returns:
            Main post text only, no comments
        """
        if not elements:
            logger.debug("No elements provided to extract_post_text_only")
            return ""
            
        # Strong indicators that we've reached the comments section
        comment_section_markers = [
            # Comment input indicators
            'write a comment', 'write a public comment', 'comment as',
            'write a reply', 'reply to this', 'add a comment',
            
            # Comments section headers and navigation
            'comments', 'most relevant', 'newest', 'all comments', 
            'view more comments', 'view previous comments', 'load more comments', 
            'top comments', 'recent comments', 'no comments yet', 
            'be the first to comment',
            
            # Comment interaction elements
            'comment with an avatar sticker', 'insert an emoji', 
            'attach a photo or video', 'comment with a gif', 
            'comment with a sticker',
            
            # Form-related comment indicators
            'available voices', 'shared with public group'
        ]
        
        # Collect text until we hit a comment marker
        post_texts = []
        found_main_content = False
        
        # Process up to 10 elements but stop early if we find comments
        for i, element in enumerate(elements[:10]):
            try:
                # Use safe extraction to handle stale elements
                text = safe_get_text(element, default="").strip()
                
                # Skip empty or very short text
                if not text or len(text) < 5:
                    logger.debug(f"Element {i}: Skipping short/empty text")
                    continue
                
                text_lower = text.lower()
                
                # ENHANCED: Check if this element contains comment section markers
                if any(marker in text_lower for marker in comment_section_markers):
                    logger.debug(f"Stopping at element {i}: Found comment section marker in text: {text[:50]}...")
                    break  # Stop here - we've reached comments
                
                # ENHANCED: Check if element is within comments section using DOM structure
                # But only stop if we haven't found any good content yet
                if self.is_element_in_comments_section(element):
                    if not found_main_content:
                        logger.debug(f"Element {i}: In comments section but no main content found yet, continuing...")
                        # Don't stop here, keep looking for actual content
                    else:
                        logger.debug(f"Stopping at element {i}: Element is within comments section structure and we have main content")
                        break
                
                # Check if this looks like a comment (starts with a name and time)
                # Pattern: "Person Name\n2h" or "Person Name\n5 mins"
                lines = text.split('\n')
                if len(lines) >= 2:
                    # Check second line for time indicators
                    second_line = lines[1].strip().lower()
                    # More specific time patterns
                    time_patterns = ['min ago', 'mins ago', 'hour ago', 'hours ago', 
                                   'day ago', 'days ago', 'week ago', 'weeks ago',
                                   '1h', '2h', '3h', '4h', '5h', '6h', '7h', '8h', '9h',
                                   '1d', '2d', '3d', '4d', '5d', '6d', '7d']
                    
                    if any(pattern in second_line for pattern in time_patterns):
                        # But only if it's not the first element (which could be post author/time)
                        if i > 0 and len(lines[0]) < 50:  # Name shouldn't be too long
                            logger.debug(f"Stopping at element {i}: Looks like a comment (name + timestamp)")
                            break
                
                # Skip metadata like reaction counts (but these usually come after the post)
                if all(word in text_lower for word in ['like', 'comment', 'share']) and len(text) < 50:
                    logger.debug(f"Element {i}: Skipping metadata")
                    continue
                
                # Skip if it's just a number or very short metadata
                if text.replace(',', '').replace('.', '').isdigit():
                    logger.debug(f"Element {i}: Skipping numeric metadata")
                    continue
                
                # ENHANCED: Handle author names - extract post content if present
                if self.is_likely_author_name(text, element):
                    logger.debug(f"Element {i}: Found author name, looking for post content: {text[:30]}...")
                    # Try to extract post content from the same element (after author name)
                    post_content = self.extract_content_after_author(text)
                    if post_content:
                        logger.debug(f"Element {i}: Extracted post content after author: {post_content[:50]}...")
                        post_texts.append(post_content)
                        found_main_content = True
                        if len(post_content) > 20:
                            logger.debug(f"Found good post content after author at element {i}, stopping here")
                            break
                    else:
                        # HYBRID: Don't stop on author names - keep searching for actual content
                        logger.debug(f"Element {i}: Author name but no content found, continuing search...")
                        continue  # Skip this author name element but keep looking
                
                # ENHANCED: Prioritize text that looks like actual post content
                if self.is_likely_post_content(text):
                    logger.debug(f"Element {i}: Found likely post content, length={len(text)}")
                    post_texts.append(text)
                    found_main_content = True
                    # If we found good post content, we can stop here
                    if len(text) > 20:  # Lowered threshold for better post content
                        logger.debug(f"Found good post content at element {i}, stopping here")
                        break
                elif not found_main_content:
                    # Only add questionable content if we haven't found good content yet
                    logger.debug(f"Element {i}: Adding as fallback content, length={len(text)}")
                    post_texts.append(text)
                    found_main_content = True
                
                # If we have substantial text (>80 chars), we probably have the main post
                if len(text) > 80:
                    logger.debug(f"Found substantial post content at element {i}, stopping here")
                    break  # We have the main post, stop here
                    
            except Exception as e:
                logger.debug(f"Failed to process element {i}: {e}")
                continue
        
        if post_texts:
            # Join all collected post texts
            combined_text = ' '.join(post_texts)
            logger.info(f"Extracted post text using {method_name} (stopped before comments): {combined_text[:100]}...")
            return combined_text
        
        # If we only have 1-2 elements total, just extract from the first one
        # This handles photo posts or posts with minimal text
        if len(elements) <= 2:
            for element in elements:
                text = safe_get_text(element, default="").strip()
                if text and len(text) > 5:
                    logger.info(f"Photo/minimal post - extracted: {text[:100]}...")
                    return text
        
        # HYBRID: Smart fallback - try to extract any meaningful content from elements
        logger.debug("Primary extraction failed, trying smart fallback...")
        return self.smart_fallback_extraction(elements, method_name)
    
    @time_method
    def extract_text_from_elements(self, elements: List[WebElement], method_name: str) -> str:
        """
        Extract and clean text from elements - ALTERNATIVE FIX: Smart post vs comment detection
        
        Args:
            elements: List of WebElements
            method_name: Name of extraction method for logging
            
        Returns:
            Cleaned text or empty string (prioritizes actual post content)
        """
        candidate_texts = []
        
        # Stronger comment indicators
        comment_indicators = [
            'reply', 'replies', 'like this', 'likes', 'react', 'share', 'shares',
            'ago', 'minute', 'minutes', 'hour', 'hours', 'day', 'days',
            'comment by', 'commented', 'see more', 'hide', 'translate',
            'write a comment', 'most relevant', 'view', 'views', 'see all'
        ]
        
        # Post-like indicators (things that suggest this is original content)
        post_indicators = [
            'looking for', 'need help', 'can anyone', 'does anyone', 'selling',
            'custom', 'handmade', 'design', 'project', 'finished', 'completed',
            'price', 'quote', 'estimate', 'available', 'contact me'
        ]
        
        for i, element in enumerate(elements):
            try:
                text = safe_get_text(element, default="").strip()
                if not text or len(text) < 10:
                    continue

                text_lower = text.lower()

                # Calculate scores for post vs comment likelihood
                comment_score = sum(1 for indicator in comment_indicators if indicator in text_lower)
                post_score = sum(1 for indicator in post_indicators if indicator in text_lower)
                
                # Element position matters - earlier elements more likely to be post
                position_bonus = max(0, 10 - i)  # First element gets +10, second +9, etc.
                
                # Length factor - posts are often longer than simple comments
                length_factor = min(len(text) / 50, 5)  # Cap at 5 points for very long text
                
                # Check if this looks like a timestamp or reaction count
                is_metadata = any(pattern in text_lower for pattern in [
                    'january', 'february', 'march', 'april', 'may', 'june',
                    'july', 'august', 'september', 'october', 'november', 'december',
                    '2023', '2024', '2025', 'am', 'pm'
                ]) and len(text) < 50
                
                # Skip obvious metadata
                if is_metadata:
                    continue
                
                # Calculate final score
                final_score = position_bonus + length_factor + post_score - (comment_score * 2)
                
                candidate_texts.append({
                    'text': text,
                    'score': final_score,
                    'length': len(text),
                    'position': i,
                    'comment_score': comment_score,
                    'post_score': post_score
                })
                
                logger.debug(f"Text candidate {i}: score={final_score:.1f}, length={len(text)}, comment_indicators={comment_score}, post_indicators={post_score}")
                
            except Exception as e:
                logger.debug(f"Failed to extract text from element {i}: {e}")
        
        if not candidate_texts:
            return ""
        
        # Sort by score descending, then by position ascending (prefer earlier elements)
        candidate_texts.sort(key=lambda x: (-x['score'], x['position']))
        
        # Log top candidates for debugging
        for i, candidate in enumerate(candidate_texts[:3]):
            logger.debug(f"Top candidate {i+1}: score={candidate['score']:.1f}, text='{candidate['text'][:60]}...'")
        
        # Return the highest scoring text
        best_candidate = candidate_texts[0]
        logger.info(f"Selected text using {method_name} (score={best_candidate['score']:.1f}): {best_candidate['text'][:100]}...")
        
        return best_candidate['text']
    
    @time_method
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
    
    def is_element_in_comments_section(self, element) -> bool:
        """
        Check if an element is within the comments section using DOM structure
        
        Args:
            element: WebElement to check
            
        Returns:
            True if element is within comments section, False otherwise
        """
        try:
            # Check if element is within a form (comment input)
            parent_forms = element.find_elements(By.XPATH, "./ancestor::form")
            if parent_forms:
                logger.debug("Element is within a form (likely comment input)")
                return True
            
            # Check if element has comment-related aria-labels in ancestors
            # But be more specific - only if it's actually a comment input or comment thread
            comment_aria_ancestors = element.find_elements(By.XPATH, 
                "./ancestor::*[contains(@aria-label, 'Write a comment') or contains(@aria-label, 'Comment thread') or contains(@aria-label, 'Reply to')]")
            if comment_aria_ancestors:
                logger.debug("Element has specific comment-related aria-label ancestors")
                return True
            
            # Check if element is after/within a "Comments" heading
            comments_headings = element.find_elements(By.XPATH, 
                "./preceding::h2[contains(text(), 'Comments')] | ./ancestor::*[.//h2[contains(text(), 'Comments')]]")
            if comments_headings:
                # But make sure it's not just the heading itself or post content before the heading
                following_post_content = element.find_elements(By.XPATH, 
                    "./following::*[contains(text(), 'Ring') or contains(text(), 'ISO') or contains(text(), 'WTB') or contains(text(), 'Looking')]")
                if not following_post_content:
                    logger.debug("Element appears after Comments heading with no post content following")
                    return True
            
            # Check if element is within comment interaction areas
            comment_interaction_ancestors = element.find_elements(By.XPATH,
                "./ancestor::*[@role='presentation'] | ./ancestor::*[contains(@class, 'comment')]")
            if comment_interaction_ancestors:
                logger.debug("Element is within comment interaction area")
                return True
                
        except Exception as e:
            logger.debug(f"Error checking if element is in comments section: {e}")
            
        return False
    
    def is_likely_author_name(self, text: str, element=None) -> bool:
        """
        Check if text looks like an author name rather than post content
        
        Args:
            text: Text to check
            element: WebElement for context (optional)
            
        Returns:
            True if this looks like an author name
        """
        if not text or len(text) > 50:  # Author names are usually short
            return False
            
        text = text.strip()
        
        # Common patterns for author names
        # 1. Two or three words that look like names
        words = text.split()
        if len(words) == 2 or len(words) == 3:
            # Check if words look like names (capitalized, no special chars)
            if all(word[0].isupper() and word.replace("'", "").replace("-", "").isalpha() for word in words if word):
                logger.debug(f"Detected author name pattern: {text}")
                return True
        
        # 2. Business names that are clearly not post content
        business_indicators = ['llc', 'inc', 'ltd', 'corp', 'jewelry', 'jewelers', 'diamonds', 'gems']
        if any(indicator in text.lower() for indicator in business_indicators) and len(words) <= 4:
            logger.debug(f"Detected business name pattern: {text}")
            return True
            
        # 3. Check DOM context - if element is near profile images or links
        if element:
            try:
                # Check if element is within or near profile link structures
                profile_context = element.find_elements(By.XPATH, 
                    "./ancestor::*[@role='link'] | ./ancestor::*[contains(@href, 'facebook.com')] | "
                    "./preceding-sibling::*//img[contains(@src, 'scontent')] | "
                    "./ancestor::*[contains(@class, 'x1heor9g')]")
                if profile_context:
                    logger.debug(f"Element in profile context: {text}")
                    return True
            except:
                pass
            
        return False
    
    def extract_content_after_author(self, text: str) -> str:
        """
        Extract post content from text that might contain author name + post content
        
        Args:
            text: Full text that may contain author name and post content
            
        Returns:
            Post content portion, or empty string if not found
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        
        # Strategy 1: If multi-line, skip first line (likely author) and get meaningful content
        if len(lines) > 1:
            # Skip the first line if it looks like an author name
            first_line = lines[0].strip()
            if self.is_likely_author_name(first_line, None):
                # Join remaining lines
                remaining_content = '\n'.join(lines[1:]).strip()
                # Check if remaining content looks like post content
                if remaining_content and self.is_likely_post_content(remaining_content):
                    return remaining_content
        
        # Strategy 2: Look for content after common separators
        separators = [' • ', ' - ', ' | ', ': ', '\n\n', '  ']
        for separator in separators:
            if separator in text:
                parts = text.split(separator, 1)  # Split only on first occurrence
                if len(parts) == 2:
                    first_part, second_part = parts
                    # If first part looks like author and second like content
                    if (self.is_likely_author_name(first_part.strip(), None) and 
                        self.is_likely_post_content(second_part.strip())):
                        return second_part.strip()
        
        # Strategy 3: If the text contains both author indicators and post indicators,
        # try to extract just the post portion
        text_lower = text.lower()
        post_keywords = ['iso ', 'wtb ', 'wts ', 'looking for', 'ring', 'diamond', 'need ', 'want ']
        
        # Find where post content might start
        for keyword in post_keywords:
            keyword_pos = text_lower.find(keyword)
            if keyword_pos > 0:  # Found keyword not at the beginning
                # Extract from keyword position
                potential_content = text[keyword_pos:].strip()
                if len(potential_content) > 10:  # Meaningful length
                    return potential_content
        
        return ""
    
    def smart_fallback_extraction(self, elements: List[WebElement], method_name: str) -> str:
        """
        HYBRID: Smart fallback that tries to find any meaningful content while avoiding author names
        
        Args:
            elements: List of WebElements
            method_name: Name of extraction method for logging
            
        Returns:
            Best available text content, avoiding pure author names
        """
        if not elements:
            logger.debug("No elements for smart fallback")
            return ""
        
        candidates = []
        
        # Collect all text candidates with analysis
        for i, element in enumerate(elements[:10]):  # Limit processing
            try:
                text = safe_get_text(element, default="").strip()
                if not text or len(text) < 3:
                    continue
                
                # Analyze this text candidate
                analysis = {
                    'text': text,
                    'length': len(text),
                    'is_author': self.is_likely_author_name(text, element),
                    'is_content': self.is_likely_post_content(text),
                    'has_punctuation': any(char in text for char in '.?!,:;'),
                    'word_count': len(text.split()),
                    'element_index': i
                }
                
                candidates.append(analysis)
                logger.debug(f"Candidate {i}: '{text[:30]}...' - Author: {analysis['is_author']}, Content: {analysis['is_content']}, Words: {analysis['word_count']}")
                
            except Exception as e:
                logger.debug(f"Failed to analyze element {i}: {e}")
                continue
        
        if not candidates:
            logger.debug("No text candidates found in smart fallback")
            return ""
        
        # HYBRID: Intelligent candidate selection
        # Priority 1: Clear post content (not author names)
        content_candidates = [c for c in candidates if c['is_content'] and not c['is_author']]
        if content_candidates:
            best = max(content_candidates, key=lambda c: c['length'])
            logger.info(f"Smart fallback found post content: {best['text'][:100]}...")
            return best['text']
        
        # Priority 2: Longer text that's not clearly an author name
        non_author_candidates = [c for c in candidates if not c['is_author'] and c['word_count'] > 2]
        if non_author_candidates:
            best = max(non_author_candidates, key=lambda c: c['length'])
            logger.info(f"Smart fallback found non-author text: {best['text'][:100]}...")
            return best['text']
        
        # Priority 3: Any text with punctuation (likely sentences)
        punctuation_candidates = [c for c in candidates if c['has_punctuation'] and c['length'] > 10]
        if punctuation_candidates:
            best = max(punctuation_candidates, key=lambda c: c['length'])
            logger.info(f"Smart fallback found punctuated text: {best['text'][:100]}...")
            return best['text']
        
        # Last resort: Longest available text (but warn it might be an author name)
        if candidates:
            best = max(candidates, key=lambda c: c['length'])
            if best['is_author']:
                logger.warning(f"Smart fallback defaulting to possible author name: {best['text'][:50]}...")
            else:
                logger.info(f"Smart fallback using longest text: {best['text'][:100]}...")
            return best['text']
        
        logger.debug("Smart fallback found no suitable content")
        return ""
    
    def is_likely_post_content(self, text: str) -> bool:
        """
        Check if text looks like actual post content
        
        Args:
            text: Text to check
            
        Returns:
            True if this looks like post content
        """
        if not text or len(text) < 5:
            return False
            
        text_lower = text.lower()
        
        # HYBRID: Enhanced indicators for all post types
        post_indicators = [
            # Jewelry-specific terms
            'iso ', 'wtb ', 'wts ', 'looking for', 'need ', 'want ', 'sell',
            'ring', 'diamond', 'gold', 'silver', 'jewelry', 'stone', 'setting',
            'mount', 'band', 'engagement', 'wedding', 'pendant', 'chain',
            'bracelet', 'necklace', 'earring', 'carat', 'ct', 'ruby', 'emerald',
            'sapphire', 'pearl', 'platinum', 'white gold', 'yellow gold',
            
            # General post patterns - EXPANDED
            'anyone have', 'does anyone', 'can someone', 'help me', 'advice',
            'question', 'thoughts', 'opinions', 'experience', 'recommend',
            'price', 'cost', 'budget', 'available', 'interested', 'urgent',
            'asap', 'please', 'thank you', 'thanks', 'appreciate',
            'trying to', 'attempting to', 'wondering if', 'curious about',
            
            # Question patterns - EXPANDED
            'how much', 'what is', 'where can', 'when will', 'why does',
            'which one', 'who has', 'how do', 'what do you think',
            'has anyone', 'any suggestions', 'any ideas', 'what about',
            
            # Business inquiry patterns
            'quote', 'estimate', 'custom', 'repair', 'resize', 'appraisal',
            'wholesale', 'retail', 'supplier', 'vendor', 'manufacturer',
            
            # HYBRID: Generic content patterns (any topic)
            'check out', 'take a look', 'here is', 'here are', 'this is',
            'just got', 'just finished', 'working on', 'proud of',
            'excited about', 'love this', 'amazing', 'beautiful', 'gorgeous'
        ]
        
        # Check for post content indicators
        indicator_count = sum(1 for indicator in post_indicators if indicator in text_lower)
        
        # Strong match if multiple indicators or specific high-value indicators
        if indicator_count >= 2:
            logger.debug(f"Strong post content match ({indicator_count} indicators): {text[:50]}...")
            return True
        elif indicator_count >= 1 and len(text) > 15:
            logger.debug(f"Good post content match: {text[:50]}...")
            return True
            
        # Check for sentence structure (contains punctuation, longer text)
        has_sentence_structure = ('.' in text or '?' in text or '!' in text or 
                                 ',' in text or ':' in text or ';' in text)
        if has_sentence_structure and len(text) > 25:
            logger.debug(f"Sentence structure detected: {text[:50]}...")
            return True
            
        return False
    
    def get_post_author_with_profile(self) -> tuple[str, str]:
        """
        Extract both author name and profile URL from Facebook post page.
        
        Returns:
            Tuple of (author_name, profile_url) or ("", "") if not found
        """
        start_time = time.time()
        logger.info("🔍 Starting enhanced author extraction (name + profile URL)...")
        
        try:
            # OPTIMIZED: Try most likely selectors first, prioritizing link elements
            author_selectors = [
                # Most common patterns first - prioritize <a> tags for profile links
                ("//div[@role='article']//h2//a[@role='link']", "H2 link"),
                ("//div[@role='article']//h3//a[@role='link']", "H3 link"),
                ("//div[@role='article']//a[contains(@href, 'facebook.com/') and @role='link'][1]", "FB profile link"),
                ("//h2//a[contains(@href, '/')]", "Generic H2 link"),
                # Fallback to span elements (but these won't have profile URLs)
                ("//div[@role='article']//h2//span", "H2 span"),
                ("//div[@role='article']//h3//span", "H3 span"),
            ]

            for i, (selector, description) in enumerate(author_selectors):
                selector_start = time.time()
                try:
                    elements = WebDriverWait(self.driver, 2).until(
                        lambda d: d.find_elements(By.XPATH, selector)
                    )
                    
                    selector_time = time.time() - selector_start
                    logger.debug(f"  Selector {i+1} ({description}): {len(elements)} elements in {selector_time:.2f}s")
                    
                    for j, element in enumerate(elements[:3]):  # Check max 3 elements per selector
                        try:
                            name = element.text.strip()
                            tag = element.tag_name
                            href = element.get_attribute('href') or "" if tag == 'a' else ""
                            
                            # DEBUGGING: More detailed URL logging to catch truncation
                            if tag == 'a' and href:
                                logger.debug(f"    Element {j}: tag='{tag}', name='{name[:50]}...', full_href='{href}'")
                            else:
                                logger.debug(f"    Element {j}: tag='{tag}', name='{name[:50]}...', no href")
                            
                            if not name:
                                logger.debug(f"    Element {j}: Skipping - no text content")
                                continue
                                
                            if not self.is_valid_author_name(name):
                                logger.debug(f"    Element {j}: Skipping - invalid author name: '{name}'")
                                continue
                                
                            if element.tag_name == 'a':
                                if not href:
                                    logger.debug(f"    Element {j}: Link element but no href attribute")
                                    continue
                                    
                                if 'facebook.com/' not in href:
                                    logger.debug(f"    Element {j}: Not a Facebook URL: {href}")
                                    continue
                                    
                                # DEBUGGING: Log URL before validation
                                logger.debug(f"    Element {j}: About to validate URL: '{href}'")
                                url_valid = self.is_valid_profile_url(href)
                                logger.debug(f"    Element {j}: URL validation result: {url_valid}")
                                
                                if not url_valid:
                                    logger.debug(f"    Element {j}: Invalid profile URL: {href}")
                                    continue
                                
                                # DEBUGGING: Clean comment parameters from profile URLs
                                cleaned_href = self.clean_profile_url(href)
                                logger.debug(f"    Element {j}: Cleaned URL from '{href}' to '{cleaned_href}'")
                                
                                # DEBUGGING: Log URL before return
                                logger.debug(f"    Element {j}: Returning valid URL: '{cleaned_href}'")
                                total_time = time.time() - start_time
                                logger.info(f"✅ Found author '{name}' with profile URL using {description} in {total_time:.2f}s")
                                logger.info(f"✅ Final URL being returned: '{cleaned_href}'")
                                return name, cleaned_href
                            else:
                                # For span elements, we only get the name
                                total_time = time.time() - start_time
                                logger.info(f"✅ Found author '{name}' (no profile URL) using {description} in {total_time:.2f}s")
                                return name, ""
                                
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
            logger.error(f"Failed to extract author with profile: {e}")
        
        total_time = time.time() - start_time
        logger.warning(f"❌ No author found after {total_time:.2f}s")
        return "", ""
    
    def is_valid_profile_url(self, url: str) -> bool:
        """
        Check if URL is a valid Facebook profile URL (not a content URL)
        
        Args:
            url: Facebook URL to validate
            
        Returns:
            True if it's a profile URL, False if it's content (photo/post/etc)
        """
        logger.debug(f"VALIDATION: Checking URL: '{url}' (length: {len(url) if url else 0})")
        
        if not url or 'facebook.com' not in url:
            logger.debug(f"VALIDATION: Rejecting - no URL or not Facebook: '{url}'")
            return False
        
        # FIXED: Handle group-based profile URLs
        # Group profile URL pattern: /groups/[groupid]/user/[userid]/
        if '/groups/' in url and '/user/' in url:
            logger.debug(f"VALIDATION: Accepting group-based profile URL: {url}")
            return True
            
        # Skip actual content URLs (but not group profile URLs)
        content_indicators = ['/photo/', '/posts/', '/videos/', 'fbid=', '/events/', '/pages/']
        if any(indicator in url for indicator in content_indicators):
            logger.debug(f"VALIDATION: Rejecting content URL: {url}")
            return False
            
        # Traditional profile URL patterns
        if '/profile.php?id=' in url:
            logger.debug(f"VALIDATION: Accepting traditional profile URL: {url}")
            return True
            
        # Direct profile URLs: facebook.com/username
        path_after_domain = url.split('facebook.com/')[1] if 'facebook.com/' in url else ""
        logger.debug(f"VALIDATION: Path after domain: '{path_after_domain}'")
        
        if path_after_domain and not path_after_domain.startswith(('photo', 'events', 'pages')):
            # Allow direct profile URLs but exclude obvious non-profile paths
            logger.debug(f"VALIDATION: Accepting direct profile URL: {url}")
            return True
            
        logger.debug(f"VALIDATION: Rejecting unrecognized URL format: {url}")
        return False
    
    def clean_profile_url(self, url: str) -> str:
        """
        Clean profile URL by removing comment tracking parameters and other non-essential params
        
        Args:
            url: Raw profile URL
            
        Returns:
            Cleaned profile URL suitable for Messenger links
        """
        if not url:
            return url
            
        logger.debug(f"CLEANING: Input URL: '{url}'")
        
        # Remove comment tracking parameters
        # These make URLs like: /KenWalkerJewelers?comment_id=XXX&__tn__=R*F
        # Into clean profile URLs: /KenWalkerJewelers
        
        # Split on ? to get base URL
        if '?' in url:
            base_url = url.split('?')[0]
            logger.debug(f"CLEANING: Removed query params, base URL: '{base_url}'")
        else:
            base_url = url
            logger.debug(f"CLEANING: No query params found, using as-is: '{base_url}'")
            
        return base_url
    
    @staticmethod
    def extract_facebook_id_from_profile_url(profile_url: str) -> Optional[str]:
        """
        Extract Facebook ID or username from profile URL for Messenger links
        
        Args:
            profile_url: Facebook profile URL
            
        Returns:
            Facebook ID/username or None if invalid
        """
        logger.debug(f"ID_EXTRACTION: Input URL: '{profile_url}' (length: {len(profile_url) if profile_url else 0})")
        
        if not profile_url or 'facebook.com' not in profile_url:
            logger.debug(f"ID_EXTRACTION: Rejecting - no URL or not Facebook: '{profile_url}'")
            return None
            
        try:
            if 'profile.php?id=' in profile_url:
                # Extract numeric ID: facebook.com/profile.php?id=123456789
                extracted = profile_url.split('id=')[1].split('&')[0]
                logger.debug(f"ID_EXTRACTION: Traditional profile - extracted: '{extracted}'")
                return extracted
            elif '/messages/' in profile_url:
                # Handle messenger URLs: /messages/t/123456789 or /messages/e2ee/t/123456789
                logger.debug(f"ID_EXTRACTION: Processing messenger URL: '{profile_url}'")
                
                # Look for the pattern after /messages/
                if '/messages/e2ee/t/' in profile_url:
                    extracted = profile_url.split('/messages/e2ee/t/')[1].split('/')[0].split('?')[0]
                elif '/messages/t/' in profile_url:
                    extracted = profile_url.split('/messages/t/')[1].split('/')[0].split('?')[0]
                else:
                    extracted = None
                
                logger.debug(f"ID_EXTRACTION: Messenger - extracted: '{extracted}'")
                return extracted
            elif '/groups/' in profile_url and '/user/' in profile_url:
                # FIXED: Handle group-based profile URLs
                # Extract from: /groups/[groupid]/user/[userid]/
                logger.debug(f"ID_EXTRACTION: Processing group-based URL: '{profile_url}'")
                
                # Detailed step-by-step extraction
                after_user = profile_url.split('/user/')[1]
                logger.debug(f"ID_EXTRACTION: After /user/ split: '{after_user}'")
                
                after_slash = after_user.split('/')[0]
                logger.debug(f"ID_EXTRACTION: After / split: '{after_slash}'")
                
                user_part = after_slash.split('?')[0]
                logger.debug(f"ID_EXTRACTION: After ? split: '{user_part}'")
                
                result = user_part if user_part else None
                logger.debug(f"ID_EXTRACTION: Group-based - final result: '{result}'")
                return result
            else:
                # Extract username: facebook.com/john.smith  
                after_domain = profile_url.split('facebook.com/')[1]
                logger.debug(f"ID_EXTRACTION: After domain split: '{after_domain}'")
                
                after_query = after_domain.split('?')[0]
                logger.debug(f"ID_EXTRACTION: After query split: '{after_query}'")
                
                path = after_query.split('/')[0]
                logger.debug(f"ID_EXTRACTION: After path split: '{path}'")
                
                result = path if path and path not in ['profile.php', 'photo', 'events'] else None
                logger.debug(f"ID_EXTRACTION: Username - final result: '{result}'")
                return result
        except (IndexError, AttributeError) as e:
            logger.error(f"ID_EXTRACTION: Exception during extraction: {e}")
            return None
    
    @staticmethod
    def create_messenger_link(profile_url: str) -> Optional[str]:
        """
        Create Facebook Messenger link from profile URL
        
        Args:
            profile_url: Facebook profile URL
            
        Returns:
            Messenger URL or None if unable to create
        """
        facebook_id = PostExtractor.extract_facebook_id_from_profile_url(profile_url)
        if facebook_id:
            return f"https://www.facebook.com/messages/t/{facebook_id}"
        return None
    
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
            # Use safe extraction to handle stale elements
            comments = []
            for el in comment_elements:
                text = safe_get_text(el, default="").strip()
                if text:
                    comments.append(text)
            return comments
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