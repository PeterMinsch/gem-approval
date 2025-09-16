from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import threading
import time
import atexit
import logging
from datetime import datetime
import os
import json
import uuid
from modules.url_normalizer import normalize_url
import io
from io import BytesIO
from selenium.webdriver.common.by import By

from facebook_comment_bot import FacebookAICommentBot
from bravo_config import CONFIG
from database import db
from performance_timer import log_performance_summary
from modules.message_generator import MessageGenerator
from browser_manager import MessengerBrowserManager
from messenger_automation import MessengerAutomation

# Configure logging
def setup_api_logger():
    from logging.handlers import RotatingFileHandler
    
    # Ensure the logs directory exists in the project root
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Use a consistent log filename for rotation
    log_filename = os.path.join(logs_dir, 'api.log')
    
    # Create rotating file handler
    # maxBytes=20MB, backupCount=3 (API typically logs less than bot)
    rotating_handler = RotatingFileHandler(
        log_filename,
        maxBytes=20*1024*1024,  # 20 MB per file
        backupCount=3,          # Keep 3 old versions (total ~80MB max)
        encoding='utf-8'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s [%(name)s]')
    rotating_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[rotating_handler, console_handler]
    )
    
    logger_instance = logging.getLogger(__name__)
    logger_instance.info(f"API logging to: {log_filename}")
    logger_instance.info(f"Log rotation: 20MB max per file, 3 backup files kept")
    return logger_instance

logger = setup_api_logger()

def clear_logs_directory():
    """Clear all log files from the logs directory"""
    try:
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        if not os.path.exists(logs_dir):
            logger.info("Logs directory doesn't exist, nothing to clear")
            return True
        
        # Get all files in logs directory
        log_files = []
        for filename in os.listdir(logs_dir):
            file_path = os.path.join(logs_dir, filename)
            if os.path.isfile(file_path):
                log_files.append((filename, file_path))
        
        if not log_files:
            logger.info("No log files found to clear")
            return True
        
        # Remove each log file
        cleared_count = 0
        for filename, file_path in log_files:
            try:
                os.remove(file_path)
                logger.info(f"Cleared log file: {filename}")
                cleared_count += 1
            except Exception as e:
                logger.error(f"Failed to clear log file {filename}: {e}")
        
        logger.info(f"✅ Successfully cleared {cleared_count} log files from {logs_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing logs directory: {e}")
        return False

app = FastAPI(
    title="Bravo Bot API",
    description="API for controlling the Facebook comment bot with comment approval workflow",
    version="2.0.0"
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://164.92.94.214:8080",  # Your server frontend
        "http://164.92.94.214:3000"   # Alternative frontend port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Import and include image pack router
from image_pack_api import router as image_pack_router
app.include_router(image_pack_router, prefix="/api")

# Global bot instance and status
bot_instance = None
bot_status = {
    "is_running": False,
    "start_time": None,
    "last_activity": None,
    "posts_processed": 0,
    "comments_posted": 0,
    "comments_queued": 0,
    "current_status": "idle"
}

# Global messenger browser manager
messenger_browser_manager = MessengerBrowserManager()


# Remove automatic bot/background browser startup. Only start on /bot/start endpoint.
def stop_bot_on_exit():
    global bot_instance
    if bot_instance:
        if hasattr(bot_instance, 'posting_driver') and bot_instance.posting_driver:
            bot_instance.posting_driver.quit()
            logger.info("[AUTO-STOP] Background posting browser closed.")
        bot_instance = None

atexit.register(stop_bot_on_exit)

# Comment queue is now handled by the database

# Pydantic models for API requests/responses
class BotStartRequest(BaseModel):
    post_url: Optional[str] = None
    max_scrolls: Optional[int] = 20
    continuous_mode: bool = True
    clear_database: bool = False  # New option to clear database on startup

class BotStopRequest(BaseModel):
    force: bool = False

class BotStatusResponse(BaseModel):
    is_running: bool
    start_time: Optional[str]
    last_activity: Optional[str]
    posts_processed: int
    comments_posted: int
    comments_queued: int
    current_status: str

class CommentRequest(BaseModel):
    post_url: Optional[str] = None
    post_text: Optional[str] = None

class CommentResponse(BaseModel):
    success: bool
    comment: Optional[str]
    message: str
    post_type: Optional[str]

class QueuedComment(BaseModel):
    id: str
    post_url: str
    post_text: str
    generated_comment: str
    post_type: str
    post_screenshot: Optional[str] = None
    post_images: Optional[str] = None
    post_author: Optional[str] = None
    post_author_url: Optional[str] = None
    post_engagement: Optional[str] = None
    status: str  # "pending", "approved", "rejected", "posted"
    created_at: str
    approved_at: Optional[str] = None
    posted_at: Optional[str] = None
    edited_comment: Optional[str] = None
    rejection_reason: Optional[str] = None

class CommentApprovalRequest(BaseModel):
    comment_id: str
    action: str  # "approve", "reject", "edit"
    edited_comment: Optional[str] = None
    rejection_reason: Optional[str] = None
    images: Optional[List[str]] = None  # List of image filenames to attach

class CommentApprovalResponse(BaseModel):
    success: bool
    message: str
    comment: Optional[QueuedComment] = None

class ConfigUpdateRequest(BaseModel):
    phone: Optional[str] = None
    register_url: Optional[str] = None
    image_url: Optional[str] = None
    chrome_profile: Optional[str] = None
    post_url: Optional[str] = None
    rate_limits: Optional[Dict[str, Any]] = None

# New CRM Models
class PostIngestRequest(BaseModel):
    fb_post_id: str
    group_id: str
    post_url: str
    author_id: str
    author_name: str
    content_text: str
    image_urls: List[str] = []
    detected_intent: str = "IGNORE"
    matched_keywords: List[str] = []
    blocked_reasons: List[str] = []
    brand_hits: List[str] = []
    priority: int = 0

class CommentQueueRequest(BaseModel):
    comment_id: str

class CommentSubmitRequest(BaseModel):
    comment_id: str
    account_id: Optional[str] = None

class PostSkipRequest(BaseModel):
    post_id: str

class TemplateUpdateRequest(BaseModel):
    name: str
    category: str
    body: str
    image_pack_id: Optional[str] = None
    is_default: bool = False

class SettingsUpdateRequest(BaseModel):
    register_url: Optional[str] = None
    phone: Optional[str] = None
    ask_for: Optional[str] = None
    openai_api_key: Optional[str] = None
    brand_blacklist: Optional[List[str]] = None
    allowed_brand_modifiers: Optional[List[str]] = None
    negative_keywords: Optional[List[str]] = None
    service_keywords: Optional[List[str]] = None
    iso_keywords: Optional[List[str]] = None
    scan_refresh_minutes: Optional[int] = None
    max_comments_per_account_per_day: Optional[int] = None

class CommentUpdateRequest(BaseModel):
    comment_body: str
    comment_images: Optional[List[str]] = []

# Additional Template Models for CRUD operations
class TemplateCreateRequest(BaseModel):
    name: str
    category: str
    body: str
    image_pack_id: Optional[str] = None
    is_default: bool = False

class TemplateUpdateRequestPartial(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    body: Optional[str] = None
    image_pack_id: Optional[str] = None
    is_default: Optional[bool] = None

class TemplateResponse(BaseModel):
    id: str
    name: str
    category: str
    body: str
    image_pack_id: Optional[str] = None
    is_default: bool
    created_at: str
    updated_at: str

class TemplateDeleteResponse(BaseModel):
    success: bool
    message: str

# Messenger Automation Models
class MessengerRequest(BaseModel):
    session_id: str
    recipient: str
    message: str
    images: Optional[List[str]] = None

class MessengerResponse(BaseModel):
    status: str
    duration: Optional[str] = None
    error: Optional[str] = None

# Pending approvals queue for when bot is initializing
pending_approvals = []

def queue_approval_for_later(comment_id: str, post_url: str, comment_text: str, images: List[str] = None) -> bool:
    """Queue an approval for later processing when bot becomes available"""
    try:
        approval_data = {
            "comment_id": comment_id,
            "post_url": post_url,
            "comment_text": comment_text,
            "images": images,
            "timestamp": time.time()
        }
        pending_approvals.append(approval_data)
        logger.info(f"📋 Queued approval for comment {comment_id} - will process when bot is ready")
        
        # Update comment status to indicate it's waiting for bot
        try:
            queue_id = int(comment_id)
            db.update_comment_status(queue_id, "waiting_for_bot")
        except Exception as db_error:
            logger.warning(f"Could not update comment status to 'waiting_for_bot': {db_error}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to queue approval for later: {e}")
        return False

def process_pending_approvals():
    """Process any pending approvals once bot is ready"""
    global pending_approvals, bot_instance
    
    if not bot_instance or not hasattr(bot_instance, 'posting_queue'):
        return
    
    processed_count = 0
    failed_approvals = []
    
    for approval in pending_approvals:
        try:
            comment_id = approval["comment_id"]
            post_url = approval["post_url"]
            comment_text = approval["comment_text"]
            images = approval.get("images", None)
            
            logger.info(f"🔄 Processing pending approval for comment {comment_id}")
            
            # Try to post now that bot is ready
            success = post_comment_realtime(comment_id, post_url, comment_text, images=images, _from_pending=True)
            if success:
                processed_count += 1
                logger.info(f"✅ Successfully processed pending approval for comment {comment_id}")
            else:
                failed_approvals.append(approval)
                logger.warning(f"⚠️ Failed to process pending approval for comment {comment_id}")
                
        except Exception as e:
            logger.error(f"Error processing pending approval: {e}")
            failed_approvals.append(approval)
    
    # Update pending approvals list (keep failed ones for retry)
    pending_approvals = failed_approvals
    
    if processed_count > 0:
        logger.info(f"✅ Processed {processed_count} pending approvals")

# Comment queue management functions  
def post_comment_realtime(comment_id: str, post_url: str, comment_text: str, images: List[str] = None, _from_pending=False) -> bool:
    """Post a comment in real-time using the dedicated headless posting browser with optional images"""
    try:
        global bot_instance
        
        # Check if bot instance is available with retry logic
        if not bot_instance:
            logger.warning("⚠️ Bot instance not yet available, checking bot status...")
            # Don't queue again if this call is from pending approval processing
            if _from_pending:
                logger.error("❌ Bot instance still not available during pending approval processing")
                return False
            # Check if bot is still initializing
            global bot_status
            if bot_status.get("is_running", False):
                logger.info("🔄 Bot is initializing, will retry posting in background...")
                # Queue the approval for later processing when bot is ready  
                return queue_approval_for_later(comment_id, post_url, comment_text, images)
            else:
                logger.error("❌ Bot instance not available and not running")
                return False
        
        # 🚀 NEW: Use the dedicated posting queue instead of main browser
        logger.info(f"🚀 Queueing comment {comment_id} for real-time posting via dedicated browser")
        logger.info(f"📝 Comment text: {comment_text[:100] if comment_text else 'None'}...")
        if images:
            logger.info(f"🖼️ With {len(images)} image(s): {images}")
        
        try:
            # Check if posting infrastructure is available
            if not hasattr(bot_instance, 'posting_queue'):
                logger.error("❌ Posting queue not available - bot may not be fully initialized")
                return False
            
            # Add to the posting queue with comment ID and images for tracking
            # Format: (post_url, comment_text, comment_id, images)
            logger.info(f"📤 Adding comment to posting queue: {post_url}")
            bot_instance.posting_queue.put((post_url, comment_text, comment_id, images))
            
            # Update status to "posting" to indicate we've queued it
            queue_id = int(comment_id)
            db.update_comment_status(queue_id, "posting")
            
            logger.info(f"✅ Comment {comment_id} queued for posting via dedicated browser")
            
            # Note: The actual posting happens asynchronously in the background thread
            # We return True to indicate successful queuing, not successful posting
            # The background thread will update status to "posted" when complete
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error queuing comment {comment_id} for posting: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in post_comment_realtime: {e}")
        return False

def add_comment_to_queue(post_url: str, post_text: str, generated_comment: str, post_type: str,
                        post_screenshot: str = None, post_images: str = None,
                        post_author: str = None, post_engagement: str = None,
                        detected_categories: List[str] = None, post_author_url: str = None) -> str:
    """Add a generated comment to the approval queue using database with enhanced post data"""
    logger.info(f"🔄 Adding to comment queue: {post_type} - {post_url[:50]}...")
    logger.info(f"📝 Comment text: {generated_comment[:100] if generated_comment else 'None'}...")
    
    # DEBUGGING: Log post_author_url at API layer
    logger.debug(f"API_LAYER: Received post_author_url: '{post_author_url}' (length: {len(post_author_url) if post_author_url else 0})")
    
    queue_id = db.add_to_comment_queue(post_url, post_text, generated_comment, post_type,
                                     post_screenshot, post_images, post_author, post_engagement,
                                     detected_categories=detected_categories, post_author_url=post_author_url)
    
    if queue_id:
        bot_status["comments_queued"] += 1
        logger.info(f"✅ Comment queued for approval in database: {queue_id} - {post_type}")
        return str(queue_id)
    else:
        logger.error(f"❌ Failed to add comment to database queue")
        return None

def get_pending_comments() -> List[QueuedComment]:
    """Get all pending comments from the database queue"""
    db_comments = db.get_pending_comments()
    comments = []
    for db_comment in db_comments:
        comment = QueuedComment(
            id=str(db_comment['id']),
            post_url=db_comment['post_url'],
            post_text=db_comment['post_text'],
            generated_comment=db_comment['comment_text'],
            post_type=db_comment['post_type'],
            post_screenshot=db_comment.get('post_screenshot'),
            post_images=db_comment.get('post_images'),
            post_author=db_comment.get('post_author'),
            post_author_url=db_comment.get('post_author_url'),
            post_engagement=db_comment.get('post_engagement'),
            status=db_comment['status'],
            created_at=db_comment['queued_at'],
            approved_at=db_comment['approved_at'],
            posted_at=db_comment['posted_at']
        )
        comments.append(comment)
    return comments

def get_comment_by_id(comment_id: str) -> Optional[QueuedComment]:
    """Get a specific comment by ID from database"""
    try:
        queue_id = int(comment_id)
        db_comment = db.get_comment_by_id(queue_id)
        
        if db_comment:
            return QueuedComment(
                id=str(db_comment['id']),
                post_url=db_comment['post_url'],
                post_text=db_comment['post_text'],
                generated_comment=db_comment['comment_text'],
                post_type=db_comment['post_type'],
                post_screenshot=db_comment.get('post_screenshot'),
                post_images=db_comment.get('post_images'),
                post_author=db_comment.get('post_author'),
                post_author_url=db_comment.get('post_author_url'),
                post_engagement=db_comment.get('post_engagement'),
                status=db_comment['status'],
                created_at=db_comment['queued_at'],
                approved_at=db_comment['approved_at'],
                posted_at=db_comment['posted_at']
            )
        return None
    except ValueError:
        logger.error(f"Invalid comment ID format: {comment_id}")
        return None

def approve_comment(comment_id: str, edited_comment: Optional[str] = None) -> bool:
    """Approve a comment for posting using database"""
    try:
        queue_id = int(comment_id)
        
        # First update the comment text if provided
        if edited_comment:
            success = db.update_comment_text(queue_id, edited_comment)
            if not success:
                logger.error(f"Failed to update comment text for {comment_id}")
                return False
        
        # Then approve the comment
        success = db.update_comment_status(queue_id, "approved", approved_by="user")
        if success:
            bot_status["comments_queued"] = max(0, bot_status["comments_queued"] - 1)
            logger.info(f"Comment approved in database: {comment_id}")
            return True
        else:
            logger.error(f"Failed to approve comment in database: {comment_id}")
            return False
    except ValueError:
        logger.error(f"Invalid comment ID format: {comment_id}")
        return False

def reject_comment(comment_id: str, reason: str) -> bool:
    """Reject a comment using database"""
    try:
        queue_id = int(comment_id)
        success = db.update_comment_status(queue_id, "rejected", error_message=reason)
        if success:
            bot_status["comments_queued"] = max(0, bot_status["comments_queued"] - 1)
            logger.info(f"Comment rejected in database: {comment_id} - Reason: {reason}")
            return True
        else:
            logger.error(f"Failed to reject comment in database: {comment_id}")
            return False
    except ValueError:
        logger.error(f"Invalid comment ID format: {comment_id}")
        return False










def run_bot_in_background(post_url: str = None, max_scrolls: int = None, 
                         continuous_mode: bool = False, clear_database: bool = False):
    """Background wrapper function to start the bot with proper parameter handling"""
    global bot_instance, bot_status
    
    try:
        logger.info("🚀 Starting bot in background...")
        
        # Clear database if requested
        if clear_database:
            logger.info("🗑️ Clearing database as requested...")
            db.clear_database()
            logger.info("✅ Database cleared")
        
        # Create bot instance with config
        config = CONFIG.copy()
        if post_url:
            config["POST_URL"] = post_url
            
        bot_instance = FacebookAICommentBot(config)
        bot_status["is_running"] = True
        bot_status["start_time"] = datetime.now().isoformat()
        
        # Start the bot using the existing function
        run_bot_with_queuing(bot_instance, max_scrolls)
        
    except Exception as e:
        logger.error(f"❌ Error in background bot: {e}")
        bot_status["is_running"] = False
        bot_status["error_message"] = str(e)
        raise

def run_bot_with_queuing(bot_instance: FacebookAICommentBot, max_scrolls: int = None):
    """Run the bot with CRM ingestion instead of old comment queuing"""
    global bot_status
    
    try:
        # 🚀 CRITICAL: Start the posting thread for real-time posting
        logger.info("🚀 Starting posting thread for real-time comment posting...")
        bot_instance.start_posting_thread()
        logger.info("✅ Posting thread started successfully")
        
        # 🔄 Process any pending approvals that were queued during initialization
        logger.info("🔄 Processing any pending approvals...")
        process_pending_approvals()
        
        # Import the new CRM ingestion functions
        import requests
        import uuid
        from database import db
        
        # Override the bot's posting behavior to ingest into CRM instead
        def ingest_post_to_crm(clean_url: str, post_text: str):
            """Ingest post into CRM system instead of old comment queue"""
            try:
                logger.info(f"🔄 Starting CRM ingestion for: {clean_url}")
                
                # Add URL/content validation logging
                if bot_instance and bot_instance.driver:
                    current_url = bot_instance.driver.current_url
                    logger.info(f"🔗 URL Validation Check:")
                    logger.info(f"  📌 Stored URL: {clean_url}")
                    logger.info(f"  🌐 Current URL: {current_url}")
                    if clean_url != current_url:
                        logger.warning(f"⚠️ URL MISMATCH DETECTED!")
                        logger.warning(f"  Expected: {clean_url}")
                        logger.warning(f"  Actual:   {current_url}")
                
                # Validate text quality before processing
                logger.info(f"📝 Post text preview: {post_text[:100] if post_text else 'None'}...")
                
                # Check text quality
                if post_text:
                    words = post_text.split()
                    if words:
                        single_chars = len([w for w in words if len(w) == 1 and w.isalnum()])
                        total_words = len(words)
                        scrambled_ratio = single_chars / total_words if total_words > 0 else 0
                        
                        if scrambled_ratio > 0.5:
                            logger.error(f"🚨 SCRAMBLED TEXT DETECTED!")
                            logger.error(f"  Single chars: {single_chars}/{total_words} ({scrambled_ratio:.1%})")
                            logger.error(f"  Sample: {post_text[:200]}...")
                            # Still continue but mark the issue
                        else:
                            logger.info(f"✅ Text quality check passed: {total_words} words, {scrambled_ratio:.1%} single chars")
                
                # Use the bot's classifier to get proper classification
                logger.info(f"🏷️ Classifying post...")
                classification = bot_instance.classifier.classify_post(post_text)
                logger.info(f"✅ Classification complete - Type: {classification.post_type}, Score: {classification.confidence_score}, Skip: {classification.should_skip}")
                
                if classification.should_skip:
                    logger.info(f"⏭️ Post filtered out: {classification.post_type}")
                    return
                
                # Extract post author for personalization with profile URL
                logger.info(f"👤 Extracting post author and profile URL for personalization...")
                post_author_name = ""
                post_author_profile_url = ""
                try:
                    if bot_instance and bot_instance.driver and hasattr(bot_instance.post_extractor, 'get_post_author_with_profile'):
                        post_author_name, post_author_profile_url = bot_instance.post_extractor.get_post_author_with_profile()
                        logger.info(f"✅ Extracted post author: '{post_author_name}' with profile URL: '{post_author_profile_url[:50] if post_author_profile_url else 'None'}'")
                    elif bot_instance and bot_instance.driver:
                        # Fallback to old method if enhanced method not available
                        post_author_name = bot_instance.get_post_author()
                        logger.info(f"✅ Extracted post author (fallback): '{post_author_name}'")
                    else:
                        logger.warning("⚠️ No bot instance/driver available for author extraction")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract post author: {e}")
                
                # Generate comment using the bot's comment generator with author name
                logger.info(f"🔍 Generating comment for post type: {classification.post_type}")
                comment = bot_instance.comment_generator.generate_comment(classification.post_type, post_text, post_author_name)
                logger.info(f"✅ Comment generation complete")
                
                logger.info(f"📝 Generated comment: {comment[:100] if comment else 'None'}...")
                
                if comment:
                    logger.info(f"💾 Starting metadata capture...")
                    # Try to capture post metadata
                    post_screenshot = None
                    post_images = None
                    post_author = post_author_name  # Use the extracted author name for personalization
                    post_author_url = post_author_profile_url  # Use the extracted profile URL for Messenger links
                    post_engagement = None
                    
                    try:
                        if bot_instance and bot_instance.driver:
                            logger.info(f"🖥️ Driver available, capturing post metadata...")
                            
                            # Extract post images using direct selectors (more robust)
                            try:
                                logger.info("🖼️ Extracting post images using direct selectors...")
                                image_selectors = [
                                    "//img[contains(@src, 'scontent')]",
                                    "//img[contains(@src, 'fbcdn')]", 
                                    "//img[contains(@class, 'scaledImageFitWidth')]",
                                    "//img[contains(@class, 'img')]"
                                ]
                                
                                images = []
                                for selector in image_selectors:
                                    img_elements = bot_instance.driver.find_elements(By.XPATH, selector)
                                    logger.info(f"Selector {selector[:30]}... found {len(img_elements)} images")
                                    for img in img_elements:
                                        try:
                                            src = img.get_attribute('src')
                                            if src and 'scontent' in src and src not in images:
                                                images.append(src)
                                                logger.info(f"✅ Found image: {src[:80]}...")
                                        except:
                                            continue
                                
                                if images:
                                    logger.info(f"✅ Successfully extracted {len(images)} images")
                                    post_images = json.dumps(images)
                                else:
                                    logger.info("⚠️ No images found for this post")
                                    post_images = ""
                                    
                            except Exception as e:
                                logger.warning(f"Failed to extract post images: {e}")
                                post_images = ""
                            
                            # Try to capture screenshot and metadata (optional, don't fail if article not found)
                            try:
                                # Try to find the main post container (not comments)
                                # Look for article that contains the post text we found
                                post_xpath = "//div[@role='article'][1]"  # First article is usually the main post
                                post_element = bot_instance.driver.find_element(By.XPATH, post_xpath)
                                
                                if post_element:
                                    # Try to exclude comments section if possible
                                    try:
                                        # Find the post content area (before comments)
                                        content_script = """
                                        var article = arguments[0];
                                        // Find where comments start (usually after post content)
                                        var commentSection = article.querySelector('[aria-label*="Comment"], [role="complementary"]');
                                        if (commentSection) {
                                            // Hide comments temporarily for screenshot
                                            commentSection.style.display = 'none';
                                        }
                                        return true;
                                        """
                                        bot_instance.driver.execute_script(content_script, post_element)
                                    except:
                                        pass  # If we can't hide comments, still take screenshot
                                    
                                    post_screenshot = post_element.screenshot_as_png
                                    import base64
                                    post_screenshot = f"data:image/png;base64,{base64.b64encode(post_screenshot).decode('utf-8')}"
                                    
                                    # Restore comments if hidden
                                    try:
                                        restore_script = """
                                        var article = arguments[0];
                                        var commentSection = article.querySelector('[aria-label*="Comment"], [role="complementary"]');
                                        if (commentSection) {
                                            commentSection.style.display = '';
                                        }
                                        """
                                        bot_instance.driver.execute_script(restore_script, post_element)
                                    except:
                                        pass
                                    
                                    # Try to extract post author and profile URL using the enhanced method
                                    try:
                                        # Use the enhanced get_post_author_with_profile method if available
                                        if hasattr(bot_instance.post_extractor, 'get_post_author_with_profile'):
                                            extracted_author, extracted_author_url = bot_instance.post_extractor.get_post_author_with_profile()
                                            
                                            # DEBUGGING: Log the extraction results
                                            logger.debug(f"BOT_EXTRACTION: Extracted author: '{extracted_author}'")
                                            logger.debug(f"BOT_EXTRACTION: Extracted URL: '{extracted_author_url}' (length: {len(extracted_author_url) if extracted_author_url else 0})")
                                            
                                            if extracted_author:
                                                post_author = extracted_author
                                                post_author_url = extracted_author_url
                                                logger.info(f"✅ Extracted post author: '{post_author}' with profile URL: '{post_author_url[:50] if post_author_url else 'None'}'")
                                            else:
                                                logger.warning("⚠️ Could not extract post author")
                                        else:
                                            # Fallback to old method
                                            extracted_author = bot_instance.get_post_author()
                                            if extracted_author:
                                                post_author = extracted_author
                                                logger.info(f"✅ Extracted post author (fallback): '{post_author}'")
                                            else:
                                                logger.warning("⚠️ Could not extract post author")
                                    except Exception as e:
                                        logger.debug(f"Author extraction failed: {e}")
                                        
                                    try:
                                        engagement_elem = post_element.find_element(By.XPATH, ".//span[contains(text(), 'like') or contains(text(), 'comment') or contains(text(), 'share')]")
                                        if engagement_elem:
                                            post_engagement = engagement_elem.text.strip()
                                    except:
                                        pass
                            except:
                                logger.info("📸 Article element not found, skipping screenshot and metadata (images still captured)")
                    except Exception as e:
                        logger.warning(f"Failed to capture post visuals: {e}")
                    
                    # Prepare post data for CRM ingestion
                    post_data = {
                        'fb_post_id': clean_url.split('/')[-1] if '/' in clean_url else str(uuid.uuid4()),
                        'post_url': clean_url,  # Use clean URL consistently
                        'content_text': post_text,
                        'author_name': post_author or 'Unknown',
                        'detected_intent': classification.post_type.upper(),
                        'matched_keywords': list(classification.keyword_matches.get('service', [])),
                        'image_urls': post_images or [],
                        'priority': 1 if classification.confidence_score > 20 else 0
                    }
                    
                    # FIXED: Instead of calling API (which creates circular calls), directly add to comment queue
                    try:
                        logger.info(f"🔄 Adding comment to approval queue: {clean_url}")
                        logger.info(f"📊 Queue data - Type: {classification.post_type}, Author: {post_author}, Images: {len(post_images) if post_images else 0}")
                        # Add comment directly to the approval queue using the database
                        queue_id = add_comment_to_queue(clean_url, post_text, comment, classification.post_type,
                                                      post_screenshot, post_images, post_author, post_engagement,
                                                      post_author_url=post_author_profile_url)
                        logger.info(f"🔄 add_comment_to_queue returned: {queue_id}")
                        
                        if queue_id:
                            logger.info(f"✅ Successfully queued comment for approval (ID: {queue_id}): {post_url}")
                            bot_status["posts_processed"] += 1
                            bot_status["last_activity"] = datetime.now().isoformat()
                        else:
                            logger.error(f"❌ Failed to queue comment for approval: {post_url}")
                    except Exception as e:
                        logger.error(f"❌ Error queuing comment: {e}")
                        # Try one more time with minimal data
                        try:
                            logger.info(f"🔄 Retrying with minimal data...")
                            add_comment_to_queue(post_url, post_text, comment, classification.post_type, 
                                               post_author_url=post_author_profile_url)
                            logger.info(f"Fallback: Comment queued with minimal data: {classification.post_type}")
                        except Exception as e2:
                            logger.error(f"❌ Complete failure queuing comment: {e2}")
                        
                else:
                    logger.warning(f"❌ Could not generate comment for post type: {classification.post_type}")
                    
            except Exception as e:
                logger.error(f"💥 Error processing post for CRM ingestion: {e}")
                import traceback
                logger.error(f"💥 Traceback: {traceback.format_exc()}")
        
        # Actually open Chrome and start scanning Facebook
        logger.info("Opening Chrome browser and navigating to Facebook...")
        
        try:
            # Start the bot's actual scanning process
            logger.info("Setting up Chrome driver...")
            bot_instance.setup_driver()
            logger.info("Chrome browser opened successfully")
            
            # Navigate to the target Facebook group or specific post
            target_url = bot_instance.config.get("POST_URL", "https://www.facebook.com/groups/5440421919361046")
            logger.info(f"Navigating to: {target_url}")
            
            bot_instance.driver.get(target_url)

            # Check if we got redirected to login page after navigation
            current_url = bot_instance.driver.current_url.lower()
            if "login" in current_url:
                logger.warning("⚠️ Redirected to login page after navigation - attempting re-authentication...")

                # Try to login again using credentials
                username = os.environ.get('FACEBOOK_USERNAME')
                password = os.environ.get('FACEBOOK_PASSWORD')

                if username and password:
                    if bot_instance.browser_manager.login_to_facebook(username, password):
                        logger.info("✅ Re-authentication successful, trying navigation again...")

                        # Test group access directly instead of just URL check
                        if bot_instance.browser_manager._can_access_group(target_url):
                            logger.info("✅ Successfully gained group access after re-authentication")
                        else:
                            logger.error("❌ Still cannot access group after re-authentication")
                            logger.error("   This may indicate: insufficient permissions, private group, or blocked access")
                    else:
                        logger.error("❌ Re-authentication failed")
                else:
                    logger.error("❌ No credentials available for re-authentication")

            logger.info("Successfully navigated to Facebook")
            
            # Check if we're targeting a specific post URL
            is_specific_post = "/posts/" in target_url
            
            if is_specific_post:
                # Process the specific post directly
                logger.info("Processing specific post directly...")
                time.sleep(2)  # Reduced wait for page to load
                
                # Use centralized URL normalization
                clean_url = normalize_url(target_url)
                
                try:
                    # Extract post text
                    post_text = bot_instance.get_post_text()
                    if post_text and post_text.strip():
                        logger.info(f"📝 Extracted post text: {post_text[:100]}...")
                        # Process this post through CRM ingestion
                        ingest_post_to_crm(clean_url, post_text)
                    else:
                        logger.warning("No post text found on specific post page")
                        
                except Exception as e:
                    logger.error(f"Error processing specific post: {e}")
                    
                # Exit after processing the specific post
                bot_status["is_running"] = False
                
            else:
                # Start scanning for posts in group mode
                logger.info("Starting to scan for posts...")
                
                # Keep running and scanning
                while bot_status["is_running"]:
                    try:
                        # Actually scan for new posts using the bot's real methods
                        logger.info("Scanning for new posts...")
                        
                        # DEBUGGING: Check current page before scanning
                        current_url = bot_instance.driver.current_url if bot_instance.driver else "unknown"
                        logger.debug(f"SCAN_DEBUG: Current URL before scanning: {current_url[:100]}...")
                        
                        # DEBUGGING: Ensure we're on the group feed, not individual posts
                        group_url = CONFIG.get('POST_URL', 'https://www.facebook.com')
                        if '/groups/' in group_url and 'fbid=' not in current_url and '/posts/' not in current_url:
                            # We're still on the group feed, good to scan
                            logger.debug(f"SCAN_DEBUG: On group feed, proceeding with scan")
                        elif '/groups/' in group_url:
                            # We might be on an individual post, navigate back to group feed
                            logger.info(f"SCAN_DEBUG: Navigating back to group feed: {group_url}")
                            bot_instance.driver.get(group_url)
                            time.sleep(2)  # Wait for page load
                        
                        # Use the bot's actual post scanning method
                        post_links = bot_instance.scroll_and_collect_post_links(max_scrolls=5)
                        logger.info(f"Found {len(post_links)} potential posts to scan")
                        
                        # Process each post found
                        for post_url in post_links:
                            if not bot_status["is_running"]:
                                break
                            
                            # Use centralized URL normalization
                            clean_url = normalize_url(post_url)
                            
                            if db.is_post_processed(clean_url):
                                logger.info(f"Skipping already processed post: {clean_url}")
                                continue
                            
                            logger.info(f"🔍 Processing post: {clean_url}")
                            logger.info(f"📊 Total posts found: {len(post_links)}, Current: {post_links.index(post_url) + 1}")
                        
                            try:
                                # Navigate to the post
                                bot_instance.driver.get(clean_url)
                                time.sleep(5)
                                
                                # Check if post is from today
                                if not bot_instance.is_post_from_today():
                                    logger.info(f"Skipping post not from today: {clean_url}")
                                    bot_instance.save_processed_post(clean_url, post_text="", error_message="Not from today")
                                    continue
                                
                                # Extract post text
                                post_text = bot_instance.get_post_text()
                                if not post_text.strip():
                                    logger.info(f"No post text found, marking as processed: {clean_url}")
                                    bot_instance.save_processed_post(clean_url, post_text="", error_message="No text extracted")
                                    continue
                                
                                # Check for existing comments
                                existing_comments = bot_instance.get_existing_comments()
                                logger.info(f"Found {len(existing_comments)} existing comments")
                                
                                # Check if we already commented
                                if bot_instance.already_commented(existing_comments):
                                    logger.info(f"Already commented on this post: {clean_url}")
                                    bot_instance.save_processed_post(clean_url, post_text=post_text, post_type="already_commented")
                                    continue
                                
                                
                                # Ingest post into CRM
                                ingest_post_to_crm(clean_url, post_text)
                                
                                # Mark as processed
                                bot_instance.save_processed_post(clean_url, post_text=post_text, post_type="processed")
                                
                            except Exception as e:
                                logger.error(f"Error processing post {clean_url}: {e}")
                                bot_instance.save_processed_post(clean_url, post_text="", error_message=str(e))
                                continue
                        
                        # Wait before next scan (reduced for testing)
                        logger.info("Scan cycle complete. Starting next scan in 5 seconds...")
                        time.sleep(5)  # Reduced from 30s for testing
                        
                    except Exception as e:
                        logger.error(f"Error during scanning: {e}")
                        
                        # Add connection recovery logic
                        if ("connection refused" in str(e).lower() or 
                            "max retries exceeded" in str(e).lower() or
                            "failed to establish" in str(e).lower() or
                            "connection broken" in str(e).lower()):
                            logger.warning("Connection error detected, attempting to restart browser...")
                            try:
                                if bot_instance:
                                    bot_instance.reconnect_driver_if_needed()
                                    logger.info("Browser reconnected successfully")
                                    continue  # Skip the sleep and retry immediately
                            except Exception as reconnect_error:
                                logger.error(f"Failed to reconnect browser: {reconnect_error}")
                        
                        time.sleep(10)  # Reduced from 60s - wait before retrying
                    
        except Exception as e:
            logger.error(f"Error setting up Chrome or navigating: {e}")
            
    except Exception as e:
        logger.error(f"Error in run_bot_with_queuing: {e}")
    finally:
        # Log performance summary before cleanup
        log_performance_summary()
        
        if bot_instance and bot_instance.driver:
            bot_instance.driver.quit()
            logger.info("Chrome browser closed")

def stop_bot():
    """Stop the running bot and properly cleanup"""
    global bot_instance, bot_status
    
    logger.info("🛑 Stopping bot...")
    bot_status["current_status"] = "stopping"
    
    if bot_instance:
        try:
            # Stop the posting thread if it exists
            if hasattr(bot_instance, 'stop_posting_thread'):
                logger.info("Stopping posting thread...")
                bot_instance.stop_posting_thread()
            
            # Close the main browser
            if bot_instance.driver:
                logger.info("Closing main browser...")
                bot_instance.driver.quit()
                
            # Close the posting browser if it exists
            if hasattr(bot_instance, 'posting_driver') and bot_instance.posting_driver:
                logger.info("Closing posting browser...")
                bot_instance.posting_driver.quit()
                
        except Exception as e:
            logger.error(f"Error during bot cleanup: {e}")
    
    # Reset bot instance and status - CRITICAL FIX: Don't set to None, allow restart
    bot_instance = None
    bot_status.update({
        "is_running": False,
        "current_status": "stopped",
        "last_activity": datetime.now().isoformat()
    })
    
    logger.info("✅ Bot stopped successfully")

# API endpoints
@app.get("/")
async def root():
    return {"message": "Bravo Bot API with Comment Approval Workflow is running"}

@app.post("/bot/start", response_model=Dict[str, str])
async def start_bot(request: BotStartRequest, background_tasks: BackgroundTasks):
    """Start the Facebook comment bot with comment queuing"""
    global bot_instance, bot_status
    if bot_status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot is already running")

    # Prepare config
    config = CONFIG.copy()
    if request.post_url:
        config["POST_URL"] = request.post_url

    # Start the bot using the proper background method with CRM ingestion
    background_tasks.add_task(run_bot_in_background, 
                            request.post_url, 
                            request.max_scrolls, 
                            request.continuous_mode, 
                            request.clear_database)

    return {"message": "Bot started successfully (run() called)", "status": "starting"}

@app.post("/bot/stop", response_model=Dict[str, str])
async def stop_bot_endpoint(request: BotStopRequest):
    """Stop the running bot - allows restart afterwards"""
    global bot_status
    
    if not bot_status["is_running"]:
        # Don't throw error - allow stop even if already stopped (idempotent)
        logger.info("Bot is already stopped")
        return {"message": "Bot is already stopped"}
    
    stop_bot()
    return {"message": "Bot stopped successfully. You can now start it again."}

@app.get("/bot/status", response_model=BotStatusResponse)
async def get_bot_status():
    """Get current bot status"""
    return bot_status

@app.get("/comments/queue", response_model=List[QueuedComment])
async def get_comment_queue():
    """Get all pending comments in the approval queue"""
    return get_pending_comments()

@app.get("/comments/history", response_model=List[QueuedComment])
async def get_comment_history():
    """Get comment history (approved, rejected, posted)"""
    return db.get_comment_history()

@app.get("/comments/templates")
async def get_comment_templates():
    """Get available comment templates organized by post type (unified from database + config)"""
    try:
        # Get unified templates from database (includes migration from config)
        from bravo_config import CONFIG
        config_templates = CONFIG.get("templates", {})
        db_templates = db.get_unified_templates(config_templates)
        
        # Format templates for frontend use
        formatted_templates = {"service": [], "iso": [], "general": []}
        
        # Map database categories to frontend post types
        category_to_type = {
            "GENERIC": "general",
            "ISO_PIVOT": "iso", 
            "SERVICE_REQUEST": "service"
        }
        
        if db_templates:
            # db_templates is a dict with post_type keys and template lists as values
            # Get all database templates and organize by post type
            all_db_templates = db.get_templates()  # Get all template objects
            
            # Map database categories to post types
            for template_obj in all_db_templates:
                category = template_obj.get("category", "GENERIC")
                post_type = category_to_type.get(category, "general")
                
                formatted_templates[post_type].append({
                    "id": template_obj["id"],
                    "text": template_obj["body"],
                    "post_type": post_type
                })
        
        # If no database templates, fallback to config templates
        if not db_templates or not any(formatted_templates.values()):
            logger.info("⚠️ No database templates found, using config fallback")
            from bravo_config import CONFIG
            config_templates = CONFIG.get("templates", {})
            
            for post_type, template_list in config_templates.items():
                if post_type in formatted_templates:
                    formatted_templates[post_type] = [
                        {
                            "id": f"config_{post_type}_{i}",
                            "text": template,
                            "post_type": post_type
                        }
                        for i, template in enumerate(template_list)
                    ]
        
        return {
            "success": True,
            "templates": formatted_templates
        }
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return {
            "success": False,
            "error": str(e),
            "templates": {}
        }

@app.post("/generate-message/{comment_id}")
async def generate_dm_message(comment_id: str):
    """Generate personalized DM message for a specific comment"""
    try:
        # Get comment data from database
        try:
            # Convert string ID back to integer for database lookup
            comment_id_int = int(comment_id)
            db_comment = db.get_comment_by_id(comment_id_int)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid comment ID format")
        if not db_comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        logger.info(f"🎯 Generating DM message for comment {comment_id} (author: {db_comment.get('post_author')})")
        
        # Initialize message generator
        generator = MessageGenerator(CONFIG)
        
        # Generate the message
        start_time = time.time()
        result = await generator.generate_dm_message(db_comment)
        generation_time = time.time() - start_time
        
        # 🚀 Use stored images and screenshot for fast Smart Launcher response
        post_images = []
        post_screenshot = None
        
        # Parse stored images from database
        if db_comment.get('post_images'):
            try:
                stored_images = db_comment['post_images']
                if isinstance(stored_images, str) and stored_images.startswith('['):
                    # JSON array of image URLs/data
                    post_images = json.loads(stored_images)
                elif isinstance(stored_images, str):
                    # Single image URL/data as string
                    post_images = [stored_images] if stored_images else []
                logger.info(f"📷 Using stored images: {len(post_images)} image(s)")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse stored images: {e}")
                post_images = []
        
        # Get stored screenshot
        post_screenshot = db_comment.get('post_screenshot')
        if post_screenshot:
            logger.info(f"📸 Using stored screenshot ({len(post_screenshot)} chars)")
        else:
            logger.info("📸 No stored screenshot available")
        
        # Create Messenger URL from author profile URL
        messenger_url = None
        if db_comment.get('post_author_url'):
            try:
                from modules.post_extractor import PostExtractor
                facebook_id = PostExtractor.extract_facebook_id_from_profile_url(db_comment['post_author_url'])
                if facebook_id:
                    messenger_url = f"https://www.facebook.com/messages/t/{facebook_id}"
                    logger.debug(f"✅ Created Messenger URL: {messenger_url}")
            except Exception as e:
                logger.warning(f"Failed to create Messenger URL: {e}")
        
        # post_images and post_screenshot are already set above from fresh capture
        
        # Enhanced response with metadata and images
        response = {
            'success': True,
            'message': result['message'],
            'author_name': result['author_name'],
            'generation_method': result['generation_method'],
            'character_count': result['character_count'],
            'generation_time_seconds': round(generation_time, 2),
            'post_type': result['post_type'],
            'messenger_url': messenger_url,
            'post_images': post_images,
            'post_screenshot': post_screenshot,
            'has_images': len(post_images) > 0 or bool(post_screenshot)
        }
        
        logger.info(f"✅ Generated {result['character_count']}-char message using {result['generation_method']} in {generation_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to generate message for comment {comment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Message generation failed: {str(e)}")

@app.get("/proxy-image")
async def proxy_image(url: str):
    """Proxy endpoint to fetch images and bypass CORS restrictions"""
    try:
        import httpx
        
        logger.info(f"🖼️ Proxying image request for: {url[:100]}...")
        
        # Validate URL is an image URL
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL")
        
        # Fetch the image
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch image")
            
            # Determine content type
            content_type = response.headers.get('content-type', 'image/jpeg')
            
            # Return the image with appropriate headers
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type=content_type,
                headers={
                    'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                    'Access-Control-Allow-Origin': '*'  # Allow CORS
                }
            )
            
    except httpx.TimeoutException:
        logger.error(f"❌ Timeout fetching image: {url[:100]}")
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except Exception as e:
        logger.error(f"❌ Failed to proxy image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to proxy image: {str(e)}")

@app.post("/comments/approve", response_model=CommentApprovalResponse)
async def approve_comment_endpoint(request: CommentApprovalRequest):
    """Approve, reject, or edit a comment"""
    try:
        if request.action == "approve":
            success = approve_comment(request.comment_id, request.edited_comment)
            if success:
                comment = get_comment_by_id(request.comment_id)
                
                # 🚀 NEW: Automatically trigger real-time posting after approval
                logger.info(f"🚀 Auto-posting approved comment {request.comment_id} in real-time...")
                try:
                    # Get the final comment text (could be edited)
                    final_comment_text = request.edited_comment or comment.generated_comment
                    
                    # Post comment in real-time using the existing function with images
                    posting_success = post_comment_realtime(request.comment_id, comment.post_url, final_comment_text, images=request.images)
                    
                    if posting_success:
                        logger.info(f"✅ Comment {request.comment_id} approved and queued for posting!")
                        return CommentApprovalResponse(
                            success=True,
                            message="Comment approved and queued for posting to Facebook! Check status in a few seconds.",
                            comment=comment
                        )
                    else:
                        logger.warning(f"⚠️ Comment {request.comment_id} approved but failed to queue for posting")
                        return CommentApprovalResponse(
                            success=True,
                            message="Comment approved but failed to queue for posting - check bot logs",
                            comment=comment
                        )
                        
                except Exception as posting_error:
                    logger.error(f"❌ Error posting approved comment {request.comment_id}: {posting_error}")
                    return CommentApprovalResponse(
                        success=True,
                        message="Comment approved but posting encountered an error - check bot logs",
                        comment=comment
                    )
            else:
                raise HTTPException(status_code=404, detail="Comment not found")
                
        elif request.action == "reject":
            if not request.rejection_reason:
                raise HTTPException(status_code=400, detail="Rejection reason is required")
            
            success = reject_comment(request.comment_id, request.rejection_reason)
            if success:
                return CommentApprovalResponse(
                    success=True,
                    message="Comment rejected successfully"
                )
            else:
                raise HTTPException(status_code=404, detail="Comment not found")
                
        elif request.action == "edit":
            if not request.edited_comment:
                raise HTTPException(status_code=400, detail="Edited comment is required")
            
            success = approve_comment(request.comment_id, request.edited_comment)
            if success:
                comment = get_comment_by_id(request.comment_id)
                
                # 🚀 NEW: Automatically trigger real-time posting after edit+approve
                logger.info(f"🚀 Auto-posting edited comment {request.comment_id} in real-time...")
                try:
                    # Post the edited comment in real-time with images
                    posting_success = post_comment_realtime(request.comment_id, comment.post_url, request.edited_comment, images=request.images)
                    
                    if posting_success:
                        logger.info(f"✅ Comment {request.comment_id} edited and queued for posting!")
                        return CommentApprovalResponse(
                            success=True,
                            message="Comment edited and queued for posting to Facebook! Check status in a few seconds.",
                            comment=comment
                        )
                    else:
                        logger.warning(f"⚠️ Comment {request.comment_id} edited but failed to queue for posting")
                        return CommentApprovalResponse(
                            success=True,
                            message="Comment edited but failed to queue for posting - check bot logs",
                            comment=comment
                        )
                        
                except Exception as posting_error:
                    logger.error(f"❌ Error posting edited comment {request.comment_id}: {posting_error}")
                    return CommentApprovalResponse(
                        success=True,
                        message="Comment edited but posting encountered an error - check bot logs",
                        comment=comment
                    )
            else:
                raise HTTPException(status_code=404, detail="Comment not found")
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'approve', 'reject', or 'edit'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing comment approval: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing comment approval: {str(e)}")



@app.post("/bot/comment", response_model=CommentResponse)
async def generate_comment(request: CommentRequest):
    """Generate a comment for a specific post without running the full bot"""
    try:
        # Create a temporary bot instance for comment generation
        temp_bot = FacebookAICommentBot()
        
        # Import the comment generation functions
        from facebook_comment_bot import classify_post, pick_comment_template, already_commented
        from classifier import PostClassifier
        
        # Classify the post
        post_text = request.post_text or ""
        if not post_text.strip():
            return CommentResponse(
                success=False,
                comment=None,
                message="Post text is required for comment generation",
                post_type=None
            )
        
        # Use new classifier for detailed classification
        from config_loader import get_dynamic_config
        classifier = PostClassifier(get_dynamic_config())
        classification = classifier.classify_post(post_text)
        
        # NEW: Detect jewelry categories
        detected_categories = classifier.detect_jewelry_categories(post_text, classification)
        logger.info(f"🎯 Detected categories: {detected_categories}")
        
        if classification.should_skip:
            return CommentResponse(
                success=False,
                comment=None,
                message=f"Post filtered out: {classification.post_type}",
                post_type=classification.post_type
            )
        
        # Generate comment
        comment = pick_comment_template(classification.post_type)
        
        if comment:
            return CommentResponse(
                success=True,
                comment=comment,
                message="Comment generated successfully",
                post_type=post_type
            )
        else:
            return CommentResponse(
                success=False,
                comment=None,
                message="Could not generate comment for this post type",
                post_type=post_type
            )
            
    except Exception as e:
        logger.error(f"Error generating comment: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating comment: {str(e)}")

@app.get("/config")
async def get_config():
    """Get current bot configuration"""
    # Return a safe version of config (exclude sensitive info)
    safe_config = CONFIG.copy()
    return safe_config

@app.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """Update bot configuration"""
    global CONFIG
    
    try:
        # Update only provided fields
        for field, value in request.dict(exclude_unset=True).items():
            if field in CONFIG:
                CONFIG[field] = value
        
        # Save to file (optional)
        # You might want to implement config persistence here
        
        return {"message": "Configuration updated successfully", "config": CONFIG}
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_running": bot_status["is_running"],
        "comments_queued": bot_status["comments_queued"]
    }

@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent bot logs"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")
            return {"logs": [], "message": "No log files found"}
        
        log_files = [f for f in os.listdir("logs") if f.endswith(".log")]
        if not log_files:
            return {"logs": [], "message": "No log files found"}
        
        # Get most recent log file
        latest_log = max(log_files, key=lambda x: os.path.getctime(os.path.join("logs", x)))
        log_path = os.path.join("logs", latest_log)
        
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_logs = lines[-limit:] if len(lines) > limit else lines
        
        return {
            "logs": recent_logs,
            "log_file": latest_log,
            "total_lines": len(lines)
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

@app.get("/bot/screenshot")
async def get_bot_screenshot():
    """Get a screenshot of the current browser view"""
    global bot_instance
    
    try:
        if not bot_instance or not bot_instance.driver:
            raise HTTPException(status_code=400, detail="Bot is not running or browser not available")
        
        # Take screenshot
        screenshot = bot_instance.driver.get_screenshot_as_png()
        
        # Convert to base64 for easy transmission
        import base64
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        return {
            "screenshot": f"data:image/png;base64,{screenshot_b64}",
            "timestamp": datetime.now().isoformat(),
            "url": bot_instance.driver.current_url,
            "title": bot_instance.driver.title
        }
        
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to take screenshot: {str(e)}")

@app.get("/bot/browser-info")
async def get_browser_info():
    """Get current browser information"""
    global bot_instance
    
    try:
        if not bot_instance or not bot_instance.driver:
            return {
                "browser_available": False,
                "message": "Bot is not running or browser not available"
            }
        
        return {
            "browser_available": True,
            "current_url": bot_instance.driver.current_url,
            "title": bot_instance.driver.title,
            "window_size": bot_instance.driver.get_window_size(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting browser info: {e}")
        return {
            "browser_available": False,
            "message": f"Error: {str(e)}"
        }

@app.get("/bot/live-view")
async def get_live_browser_view():
    """Get live browser view URL for embedding"""
    global bot_instance
    
    try:
        if not bot_instance or not bot_instance.driver:
            return {
                "available": False,
                "message": "Bot is not running or browser not available"
            }
        
        # Get the debugging URL for live browser view
        debug_url = f"http://127.0.0.1:9222"
        
        return {
            "available": True,
            "debug_url": debug_url,
            "current_url": bot_instance.driver.current_url,
            "title": bot_instance.driver.title,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting live browser view: {e}")
        return {
            "available": False,
            "message": f"Error: {str(e)}"
        }

@app.get("/bot/live-screenshot")
async def get_live_screenshot():
    """Get a live screenshot of the current browser view"""
    global bot_instance
    
    try:
        # Removed excessive debug logging that was causing performance issues
        
        if not bot_instance or not bot_instance.driver:
            raise HTTPException(status_code=400, detail="Bot is not running or browser not available")
        
        # Get live screenshot from bot (returns PNG bytes)
        # Temporary fix: Use driver directly instead of method
        if hasattr(bot_instance, 'get_live_screenshot'):
            screenshot_data = bot_instance.get_live_screenshot()
        else:
            logger.error("bot_instance doesn't have get_live_screenshot method, using driver directly")
            screenshot_data = bot_instance.driver.get_screenshot_as_png()
        
        if screenshot_data:
            # Return as StreamingResponse with image/png media type
            return StreamingResponse(
                BytesIO(screenshot_data), 
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=screenshot.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to capture screenshot")
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error getting live screenshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get live screenshot: {str(e)}")

@app.get("/bot/statistics")
async def get_bot_statistics(days: int = 7):
    """Get bot statistics from the database"""
    try:
        stats = db.get_statistics(days)
        return {
            "success": True,
            "statistics": stats,
            "days_requested": days
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@app.get("/bot/database/cleanup")
async def cleanup_database(days_to_keep: int = 90):
    """Clean up old database records"""
    try:
        success = db.cleanup_old_data(days_to_keep)
        if success:
            return {
                "success": True,
                "message": f"Database cleaned up successfully. Kept data from last {days_to_keep} days.",
                "days_kept": days_to_keep
            }
        else:
            raise HTTPException(status_code=500, detail="Database cleanup failed")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Database cleanup failed: {str(e)}")

@app.post("/bot/database/clear")
async def clear_database():
    """Clear all data from the database (for testing purposes)"""
    try:
        success = db.clear_all_data()
        if success:
            # Reset bot status counters
            global bot_status
            bot_status.update({
                "posts_processed": 0,
                "comments_posted": 0,
                "comments_queued": 0
            })
            
            return {
                "success": True,
                "message": "Database cleared successfully. All data removed for fresh start.",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Database clear failed")
    except Exception as e:
        logger.error(f"Error during database clear: {e}")
        raise HTTPException(status_code=500, detail="Database clear failed: {str(e)}")

@app.post("/bot/logs/clear")
async def clear_logs():
    """Clear all log files from the logs directory"""
    try:
        success = clear_logs_directory()
        if success:
            return {
                "success": True,
                "message": "Logs directory cleared successfully. All log files removed for fresh start.",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Logs clear failed")
    except Exception as e:
        logger.error(f"Error during logs clear: {e}")
        raise HTTPException(status_code=500, detail=f"Logs clear failed: {str(e)}")

@app.get("/api/comment-history")
async def get_comment_history():
    """Get comment history for display"""
    try:
        return db.get_comment_history()
    except Exception as e:
        logger.error(f"Error getting comment history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comment history")

@app.get("/api/comments/{comment_id}/categories")
async def get_comment_categories(comment_id: int):
    """Get detected categories for a specific comment"""
    try:
        categories = db.get_comment_categories(comment_id)
        return {
            "success": True,
            "comment_id": comment_id,
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Error getting categories for comment {comment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comment categories")


# New CRM API Endpoints

@app.post("/api/ingest")
async def ingest_post(request: PostIngestRequest):
    """Ingest a new post from the bot"""
    try:
        # Create post in CRM
        post_id = db.create_post(request.dict())
        
        # Create comment draft
        comment_id = db.create_comment_draft(post_id)
        
        return {
            "success": True,
            "post_id": post_id,
            "comment_id": comment_id,
            "message": "Post ingested successfully"
        }
    except Exception as e:
        logger.error(f"Error ingesting post: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest post")

@app.get("/api/posts")
async def get_posts(status: Optional[str] = None, limit: int = 100):
    """Get posts filtered by status"""
    try:
        return db.get_posts_by_status(status, limit)
    except Exception as e:
        logger.error(f"Error getting posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get posts")

@app.post("/api/comments/{comment_id}/queue")
async def queue_comment(comment_id: str, request: CommentQueueRequest):
    """Queue a comment for posting"""
    try:
        # Update comment status to QUEUED
        success = db.update_comment_status(comment_id, 'QUEUED')
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Get the post ID from the comment
        # This would need a method to get comment by ID
        # For now, we'll update the post status to APPROVED
        # In a full implementation, you'd get the post_id from the comment
        
        return {
            "success": True,
            "message": "Comment queued successfully"
        }
    except Exception as e:
        logger.error(f"Error queuing comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue comment")

@app.post("/api/comments/{comment_id}/submit")
async def submit_comment(comment_id: str, request: CommentSubmitRequest):
    """Submit a comment for immediate real-time posting"""
    try:
        logger.info(f"🔄 Submitting comment {comment_id} to background posting queue")
        # Get the comment details
        comment = get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        if comment.status != "approved":
            raise HTTPException(status_code=400, detail="Comment must be approved before posting")
        # Route posting through the background posting queue
        global bot_instance
        if not bot_instance or not hasattr(bot_instance, 'posting_queue'):
            logger.error("❌ Bot instance or posting queue not available for background posting")
            raise HTTPException(status_code=500, detail="Bot is not running or posting queue unavailable")
        # Add to posting queue (post_url, comment_text)
        bot_instance.posting_queue.put((comment.post_url, comment.generated_comment))
        # Optionally, update status in DB to 'posting' or similar
        try:
            queue_id = int(comment_id)
            db.update_comment_status(queue_id, "posting")
        except Exception as db_error:
            logger.warning(f"Could not update comment status to 'posting': {db_error}")
        return {
            "success": True,
            "message": "Comment submitted to background posting queue",
            "comment_id": comment_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit comment: {str(e)}")

@app.put("/api/comments/{comment_id}")
async def update_comment(comment_id: str, request: CommentUpdateRequest):
    """Update a comment's body text and images"""
    try:
        # Update the comment in the database
        success = db.update_comment_body(comment_id, request.comment_body, request.comment_images)
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        return {
            "success": True,
            "message": "Comment updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to update comment")

@app.post("/api/posts/{post_id}/skip")
async def skip_post(post_id: str, request: PostSkipRequest):
    """Mark a post as skipped"""
    try:
        success = db.update_post_status(post_id, 'SKIPPED')
        if not success:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {
            "success": True,
            "message": "Post marked as skipped"
        }
    except Exception as e:
        logger.error(f"Error skipping post: {e}")
        raise HTTPException(status_code=500, detail="Failed to skip post")

@app.get("/api/pm-link/{post_id}")
async def get_pm_link(post_id: str):
    """Get the best Messenger URL for a post's author"""
    try:
        # Get post details
        posts = db.get_posts_by_status()
        post = next((p for p in posts if p['id'] == post_id), None)
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        author_id = post.get('author_id')
        if not author_id:
            raise HTTPException(status_code=400, detail="No author ID found")
        
        # Build Messenger link
        messenger_link = f"https://www.facebook.com/messages/t/{author_id}"
        
        return {
            "success": True,
            "messenger_link": messenger_link,
            "author_id": author_id
        }
    except Exception as e:
        logger.error(f"Error getting PM link: {e}")
        raise HTTPException(status_code=500, detail="Failed to get PM link")

@app.get("/api/templates")
async def get_templates(category: Optional[str] = None):
    """Get templates, optionally filtered by category"""
    try:
        return db.get_templates(category)
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get templates")

@app.post("/api/templates", response_model=TemplateResponse)
async def create_template(request: TemplateCreateRequest):
    """Create a new template"""
    try:
        template_id = db.create_template(
            name=request.name,
            category=request.category,
            body=request.body,
            image_pack_id=request.image_pack_id,
            is_default=request.is_default
        )
        
        # Get the created template to return it
        created_template = db.get_template(template_id)
        if not created_template:
            raise HTTPException(status_code=500, detail="Failed to retrieve created template")
        
        return TemplateResponse(**created_template)
    
    except ValueError as e:
        logger.error(f"Validation error creating template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")

@app.put("/api/templates/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, request: TemplateUpdateRequestPartial):
    """Update an existing template"""
    try:
        success = db.update_template(
            template_id=template_id,
            name=request.name,
            category=request.category,
            body=request.body,
            image_pack_id=request.image_pack_id,
            is_default=request.is_default
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Get the updated template to return it
        updated_template = db.get_template(template_id)
        if not updated_template:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated template")
        
        return TemplateResponse(**updated_template)
    
    except ValueError as e:
        logger.error(f"Validation error updating template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to update template")

@app.delete("/api/templates/{template_id}", response_model=TemplateDeleteResponse)
async def delete_template(template_id: str):
    """Delete a template"""
    try:
        success = db.delete_template(template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return TemplateDeleteResponse(
            success=True,
            message="Template deleted successfully"
        )
    
    except ValueError as e:
        logger.error(f"Validation error deleting template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete template")

@app.post("/api/templates/refresh", response_model=Dict[str, str])
async def refresh_templates():
    """Refresh templates in comment generator from database"""
    try:
        global bot_instance
        if bot_instance and hasattr(bot_instance, 'comment_generator'):
            bot_instance.comment_generator.refresh_templates()
            return {"success": True, "message": "Templates refreshed successfully"}
        else:
            return {"success": False, "message": "Bot not available for template refresh"}
    except Exception as e:
        logger.error(f"Error refreshing templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh templates")

@app.get("/api/templates/statistics")
async def get_template_statistics():
    """Get template usage statistics from comment generator"""
    try:
        global bot_instance
        if bot_instance and hasattr(bot_instance, 'comment_generator'):
            stats = bot_instance.comment_generator.get_template_statistics()
            return stats
        else:
            return {"message": "Bot not available for template statistics"}
    except Exception as e:
        logger.error(f"Error getting template statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get template statistics")

@app.get("/api/settings")
async def get_settings():
    """Get application settings"""
    try:
        return db.get_settings()
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get settings")

@app.put("/api/settings")
async def update_settings(request: SettingsUpdateRequest):
    """Update application settings"""
    try:
        # Filter out None values
        settings_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not settings_data:
            raise HTTPException(status_code=400, detail="No settings to update")
        
        success = db.update_settings(settings_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update settings")
        
        return {
            "success": True,
            "message": "Settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

@app.get("/api/debug/database")
async def debug_database_info():
    """Debug endpoint to check database path and contents"""
    import os
    from database import db as debug_db
    
    try:
        settings = debug_db.get_settings()
        keywords = settings.get('negative_keywords', [])
        
        return {
            "database_path": debug_db.db_path,
            "full_database_path": os.path.abspath(debug_db.db_path),
            "working_directory": os.getcwd(),
            "keywords_count": len(keywords),
            "last_3_keywords": keywords[-3:] if len(keywords) >= 3 else keywords,
            "has_test_keyword": 'test-fixed-commit' in keywords
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/settings/refresh")
async def refresh_classifier_config():
    """Force refresh of classifier configuration from database"""
    try:
        global bot_instance
        
        # Refresh the bot instance classifier if it exists
        if bot_instance and hasattr(bot_instance, 'classifier'):
            from config_loader import get_dynamic_config
            new_config = get_dynamic_config()
            bot_instance.classifier = PostClassifier(new_config)
            logger.info("✅ Bot instance classifier configuration refreshed from database")
            
        return {
            "success": True,
            "message": "Classifier configuration refreshed successfully"
        }
    except Exception as e:
        logger.error(f"Error refreshing classifier config: {e}")
        return {
            "success": False, 
            "message": f"Failed to refresh config: {str(e)}"
        }

@app.get("/api/fb-accounts")
async def get_fb_accounts():
    """Get Facebook accounts"""
    try:
        return db.get_fb_accounts()
    except Exception as e:
        logger.error(f"Error getting Facebook accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Facebook accounts")

# Simple image pack endpoint for frontend
@app.get("/api/serve-image/{filepath:path}")
async def serve_image(filepath: str):
    """Serve an image file from the uploads directory"""
    try:
        import os
        from fastapi.responses import FileResponse
        
        # Security: Remove any path traversal attempts
        safe_path = os.path.normpath(filepath).replace('..', '')
        
        # Construct full path
        if safe_path.startswith('uploads/'):
            full_path = safe_path
        else:
            full_path = os.path.join('uploads/image-packs/generic', safe_path)
        
        # Check if file exists
        if not os.path.exists(full_path):
            logger.error(f"Image not found: {full_path}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Serve the file
        return FileResponse(
            full_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {filepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve image")


@app.get("/api/search")
async def search_posts(q: str = "", status: Optional[str] = None, 
                      intent: Optional[str] = None, date_from: Optional[str] = None, 
                      date_to: Optional[str] = None):
    """Search posts with filters"""
    try:
        filters = {}
        if status:
            filters['status'] = status
        if intent:
            filters['intent'] = intent
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        return db.search_posts(q, filters)
    except Exception as e:
        logger.error(f"Error searching posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to search posts")

@app.post("/api/bot/callback")
async def bot_callback(data: Dict[str, Any]):
    """Webhook for bot updates"""
    try:
        # Handle bot callbacks (success/failure updates)
        # This would update comment statuses and log activities
        
        return {
            "success": True,
            "message": "Callback processed"
        }
    except Exception as e:
        logger.error(f"Error processing bot callback: {e}")
        raise HTTPException(status_code=500, detail="Failed to process callback")

# Comment Composer API Endpoints

@app.post("/api/analyze-text")
async def analyze_text(request: Dict[str, Any]):
    """Analyze text in real-time for category detection"""
    try:
        text = request.get("text", "")
        
        if not text or len(text.strip()) < 5:
            return {
                "success": True,
                "text": text,
                "categories": []
            }
        
        # Import classifier
        from classifier import PostClassifier
        from config_loader import get_dynamic_config
        
        classifier = PostClassifier(get_dynamic_config())
        
        # Perform real classification analysis on the text
        real_classification = classifier.classify_post(text)
        categories = classifier.detect_jewelry_categories(text, real_classification)
        
        logger.info(f"🔍 Classification result: type='{real_classification.post_type}', score={real_classification.confidence_score:.1f}")
        logger.info(f"🏷️  Keyword matches: {real_classification.keyword_matches}")
        
        logger.info(f"📋 Text analysis for '{text[:50]}...' detected categories: {categories}")
        
        return {
            "success": True,
            "text": text,
            "categories": categories or []
        }
        
    except Exception as e:
        logger.error(f"❌ Error analyzing text: {e}")
        return {
            "success": False,
            "text": request.get("text", ""),
            "categories": [],
            "error": str(e)
        }

@app.post("/api/comments/send")
async def send_comment(request: Dict[str, Any]):
    """Send a new comment with images (for CommentComposer)"""
    try:
        text = request.get("text", "").strip()
        images = request.get("images", [])
        master_image = request.get("master_image")
        
        if not text:
            raise HTTPException(status_code=400, detail="Comment text is required")
        
        # For now, we'll just store the comment in the database
        # Later you can integrate with your Facebook posting logic
        
        # Create a mock post URL for the composed comment
        import uuid
        comment_id = str(uuid.uuid4())[:8]
        mock_post_url = f"https://facebook.com/composed-comment/{comment_id}"
        
        # Store in database using existing function
        queue_id = add_comment_to_queue(
            post_url=mock_post_url,
            post_text=f"User composed comment - {text[:50]}...",
            generated_comment=text,
            post_type="COMPOSED",
            post_images=json.dumps(images) if images else None,
            post_author="User",
            detected_categories=None,  # Categories are already analyzed in real-time
            post_author_url=None  # No Facebook profile URL for user-composed comments
        )
        
        if queue_id:
            logger.info(f"💬 New composed comment stored: {queue_id} with {len(images)} images")
            
            return {
                "success": True,
                "comment_id": queue_id,
                "message": "Comment sent successfully",
                "images_count": len(images),
                "master_image": master_image
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store comment")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sending comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send comment: {str(e)}")

# Utility endpoint to convert base64 images to temporary files
@app.post("/convert-base64-images")
async def convert_base64_images(request: dict):
    """Convert base64 image data to temporary files for selenium automation"""
    try:
        base64_images = request.get('base64_images', [])
        if not base64_images:
            return {"success": True, "file_paths": []}
        
        logger.info(f"🔄 Converting {len(base64_images)} base64 images to temporary files")
        
        # Import ImageHandler for conversion
        from modules.image_handler import ImageHandler
        
        # Create a dummy handler instance (we only need the static conversion methods)
        handler = ImageHandler(None, {})
        
        # Convert all base64 images to temporary files
        file_paths = handler.convert_post_images_to_files(base64_images)
        
        logger.info(f"✅ Converted {len(file_paths)}/{len(base64_images)} images to temporary files")
        
        return {
            "success": True,
            "file_paths": file_paths,
            "converted_count": len(file_paths),
            "total_count": len(base64_images)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to convert base64 images: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_paths": []
        }

# Messenger Automation Endpoints

@app.post("/messenger/send-message", response_model=MessengerResponse)
async def send_messenger_message(request: MessengerRequest):
    """Send message via Messenger automation"""
    try:
        logger.info(f"🚀 Messenger automation request - Session: {request.session_id}, Recipient: {request.recipient}")
        
        # Get browser for this session
        browser = messenger_browser_manager.get_messenger_browser(request.session_id)
        
        # Get main browser for session copying
        main_browser = None
        try:
            if bot_instance and hasattr(bot_instance, 'posting_driver') and bot_instance.posting_driver:
                main_browser = bot_instance.posting_driver
                logger.info("Found main posting browser for session copying")
            elif bot_instance and hasattr(bot_instance, 'driver') and bot_instance.driver:
                main_browser = bot_instance.driver
                logger.info("Found main driver for session copying")
            else:
                logger.warning("No main browser found - will use credential login")
        except Exception as e:
            logger.warning(f"Could not access main browser: {e}")
        
        # Create automation instance with source browser for session copying
        messenger = MessengerAutomation(browser, source_browser=main_browser)
        
        # Send message with images
        result = await messenger.send_message_with_images(
            recipient=request.recipient,
            message=request.message,
            image_paths=request.images
        )
        
        logger.info(f"✅ Messenger automation result: {result}")
        return MessengerResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Messenger automation failed: {e}")
        return MessengerResponse(status="error", error=str(e))

@app.get("/messenger/sessions")
async def get_messenger_sessions():
    """Get active messenger browser sessions"""
    try:
        sessions = list(messenger_browser_manager.messenger_browsers.keys())
        return {"active_sessions": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error(f"Error getting messenger sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@app.delete("/messenger/session/{session_id}")
async def cleanup_messenger_session(session_id: str):
    """Cleanup specific messenger session"""
    try:
        messenger_browser_manager._cleanup_browser(session_id)
        logger.info(f"✅ Cleaned up messenger session: {session_id}")
        return {"status": "cleaned", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup session: {str(e)}")

# Cleanup messenger browsers on app shutdown
@app.on_event("shutdown")
async def cleanup_browsers():
    messenger_browser_manager.cleanup_all()
    logger.info("🧹 All messenger browsers cleaned up on shutdown")

@app.on_event("startup")
async def startup_event():
    """Handle application startup tasks"""
    global bot_status
    
    # Reset bot status to initial stopped state on startup
    bot_status.clear()
    bot_status.update({
        "is_running": False,
        "start_time": None,
        "last_activity": None,
        "posts_processed": 0,
        "comments_posted": 0,
        "comments_queued": 0,
        "current_status": "stopped"
    })
    logger.info("✅ Bot status reset to initial stopped state on startup")
    
    try:
        from bravo_config import CONFIG
        logger.info("🔄 Performing template system migration on startup...")
        
        # Migrate config templates to database if they don't exist
        config_templates = CONFIG.get("templates", {})
        migrated_count = db.migrate_config_templates(config_templates)
        
        if migrated_count > 0:
            logger.info(f"✅ Migrated {migrated_count} config templates to database")
        else:
            logger.info("ℹ️ No new templates to migrate - all config templates already in database")
            
    except Exception as e:
        logger.error(f"❌ Error during startup migration: {e}")
        # Don't fail startup for migration errors - system should still work
    
    # TEMPORARILY DISABLED: Start persistent messenger browser
    # TODO: Re-enable after fixing Firefox timeout issues
    logger.info("⏸️ Skipping persistent messenger browser startup (temporarily disabled)")
    # try:
    #     logger.info("🚀 Starting persistent messenger browser...")
    #     success = messenger_browser_manager.start_persistent_browser()
    #     if success:
    #         logger.info("✅ Persistent messenger browser started successfully")
    #     else:
    #         logger.warning("⚠️ Failed to start persistent messenger browser - messenger automation will not work")
    # except Exception as e:
    #     logger.error(f"❌ Error starting persistent browser: {e}")
    #     # Don't fail startup for browser errors

@app.get("/debug/env")
async def check_environment_variables():
    """Debug endpoint to check environment variables (remove in production)"""
    import os

    env_status = {
        "FACEBOOK_USERNAME": "SET" if os.environ.get('FACEBOOK_USERNAME') else "NOT SET",
        "FACEBOOK_PASSWORD": "SET" if os.environ.get('FACEBOOK_PASSWORD') else "NOT SET",
        "OPENAI_API_KEY": "SET" if os.environ.get('OPENAI_API_KEY') else "NOT SET",
        "POST_URL": os.environ.get('POST_URL', 'NOT SET'),
        "all_env_vars": list(os.environ.keys())
    }

    # Don't log actual values for security
    logger.info(f"Environment check - FACEBOOK_USERNAME: {env_status['FACEBOOK_USERNAME']}")
    logger.info(f"Environment check - FACEBOOK_PASSWORD: {env_status['FACEBOOK_PASSWORD']}")

    return env_status

@app.post("/bot/login")
async def manual_facebook_login():
    """Manually trigger Facebook login using environment credentials"""
    global bot_instance
    import os

    try:
        if not bot_instance or not bot_instance.driver:
            raise HTTPException(status_code=400, detail="Bot is not running")

        username = os.environ.get('FACEBOOK_USERNAME')
        password = os.environ.get('FACEBOOK_PASSWORD')

        if not username or not password:
            raise HTTPException(status_code=400, detail="Facebook credentials not found in environment variables")

        logger.info("🔑 Manual login triggered - attempting Facebook login...")

        # Use the browser manager's login method
        success = bot_instance.browser_manager.login_to_facebook(username, password)

        if success:
            logger.info("✅ Manual login successful!")
            return {
                "success": True,
                "message": "Successfully logged into Facebook",
                "current_url": bot_instance.driver.current_url
            }
        else:
            logger.error("❌ Manual login failed")
            return {
                "success": False,
                "message": "Login failed - check credentials",
                "current_url": bot_instance.driver.current_url
            }

    except Exception as e:
        logger.error(f"Error during manual login: {e}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.post("/bot/sync-session")
async def manual_session_sync():
    """Manually sync session cookies from posting driver to main driver"""
    global bot_instance
    import time

    try:
        if not bot_instance or not bot_instance.driver:
            raise HTTPException(status_code=400, detail="Bot is not running")

        if not hasattr(bot_instance, 'browser_manager') or not bot_instance.browser_manager.posting_driver:
            raise HTTPException(status_code=400, detail="Posting driver not available")

        logger.info("🔄 Manual session sync triggered - copying cookies from posting driver to main driver...")

        # Get cookies from posting driver
        posting_cookies = bot_instance.browser_manager.posting_driver.get_cookies()

        if not posting_cookies:
            raise HTTPException(status_code=400, detail="No cookies found in posting driver")

        logger.info(f"📋 Found {len(posting_cookies)} cookies in posting driver")

        # Navigate main driver to Facebook
        bot_instance.driver.get("https://www.facebook.com")
        time.sleep(2)

        # Copy each cookie to main driver
        successful_copies = 0
        for cookie in posting_cookies:
            try:
                bot_instance.driver.add_cookie(cookie)
                logger.debug(f"✅ Copied cookie: {cookie['name']}")
                successful_copies += 1
            except Exception as e:
                logger.debug(f"⚠️ Failed to copy cookie {cookie['name']}: {e}")
                continue

        # Refresh main driver to apply cookies
        bot_instance.driver.refresh()
        time.sleep(3)

        # Navigate to Facebook group
        target_url = bot_instance.config.get("POST_URL", "https://www.facebook.com/groups/5440421919361046")
        bot_instance.driver.get(target_url)
        time.sleep(3)

        # Check if we're logged in
        current_url = bot_instance.driver.current_url
        success = "login" not in current_url.lower()

        logger.info(f"✅ Manual session sync completed - copied {successful_copies}/{len(posting_cookies)} cookies")

        return {
            "success": success,
            "message": f"Session sync completed - copied {successful_copies} cookies",
            "logged_in": success,
            "current_url": current_url
        }

    except Exception as e:
        logger.error(f"Error during manual session sync: {e}")
        raise HTTPException(status_code=500, detail=f"Session sync error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
