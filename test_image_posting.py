#!/usr/bin/env python3
"""
Demo Script: Populate Comment Approval Queue for Image Posting Demo
Populates the comment approval queue with specific post links to demonstrate
image posting functionality without requiring the bot to be running.
"""

import sys
import os
import json
import logging
import random
from datetime import datetime
from typing import List, Dict

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot'))

# Import bot configuration and database
try:
    from bravo_config import CONFIG as config
    from database import db
    from comment_generator import CommentGenerator
    from classifier import PostClassifier
except ImportError as e:
    print(f"Error importing bot modules: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommentQueuePopulator:
    def __init__(self):
        self.comment_generator = CommentGenerator(config, database=db)
        self.classifier = PostClassifier(config)
        
    def get_sample_post_data(self) -> List[Dict]:
        """Generate sample post data for different post types"""
        return [
            {
                "url": "https://www.facebook.com/photo/?fbid=122143481480825821&set=gm.31193893066920578&idorvanity=5440421919361046",
                "text": "Looking for help with custom engagement ring design. Need CAD work and stone setting for a vintage-style ring with emerald cut center stone and side diamonds.",
                "author": "Sarah Johnson",
                "post_type": "service",
                "engagement": "5 likes, 2 comments"
            },
            {
                "url": "https://www.facebook.com/photo/?fbid=987654321098765&set=gm.456789123456789&idorvanity=5440421919361046", 
                "text": "ISO - anyone have this style bracelet available? Looking for something similar in white gold with diamonds.",
                "author": "Mike Chen",
                "post_type": "iso",
                "engagement": "12 likes, 8 comments"
            },
            {
                "url": "https://www.facebook.com/photo/?fbid=555666777888999&set=gm.789012345678901&idorvanity=5440421919361046",
                "text": "Just finished this beautiful tennis bracelet! The sparkle is incredible ✨",
                "author": "Jennifer Martinez", 
                "post_type": "general",
                "engagement": "28 likes, 15 comments"
            },
            {
                "url": "https://www.facebook.com/photo/?fbid=111222333444555&set=gm.234567890123456&idorvanity=5440421919361046",
                "text": "Need urgent help with stone replacement in this vintage ring. Original stone cracked and client needs it ready for anniversary.",
                "author": "David Wilson",
                "post_type": "service", 
                "engagement": "3 likes, 1 comment"
            },
            {
                "url": "https://www.facebook.com/photo/?fbid=777888999000111&set=gm.567890123456789&idorvanity=5440421919361046",
                "text": "Does anyone carry this exact pendant design? Client is looking for an exact match.",
                "author": "Lisa Thompson",
                "post_type": "iso",
                "engagement": "7 likes, 4 comments"
            }
        ]
    
    def get_available_image_packs(self) -> List[Dict]:
        """Get available image packs for assignment"""
        try:
            image_packs = db.get_image_packs()
            if image_packs:
                logger.info(f"✅ Found {len(image_packs)} image packs in database")
                return image_packs
            else:
                logger.info("📦 No image packs found, creating default pack")
                return self.create_default_image_pack()
        except Exception as e:
            logger.error(f"❌ Error getting image packs: {e}")
            return self.create_default_image_pack()
    
    def create_default_image_pack(self) -> List[Dict]:
        """Create a default image pack for demo purposes"""
        try:
            pack_id = db.create_image_pack("Demo Image Pack", "GENERIC")
            if pack_id:
                logger.info(f"✅ Created demo image pack: {pack_id}")
                return [{"id": pack_id, "name": "Demo Image Pack", "category": "GENERIC"}]
        except Exception as e:
            logger.error(f"❌ Failed to create demo image pack: {e}")
        return []
    
    def populate_comment_queue(self, post_urls: List[str] = None) -> bool:
        """Populate comment approval queue with sample posts and generated comments"""
        try:
            logger.info("🔄 Starting comment queue population...")
            
            # Use provided URLs or default sample data
            if post_urls:
                posts_data = []
                for i, url in enumerate(post_urls):
                    sample_posts = self.get_sample_post_data()
                    if i < len(sample_posts):
                        post_data = sample_posts[i].copy()
                        post_data["url"] = url  # Override with provided URL
                        posts_data.append(post_data)
                    else:
                        # Generate basic post data for additional URLs
                        posts_data.append({
                            "url": url,
                            "text": f"Sample jewelry post #{i+1}",
                            "author": f"Demo User {i+1}",
                            "post_type": random.choice(["service", "iso", "general"]),
                            "engagement": f"{random.randint(1, 15)} likes, {random.randint(0, 8)} comments"
                        })
            else:
                posts_data = self.get_sample_post_data()
            
            # Get available image packs
            image_packs = self.get_available_image_packs()
            
            # Process each post
            success_count = 0
            for post_data in posts_data:
                try:
                    logger.info(f"📝 Processing post: {post_data['url']}")
                    
                    # Generate appropriate comment
                    comment = self.comment_generator.generate_comment(
                        post_data["post_type"], 
                        post_data["text"], 
                        post_data["author"]
                    )
                    
                    if not comment:
                        logger.warning(f"⚠️ Could not generate comment for post type: {post_data['post_type']}")
                        comment = f"Hi {post_data['author'].split()[0]}! We're Bravo Creations - full-service jewelry manufacturing. (760) 431-9977 • welcome.bravocreations.com"
                    
                    # Select random image pack for demo
                    image_pack_id = None
                    if image_packs:
                        selected_pack = random.choice(image_packs)
                        image_pack_id = selected_pack["id"]
                        logger.info(f"📦 Assigned image pack: {selected_pack['name']}")
                    
                    # Add to comment queue
                    queue_id = db.add_to_comment_queue(
                        post_url=post_data["url"],
                        post_text=post_data["text"],
                        comment_text=comment,
                        post_type=post_data["post_type"],
                        post_screenshot=None,  # No screenshot for demo
                        post_images=json.dumps([]),  # No post images for demo
                        post_author=post_data["author"],
                        post_engagement=post_data["engagement"],
                        image_pack_id=image_pack_id
                    )
                    
                    if queue_id:
                        logger.info(f"✅ Added to queue (ID: {queue_id}): {post_data['post_type']} post by {post_data['author']}")
                        success_count += 1
                    else:
                        logger.error(f"❌ Failed to add post to queue: {post_data['url']}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing post {post_data['url']}: {e}")
                    continue
            
            logger.info(f"🎉 Successfully populated queue with {success_count}/{len(posts_data)} posts")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error populating comment queue: {e}")
            return False
    
    def clear_existing_queue(self) -> bool:
        """Clear existing comment queue for fresh demo"""
        try:
            logger.info("🗑️ Clearing existing comment queue...")
            # Get pending comments and delete them
            pending_comments = db.get_comment_queue()
            deleted_count = 0
            
            for comment in pending_comments:
                if comment.get('status') == 'pending':
                    try:
                        db.delete_comment_queue_item(comment['id'])
                        deleted_count += 1
                    except:
                        continue
            
            logger.info(f"✅ Cleared {deleted_count} pending comments from queue")
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing comment queue: {e}")
            return True  # Don't fail the whole process if this fails
    
    def show_queue_summary(self) -> None:
        """Show summary of populated comment queue"""
        try:
            logger.info("📊 Comment Queue Summary:")
            logger.info("=" * 50)
            
            pending_comments = db.get_comment_queue()
            if not pending_comments:
                logger.info("📝 No comments in queue")
                return
            
            by_type = {}
            for comment in pending_comments:
                post_type = comment.get('post_type', 'unknown')
                if post_type not in by_type:
                    by_type[post_type] = 0
                by_type[post_type] += 1
            
            logger.info(f"📈 Total comments in queue: {len(pending_comments)}")
            for post_type, count in by_type.items():
                logger.info(f"   - {post_type}: {count} comments")
            
            # Show first few comments as examples
            logger.info("\n📝 Sample comments:")
            for i, comment in enumerate(pending_comments[:3]):
                logger.info(f"   {i+1}. [{comment.get('post_type', 'unknown')}] {comment.get('post_author', 'Unknown')}: {comment.get('comment_text', '')[:80]}...")
            
            if len(pending_comments) > 3:
                logger.info(f"   ... and {len(pending_comments) - 3} more")
            
            logger.info("\n🚀 Ready for demo! Visit your web interface to:")
            logger.info("   1. View pending comments for approval")
            logger.info("   2. Attach images using image packs")
            logger.info("   3. Edit comments and select templates")
            logger.info("   4. Approve and post comments")
            
        except Exception as e:
            logger.error(f"❌ Error showing queue summary: {e}")
    
    def run_demo_setup(self, post_urls: List[str] = None) -> bool:
        """Run the complete demo setup workflow"""
        try:
            logger.info("🔧 Setting up demo environment...")
            
            # Step 1: Clear existing queue
            self.clear_existing_queue()
            
            # Step 2: Populate comment queue
            logger.info("📝 Populating comment queue with demo data...")
            if not self.populate_comment_queue(post_urls):
                logger.error("❌ Failed to populate comment queue")
                return False
            
            # Step 3: Show summary
            self.show_queue_summary()
            
            logger.info("✅ Demo setup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Demo setup failed: {e}")
            return False

def main(post_urls: List[str] = None):
    """Main demo setup function"""
    logger.info("🚀 Starting Comment Queue Population for Image Posting Demo")
    logger.info("📦 This script will populate your approval queue with demo posts")
    logger.info("=" * 60)
    
    populator = CommentQueuePopulator()
    success = populator.run_demo_setup(post_urls)
    
    if success:
        print("\n🎉 SUCCESS: Comment approval queue is ready for demo!")
        print("🌐 Visit your web interface to:")
        print("   • View pending comments")
        print("   • Attach images using image packs")
        print("   • Edit comments and templates") 
        print("   • Approve and post comments")
    else:
        print("\n💥 FAILED: Check the logs for issues.")
    
    return success

def main_with_urls():
    """Interactive version that accepts custom URLs"""
    print("🚀 Image Posting Demo Setup")
    print("=" * 40)
    
    # Ask if user wants to provide custom URLs
    response = input("Do you want to provide custom Facebook post URLs? (y/n): ").lower().strip()
    
    post_urls = []
    if response in ['y', 'yes']:
        print("\nEnter Facebook post URLs (one per line, empty line to finish):")
        while True:
            url = input("URL: ").strip()
            if not url:
                break
            if "facebook.com" in url:
                post_urls.append(url)
                print(f"✅ Added: {url}")
            else:
                print("⚠️ Please enter a valid Facebook URL")
        
        if not post_urls:
            print("No valid URLs provided. Using default sample data.")
    
    return main(post_urls if post_urls else None)

if __name__ == "__main__":
    # Check command line arguments
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        main_with_urls()
    elif len(sys.argv) > 1:
        # URLs provided as command line arguments
        urls = [arg for arg in sys.argv[1:] if "facebook.com" in arg]
        if urls:
            main(urls)
        else:
            print("No valid Facebook URLs found in arguments")
            main()
    else:
        main()