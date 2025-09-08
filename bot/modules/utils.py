"""
Utility Functions Module
Common utilities used across the bot modules
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Any
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException

logger = logging.getLogger(__name__)


def retry_on_failure(func: Callable = None, max_retries: int = 3, wait_time: float = 2.0, 
                    exceptions: tuple = (WebDriverException,)) -> Callable:
    """
    Decorator for retrying functions on failure
    
    Args:
        func: Function to wrap
        max_retries: Maximum number of retry attempts
        wait_time: Initial wait time between retries (exponential backoff)
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Wrapped function with retry logic
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    result = f(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(f"✅ {f.__name__} succeeded on retry {attempt + 1}")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"{f.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}")
                    
                    if attempt < max_retries - 1:
                        wait = wait_time * (attempt + 1)  # Exponential backoff
                        logger.info(f"Waiting {wait} seconds before retry...")
                        time.sleep(wait)
                    else:
                        logger.error(f"{f.__name__} failed after {max_retries} attempts")
            
            raise last_exception
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def with_driver_recovery(func: Callable) -> Callable:
    """
    Decorator to handle driver recovery on stale element exceptions
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with driver recovery logic
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except StaleElementReferenceException:
            logger.warning(f"Stale element in {func.__name__}, attempting recovery...")
            time.sleep(2)
            return func(self, *args, **kwargs)
        except WebDriverException as e:
            logger.error(f"WebDriver error in {func.__name__}: {e}")
            raise
    
    return wrapper


def human_like_delay(min_seconds: float = 0.5, max_seconds: float = 2.0):
    """
    Add a random human-like delay
    
    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def type_like_human(element, text: str, min_delay: float = 0.05, max_delay: float = 0.15):
    """
    Type text with human-like delays between keystrokes
    
    Args:
        element: Input element to type into
        text: Text to type
        min_delay: Minimum delay between keystrokes
        max_delay: Maximum delay between keystrokes
    """
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))


def safe_scroll_to_element(driver, element):
    """
    Safely scroll an element into view
    
    Args:
        driver: WebDriver instance
        element: WebElement to scroll to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.error(f"Failed to scroll to element: {e}")
        return False


def extract_numbers_from_string(text: str) -> list:
    """
    Extract all numbers from a string
    
    Args:
        text: String to extract numbers from
        
    Returns:
        List of numbers found in the string
    """
    import re
    return re.findall(r'\d+', text)


def generate_unique_id() -> str:
    """
    Generate a unique ID for tracking
    
    Returns:
        Unique ID string
    """
    import uuid
    return str(uuid.uuid4())[:8]


def clean_text(text: str) -> str:
    """
    Clean and normalize text
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove zero-width characters
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    
    return text.strip()