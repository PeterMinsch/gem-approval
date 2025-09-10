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
        Extract images as base64 data from a post
        
        Args:
            post_element: WebElement of the post
            
        Returns:
            List of base64 encoded images
        """
        try:
            img_elements = post_element.find_elements(By.TAG_NAME, "img")
            image_data_list = []
            
            for img in img_elements:
                src = img.get_attribute("src")
                if not self.validate_image_url(src):
                    continue
                    
                try:
                    # Method 1: Try to screenshot the specific image element
                    img_base64 = self.capture_element_as_base64(img)
                    if img_base64:
                        image_data_list.append(img_base64)
                        logger.debug(f"✅ Captured image via element screenshot")
                    else:
                        # Method 2: Use canvas to extract image data
                        canvas_base64 = self.extract_image_via_canvas(img)
                        if canvas_base64:
                            image_data_list.append(canvas_base64)
                            logger.debug(f"✅ Captured image via canvas method")
                except Exception as img_error:
                    logger.debug(f"Failed to capture individual image: {img_error}")
                    
            logger.info(f"📷 Extracted {len(image_data_list)} images as base64")
            return image_data_list
        except Exception as e:
            logger.error(f"Failed to extract images: {e}")
            return []
    
    def capture_element_as_base64(self, element: WebElement) -> Optional[str]:
        """
        Capture a specific element as base64 screenshot
        
        Args:
            element: WebElement to capture
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            # Selenium can screenshot specific elements
            png_bytes = element.screenshot_as_png
            import base64
            base64_string = base64.b64encode(png_bytes).decode('utf-8')
            return f"data:image/png;base64,{base64_string}"
        except Exception as e:
            logger.debug(f"Element screenshot failed: {e}")
            return None
    
    def extract_image_via_canvas(self, img_element: WebElement) -> Optional[str]:
        """
        Extract image data using canvas (bypasses CORS)
        
        Args:
            img_element: Image WebElement
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            # JavaScript to extract image via canvas
            script = """
            var img = arguments[0];
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
            
            // Set canvas size to image size
            canvas.width = img.naturalWidth || img.width;
            canvas.height = img.naturalHeight || img.height;
            
            // Draw image to canvas
            ctx.drawImage(img, 0, 0);
            
            // Get base64 data
            try {
                return canvas.toDataURL('image/png');
            } catch(e) {
                // If CORS blocks even this, return null
                return null;
            }
            """
            
            base64_data = self.driver.execute_script(script, img_element)
            if base64_data and base64_data.startswith('data:image'):
                return base64_data
            return None
            
        except Exception as e:
            logger.debug(f"Canvas extraction failed: {e}")
            return None
    
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