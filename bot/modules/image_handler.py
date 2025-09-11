"""
Image Handler Module
Handles image extraction, validation, and uploading
"""

import os
import logging
import requests
import tempfile
import base64
import uuid
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
    
    def convert_base64_to_temp_file(self, base64_data: str) -> Optional[str]:
        """
        Convert base64 image data to a temporary file
        
        Args:
            base64_data: Base64 encoded image string (e.g., "data:image/png;base64,...")
            
        Returns:
            Path to temporary file or None if conversion fails
        """
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image'):
                # Extract the actual base64 data after the comma
                base64_data = base64_data.split(',')[1]
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_data)
            
            # Create temporary file with unique name
            temp_dir = tempfile.gettempdir()
            unique_filename = f"post_image_{uuid.uuid4().hex[:8]}.png"
            temp_file_path = os.path.join(temp_dir, unique_filename)
            
            # Write image bytes to temporary file
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(image_bytes)
            
            # Verify file was created successfully
            if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) > 0:
                logger.debug(f"✅ Created temporary file: {temp_file_path}")
                return temp_file_path
            else:
                logger.error(f"❌ Failed to create temporary file: {temp_file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to convert base64 to temporary file: {e}")
            return None
    
    def convert_post_images_to_files(self, post_images: List[str]) -> List[str]:
        """
        Convert a list of base64 post images to temporary files
        
        Args:
            post_images: List of base64 encoded image strings
            
        Returns:
            List of temporary file paths
        """
        temp_file_paths = []
        
        for i, base64_img in enumerate(post_images):
            temp_path = self.convert_base64_to_temp_file(base64_img)
            if temp_path:
                temp_file_paths.append(temp_path)
                logger.debug(f"📷 Converted post image {i+1}/{len(post_images)} to {temp_path}")
            else:
                logger.warning(f"⚠️ Failed to convert post image {i+1}/{len(post_images)}")
        
        logger.info(f"📁 Converted {len(temp_file_paths)}/{len(post_images)} post images to temporary files")
        return temp_file_paths