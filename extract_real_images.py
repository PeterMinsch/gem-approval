#!/usr/bin/env python3
"""
Extract actual images from real Facebook URLs for demo comments
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

def extract_images_from_url(bot, post_url: str) -> List[str]:
    """Extract images from a Facebook post URL"""
    try:
        logger.info(f"Extracting images from: {post_url}")
        
        # Navigate to the post
        bot.driver.get(post_url)
        time.sleep(4)  # Wait for page load
        
        # Try to extract images using bot's method
        images = []
        
        # Use multiple selectors to find images
        image_selectors = [
            "//img[contains(@src, 'scontent')]",
            "//img[contains(@src, 'fbcdn')]"
        ]
        
        for selector in image_selectors:
            try:
                from selenium.webdriver.common.by import By
                img_elements = bot.driver.find_elements(By.XPATH, selector)
                logger.info(f"Found {len(img_elements)} images with selector")
                
                for img in img_elements:
                    try:
                        src = img.get_attribute('src')
                        if src and ('scontent' in src or 'fbcdn' in src) and src not in images:
                            # Filter out tiny images (profile pics, icons)
                            try:
                                width = img.get_attribute('naturalWidth') or img.get_attribute('width') or '0'
                                height = img.get_attribute('naturalHeight') or img.get_attribute('height') or '0'
                                if int(width) > 200 and int(height) > 200:
                                    images.append(src)
                                    logger.info(f"Found large image: {src[:60]}...")
                            except:
                                if len(src) > 100:  # Long URLs are usually full-size images
                                    images.append(src)
                                    logger.info(f"Found image: {src[:60]}...")
                    except Exception as e:
                        continue
            except Exception as e:
                continue
        
        logger.info(f"Total images extracted: {len(images)}")
        return images[:3]  # Limit to 3 images max
        
    except Exception as e:
        logger.error(f"Error extracting images from {post_url}: {e}")
        return []

def main():
    """Main function"""
    logger.info("Starting Real Image Extraction for Demo Comments")
    logger.info("=" * 60)
    
    bot = None
    try:
        # Setup bot
        logger.info("Setting up bot...")
        bot = FacebookAICommentBot(config)
        bot.setup_driver()
        logger.info("Bot initialized successfully")
        
        # Get demo comments
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, post_author, post_url FROM comment_queue WHERE id IN (12,13,14,15) AND post_url LIKE "%facebook.com%"')
        comments = cursor.fetchall()
        
        updated_count = 0
        for comment_id, author, post_url in comments:
            logger.info(f"Processing comment {comment_id} ({author})")
            
            # Extract images from this post
            images = extract_images_from_url(bot, post_url)
            
            if images:
                # Update the comment with extracted images
                images_json = json.dumps(images)
                cursor.execute(
                    "UPDATE comment_queue SET post_images = ? WHERE id = ?",
                    (images_json, comment_id)
                )
                conn.commit()
                logger.info(f"Updated comment {comment_id} with {len(images)} real images")
                updated_count += 1
            else:
                logger.warning(f"No images found for comment {comment_id}")
        
        conn.close()
        
        if updated_count > 0:
            print(f"\nSUCCESS: Updated {updated_count} comments with real Facebook images!")
        else:
            print("\nNo images were extracted from the Facebook posts")
        
        return updated_count > 0
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        return False
    
    finally:
        if bot and bot.driver:
            try:
                bot.driver.quit()
                logger.info("Browser closed")
            except:
                pass

if __name__ == "__main__":
    main()