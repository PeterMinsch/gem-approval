"""
Image Handler Module
Handles image extraction, validation, and uploading
"""

import os
import logging
import requests
from typing import List, Optional
from io import BytesIO
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


class ImageHandler:
    """Handles all image-related operations"""
    
    def __init__(self, driver, config: dict):
        """
        Initialize ImageHandler
        
        Args:
            driver: Selenium WebDriver instance
            config: Configuration dictionary
        """
        self.driver = driver
        self.config = config
    
    def extract_post_images(self, post_element: WebElement) -> List[str]:
        """
        Extract image URLs from a post
        
        Args:
            post_element: WebElement of the post
            
        Returns:
            List of image URLs
        """
        try:
            img_elements = post_element.find_elements(By.TAG_NAME, "img")
            image_urls = []
            
            for img in img_elements:
                src = img.get_attribute("src")
                if self.validate_image_url(src):
                    image_urls.append(src)
                    
            return image_urls
        except Exception as e:
            logger.error(f"Failed to extract images: {e}")
            return []
    
    def validate_image_url(self, url: str) -> bool:
        """
        Validate if a URL points to a valid image
        
        Args:
            url: Image URL to validate
            
        Returns:
            True if valid image URL, False otherwise
        """
        if not url:
            return False
            
        # Skip emojis, SVGs, icons, and profile images
        invalid_patterns = ["emoji", ".svg", "profile", "static", "icon"]
        if any(pattern in url for pattern in invalid_patterns):
            return False
            
        # Must be HTTP(S)
        if not url.startswith(("http://", "https://")):
            return False
            
        # Facebook CDN images are usually real
        if url.startswith("https://scontent") and url.endswith(".jpg"):
            return True
            
        # Other valid image extensions
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        return any(url.lower().endswith(ext) for ext in valid_extensions)
    
    def download_image(self, url: str) -> Optional[bytes]:
        """
        Download image from URL
        
        Args:
            url: Image URL
            
        Returns:
            Image bytes or None if download fails
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None
    
    def prepare_image_for_upload(self, image_data: bytes) -> Optional[str]:
        """
        Prepare image for upload (resize, convert format if needed)
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Path to prepared image file or None if preparation fails
        """
        # Stub implementation
        pass
    
    def upload_to_comment(self, image_paths: List[str]) -> bool:
        """
        Upload images to a Facebook comment
        
        Args:
            image_paths: List of local image file paths
            
        Returns:
            True if upload successful, False otherwise
        """
        # Stub implementation
        pass
    
    def cleanup_temp_images(self):
        """
        Clean up temporary image files
        """
        # Stub implementation
        pass