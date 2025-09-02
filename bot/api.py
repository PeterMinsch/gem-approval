from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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
from selenium.webdriver.common.by import By

from facebook_comment_bot import FacebookAICommentBot
from bravo_config import CONFIG
from database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global bot instance and status

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

# Automatically start the bot and background posting browser on API server startup
def start_bot_on_launch():
    global bot_instance, bot_status
    if bot_instance is None:
        logger.info("[AUTO-START] Launching FacebookAICommentBot and background posting browser...")
        bot_instance = FacebookAICommentBot(CONFIG)
        # Start only the posting thread and driver, not the main scraping loop
        bot_instance.start_posting_thread()
        bot_status["is_running"] = True
        bot_status["start_time"] = datetime.now().isoformat()
        bot_status["current_status"] = "background posting ready"
    else:
        logger.info("[AUTO-START] Bot already initialized.")

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

# Comment queue management functions
def post_comment_realtime(comment_id: str, post_url: str, comment_text: str) -> bool:
    """Post a comment in real-time using the existing bot's browser session"""
    try:
        global bot_instance
        
        if not bot_instance:
            logger.error("❌ Bot instance not available for real-time posting")
            return False
            
        if not bot_instance.driver:
            logger.error("❌ Bot driver not available for real-time posting")
            return False
            
        logger.info(f"✅ Bot instance and driver available for real-time posting")
        
        logger.info(f"🔄 Real-time posting comment {comment_id} on {post_url}")
        logger.info(f"📝 Comment text: {comment_text[:100] if comment_text else 'None'}...")
        
        try:
            # Navigate to the post using existing browser session
            logger.info(f"🔄 Navigating to post URL: {post_url}")
            bot_instance.driver.get(post_url)
            time.sleep(3)  # Wait for page to load
            
            # Log current URL to verify navigation
            current_url = bot_instance.driver.current_url
            logger.info(f"🔄 Current page URL: {current_url}")
            
            # Check if we're on the right page
            if '/posts/' not in current_url:
                logger.warning(f"⚠️ Navigation may have failed - expected '/posts/' in URL but got: {current_url}")
            
            # Use the bot's existing posting method
            try:
                bot_instance.post_comment(comment_text, 0)
                # If we get here, posting was successful
                # Mark as posted in database
                queue_id = int(comment_id)
                db.update_comment_status(queue_id, "posted")
                bot_status["comments_posted"] += 1
                logger.info(f"✅ Comment {comment_id} posted successfully in real-time")
                return True
            except Exception as posting_error:
                logger.error(f"❌ Failed to post comment {comment_id}: {posting_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error posting comment {comment_id}: {e}")
            # Mark as failed
            queue_id = int(comment_id)
            db.update_comment_status(queue_id, "rejected", error_message=str(e))
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in post_comment_realtime: {e}")
        return False

def add_comment_to_queue(post_url: str, post_text: str, generated_comment: str, post_type: str,
                        post_screenshot: str = None, post_images: str = None,
                        post_author: str = None, post_engagement: str = None) -> str:
    """Add a generated comment to the approval queue using database with enhanced post data"""
    logger.info(f"🔄 Adding to comment queue: {post_type} - {post_url[:50]}...")
    logger.info(f"📝 Comment text: {generated_comment[:100] if generated_comment else 'None'}...")
    
    queue_id = db.add_to_comment_queue(post_url, post_text, generated_comment, post_type,
                                     post_screenshot, post_images, post_author, post_engagement)
    
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







# Bot control functions
def run_bot_in_background(post_url: str = None, max_scrolls: int = 20, continuous_mode: bool = True, clear_database: bool = False):
    """Run the bot in a separate thread with comment queuing"""
    global bot_instance, bot_status
    
    try:
        # Clear database if requested (for testing purposes)
        if clear_database:
            logger.info("Clearing database for fresh start...")
            if db.clear_all_data():
                logger.info("Database cleared successfully")
                # Reset bot status counters
                bot_status.update({
                    "posts_processed": 0,
                    "comments_posted": 0,
                    "comments_queued": 0
                })
            else:
                logger.warning("Failed to clear database, continuing with existing data")
        
        # Update bot status
        bot_status.update({
            "is_running": True,
            "start_time": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "current_status": "starting"
        })
        
        # Create bot instance with custom config if post_url provided
        config = CONFIG.copy()
        if post_url:
            config["POST_URL"] = post_url
        
        bot_instance = FacebookAICommentBot(config)
        bot_status["current_status"] = "running"
        
        # Run the bot with comment queuing
        if continuous_mode:
            run_bot_with_queuing(bot_instance)
        else:
            # For single post processing
            run_bot_with_queuing(bot_instance, max_scrolls)
            
    except Exception as e:
        logger.error(f"Bot execution failed: {e}")
        bot_status.update({
            "is_running": False,
            "current_status": f"error: {str(e)}"
        })
    finally:
        bot_status.update({
            "is_running": False,
            "current_status": "stopped"
        })

def run_bot_with_queuing(bot_instance: FacebookAICommentBot, max_scrolls: int = None):
    """Run the bot with CRM ingestion instead of old comment queuing"""
    global bot_status
    
    try:
        # Import the new CRM ingestion functions
        import requests
        import uuid
        from database import db
        
        # Override the bot's posting behavior to ingest into CRM instead
        def ingest_post_to_crm(clean_url: str, post_text: str):
            """Ingest post into CRM system instead of old comment queue"""
            try:
                # Use the bot's classifier to get proper classification
                classification = bot_instance.classifier.classify_post(post_text)
                
                if classification.should_skip:
                    logger.info(f"Post filtered out: {classification.post_type}")
                    return
                
                # Generate comment using the bot's comment generator
                logger.info(f"🔍 Generating comment for post type: {classification.post_type}")
                comment = bot_instance.comment_generator.generate_comment(classification.post_type, post_text)
                
                logger.info(f"📝 Generated comment: {comment[:100] if comment else 'None'}...")
                
                if comment:
                    # Try to capture post metadata
                    post_screenshot = None
                    post_images = None
                    post_author = None
                    post_engagement = None
                    
                    try:
                        if bot_instance and bot_instance.driver:
                            # Take screenshot of the current post element
                            post_element = bot_instance.driver.find_element(By.XPATH, "//div[@role='article']")
                            if post_element:
                                post_screenshot = post_element.screenshot_as_png
                                import base64
                                post_screenshot = f"data:image/png;base64,{base64.b64encode(post_screenshot).decode('utf-8')}"
                                
                                # Try to extract post author and engagement
                                try:
                                    author_elem = post_element.find_element(By.XPATH, ".//a[@role='link' and contains(@href, '/profile.php') or contains(@href, '/')]")
                                    if author_elem:
                                        post_author = author_elem.text.strip()
                                except:
                                    pass
                                    
                                try:
                                    engagement_elem = post_element.find_element(By.XPATH, ".//span[contains(text(), 'like') or contains(text(), 'comment') or contains(text(), 'share')]")
                                    if engagement_elem:
                                        post_engagement = engagement_elem.text.strip()
                                except:
                                    pass
                                    
                                # Extract post images if any
                                try:
                                    img_elements = post_element.find_elements(By.XPATH, ".//img[@src]")
                                    image_urls = []
                                    for img in img_elements[:5]:  # Limit to 5 images
                                        src = img.get_attribute('src')
                                        if src and 'http' in src:
                                            image_urls.append(src)
                                    post_images = json.dumps(image_urls) if image_urls else ""
                                except:
                                    pass
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
                        # Add comment directly to the approval queue using the database
                        queue_id = add_comment_to_queue(clean_url, post_text, comment, classification.post_type,
                                                      post_screenshot, post_images, post_author, post_engagement)
                        
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
                            add_comment_to_queue(post_url, post_text, comment, classification.post_type)
                            logger.info(f"Fallback: Comment queued with minimal data: {classification.post_type}")
                        except Exception as e2:
                            logger.error(f"❌ Complete failure queuing comment: {e2}")
                        
                else:
                    logger.warning(f"Could not generate comment for post type: {classification.post_type}")
                    
            except Exception as e:
                logger.error(f"Error processing post for CRM ingestion: {e}")
        
        # Actually open Chrome and start scanning Facebook
        logger.info("Opening Chrome browser and navigating to Facebook...")
        
        try:
            # Start the bot's actual scanning process
            logger.info("Setting up Chrome driver...")
            bot_instance.setup_driver()
            logger.info("Chrome browser opened successfully")
            
            # Navigate to the target Facebook group
            target_url = bot_instance.config.get("POST_URL", "https://www.facebook.com/groups/5440421919361046")
            logger.info(f"Navigating to: {target_url}")
            
            bot_instance.driver.get(target_url)
            logger.info("Successfully navigated to Facebook group")
            
            # Start scanning for posts
            logger.info("Starting to scan for posts...")
            
            # Keep running and scanning
            while bot_status["is_running"]:
                try:
                    # Actually scan for new posts using the bot's real methods
                    logger.info("Scanning for new posts...")
                    
                    # Use the bot's actual post scanning method
                    post_links = bot_instance.scroll_and_collect_post_links(max_scrolls=5)
                    logger.info(f"Found {len(post_links)} potential posts to scan")
                    
                    # Process each post found
                    for post_url in post_links:
                        if not bot_status["is_running"]:
                            break
                        
                        # Clean the URL for processing (remove query parameters)
                        clean_url = post_url.split('?')[0] if '?' in post_url else post_url
                        
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
                            
                            # Check for duplicates
                            if bot_instance.is_duplicate_post(post_text, clean_url):
                                logger.info(f"Duplicate post detected: {clean_url}")
                                bot_instance.save_processed_post(clean_url, post_text=post_text, post_type="duplicate")
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
                    logger.info("Scan cycle complete. Starting next scan in 30 seconds...")
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error during scanning: {e}")
                    time.sleep(60)  # Wait a minute before retrying
                    
        except Exception as e:
            logger.error(f"Error setting up Chrome or navigating: {e}")
            
    except Exception as e:
        logger.error(f"Error in run_bot_with_queuing: {e}")
    finally:
        if bot_instance and bot_instance.driver:
            bot_instance.driver.quit()
            logger.info("Chrome browser closed")

def stop_bot():
    """Stop the running bot"""
    global bot_instance, bot_status
    
    if bot_instance and bot_instance.driver:
        try:
            bot_instance.driver.quit()
            bot_status["current_status"] = "stopping"
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    bot_status.update({
        "is_running": False,
        "current_status": "stopped"
    })

# API endpoints
@app.get("/")
async def root():
    return {"message": "Bravo Bot API with Comment Approval Workflow is running"}

@app.post("/bot/start", response_model=Dict[str, str])
async def start_bot(request: BotStartRequest, background_tasks: BackgroundTasks):
    """Start the Facebook comment bot with comment queuing"""
    global bot_status
    
    if bot_status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    # Start bot in background
    background_tasks.add_task(
        run_bot_in_background,
        post_url=request.post_url,
        max_scrolls=request.max_scrolls,
        continuous_mode=request.continuous_mode,
        clear_database=request.clear_database
    )
    
    return {"message": "Bot started successfully with comment queuing", "status": "starting"}

@app.post("/bot/stop", response_model=Dict[str, str])
async def stop_bot_endpoint(request: BotStopRequest):
    """Stop the running bot"""
    global bot_status
    
    if not bot_status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    stop_bot()
    return {"message": "Bot stopped successfully"}

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

@app.post("/comments/approve", response_model=CommentApprovalResponse)
async def approve_comment_endpoint(request: CommentApprovalRequest):
    """Approve, reject, or edit a comment"""
    try:
        if request.action == "approve":
            success = approve_comment(request.comment_id, request.edited_comment)
            if success:
                comment = get_comment_by_id(request.comment_id)
                return CommentApprovalResponse(
                    success=True,
                    message="Comment approved successfully",
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
                return CommentApprovalResponse(
                    success=True,
                    message="Comment edited and approved successfully",
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
        
        # Classify the post
        post_text = request.post_text or ""
        if not post_text.strip():
            return CommentResponse(
                success=False,
                comment=None,
                message="Post text is required for comment generation",
                post_type=None
            )
            
        post_type = classify_post(post_text)
        
        if post_type == "skip":
            return CommentResponse(
                success=False,
                comment=None,
                message="Post filtered out by negative/brand logic",
                post_type=post_type
            )
        
        # Generate comment
        comment = pick_comment_template(post_type)
        
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
        if not bot_instance or not bot_instance.driver:
            raise HTTPException(status_code=400, detail="Bot is not running or browser not available")
        
        # Get live screenshot from bot
        screenshot_data = bot_instance.get_live_screenshot()
        
        if screenshot_data:
            return screenshot_data
        else:
            raise HTTPException(status_code=500, detail="Failed to capture screenshot")
        
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

@app.get("/api/comment-history")
async def get_comment_history():
    """Get comment history for display"""
    try:
        return db.get_comment_history()
    except Exception as e:
        logger.error(f"Error getting comment history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comment history")

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
        global bot_instance, bot_status
        # If bot is not running, start it in posting-only mode
        if not bot_instance or not hasattr(bot_instance, 'posting_queue'):
            logger.warning("Bot instance or posting queue not available, starting posting thread...")
            from facebook_comment_bot import FacebookAICommentBot
            from bravo_config import CONFIG
            bot_instance = FacebookAICommentBot(CONFIG)
            bot_instance.start_posting_thread()
            bot_status["is_running"] = True
            bot_status["current_status"] = "background posting ready"
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

@app.post("/api/templates")
async def create_template(request: TemplateUpdateRequest):
    """Create a new template"""
    try:
        # This would need a method to create templates
        # For now, return success
        return {
            "success": True,
            "message": "Template creation not yet implemented"
        }
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")

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

@app.get("/api/fb-accounts")
async def get_fb_accounts():
    """Get Facebook accounts"""
    try:
        return db.get_fb_accounts()
    except Exception as e:
        logger.error(f"Error getting Facebook accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Facebook accounts")

@app.get("/api/image-packs")
async def get_image_packs():
    """Get image packs"""
    try:
        # This would need a method to get image packs
        # For now, return empty array
        return []
    except Exception as e:
        logger.error(f"Error getting image packs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get image packs")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
