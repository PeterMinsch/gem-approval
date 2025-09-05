#!/usr/bin/env python3
"""
Quick Demo Queue Reset Script
Repopulates the comment approval queue with real Facebook posts for demo.
"""

import sys
import os
import json

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot'))

try:
    from database import db
    from comment_generator import CommentGenerator  
    from bravo_config import CONFIG as config
except ImportError as e:
    print(f"Error importing bot modules: {e}")
    sys.exit(1)

def repopulate_queue():
    """Repopulate demo queue with real Facebook posts"""
    
    # Real Facebook posts with actual images and content
    demo_posts = [
        {
            'url': 'https://www.facebook.com/photo/?fbid=24358671130457313&set=pcb.30915708561405698',
            'text': 'Hello! I have a costumer that just got her ring a week ago, in my opinion the person that made it put the marquee diamond on an oval/round crown with only four prongs, the marquee already chip on one tip and stone fell out days after she got it, she absolutely loves the design on the crown, I need advice on how I can secure the stone with preferably keeping the design, Is it possible or should we go for a new crown? Could I put bigger prongs and add more? Would that make it stronger? Please help',
            'author': 'Sarah Johnson',
            'post_type': 'service',
            'image': 'https://scontent-lax3-1.xx.fbcdn.net/v/t39.30808-6/531584279_24358672240457202_1540481224194654532_n.jpg?stp=cp6_dst-jpg_tt6&_nc_cat=105&ccb=1-7&_nc_sid=aa7b47&_nc_ohc=nU22EmxONkUQ7kNvwHu2D3n&_nc_oc=AdmbwjaPsxP90CUIUoJmEmS4RBDClLJyAMAmdhuuzIg6biEPw-G52S2U0Q67LuGqr9o&_nc_zt=23&_nc_ht=scontent-lax3-1.xx&_nc_gid=ON82h3ZyoLT6GuahYE2byg&oh=00_AfYTOh2mlw3vUGlJ_NjRDQngZ14Gn5Ced4-NzxCLz7gzyw&oe=68C10B52'
        },
        {
            'url': 'https://www.facebook.com/photo/?fbid=1263404155797914&set=gm.31190122773964274&idorvanity=5440421919361046',
            'text': '1.2ct Radiant G-VS1 Diamond for $3,850 on DiamondHedge.com for a limited time! #radiantcut #radiant #EngagementRing #diamonds #DiamondHedge',
            'author': 'Mike Chen',
            'post_type': 'iso',
            'image': 'https://scontent-lax3-1.xx.fbcdn.net/v/t39.30808-6/541473086_1263404159131247_5389837839206051746_n.jpg?_nc_cat=102&ccb=1-7&_nc_sid=aa7b47&_nc_ohc=19e84FDttJwQ7kNvwGvxuga&_nc_oc=AdmHCGmlEMM-H-Sp0qmXFKKI6nAj5v5P7OmFhVP46FD15VR2tYcGkOQhkQsgCMM45Bk&_nc_zt=23&_nc_ht=scontent-lax3-1.xx&_nc_gid=YvmarSXc8e0JKQsOb7oDdg&oh=00_AfaBlaB3oKtwp6w6eetUjS9_4SBluu7dbh3OU6nQdkmfSA&oe=68C11565'
        },
        {
            'url': 'https://www.facebook.com/photo/?fbid=122143481480825821&set=gm.31193893066920578&idorvanity=5440421919361046',
            'text': 'Vacancy: Gemmological Assistant | Van Deijl Jewellers - Tyger Valley, Bellville. Van Deijl Jewellers is seeking a Gemmologist with a recognised gemmological qualification, or a current gemmology student, who has a keen eye for detail, a passion for gemstones and strong ethical values. For more information or to apply, please e-mail: info@vandeijl.co.za',
            'author': 'Jennifer Martinez',
            'post_type': 'general',
            'image': 'https://scontent-lax3-2.xx.fbcdn.net/v/t39.30808-6/540660448_122143481426825821_7896264772864429342_n.jpg?_nc_cat=103&ccb=1-7&_nc_sid=aa7b47&_nc_ohc=nrPwMUkFlnIQ7kNvwGCqFtX&_nc_oc=AdlJ_AqbzXUwIyZ9PnpRpjxo1Hgov0gxnypOK9ePK6jx-I67OKuAN4gAqYSb0nBaWC8&_nc_zt=23&_nc_ht=scontent-lax3-2.xx&_nc_gid=vgQjDJi_VuGyEEdb8AJS3w&oh=00_AfZJMkzRbp2vHdi36UDz8fhsdo9rq_mYrJLhRIV8czNUUw&oe=68C11ADF'
        },
        {
            'url': 'https://www.facebook.com/photo?fbid=10161828733142335&set=pcb.31248814628095088',
            'text': 'Need urgent help with stone replacement in this vintage ring. Client needs it ready for anniversary.',
            'author': 'David Wilson',
            'post_type': 'service',
            'image': 'https://images.unsplash.com/photo-1544378241-76d0ce6ed1cb?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
        }
    ]
    
    print("DEMO QUEUE REPOPULATION")
    print("="*40)
    
    try:
        # Clear pending comments
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comment_queue WHERE status = 'pending'")
        cleared_count = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Cleared {cleared_count} pending comments")
        
        # Get image pack
        image_packs = db.get_image_packs()
        pack_id = image_packs[0]['id'] if image_packs else None
        
        # Initialize comment generator
        generator = CommentGenerator(config, database=db)
        
        # Add demo posts
        success_count = 0
        for post in demo_posts:
            try:
                # Generate comment
                comment = generator.generate_comment(post['post_type'], post['text'], post['author'])
                if not comment:
                    first_name = post['author'].split()[0]
                    comment = f"Hi {first_name}! We're Bravo Creations - full-service jewelry manufacturing. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene."
                
                # Add to queue
                queue_id = db.add_to_comment_queue(
                    post_url=post['url'],
                    post_text=post['text'],
                    comment_text=comment,
                    post_type=post['post_type'],
                    post_screenshot=None,
                    post_images=json.dumps([post['image']]),
                    post_author=post['author'],
                    post_engagement='5 likes, 2 comments',
                    image_pack_id=pack_id
                )
                
                if queue_id:
                    print(f"Added {post['author']} ({post['post_type']}) - ID: {queue_id}")
                    success_count += 1
                else:
                    print(f"Failed to add {post['author']}")
                    
            except Exception as e:
                print(f"Error adding {post['author']}: {e}")
        
        # Show final status
        pending = db.get_pending_comments()
        print(f"\\nSUCCESS: {success_count} demo comments added")
        print(f"Total pending comments: {len(pending)}")
        print("\\nDemo queue is ready!")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    repopulate_queue()