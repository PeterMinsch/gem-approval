import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import json

logger = logging.getLogger(__name__)

class BotDatabase:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Enhanced posts table for CRM
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    fb_post_id TEXT UNIQUE NOT NULL,
                    group_id TEXT,
                    post_url TEXT,
                    author_id TEXT,
                    author_name TEXT,
                    content_text TEXT,
                    image_urls TEXT, -- JSON array as text
                    detected_intent TEXT CHECK(detected_intent IN ('SERVICE', 'ISO_BUY', 'IGNORE')),
                    matched_keywords TEXT, -- JSON array as text
                    blocked_reasons TEXT, -- JSON array as text
                    brand_hits TEXT, -- JSON array as text
                    status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'QUEUED', 'POSTED', 'SKIPPED', 'PM_SENT')),
                    priority INTEGER DEFAULT 0,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_by TEXT, -- user id (nullable)
                    notes_internal TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Enhanced comments table for CRM
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    comment_body TEXT NOT NULL,
                    comment_images TEXT, -- JSON array of image URLs
                    status TEXT DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'QUEUED', 'POSTED', 'FAILED', 'CANCELLED')),
                    fb_comment_id TEXT, -- nullable
                    submitted_by_account_id TEXT, -- fk to fb_accounts (nullable)
                    submitted_at TIMESTAMP, -- nullable
                    error_message TEXT, -- nullable
                    template_id TEXT, -- fk to templates (nullable)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (id),
                    FOREIGN KEY (submitted_by_account_id) REFERENCES fb_accounts (id)
                )
            """)
            
            # Templates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT CHECK(category IN ('GENERIC', 'ISO_PIVOT', 'CAD', 'CASTING', 'SETTING', 'ENGRAVING', 'ENAMEL')),
                    body TEXT NOT NULL,
                    image_pack_id TEXT, -- fk to image_packs (nullable)
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (image_pack_id) REFERENCES image_packs (id)
                )
            """)
            
            # Image packs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_packs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    images TEXT NOT NULL, -- JSON array as text
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Facebook accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fb_accounts (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    profile_url TEXT,
                    status TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'COOL_DOWN', 'DISABLED')),
                    daily_quota INTEGER DEFAULT 8,
                    last_used_at TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Settings table (singleton)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id TEXT PRIMARY KEY DEFAULT 'singleton',
                    register_url TEXT DEFAULT 'https://welcome.bravocreations.com',
                    phone TEXT DEFAULT '(760) 431-9977',
                    ask_for TEXT DEFAULT 'Eugene',
                    openai_api_key TEXT, -- encrypted
                    brand_blacklist TEXT, -- JSON array as text
                    allowed_brand_modifiers TEXT, -- JSON array as text
                    negative_keywords TEXT, -- JSON array as text
                    service_keywords TEXT, -- JSON array as text
                    iso_keywords TEXT, -- JSON array as text
                    scan_refresh_minutes INTEGER DEFAULT 3,
                    max_comments_per_account_per_day INTEGER DEFAULT 8,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Activity log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id TEXT PRIMARY KEY,
                    post_id TEXT, -- nullable
                    comment_id TEXT, -- nullable
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    meta TEXT, -- JSON as text
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (id),
                    FOREIGN KEY (comment_id) REFERENCES comments (id)
                )
            """)
            
            # Legacy tables (keep for backward compatibility)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_url TEXT UNIQUE NOT NULL,
                    post_text TEXT,
                    post_type TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'processed',
                    error_message TEXT,
                    comment_generated BOOLEAN DEFAULT FALSE,
                    comment_text TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comment_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_url TEXT NOT NULL,
                    post_text TEXT NOT NULL,
                    comment_text TEXT NOT NULL,
                    post_type TEXT NOT NULL,
                    post_screenshot TEXT,
                    post_images TEXT,
                    post_author TEXT,
                    post_engagement TEXT,
                    image_pack_id TEXT,
                    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    approved_at TIMESTAMP,
                    approved_by TEXT,
                    posted_at TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (image_pack_id) REFERENCES image_packs (id)
                )
            """)
            
            # Add image_pack_id column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE comment_queue ADD COLUMN image_pack_id TEXT")
                logger.info("Added image_pack_id column to comment_queue table")
            except Exception as e:
                # Column probably already exists
                if "duplicate column name" in str(e).lower():
                    logger.debug("image_pack_id column already exists in comment_queue table")
                else:
                    logger.debug(f"Migration note: {e}")
            
            # Add detected_categories column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE comment_queue ADD COLUMN detected_categories TEXT DEFAULT '[]'")
                logger.info("Added detected_categories column to comment_queue table")
            except Exception as e:
                # Column probably already exists
                if "duplicate column name" in str(e).lower():
                    logger.debug("detected_categories column already exists in comment_queue table")
                else:
                    logger.debug(f"Migration note: {e}")
            
            # Add post_author_url column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE comment_queue ADD COLUMN post_author_url TEXT")
                logger.info("Added post_author_url column to comment_queue table")
            except Exception as e:
                # Column probably already exists
                if "duplicate column name" in str(e).lower():
                    logger.debug("post_author_url column already exists in comment_queue table")
                else:
                    logger.debug(f"Migration note: {e}")
            
            # Bot statistics and sessions tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    posts_processed INTEGER DEFAULT 0,
                    comments_generated INTEGER DEFAULT 0,
                    comments_posted INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    scan_duration_seconds INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    status TEXT DEFAULT 'running',
                    posts_processed INTEGER DEFAULT 0,
                    comments_generated INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    session_duration_seconds INTEGER
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_fb_id ON posts(fb_post_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_intent ON posts(detected_intent)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_status ON comments(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_accounts_status ON fb_accounts(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_post ON activity_log(post_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_created ON activity_log(created_at)")
            
            # Legacy indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_posts_url ON processed_posts(post_url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_posts_date ON processed_posts(processed_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comment_queue_status ON comment_queue(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comment_queue_date ON comment_queue(queued_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_stats_date ON bot_stats(date)")
            
            # Seed default data
            self._seed_default_data(cursor)
            
            conn.commit()
    
    def _seed_default_data(self, cursor):
        """Seed the database with default templates, image packs, and settings"""
        import uuid
        
        # Check if we already have data
        cursor.execute("SELECT COUNT(*) FROM templates")
        if cursor.fetchone()[0] > 0:
            return
        
        # Seed default templates
        default_templates = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Generic',
                'category': 'GENERIC',
                'body': "Hi! We're Bravo Creations — full-service B2B for jewelers: CAD, casting, stone setting, engraving, enamel, finishing. Fast turnaround, meticulous QC. {{phone}} • {{register_url}} — ask for {{ask_for}}.",
                'is_default': True
            },
            # DM Templates for Smart Launcher
            {
                'id': str(uuid.uuid4()),
                'name': 'DM Service',
                'category': 'DM_SERVICE',
                'body': "Hi {{author_name}}! Saw your jewelry work - impressive craftsmanship! We're Bravo Creations, full-service B2B manufacturing specializing in CAD, casting, and setting. Would love to chat about partnership opportunities. {{register_url}} • {{phone}} — ask for {{ask_for}}",
                'is_default': True
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'DM ISO Pivot',
                'category': 'DM_ISO',
                'body': "Hi {{author_name}}! Great style in your post! We don't stock pieces, but this is exactly what we manufacture daily with CAD + casting + setting. Quick turnaround, quality focus. {{register_url}} • {{phone}} — ask for {{ask_for}}",
                'is_default': True
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'DM General',
                'category': 'DM_GENERAL',
                'body': "Hi {{author_name}}! Noticed your jewelry post - beautiful work! We're Bravo Creations, full-service B2B manufacturing (CAD, casting, setting, engraving). Always looking to connect with quality jewelers. {{register_url}} • {{phone}} — ask for {{ask_for}}",
                'is_default': True
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'ISO Pivot',
                'category': 'ISO_PIVOT',
                'body': "✨ Great style! We don't stock it, but this is exactly what we make daily with CAD + casting + setting. Upload in minutes: {{register_url}} • {{phone}} — ask for {{ask_for}}.",
                'is_default': False
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'CAD',
                'category': 'CAD',
                'body': "Need CAD design? We handle complex jewelry modeling with precision. Fast turnaround, meticulous attention to detail. {{phone}} • {{register_url}} — ask for {{ask_for}}.",
                'is_default': False
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Casting',
                'category': 'CASTING',
                'body': "Professional casting services with clean results and tight deadlines. We handle everything from CAD to final finish. {{phone}} • {{register_url}} — ask for {{ask_for}}.",
                'is_default': False
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Setting',
                'category': 'SETTING',
                'body': "Microscope-grade stone setting with precision and care. From simple prongs to complex pavé work. {{phone}} • {{register_url}} — ask for {{ask_for}}.",
                'is_default': False
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Engraving',
                'category': 'ENGRAVING',
                'body': "Laser and hand engraving services for personalization and detail work. Clean, precise results every time. {{phone}} • {{register_url}} — ask for {{ask_for}}.",
                'is_default': False
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Enamel',
                'category': 'ENAMEL',
                'body': "Color fill and enamel services to bring your designs to life. Vibrant, durable finishes. {{phone}} • {{register_url}} — ask for {{ask_for}}.",
                'is_default': False
            }
        ]
        
        for template in default_templates:
            cursor.execute("""
                INSERT INTO templates (id, name, category, body, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (template['id'], template['name'], template['category'], template['body'], template['is_default']))
        
        # Seed default image pack
        default_image_pack_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO image_packs (id, name, images, is_default)
            VALUES (?, ?, ?, ?)
        """, (default_image_pack_id, 'Generic Card', json.dumps(['https://your-cdn/bravo-comment-card.png']), True))
        
        # Seed default settings
        cursor.execute("""
            INSERT INTO settings (id, register_url, phone, ask_for, brand_blacklist, allowed_brand_modifiers, negative_keywords, service_keywords, iso_keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'singleton',
            'https://welcome.bravocreations.com',
            '(760) 431-9977',
            'Eugene',
            json.dumps(['cartier', 'tiffany', 'kay', 'pompeii', 'van cleef', 'bulgari', 'david yurman', 'rolex', 'gucci', 'chanel', 'hermes', 'pandora', 'mikimoto', 'graff', 'harry winston', 'messika']),
            json.dumps(['similar to', 'in the style of', 'inspired by', 'style like', 'similar pls']),
            json.dumps(['memo', 'consignment', 'for sale', 'wts', 'fs', 'sold', 'giveaway', 'admin', 'rule', 'meme', 'joke', 'loose stone', 'loose stones', 'findings', 'gallery wire', 'strip stock', 'equipment', 'tool', 'supplies']),
            json.dumps(['casting', 'casting house', 'service bureau', 'service house', 'manufacturing partner', 'cad', '3d design', 'stl', '3dm', 'matrix', 'matrixgold', 'rhino', 'stone setting', 'prong', 'pavé', 'pave', 'channel', 'flush', 'gypsy', 'bezel', 'micro setting', 'engraving', 'laser engraving', 'hand engraving', 'deep engraving', 'enamel', 'color fill', 'rhodium', 'plating', 'vermeil', 'laser weld', 'solder', 'retip', 're-tip', 'repair', 'ring sizing', 'finish', 'polish', 'texture', 'rush', 'overnight', 'fast turnaround', 'custom', 'custom ring', 'custom jewelry', 'design', 'ring design', 'jewelry design', 'help', 'need help', 'looking for', 'searching for', 'find', 'looking to find', 'make', 'create', 'build', 'craft', 'fabricate', 'manufacture', 'wedding band', 'wedding ring', 'engagement ring', 'anniversary ring', 'band', 'ring', 'jewelry', 'necklace', 'bracelet', 'earrings', 'pendant', 'gold', 'silver', 'platinum', 'white gold', 'yellow gold', 'rose gold', 'diamond', 'gemstone', 'stone', 'precious metal', 'metal']),
            json.dumps(['iso', 'in stock', 'ready to ship', 'available now', 'who makes this', 'who manufactures this', 'supplier', 'similar to', 'in the style of', 'inspired by', 'like this style', 'similar pls', 'looking for', 'searching for', 'need', 'want', 'find', 'available', 'who can', 'who makes', 'who manufactures', 'who does', 'who offers', 'custom', 'custom ring', 'custom jewelry', 'design', 'ring design', 'jewelry design', 'help', 'need help', 'looking for help', 'advice', 'recommendation', 'make', 'create', 'build', 'craft', 'fabricate', 'manufacture', 'wedding band', 'wedding ring', 'engagement ring', 'anniversary ring', 'band', 'ring', 'jewelry', 'necklace', 'bracelet', 'earrings', 'pendant'])
        ))
        
        # Seed default Facebook account
        cursor.execute("""
            INSERT INTO fb_accounts (id, display_name, profile_url, status, daily_quota)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), 'Default Account', 'https://facebook.com', 'ACTIVE', 8))
    
    def is_post_processed(self, post_url: str) -> bool:
        """Check if a post has already been processed. Always use normalized URL."""
        # For photo URLs, preserve fbid and set parameters but remove tracking
        if '/photo/' in post_url and 'fbid=' in post_url:
            import re
            # Remove tracking parameters but keep fbid and set
            norm_url = re.sub(r'&(__cft__|__tn__|notif_id|notif_t|ref)=[^&]*', '', post_url)
            norm_url = re.sub(r'&context=[^&]*', '', norm_url)
        else:
            # For non-photo URLs, remove all query parameters
            norm_url = post_url.split('?')[0].split('#')[0] if post_url else post_url
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM processed_posts WHERE post_url = ?", (norm_url,))
            return cursor.fetchone() is not None
    
    def mark_post_processed(self, post_url: str, post_text: str = "", post_type: str = "", 
                           comment_generated: bool = False, comment_text: str = "", 
                           error_message: str = "") -> bool:
        """Mark a post as processed"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO processed_posts 
                    (post_url, post_text, post_type, comment_generated, comment_text, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (post_url, post_text, post_type, comment_generated, comment_text, error_message))
                conn.commit()
                logger.info(f"Marked post as processed: {post_url}")
                return True
        except Exception as e:
            logger.error(f"Failed to mark post as processed: {e}")
            return False
    
    def add_to_comment_queue(self, post_url: str, post_text: str, comment_text: str, 
                            post_type: str, post_screenshot: str = None, post_images: str = None,
                            post_author: str = None, post_engagement: str = None,
                            image_pack_id: str = None, detected_categories: List[str] = None,
                            post_author_url: str = None) -> Optional[int]:
        """Add a comment to the approval queue with enhanced post data"""
        try:
            # DEBUGGING: Log post_author_url input
            logger.debug(f"DB_STORAGE: Received post_author_url: '{post_author_url}' (length: {len(post_author_url) if post_author_url else 0})")
            
            # Convert categories to JSON string
            categories_json = json.dumps(detected_categories or [])
            
            # For photo URLs, preserve parameters; for others, normalize
            if '/photo/' in post_url and 'fbid=' in post_url:
                # Photo URLs need their parameters to work properly
                norm_url = post_url
                logger.info(f"Preserving photo URL with parameters: {norm_url}")
            else:
                # Normalize URL by removing query parameters and fragments
                norm_url = post_url.split('?')[0].split('#')[0] if post_url else post_url
                logger.info(f"Normalized non-photo URL: {norm_url}")
            
            # DEBUGGING: Log what we're about to store
            logger.debug(f"DB_STORAGE: About to store post_author_url: '{post_author_url}'")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO comment_queue (post_url, post_text, comment_text, post_type, 
                                            post_screenshot, post_images, post_author, post_engagement, 
                                            image_pack_id, detected_categories, post_author_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (norm_url, post_text, comment_text, post_type, post_screenshot, 
                     post_images, post_author, post_engagement, image_pack_id, categories_json, post_author_url))
                conn.commit()
                queue_id = cursor.lastrowid
                logger.info(f"Added comment to queue (ID: {queue_id}): {norm_url}")
                
                # DEBUGGING: Verify what was actually stored
                cursor.execute("SELECT post_author_url FROM comment_queue WHERE id = ?", (queue_id,))
                stored_url = cursor.fetchone()[0]
                logger.debug(f"DB_STORAGE: Verified stored post_author_url: '{stored_url}' (length: {len(stored_url) if stored_url else 0})")
                
                return queue_id
        except Exception as e:
            logger.error(f"Failed to add comment to queue: {e}")
            return None
    
    def get_pending_comments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending comments from the queue"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM comment_queue 
                WHERE status = 'pending' 
                ORDER BY queued_at DESC 
                LIMIT ?
            """, (limit,))
            
            comments = []
            for row in cursor.fetchall():
                comments.append(dict(row))
            return comments
    
    def get_comment_by_id(self, comment_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific comment by ID regardless of status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM comment_queue 
                WHERE id = ?
            """, (comment_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_comment_history(self) -> List[Dict[str, Any]]:
        """Get comment history for display"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cq.*, 
                       CASE 
                           WHEN cq.status = 'posted' THEN '✅ Posted'
                           WHEN cq.status = 'approved' THEN '🔄 Approved'
                           WHEN cq.status = 'rejected' THEN '❌ Rejected'
                           ELSE '⏳ Pending'
                       END as status_display
                FROM comment_queue cq
                ORDER BY cq.queued_at DESC
                LIMIT 100
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results

    # New CRM Methods
    
    def create_post(self, post_data: Dict[str, Any]) -> str:
        """Create a new post in the CRM"""
        import uuid
        post_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (
                    id, fb_post_id, group_id, post_url, author_id, author_name,
                    content_text, image_urls, detected_intent, matched_keywords,
                    blocked_reasons, brand_hits, status, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_id,
                post_data.get('fb_post_id'),
                post_data.get('group_id'),
                post_data.get('post_url'),
                post_data.get('author_id'),
                post_data.get('author_name'),
                post_data.get('content_text'),
                json.dumps(post_data.get('image_urls', [])),
                post_data.get('detected_intent', 'IGNORE'),
                json.dumps(post_data.get('matched_keywords', [])),
                json.dumps(post_data.get('blocked_reasons', [])),
                json.dumps(post_data.get('brand_hits', [])),
                'PENDING',
                post_data.get('priority', 0)
            ))
            
            # Log the activity
            self._log_activity('INGESTED', 'bot', post_id=post_id, meta=post_data)
            
            return post_id
    
    def create_comment_draft(self, post_id: str, template_id: str = None) -> str:
        """Create a comment draft for a post"""
        import uuid
        comment_id = str(uuid.uuid4())
        
        # Get template and settings for comment generation
        template = self.get_template(template_id) if template_id else self.get_default_template()
        settings = self.get_settings()
        
        # Generate comment body with template variables
        comment_body = self._process_template(template['body'], settings)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO comments (
                    id, post_id, comment_body, template_id, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (comment_id, post_id, comment_body, template_id, 'DRAFT'))
            
            # Log the activity
            self._log_activity('DRAFT_CREATED', 'bot', post_id=post_id, comment_id=comment_id)
            
            return comment_id
    
    def get_posts_by_status(self, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get posts filtered by status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT p.*, c.comment_body, c.status as comment_status, c.id as comment_id
                    FROM posts p
                    LEFT JOIN comments c ON p.id = c.post_id
                    WHERE p.status = ?
                    ORDER BY p.created_at DESC
                    LIMIT ?
                """, (status, limit))
            else:
                cursor.execute("""
                    SELECT p.*, c.comment_body, c.status as comment_status, c.id as comment_id
                    FROM posts p
                    LEFT JOIN comments c ON p.id = c.post_id
                    ORDER BY p.created_at DESC
                    LIMIT ?
                """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                post_data = dict(row)
                # Parse JSON fields
                for field in ['image_urls', 'matched_keywords', 'blocked_reasons', 'brand_hits']:
                    if post_data.get(field):
                        try:
                            post_data[field] = json.loads(post_data[field])
                        except:
                            post_data[field] = []
                results.append(post_data)
            
            return results
    
    def update_post_status(self, post_id: str, status: str, processed_by: str = None) -> bool:
        """Update post status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE posts 
                SET status = ?, processed_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, processed_by, post_id))
            
            # Log the activity
            self._log_activity(f'STATUS_CHANGED_TO_{status}', 'system', post_id=post_id)
            
            return cursor.rowcount > 0
    
    def update_comment_status(self, comment_id: str, status: str, meta: Dict[str, Any] = None) -> bool:
        """Update comment status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE comments 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, comment_id))
            
            # Log the activity
            self._log_activity(f'COMMENT_{status}', 'system', comment_id=comment_id, meta=meta)
            
            return cursor.rowcount > 0
    
    def update_comment_body(self, comment_id: str, comment_body: str, comment_images: List[str] = None) -> bool:
        """Update comment body text and images"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if comment_images is not None:
                cursor.execute("""
                    UPDATE comments 
                    SET comment_body = ?, comment_images = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (comment_body, json.dumps(comment_images), comment_id))
            else:
                cursor.execute("""
                    UPDATE comments 
                    SET comment_body = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (comment_body, comment_id))
            
            # Log the activity
            meta = {'new_body': comment_body}
            if comment_images is not None:
                meta['new_images'] = comment_images
            self._log_activity('COMMENT_EDITED', 'user', comment_id=comment_id, meta=meta)
            
            return cursor.rowcount > 0

    def get_templates(self, category: str = None) -> List[Dict[str, Any]]:
        """Get templates, optionally filtered by category"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute("""
                    SELECT * FROM templates WHERE category = ? ORDER BY name
                """, (category,))
            else:
                cursor.execute("SELECT * FROM templates ORDER BY category, name")
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get a specific template by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_default_template(self) -> Dict[str, Any]:
        """Get the default template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates WHERE is_default = TRUE LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_template(self, name: str, category: str, body: str, image_pack_id: str = None, is_default: bool = False) -> str:
        """Create a new template"""
        import uuid
        from datetime import datetime
        
        template_id = str(uuid.uuid4())
        
        # Validate category
        valid_categories = ['GENERIC', 'ISO_PIVOT', 'CAD', 'CASTING', 'SETTING', 'ENGRAVING', 'ENAMEL', 'DM_SERVICE', 'DM_ISO', 'DM_GENERAL']
        if category not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if template name already exists
            cursor.execute("SELECT COUNT(*) FROM templates WHERE name = ?", (name,))
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"Template with name '{name}' already exists")
            
            # If this is set as default, unset other defaults in same category
            if is_default:
                cursor.execute(
                    "UPDATE templates SET is_default = FALSE WHERE category = ? AND is_default = TRUE",
                    (category,)
                )
            
            cursor.execute("""
                INSERT INTO templates (id, name, category, body, image_pack_id, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (template_id, name, category, body, image_pack_id, is_default, datetime.now(), datetime.now()))
            
            conn.commit()
            return template_id
    
    def update_template(self, template_id: str, name: str = None, category: str = None, 
                       body: str = None, image_pack_id: str = None, is_default: bool = None) -> bool:
        """Update an existing template"""
        from datetime import datetime
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if template exists
            cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            existing = cursor.fetchone()
            if not existing:
                return False
            
            # Build update query dynamically
            updates = []
            params = []
            
            if name is not None:
                # Check if new name conflicts with existing templates (excluding current)
                cursor.execute("SELECT COUNT(*) FROM templates WHERE name = ? AND id != ?", (name, template_id))
                if cursor.fetchone()[0] > 0:
                    raise ValueError(f"Template with name '{name}' already exists")
                updates.append("name = ?")
                params.append(name)
            
            if category is not None:
                valid_categories = ['GENERIC', 'ISO_PIVOT', 'CAD', 'CASTING', 'SETTING', 'ENGRAVING', 'ENAMEL', 'DM_SERVICE', 'DM_ISO', 'DM_GENERAL']
                if category not in valid_categories:
                    raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
                updates.append("category = ?")
                params.append(category)
                
                # If changing category and this was default, unset default
                if existing['is_default'] and category != existing['category']:
                    updates.append("is_default = ?")
                    params.append(False)
            
            if body is not None:
                updates.append("body = ?")
                params.append(body)
            
            if image_pack_id is not None:
                updates.append("image_pack_id = ?")
                params.append(image_pack_id)
            
            if is_default is not None:
                # If setting as default, unset other defaults in same category
                if is_default:
                    current_category = category if category is not None else existing['category']
                    cursor.execute(
                        "UPDATE templates SET is_default = FALSE WHERE category = ? AND is_default = TRUE AND id != ?",
                        (current_category, template_id)
                    )
                updates.append("is_default = ?")
                params.append(is_default)
            
            if not updates:
                return True  # No changes needed
            
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(template_id)
            
            query = f"UPDATE templates SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if template exists
            cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            template = cursor.fetchone()
            if not template:
                return False
            
            # Check if template is being used by any comments
            cursor.execute("SELECT COUNT(*) FROM comments WHERE template_id = ?", (template_id,))
            usage_count = cursor.fetchone()[0]
            
            if usage_count > 0:
                raise ValueError(f"Cannot delete template: it is used by {usage_count} comment(s)")
            
            cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            conn.commit()
            
            return cursor.rowcount > 0

    def migrate_config_templates(self, config_templates: Dict[str, List[str]]) -> int:
        """Migrate config-based templates to database if they don't already exist"""
        import uuid
        from datetime import datetime
        
        migrated_count = 0
        
        # Mapping of config post types to database categories
        category_mapping = {
            "service": "GENERIC",
            "iso": "ISO_PIVOT", 
            "general": "GENERIC"
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for post_type, template_list in config_templates.items():
                category = category_mapping.get(post_type, "GENERIC")
                
                for i, template_text in enumerate(template_list):
                    # Create a descriptive name for the template
                    template_name = f"Config {post_type.title()} Template {i+1}"
                    
                    # Check if this template already exists (by name or exact body match)
                    cursor.execute("""
                        SELECT COUNT(*) FROM templates 
                        WHERE name = ? OR body = ?
                    """, (template_name, template_text))
                    
                    if cursor.fetchone()[0] == 0:
                        # Template doesn't exist, create it
                        template_id = str(uuid.uuid4())
                        
                        cursor.execute("""
                            INSERT INTO templates (id, name, category, body, image_pack_id, is_default, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            template_id,
                            template_name,
                            category,
                            template_text,
                            None,
                            False,  # Config templates are not default
                            datetime.now(),
                            datetime.now()
                        ))
                        
                        migrated_count += 1
            
            conn.commit()
        
        return migrated_count

    def get_templates_by_post_type(self, post_type: str) -> List[str]:
        """Get templates for a specific post type (for backward compatibility)"""
        # Mapping of post types to database categories
        category_mapping = {
            "service": "GENERIC",
            "iso": "ISO_PIVOT", 
            "general": "GENERIC"
        }
        
        category = category_mapping.get(post_type, "GENERIC")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT body FROM templates 
                WHERE category = ? 
                ORDER BY is_default DESC, created_at ASC
            """, (category,))
            
            return [row[0] for row in cursor.fetchall()]

    def get_unified_templates(self, config_templates: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Get unified templates (database + config fallback)"""
        unified_templates = {}
        
        for post_type in ["service", "iso", "general"]:
            # Get database templates first
            db_templates = self.get_templates_by_post_type(post_type)
            
            if db_templates:
                # Use database templates if available
                unified_templates[post_type] = db_templates
            else:
                # Fallback to config templates
                unified_templates[post_type] = config_templates.get(post_type, [])
        
        return unified_templates
    
    def get_settings(self) -> Dict[str, Any]:
        """Get application settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settings WHERE id = 'singleton'")
            row = cursor.fetchone()
            if row:
                settings = dict(row)
                # Parse JSON fields
                for field in ['brand_blacklist', 'allowed_brand_modifiers', 'negative_keywords', 'service_keywords', 'iso_keywords']:
                    if settings.get(field):
                        try:
                            settings[field] = json.loads(settings[field])
                        except:
                            settings[field] = []
                return settings
            return {}
    
    def update_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Update application settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert lists to JSON strings
            for field in ['brand_blacklist', 'allowed_brand_modifiers', 'negative_keywords', 'service_keywords', 'iso_keywords']:
                if field in settings_data and isinstance(settings_data[field], list):
                    settings_data[field] = json.dumps(settings_data[field])
            
            # Build dynamic UPDATE query
            fields = list(settings_data.keys())
            if not fields:
                return False
            
            set_clause = ", ".join([f"{field} = ?" for field in fields])
            values = [settings_data[field] for field in fields]
            values.append('singleton')  # for WHERE clause
            
            cursor.execute(f"""
                UPDATE settings 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            
            conn.commit()  # Explicitly commit the transaction
            return cursor.rowcount > 0
    
    def get_fb_accounts(self) -> List[Dict[str, Any]]:
        """Get Facebook accounts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fb_accounts ORDER BY display_name")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_available_fb_account(self) -> Dict[str, Any]:
        """Get an available Facebook account under quota"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fb_accounts 
                WHERE status = 'ACTIVE' 
                AND (last_used_at IS NULL OR 
                     date(last_used_at) < date('now') OR
                     (SELECT COUNT(*) FROM comments 
                      WHERE submitted_by_account_id = fb_accounts.id 
                      AND date(submitted_at) = date('now') 
                      AND status = 'POSTED') < daily_quota)
                ORDER BY last_used_at ASC NULLS FIRST
                LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_fb_account_usage(self, account_id: str) -> bool:
        """Update Facebook account last used timestamp"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE fb_accounts 
                SET last_used_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (account_id,))
            return cursor.rowcount > 0
    
    def search_posts(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search posts with filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build search query
            sql = """
                SELECT p.*, c.comment_body, c.status as comment_status, c.id as comment_id
                FROM posts p
                LEFT JOIN comments c ON p.id = c.post_id
                WHERE 1=1
            """
            params = []
            
            if query:
                sql += " AND (p.content_text LIKE ? OR p.author_name LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if filters:
                if filters.get('status'):
                    sql += " AND p.status = ?"
                    params.append(filters['status'])
                
                if filters.get('intent'):
                    sql += " AND p.detected_intent = ?"
                    params.append(filters['intent'])
                
                if filters.get('date_from'):
                    sql += " AND date(p.created_at) >= ?"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    sql += " AND date(p.created_at) <= ?"
                    params.append(filters['date_to'])
            
            sql += " ORDER BY p.created_at DESC LIMIT 100"
            
            cursor.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                post_data = dict(row)
                # Parse JSON fields
                for field in ['image_urls', 'matched_keywords', 'blocked_reasons', 'brand_hits']:
                    if post_data.get(field):
                        try:
                            post_data[field] = json.loads(post_data[field])
                        except:
                            post_data[field] = []
                results.append(post_data)
            
            return results
    
    def _process_template(self, template_body: str, settings: Dict[str, Any]) -> str:
        """Process template variables"""
        replacements = {
            '{{register_url}}': settings.get('register_url', ''),
            '{{phone}}': settings.get('phone', ''),
            '{{ask_for}}': settings.get('ask_for', '')
        }
        
        result = template_body
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def _log_activity(self, action: str, actor: str, post_id: str = None, comment_id: str = None, meta: Dict[str, Any] = None):
        """Log activity for audit trail"""
        import uuid
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activity_log (id, post_id, comment_id, action, actor, meta)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                post_id,
                comment_id,
                action,
                actor,
                json.dumps(meta) if meta else None
            ))
    
    def update_comment_status(self, queue_id: int, status: str, 
                            approved_by: str = None, error_message: str = None) -> bool:
        """Update the status of a queued comment"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if status == 'approved':
                    cursor.execute("""
                        UPDATE comment_queue 
                        SET status = ?, approved_at = CURRENT_TIMESTAMP, approved_by = ?
                        WHERE id = ?
                    """, (status, approved_by, queue_id))
                elif status == 'posted':
                    cursor.execute("""
                        UPDATE comment_queue 
                        SET status = ?, posted_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, queue_id))
                elif status == 'rejected':
                    cursor.execute("""
                        UPDATE comment_queue 
                        SET status = ?, error_message = ?
                        WHERE id = ?
                    """, (status, error_message, queue_id))
                else:
                    cursor.execute("""
                        UPDATE comment_queue 
                        SET status = ?
                        WHERE id = ?
                    """, (status, queue_id))
                
                conn.commit()
                logger.info(f"Updated comment {queue_id} status to: {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update comment status: {e}")
            return False



    def update_comment_text(self, queue_id: int, new_text: str) -> bool:
        """Update the comment text for a queued comment"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE comment_queue 
                    SET comment_text = ?
                    WHERE id = ?
                """, (new_text, queue_id))
                
                conn.commit()
                logger.info(f"Updated comment text for {queue_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update comment text: {e}")
            return False

    def get_comment_categories(self, comment_id: int) -> List[str]:
        """Get detected categories for a specific comment"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT detected_categories FROM comment_queue 
                    WHERE id = ?
                """, (comment_id,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    return json.loads(result[0])
                return []
                
        except Exception as e:
            logger.error(f"Error getting comment categories: {e}")
            return []
    
    def record_bot_session_start(self) -> Optional[int]:
        """Record the start of a bot session"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO bot_sessions (started_at, status)
                    VALUES (CURRENT_TIMESTAMP, 'running')
                """)
                conn.commit()
                session_id = cursor.lastrowid
                logger.info(f"Started bot session (ID: {session_id})")
                return session_id
        except Exception as e:
            logger.error(f"Failed to record bot session start: {e}")
            return None
    
    def update_bot_session(self, session_id: int, posts_processed: int = 0, 
                          comments_generated: int = 0, errors_count: int = 0) -> bool:
        """Update bot session statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bot_sessions 
                    SET posts_processed = ?, comments_generated = ?, errors_count = ?
                    WHERE id = ?
                """, (posts_processed, comments_generated, errors_count, session_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update bot session: {e}")
            return False
    
    def end_bot_session(self, session_id: int) -> bool:
        """End a bot session"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bot_sessions 
                    SET ended_at = CURRENT_TIMESTAMP, status = 'completed',
                        session_duration_seconds = 
                        (julianday('now') - julianday(started_at)) * 86400
                    WHERE id = ?
                """, (session_id,))
                conn.commit()
                logger.info(f"Ended bot session (ID: {session_id})")
                return True
        except Exception as e:
            logger.error(f"Failed to end bot session: {e}")
            return False
    
    def update_daily_stats(self, posts_processed: int = 0, comments_generated: int = 0,
                          comments_posted: int = 0, errors_count: int = 0) -> bool:
        """Update daily statistics"""
        try:
            today = datetime.now().date().isoformat()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Try to insert new record, or update existing
                cursor.execute("""
                    INSERT INTO bot_stats (date, posts_processed, comments_generated, 
                                        comments_posted, errors_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(date) DO UPDATE SET
                        posts_processed = posts_processed + ?,
                        comments_generated = comments_generated + ?,
                        comments_posted = comments_posted + ?,
                        errors_count = errors_count + ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (today, posts_processed, comments_generated, comments_posted, errors_count,
                      posts_processed, comments_generated, comments_posted, errors_count))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update daily stats: {e}")
            return False
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get bot statistics for the last N days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get daily stats
            cursor.execute("""
                SELECT date, posts_processed, comments_generated, comments_posted, errors_count
                FROM bot_stats 
                WHERE date >= date('now', '-{} days')
                ORDER BY date DESC
            """.format(days))
            
            daily_stats = []
            for row in cursor.fetchall():
                daily_stats.append(dict(row))
            
            # Get total counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_posts,
                    SUM(comments_generated) as total_comments,
                    SUM(comments_posted) as total_posted,
                    SUM(errors_count) as total_errors
                FROM bot_stats
                WHERE date >= date('now', '-{} days')
            """.format(days))
            
            totals = dict(cursor.fetchone())
            
            # Get recent sessions
            cursor.execute("""
                SELECT started_at, ended_at, posts_processed, comments_generated, errors_count
                FROM bot_sessions 
                WHERE started_at >= datetime('now', '-{} days')
                ORDER BY started_at DESC
                LIMIT 10
            """.format(days))
            
            recent_sessions = []
            for row in cursor.fetchall():
                recent_sessions.append(dict(row))
            
            return {
                'daily_stats': daily_stats,
                'totals': totals,
                'recent_sessions': recent_sessions
            }
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """Clean up old data to keep database size manageable"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clean up old processed posts
                cursor.execute("""
                    DELETE FROM processed_posts 
                    WHERE processed_at < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                # Clean up old comment queue items
                cursor.execute("""
                    DELETE FROM comment_queue 
                    WHERE queued_at < datetime('now', '-{} days')
                    AND status IN ('posted', 'rejected')
                """.format(days_to_keep))
                
                # Clean up old bot sessions
                cursor.execute("""
                    DELETE FROM bot_sessions 
                    WHERE started_at < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days_to_keep} days")
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    def clear_all_data(self) -> bool:
        """Clear all data from the database (for testing purposes)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear all tables
                cursor.execute("DELETE FROM comment_queue")
                cursor.execute("DELETE FROM processed_posts")
                cursor.execute("DELETE FROM bot_sessions")
                cursor.execute("DELETE FROM bot_stats")
                
                # Reset auto-increment counters
                cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('comment_queue', 'processed_posts', 'bot_sessions', 'bot_stats')")
                
                conn.commit()
                logger.info("Cleared all data from database for fresh start")
                return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False

    # Image Pack Management Functions
    def create_image_pack(self, name: str, category: str) -> str:
        """Create a new image pack"""
        import uuid
        from datetime import datetime
        
        image_pack_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO image_packs (id, name, images, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (image_pack_id, name, json.dumps([]), False, datetime.now(), datetime.now()))
            
            conn.commit()
            return image_pack_id

    def get_image_packs(self) -> List[Dict[str, Any]]:
        """Get all image packs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM image_packs 
                ORDER BY created_at DESC
            """)
            
            packs = []
            for row in cursor.fetchall():
                pack = dict(row)
                # Parse images JSON
                try:
                    pack['images'] = json.loads(pack['images']) if pack['images'] else []
                except json.JSONDecodeError:
                    pack['images'] = []
                packs.append(pack)
            return packs

    def get_image_pack_by_id(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific image pack by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM image_packs WHERE id = ?", (pack_id,))
            
            row = cursor.fetchone()
            if row:
                pack = dict(row)
                # Parse images JSON
                try:
                    pack['images'] = json.loads(pack['images']) if pack['images'] else []
                except json.JSONDecodeError:
                    pack['images'] = []
                return pack
            return None

    def add_image_to_pack(self, pack_id: str, filename: str, file_path: str) -> bool:
        """Add an image to an existing image pack"""
        from datetime import datetime
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current images
            cursor.execute("SELECT images FROM image_packs WHERE id = ?", (pack_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            # Parse current images
            try:
                current_images = json.loads(row['images']) if row['images'] else []
            except json.JSONDecodeError:
                current_images = []
            
            # Add new image path
            current_images.append(file_path)
            
            # Update the pack
            cursor.execute("""
                UPDATE image_packs 
                SET images = ?, updated_at = ?
                WHERE id = ?
            """, (json.dumps(current_images), datetime.now(), pack_id))
            
            conn.commit()
            return True

    def delete_image_pack(self, pack_id: str) -> bool:
        """Delete an image pack and all its images"""
        import os
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get the pack to find image files to delete
                pack = self.get_image_pack_by_id(pack_id)
                if not pack:
                    return False
                
                # Delete physical image files
                for image_path in pack['images']:
                    full_path = os.path.join(os.getcwd(), image_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted image file: {full_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete image file {full_path}: {e}")
                
                # Delete from database
                cursor.execute("DELETE FROM image_packs WHERE id = ?", (pack_id,))
                
                # Also clear any template references
                cursor.execute("UPDATE templates SET image_pack_id = NULL WHERE image_pack_id = ?", (pack_id,))
                
                conn.commit()
                logger.info(f"Deleted image pack {pack_id} and cleared template references")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete image pack {pack_id}: {e}")
            return False

    def delete_image_from_pack(self, pack_id: str, image_path: str) -> bool:
        """Remove a specific image from a pack"""
        import os
        from datetime import datetime
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current images
                pack = self.get_image_pack_by_id(pack_id)
                if not pack:
                    return False
                
                # Remove the image from list
                updated_images = [img for img in pack['images'] if img != image_path]
                
                # Update the pack
                cursor.execute("""
                    UPDATE image_packs 
                    SET images = ?, updated_at = ?
                    WHERE id = ?
                """, (json.dumps(updated_images), datetime.now(), pack_id))
                
                # Delete physical file
                full_path = os.path.join(os.getcwd(), image_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    logger.info(f"Deleted image file: {full_path}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete image {image_path} from pack {pack_id}: {e}")
            return False

# Global database instance
db = BotDatabase()
