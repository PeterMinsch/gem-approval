"""
Stale Element Handler Module
Utilities for handling StaleElementReferenceException in Selenium
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, List, Optional
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)

# Default retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 0.5


def retry_on_stale(max_retries: int = DEFAULT_MAX_RETRIES, delay: float = DEFAULT_RETRY_DELAY):
    """
    Decorator that retries a function if StaleElementReferenceException occurs.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds

    Usage:
        @retry_on_stale(max_retries=3)
        def click_element(element):
            element.click()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.debug(f"Stale element on attempt {attempt + 1}/{max_retries + 1}, retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.warning(f"Stale element after {max_retries + 1} attempts in {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


def safe_get_attribute(element: WebElement, attribute: str, default: str = "") -> str:
    """
    Safely get an attribute from an element, handling stale elements.

    Args:
        element: WebElement to get attribute from
        attribute: Name of attribute to get
        default: Default value if attribute not found or element is stale

    Returns:
        Attribute value or default
    """
    try:
        value = element.get_attribute(attribute)
        return value if value is not None else default
    except StaleElementReferenceException:
        logger.debug(f"Stale element when getting attribute '{attribute}'")
        return default
    except Exception as e:
        logger.debug(f"Error getting attribute '{attribute}': {e}")
        return default


def safe_get_text(element: WebElement, default: str = "") -> str:
    """
    Safely get text from an element, handling stale elements.

    Args:
        element: WebElement to get text from
        default: Default value if element is stale

    Returns:
        Element text or default
    """
    try:
        return element.text
    except StaleElementReferenceException:
        logger.debug("Stale element when getting text")
        return default
    except Exception as e:
        logger.debug(f"Error getting text: {e}")
        return default


def extract_hrefs_safely(elements: List[WebElement]) -> List[str]:
    """
    Extract href attributes from a list of elements, handling stale elements.
    Extracts data immediately to avoid stale element issues.

    Args:
        elements: List of WebElements (likely <a> tags)

    Returns:
        List of href values (excluding empty/None values)
    """
    hrefs = []
    for i, element in enumerate(elements):
        try:
            href = element.get_attribute('href')
            if href:
                hrefs.append(href)
        except StaleElementReferenceException:
            logger.debug(f"Stale element at index {i} when extracting href")
            continue
        except Exception as e:
            logger.debug(f"Error extracting href at index {i}: {e}")
            continue
    return hrefs


def extract_element_data_safely(
    elements: List[WebElement],
    attributes: List[str] = None,
    include_text: bool = True
) -> List[dict]:
    """
    Extract multiple attributes and text from elements immediately.
    This is the key function for Option 2 - extract data immediately to avoid stale elements.

    Args:
        elements: List of WebElements
        attributes: List of attribute names to extract (e.g., ['href', 'class'])
        include_text: Whether to include element text

    Returns:
        List of dicts containing extracted data
    """
    if attributes is None:
        attributes = []

    extracted_data = []

    for i, element in enumerate(elements):
        data = {'_index': i, '_valid': True}

        try:
            # Extract text first (most likely to be needed)
            if include_text:
                data['text'] = element.text

            # Extract requested attributes
            for attr in attributes:
                data[attr] = element.get_attribute(attr)

            extracted_data.append(data)

        except StaleElementReferenceException:
            logger.debug(f"Stale element at index {i}, skipping")
            data['_valid'] = False
            extracted_data.append(data)
            continue
        except Exception as e:
            logger.debug(f"Error extracting data at index {i}: {e}")
            data['_valid'] = False
            extracted_data.append(data)
            continue

    # Filter out invalid entries
    return [d for d in extracted_data if d.get('_valid', False)]


def find_elements_with_retry(
    driver,
    by,
    value: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay: float = DEFAULT_RETRY_DELAY
) -> List[WebElement]:
    """
    Find elements with retry logic for transient failures.

    Args:
        driver: Selenium WebDriver instance
        by: Locator strategy (e.g., By.XPATH)
        value: Locator value
        max_retries: Maximum retry attempts
        delay: Delay between retries

    Returns:
        List of found elements (may be empty)
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            elements = driver.find_elements(by, value)
            return elements
        except StaleElementReferenceException as e:
            last_exception = e
            if attempt < max_retries:
                logger.debug(f"Stale element during find on attempt {attempt + 1}, retrying...")
                time.sleep(delay)
        except Exception as e:
            logger.debug(f"Error finding elements: {e}")
            return []

    logger.warning(f"Failed to find elements after {max_retries + 1} attempts")
    return []


def collect_links_with_extraction(
    driver,
    xpath: str,
    max_retries: int = DEFAULT_MAX_RETRIES
) -> List[str]:
    """
    Find link elements and immediately extract their hrefs.
    Combines finding and extraction to minimize stale element window.

    Args:
        driver: Selenium WebDriver instance
        xpath: XPath to find link elements
        max_retries: Maximum retry attempts

    Returns:
        List of href values
    """
    for attempt in range(max_retries + 1):
        try:
            # Find elements
            elements = driver.find_elements("xpath", xpath)

            if not elements:
                return []

            # Immediately extract hrefs - don't store element references
            hrefs = []
            for element in elements:
                try:
                    href = element.get_attribute('href')
                    if href:
                        hrefs.append(href)
                except StaleElementReferenceException:
                    # Individual element went stale, continue with others
                    continue

            return hrefs

        except StaleElementReferenceException:
            if attempt < max_retries:
                logger.debug(f"Stale element during link collection attempt {attempt + 1}, retrying...")
                time.sleep(DEFAULT_RETRY_DELAY)
            continue
        except Exception as e:
            logger.debug(f"Error collecting links: {e}")
            return []

    logger.warning(f"Failed to collect links after {max_retries + 1} attempts")
    return []
