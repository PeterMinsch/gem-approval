#!/usr/bin/env python3
"""
Auto-Repopulate Demo Queue Script
Quickly repopulates the comment approval queue with real Facebook posts for demo purposes.
Run this anytime you need to reset your demo environment.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add the bot directory to Python path
bot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot')
sys.path.append(bot_dir)

# Change to bot directory to ensure correct database path
original_cwd = os.getcwd()
os.chdir(bot_dir)

try:
    from database import db
    from comment_generator import CommentGenerator
    from bravo_config import CONFIG as config
except ImportError as e:
    print(f"Error importing bot modules: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DemoQueueManager:
    def __init__(self):
        self.comment_generator = CommentGenerator(config, database=db)
        
        # Your real Facebook posts with actual images and content
        self.demo_posts = [
            {
                'url': 'https://www.facebook.com/photo/?fbid=24358671130457313&set=pcb.30915708561405698',
                'text': 'Hello! I have a costumer that just got her ring a week ago, in my opinion the person that made it put the marquee diamond on an oval/round crown with only four prongs, the marquee already chip on one tip and stone fell out days after she got it, she absolutely loves the design on the crown, I need advice on how I can secure the stone with preferably keeping the design, Is it possible or should we go for a new crown? Could I put bigger prongs and add more? Would that make it stronger? Please help',
                'author': 'Sarah Johnson',
                'post_type': 'service',
                'image': 'https://scontent-lax3-1.xx.fbcdn.net/v/t39.30808-6/531584279_24358672240457202_1540481224194654532_n.jpg?stp=cp6_dst-jpg_tt6&_nc_cat=105&ccb=1-7&_nc_sid=aa7b47&_nc_ohc=nU22EmxONkUQ7kNvwHu2D3n&_nc_oc=AdmbwjaPsxP90CUIUoJmEmS4RBDClLJyAMAmdhuuzIg6biEPw-G52S2U0Q67LuGqr9o&_nc_zt=23&_nc_ht=scontent-lax3-1.xx&_nc_gid=ON82h3ZyoLT6GuahYE2byg&oh=00_AfYTOh2mlw3vUGlJ_NjRDQngZ14Gn5Ced4-NzxCLz7gzyw&oe=68C10B52',
                'engagement': '8 likes, 3 comments'
            },
            {
                'url': 'https://www.facebook.com/photo/?fbid=1263404155797914&set=gm.31190122773964274&idorvanity=5440421919361046',
                'text': '1.2ct Radiant G-VS1 Diamond for $3,850 on DiamondHedge.com for a limited time! #radiantcut #radiant #EngagementRing #diamonds #DiamondHedge',
                'author': 'Mike Chen',
                'post_type': 'iso',
                'image': 'https://scontent-lax3-1.xx.fbcdn.net/v/t39.30808-6/541473086_1263404159131247_5389837839206051746_n.jpg?_nc_cat=102&ccb=1-7&_nc_sid=aa7b47&_nc_ohc=19e84FDttJwQ7kNvwGvxuga&_nc_oc=AdmHCGmlEMM-H-Sp0qmXFKKI6nAj5v5P7OmFhVP46FD15VR2tYcGkOQhkQsgCMM45Bk&_nc_zt=23&_nc_ht=scontent-lax3-1.xx&_nc_gid=YvmarSXc8e0JKQsOb7oDdg&oh=00_AfaBlaB3oKtwp6w6eetUjS9_4SBluu7dbh3OU6nQdkmfSA&oe=68C11565',
                'engagement': '12 likes, 5 comments'
            },
            {
                'url': 'https://www.facebook.com/photo/?fbid=122143481480825821&set=gm.31193893066920578&idorvanity=5440421919361046',
                'text': 'Vacancy: Gemmological Assistant | Van Deijl Jewellers – Tyger Valley, Bellville\\n\\nVan Deijl Jewellers is seeking a Gemmologist with a recognised gemmological qualification, or a current gemmology student, who has a keen eye for detail, a passion for gemstones and strong ethical values.\\n\\nFor more information or to apply, please e-mail: info@vandeijl.co.za',
                'author': 'Jennifer Martinez',
                'post_type': 'general',
                'image': 'https://scontent-lax3-2.xx.fbcdn.net/v/t39.30808-6/540660448_122143481426825821_7896264772864429342_n.jpg?_nc_cat=103&ccb=1-7&_nc_sid=aa7b47&_nc_ohc=nrPwMUkFlnIQ7kNvwGCqFtX&_nc_oc=AdlJ_AqbzXUwIyZ9PnpRpjxo1Hgov0gxnypOK9ePK6jx-I67OKuAN4gAqYSb0nBaWC8&_nc_zt=23&_nc_ht=scontent-lax3-2.xx&_nc_gid=vgQjDJi_VuGyEEdb8AJS3w&oh=00_AfZJMkzRbp2vHdi36UDz8fhsdo9rq_mYrJLhRIV8czNUUw&oe=68C11ADF',
                'engagement': '6 likes, 2 comments'
            },
            {
                'url': 'https://www.facebook.com/photo?fbid=10161828733142335&set=pcb.31248814628095088',
                'text': 'Need urgent help with stone replacement in this vintage ring. Client needs it ready for anniversary.',
                'author': 'David Wilson',
                'post_type': 'service',
                'image': 'https://images.unsplash.com/photo-1544378241-76d0ce6ed1cb?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
                'engagement': '4 likes, 1 comment'
            }
        ]
    
    def clear_pending_comments(self):
        """Clear all pending comments from the queue"""
        try:
            import sqlite3
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            
            # Delete only pending comments to preserve approved/rejected history
            cursor.execute("DELETE FROM comment_queue WHERE status = 'pending'")
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleared {deleted_count} pending comments from queue")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing pending comments: {e}")
            return False
    
    def get_or_create_image_pack(self):
        """Get existing image pack or create default one"""
        try:
            image_packs = db.get_image_packs()
            if image_packs:
                logger.info(f"Found {len(image_packs)} image packs")
                return image_packs[0]['id']
            else:
                # Create default image pack
                pack_id = db.create_image_pack("Demo Image Pack", "GENERIC")
                logger.info(f"Created demo image pack: {pack_id}")
                return pack_id
        except Exception as e:
            logger.error(f"Error with image packs: {e}")
            return None
    
    def add_demo_posts(self):
        """Add demo posts to the comment queue"""
        try:
            logger.info("Adding demo posts to comment queue...")
            
            # Get image pack ID
            image_pack_id = self.get_or_create_image_pack()
            
            success_count = 0
            for i, post in enumerate(self.demo_posts, 1):
                try:
                    logger.info(f"Processing post {i}/4: {post['author']} ({post['post_type']})")
                    
                    # Generate appropriate comment
                    comment = self.comment_generator.generate_comment(
                        post['post_type'], 
                        post['text'], 
                        post['author']
                    )
                    
                    if not comment:
                        # Fallback comment
                        first_name = post['author'].split()[0]
                        comment = f"Hi {first_name}! We're Bravo Creations - full-service jewelry manufacturing. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene."
                        logger.warning(f"Used fallback comment for {post['author']}")
                    
                    # Add to comment queue
                    queue_id = db.add_to_comment_queue(
                        post_url=post['url'],
                        post_text=post['text'],
                        comment_text=comment,
                        post_type=post['post_type'],
                        post_screenshot=None,
                        post_images=json.dumps([post['image']]),
                        post_author=post['author'],
                        post_engagement=post['engagement'],
                        image_pack_id=image_pack_id
                    )
                    
                    if queue_id:
                        logger.info(f"Added {post['author']} to queue (ID: {queue_id})")
                        success_count += 1
                    else:
                        logger.error(f"Failed to add {post['author']} to queue")
                        
                except Exception as e:
                    logger.error(f"Error processing {post['author']}: {e}")
                    continue
            
            logger.info(f"Successfully added {success_count}/{len(self.demo_posts)} demo posts")
            return success_count
            
        except Exception as e:
            logger.error(f"Error adding demo posts: {e}")
            return 0
    
    def show_queue_summary(self):
        """Show summary of the populated queue"""
        try:
            pending_comments = db.get_pending_comments()
            
            print("\\n" + "="*60)
            print("📊 DEMO QUEUE SUMMARY")
            print("="*60)
            print(f"📝 Total pending comments: {len(pending_comments)}")
            
            if pending_comments:
                print("\\n📋 Comments ready for demo:")
                for comment in pending_comments:
                    post_type = comment.get('post_type', 'unknown')
                    author = comment.get('post_author', 'Unknown')
                    comment_text = comment.get('comment_text', '')
                    print(f"  • {author} ({post_type}): {comment_text[:60]}...")
                
                print("\\n🚀 Demo Workflow:")
                print("  1. Open your web interface")
                print("  2. Navigate to comment approval section")
                print("  3. View pending comments with Facebook post images")
                print("  4. Edit comments and attach company images")
                print("  5. Approve and demonstrate posting workflow")
            else:
                print("❌ No pending comments found")
            
            print("="*60)
            
        except Exception as e:
            logger.error(f"Error showing queue summary: {e}")
    
    def repopulate_demo_queue(self):
        """Main function to repopulate the demo queue"""
        try:
            logger.info("Starting demo queue repopulation...")
            print("Repopulating Comment Approval Queue for Demo")
            print("="*50)
            
            # Step 1: Clear existing pending comments
            print("Clearing existing pending comments...")
            if not self.clear_pending_comments():
                print("❌ Failed to clear existing comments")
                return False
            
            # Step 2: Add demo posts
            print("Adding demo posts with real Facebook content...")
            added_count = self.add_demo_posts()
            
            if added_count == 0:
                print("❌ Failed to add demo posts")
                return False
            
            # Step 3: Show summary
            self.show_queue_summary()
            
            print(f"\\nSUCCESS: Demo queue repopulated with {added_count} realistic posts!")
            print("Your comment approval queue is ready for demonstration.")
            
            return True
            
        except Exception as e:
            logger.error(f"Error repopulating demo queue: {e}")
            print(f"❌ Error: {e}")
            return False

def main():
    """Main function"""
    print("Facebook Comment Bot - Demo Queue Repopulation")
    print("="*55)
    
    try:
        manager = DemoQueueManager()
        success = manager.repopulate_demo_queue()
        
        if success:
            print("\\nDemo environment ready!")
            return True
        else:
            print("\\nFailed to repopulate demo queue")
            return False
            
    except KeyboardInterrupt:
        print("\\nOperation cancelled by user")
        return False
    except Exception as e:
        print(f"\\nUnexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        main()
    finally:
        # Restore original working directory
        os.chdir(original_cwd)