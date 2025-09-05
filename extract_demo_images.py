#!/usr/bin/env python3
"""
Extract images from Facebook posts for demo purposes
"""

import sys
import os
import json
import logging
import time
from typing import List, Optional

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot'))

try:
    from database import db
    from facebook_comment_bot import FacebookAICommentBot
    from bravo_config import CONFIG as config
except ImportError as e:
    print(f"Error importing bot modules: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageExtractor:
    def __init__(self):
        self.bot = None
    
    def setup_bot(self):
        """Initialize bot with driver for image extraction"""
        try:
            logger.info("Setting up bot for image extraction...")
            self.bot = FacebookAICommentBot(config)
            self.bot.setup_driver()
            logger.info("✅ Bot initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to setup bot: {e}")
            return False
    
    def extract_images_from_url(self, post_url: str) -> List[str]:
        """Extract images from a Facebook post URL"""
        try:
            logger.info(f"🔍 Extracting images from: {post_url}")
            
            # Navigate to the post
            self.bot.driver.get(post_url)
            time.sleep(3)  # Wait for page load
            
            # Try to extract images using bot's method
            images = []
            
            # Use multiple selectors to find images
            image_selectors = [
                "//img[contains(@src, 'scontent')]",
                "//img[contains(@src, 'fbcdn')]", 
                "//img[contains(@class, 'scaledImageFitWidth')]",
                "//img[contains(@class, 'img')]",
                "//div[@data-pagelet='MediaViewerPhoto']//img",
                "//div[contains(@class, 'x1lliihq')]//img"
            ]
            
            for selector in image_selectors:
                try:
                    from selenium.webdriver.common.by import By
                    img_elements = self.bot.driver.find_elements(By.XPATH, selector)
                    logger.info(f"Selector {selector[:30]}... found {len(img_elements)} images")
                    
                    for img in img_elements:
                        try:
                            src = img.get_attribute('src')
                            if src and ('scontent' in src or 'fbcdn' in src) and src not in images:
                                # Filter out tiny images (profile pics, icons)
                                try:
                                    width = img.get_attribute('width') or '0'
                                    height = img.get_attribute('height') or '0'
                                    if int(width) > 100 and int(height) > 100:
                                        images.append(src)
                                        logger.info(f"✅ Found image: {src[:80]}...")
                                except:
                                    # If we can't get dimensions, include it anyway
                                    images.append(src)
                                    logger.info(f"✅ Found image: {src[:80]}...")
                        except Exception as e:
                            continue
                except Exception as e:
                    logger.warning(f"Selector failed: {e}")
                    continue
            
            logger.info(f"🎯 Total images extracted: {len(images)}")
            return images[:5]  # Limit to 5 images max
            
        except Exception as e:
            logger.error(f"❌ Error extracting images from {post_url}: {e}")
            return []
    
    def update_demo_comments_with_images(self):
        """Update the demo comments with actual post images"""
        try:
            logger.info("🔄 Updating demo comments with extracted images...")
            
            # Get pending comments
            pending_comments = db.get_pending_comments()
            if not pending_comments:
                logger.warning("No pending comments found")
                return False
            
            updated_count = 0
            for comment in pending_comments:
                comment_id = comment.get('id')
                post_url = comment.get('post_url')
                
                if not post_url or 'facebook.com' not in post_url:
                    logger.info(f"Skipping comment {comment_id}: no valid Facebook URL")
                    continue
                
                logger.info(f"📸 Processing comment {comment_id}: {post_url}")
                
                # Extract images from this post
                images = self.extract_images_from_url(post_url)
                
                if images:
                    # Update the comment with extracted images
                    images_json = json.dumps(images)
                    
                    # Update database directly
                    import sqlite3
                    conn = sqlite3.connect(db.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE comment_queue SET post_images = ? WHERE id = ?",
                        (images_json, comment_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"✅ Updated comment {comment_id} with {len(images)} images")
                    updated_count += 1
                else:
                    logger.warning(f"⚠️ No images found for comment {comment_id}")
            
            logger.info(f"🎉 Updated {updated_count}/{len(pending_comments)} comments with images")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error updating comments: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.bot and self.bot.driver:
                self.bot.driver.quit()
                logger.info("🔧 Browser closed")
        except:
            pass

def main():
    """Main function"""
    logger.info("🚀 Starting Image Extraction for Demo Comments")
    logger.info("=" * 60)
    
    extractor = ImageExtractor()
    
    try:
        # Setup bot
        if not extractor.setup_bot():
            return False
        
        # Extract images and update comments
        success = extractor.update_demo_comments_with_images()
        
        if success:
            print("\n🎉 SUCCESS: Demo comments updated with post images!")
            print("🌐 Your web interface should now show the actual Facebook post images")
        else:
            print("\n💥 FAILED: Could not extract images from posts")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}")
        return False
    
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    main()