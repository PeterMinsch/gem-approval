import threading
import queue
import time
import os
print("RUNNING FILE:", os.path.abspath(__file__))
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import os
import random
import time
import threading
import queue
import time
import os
print("RUNNING FILE:", os.path.abspath(__file__))
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import os
import random
import time
import logging
from datetime import datetime
import re
import json
import uuid
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bravo_config import CONFIG
from database import db
from comment_generator import CommentGenerator as ExternalCommentGenerator

# Enhanced configuration for weighted scoring
KEYWORD_WEIGHTS = {
    "negative": -100,      # Strong negative weight
    "brand_blacklist": -50, # Brand blacklist weight
    "service": 8,          # Service keyword weight (reduced from 10)
    "iso": 6,              # ISO keyword weight (reduced from 8)
    "general": 3,          # General keyword weight (reduced from 5)
    "modifier": 15,        # Allowed brand modifier weight
}
# Post type thresholds
POST_TYPE_THRESHOLDS = {
    "service": 15,         # Lowered from 25 - more posts will qualify as service
    "iso": 10,             # Lowered from 18 - more posts will qualify as ISO
    "general": 8,          # Lower threshold for general (positive comments)
    "skip": -25,           # Maximum score before skipping
}

@dataclass
class PostClassification:
    """Data class for post classification results"""
    post_type: str
    confidence_score: float
    keyword_matches: Dict[str, List[str]]
    reasoning: List[str]
    should_skip: bool

@dataclass
class CommentTemplate:
    """Data class for comment templates with variation options"""
    text: str
    variations: List[str]
    use_count: int = 0

class PostClassifier:
    """Enhanced post classification system with weighted scoring"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.processed_posts: Set[str] = set()
        
    def calculate_keyword_score(self, text: str, keyword_list: List[str], weight: float) -> Tuple[float, List[str]]:
        """Calculate weighted score for a keyword category and return matches"""
        text_lower = text.lower()
        matches = []
        score = 0.0
        
        for keyword in keyword_list:
            if keyword.lower() in text_lower:
                matches.append(keyword)
                score += weight
                
        return score, matches
    
    def check_brand_blacklist(self, text: str) -> Tuple[float, List[str], List[str]]:
        """Check for blacklisted brands and allowed modifiers"""
        brand_score, brand_matches = self.calculate_keyword_score(
            text, self.config["brand_blacklist"], KEYWORD_WEIGHTS["brand_blacklist"]
        )
        
        modifier_score, modifier_matches = self.calculate_keyword_score(
            text, self.config["allowed_brand_modifiers"], KEYWORD_WEIGHTS["modifier"]
        )
        
        # If brands found but no modifiers, apply strong penalty
        if brand_matches and not modifier_matches:
            brand_score = -100  # Override to ensure skip
            
        return brand_score, brand_matches, modifier_matches
    
    def classify_post(self, text: str) -> PostClassification:
        """Enhanced post classification with weighted scoring and priority logic"""
        logger.info(f"Classifying post text: {text[:100]}...")
        
        # Initialize scoring
        total_score = 0.0
        keyword_matches = {}
        reasoning = []
        
        # Check negative keywords (immediate skip if found)
        neg_score, neg_matches = self.calculate_keyword_score(
            text, self.config["negative_keywords"], KEYWORD_WEIGHTS["negative"]
        )
        if neg_matches:
            keyword_matches["negative"] = neg_matches
            reasoning.append(f"Negative keywords found: {neg_matches}")
            return PostClassification(
                post_type="skip",
                confidence_score=abs(neg_score),
                keyword_matches=keyword_matches,
                reasoning=reasoning,
                should_skip=True
            )
        
        # Check brand blacklist and modifiers
        brand_score, brand_matches, modifier_matches = self.check_brand_blacklist(text)
        total_score += brand_score
        
        if brand_matches:
            keyword_matches["brand_blacklist"] = brand_matches
            if modifier_matches:
                keyword_matches["modifiers"] = modifier_matches
                reasoning.append(f"Blacklisted brands found but allowed modifiers present: {modifier_matches}")
            else:
                reasoning.append(f"Blacklisted brands found without modifiers: {brand_matches}")
                return PostClassification(
                    post_type="skip",
                    confidence_score=abs(brand_score),
                    keyword_matches=keyword_matches,
                    reasoning=reasoning,
                    should_skip=True
                )
        
        # Calculate scores for each category
        service_score, service_matches = self.calculate_keyword_score(
            text, self.config["service_keywords"], KEYWORD_WEIGHTS["service"]
        )
        iso_score, iso_matches = self.calculate_keyword_score(
            text, self.config["iso_keywords"], KEYWORD_WEIGHTS["iso"]
        )
        general_score, general_matches = self.calculate_keyword_score(
            text, self.config["general_keywords"], KEYWORD_WEIGHTS["general"]
        )
        
        # Store keyword matches
        if service_matches:
            keyword_matches["service"] = service_matches
            reasoning.append(f"Service keywords found: {service_matches[:5]}...")
        if iso_matches:
            keyword_matches["iso"] = iso_matches
            reasoning.append(f"ISO keywords found: {iso_matches[:5]}...")
        if general_matches:
            keyword_matches["general"] = general_matches
            reasoning.append(f"General keywords found: {general_matches[:5]}...")
        
        # Priority-based classification (most specific wins)
        post_type = "skip"
        
        # Check for ISO classification first if it starts with ISO indicators
        iso_indicators = ["iso", "in stock", "who makes", "who manufactures", "supplier"]
        starts_with_iso = any(text.lower().startswith(indicator) for indicator in iso_indicators)
        
        # Get thresholds from config (fallback to hardcoded if not available)
        service_threshold = self.config.get("post_type_thresholds", {}).get("service", POST_TYPE_THRESHOLDS["service"])
        iso_threshold = self.config.get("post_type_thresholds", {}).get("iso", POST_TYPE_THRESHOLDS["iso"])
        general_threshold = self.config.get("post_type_thresholds", {}).get("general", POST_TYPE_THRESHOLDS["general"])
        
        if starts_with_iso and iso_score >= iso_threshold:
            post_type = "iso"
            total_score = iso_score
        # Check for service classification (most specific)
        elif service_score >= service_threshold:
            # Classify as service if it meets the threshold
            post_type = "service"
            total_score = service_score
        # Check if it's more of an ISO request
        elif iso_score >= iso_threshold:
            post_type = "iso"
            total_score = iso_score
        elif general_score >= general_threshold:
            post_type = "general"
            total_score = general_score
        elif iso_score >= iso_threshold:
            post_type = "iso"
            total_score = iso_score
        elif general_score >= general_threshold:
            post_type = "general"
            total_score = general_score
        
        # Log classification details
        logger.info(f"Classification score: {total_score}")
        logger.info(f"Post type: {post_type}")
        logger.info(f"Reasoning: {'; '.join(reasoning)}")
        
        return PostClassification(
            post_type=post_type,
            confidence_score=total_score,
            keyword_matches=keyword_matches,
            reasoning=reasoning,
            should_skip=(post_type == "skip" or total_score <= self.config.get("post_type_thresholds", {}).get("skip", POST_TYPE_THRESHOLDS["skip"]))
        )

class CommentGenerator:
    """Enhanced comment generation system with OpenAI LLM and template fallback"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.template_usage = {}  # Track template usage for variation
        self._initialize_templates()
        
        # Initialize OpenAI client if enabled
        self.openai_client = None
        if self.config.get("openai", {}).get("enabled", False):
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    openai.api_key = api_key
                    self.openai_client = openai
                    logger.info("✅ OpenAI client initialized successfully")
                else:
                    logger.warning("⚠️ OPENAI_API_KEY not found in environment variables")
            except ImportError:
                logger.warning("⚠️ OpenAI package not installed. Install with: pip install openai")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI client: {e}")
    
    def _initialize_templates(self):
        """Initialize comment templates with variation tracking"""
        logger.info("🔧 Initializing comment templates...")
        for post_type, templates in self.config["templates"].items():
            logger.info(f"📝 Loading {len(templates)} templates for post type: {post_type}")
            self.template_usage[post_type] = []
            for i, template in enumerate(templates):
                logger.debug(f"  Template {i+1}: {template[:50]}...")
                self.template_usage[post_type].append(CommentTemplate(
                    text=template,
                    variations=self._generate_variations(template),
                    use_count=0
                ))
        logger.info(f"✅ Loaded templates for {len(self.template_usage)} post types")
    
    def _generate_variations(self, template: str) -> List[str]:
        """Generate slight variations of a template to avoid repetition"""
        variations = []
        
        # Variation 1: Change punctuation
        if "!" in template:
            variations.append(template.replace("!", "."))
        if "." in template:
            variations.append(template.replace(".", "!"))
        
        # Variation 2: Change connector words
        if " — " in template:
            variations.append(template.replace(" — ", " • "))
        if " • " in template:
            variations.append(template.replace(" • ", " — "))
        
        # Variation 3: Slight word order changes
        words = template.split()
        if len(words) > 10:
            # Swap adjacent words occasionally
            for i in range(len(words) - 1):
                if random.random() < 0.3:  # 30% chance
                    words[i], words[i+1] = words[i+1], words[i]
            variations.append(" ".join(words))
        
        return variations
    
    def _generate_llm_comment(self, post_type: str, post_text: str = "", author_name: str = "") -> str:
        """Generate comment using OpenAI LLM with first name personalization"""
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available")
                return None
            
            # Get the appropriate prompt for the post type
            prompt = self.config.get("llm_prompts", {}).get(post_type)
            if not prompt:
                logger.warning(f"No LLM prompt found for post type: {post_type}")
                return None
            
            # Extract first name for personalization
            first_name = self.extract_first_name(author_name) if author_name else ""
            
            # Add post context if available
            if post_text:
                prompt += f"\n\nPost content: {post_text[:200]}..."
            
            # Add author name context
            if first_name:
                prompt += f"\n\nAuthor's first name: {first_name}"
                # Note: Using {{author_name}} placeholder format - will be handled by personalize_comment method
            else:
                prompt += f"\n\nAuthor's first name: not available"
                # Note: Using {{author_name}} placeholder format - will be handled by personalize_comment method
            
            # Get OpenAI configuration
            openai_config = self.config.get("openai", {})
            
            # Make API call using NEW v1.x+ syntax
            response = self.openai_client.chat.completions.create(
                model=openai_config.get("model", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": prompt}
                ],
                max_tokens=openai_config.get("max_tokens", 150),
                temperature=openai_config.get("temperature", 0.7)
            )
            
            comment = response.choices[0].message.content.strip()
            logger.info(f"🤖 LLM generated comment: {comment[:100]}...")
            return comment
            
        except Exception as e:
            logger.error(f"❌ LLM comment generation failed: {e}")
            return None
        
    def select_template(self, post_type: str) -> str:
        """Select a template with usage tracking and variation"""
        if post_type not in self.template_usage:
            logger.warning(f"No templates found for post type: {post_type}")
            return None
        
        templates = self.template_usage[post_type]
        
        # Find templates with lowest usage
        min_usage = min(template.use_count for template in templates)
        candidates = [t for t in templates if t.use_count == min_usage]
        
        # Select random candidate
        selected = random.choice(candidates)
        selected.use_count += 1
        
        # Decide whether to use variation or original
        if selected.variations and random.random() < 0.4:  # 40% chance for variation
            variation = random.choice(selected.variations)
            logger.info(f"Using template variation for {post_type}")
            return variation
        else:
            logger.info(f"Using original template for {post_type}")
            return selected.text
    
    def extract_first_name(self, full_name: str) -> str:
        """Extract and validate first name from full name"""
        logger.info(f"🔍 Extracting first name from: '{full_name}' (type: {type(full_name)})")
        
        if not full_name or not isinstance(full_name, str):
            logger.warning(f"❌ Invalid full_name: {full_name} (type: {type(full_name)})")
            return ""
        
        # Clean up the name
        full_name = full_name.strip()
        
        # Skip if it contains UI elements or suspicious content
        skip_indicators = [
            'sponsored', 'admin', 'moderator', 'page', 'business', 'group',
            'like', 'comment', 'share', 'follow', 'unfollow', 'report',
            'see more', 'hide', 'block', 'message', 'add friend'
        ]
        
        if any(indicator in full_name.lower() for indicator in skip_indicators):
            logger.info(f"❌ Skipping name that contains UI elements: {full_name}")
            return ""
        
        # Extract first name (skip common titles)
        name_parts = full_name.split()
        logger.info(f"🔍 Name parts: {name_parts}")
        
        if not name_parts:
            logger.warning(f"❌ No name parts found after splitting: {full_name}")
            return ""
        
        # Skip common titles and prefixes
        titles_to_skip = ['dr.', 'dr', 'mr.', 'mr', 'mrs.', 'mrs', 'ms.', 'ms', 'prof.', 'prof', 'rev.', 'rev']
        
        first_name = name_parts[0]
        # If first part is a title and we have more parts, use the second part
        if len(name_parts) > 1 and first_name.lower().rstrip('.') in titles_to_skip:
            first_name = name_parts[1]
            logger.info(f"🔍 Skipped title '{name_parts[0]}', using: '{first_name}'")
        
        logger.info(f"🔍 First name part: '{first_name}'")
        
        # Validate first name
        if len(first_name) < 2 or len(first_name) > 20:
            logger.info(f"❌ First name rejected (length): {first_name}")
            return ""
        
        # Must contain only letters and common name characters
        if not all(c.isalpha() or c in "'-." for c in first_name):
            logger.info(f"❌ First name rejected (invalid characters): {first_name}")
            return ""
        
        # Clean up the first name (remove trailing punctuation)
        first_name = first_name.strip("'-.")
        logger.info(f"🔍 Cleaned first name: '{first_name}'")
        
        # Check for common non-name words that might get picked up
        non_names = ['the', 'and', 'or', 'but', 'for', 'with', 'from', 'to', 'at', 'by']
        if first_name.lower() in non_names:
            logger.info(f"❌ First name rejected (common word): {first_name}")
            return ""
        
        logger.info(f"✅ Extracted first name: '{first_name}' from '{full_name}'")
        return first_name

    def personalize_comment(self, template: str, author_name: str = "") -> str:
        """Add personalized greeting to comment template"""
        logger.info(f"🔧 Personalizing comment template: '{template[:50]}...'")
        logger.info(f"🔧 Author name provided: '{author_name}'")
        
        first_name = self.extract_first_name(author_name) if author_name else ""
        logger.info(f"🔧 Extracted first name: '{first_name}'")
        
        if first_name:
            # Replace the placeholder with the actual first name
            personalized_comment = template.replace("{{author_name}}", first_name)
            logger.info(f"✅ Personalized comment for '{first_name}': {personalized_comment[:50]}...")
            return personalized_comment
        else:
            # Use generic greeting - replace placeholder with "there"
            generic_comment = template.replace("{{author_name}}", "there")
            logger.info(f"ℹ️ Using generic greeting: {generic_comment[:50]}...")
            return generic_comment

    def generate_comment(self, post_type: str, post_text: str = "", author_name: str = "") -> str:
        """Generate a comment for the given post type using LLM or templates"""
        logger.info(f"Generating comment for post type: {post_type}")
        logger.info(f"Author name provided: '{author_name}'")
        
        # Try LLM first if enabled
        if self.openai_client and self.config.get("openai", {}).get("enabled", False):
            logger.info("🤖 Attempting LLM comment generation...")
            llm_comment = self._generate_llm_comment(post_type, post_text, author_name)
            if llm_comment:
                logger.info(f"🤖 LLM generated raw comment: {llm_comment[:100]}...")
                # Personalize LLM comments using the same method as templates
                personalized_llm_comment = self.personalize_comment(llm_comment, author_name)
                logger.info(f"🤖 LLM comment after personalization: {personalized_llm_comment[:100]}...")
                return personalized_llm_comment
            else:
                logger.warning("🤖 LLM comment generation failed, falling back to templates")
        
        # Fallback to templates if LLM fails or is disabled
        if self.config.get("openai", {}).get("fallback_to_templates", True):
            logger.info("🔄 Falling back to template-based comment generation")
            
            comment = self.select_template(post_type)
            if comment:
                logger.info(f"📝 Raw template selected: {comment[:100]}...")
                
                # Personalize the template with the author's first name
                personalized_comment = self.personalize_comment(comment, author_name)
                
                logger.info(f"📝 Final personalized comment: {personalized_comment[:100]}...")
                return personalized_comment
            else:
                logger.warning(f"❌ No template found for post type: {post_type}")
        
        logger.warning(f"No comment generated for post type: {post_type}")
        return None

class DuplicateDetector:
    """Enhanced duplicate detection system"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.commented_posts: Set[str] = set()
    
    def already_commented(self, existing_comments: List[str]) -> bool:
        """Check if Bravo already commented on this post"""
        for comment in existing_comments:
            comment_lower = comment.lower()
            if any(indicator in comment_lower for indicator in [
                "bravo creations",
                self.config["phone"],
                "bravocreations.com",
                "welcome.bravocreations.com"
            ]):
                return True
        return False
    
    def is_duplicate_post(self, post_text: str, post_url: str) -> bool:
        """Check if this is a duplicate post"""
        # Check if URL already processed
        if post_url in self.commented_posts:
            return True
        
        # Check for similar post text (basic similarity)
        post_text_normalized = re.sub(r'\s+', ' ', post_text.lower().strip())
        return False  # Could implement more sophisticated similarity checking

def setup_logger():
    from logging.handlers import RotatingFileHandler
    
    # Ensure the logs directory exists in the project root
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Use a consistent log filename for rotation
    log_filename = os.path.join(logs_dir, 'facebook_comment_bot.log')
    
    # Create rotating file handler
    # maxBytes=50MB, backupCount=5 (keeps 5 old versions)
    rotating_handler = RotatingFileHandler(
        log_filename, 
        maxBytes=50*1024*1024,  # 50 MB per file
        backupCount=5,          # Keep 5 old versions (total ~250MB max)
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
        level=logging.DEBUG,
        handlers=[rotating_handler, console_handler]
    )
    
    logger_instance = logging.getLogger(__name__)
    logger_instance.info(f"Logging to: {log_filename}")
    logger_instance.info(f"Log rotation: 50MB max per file, 5 backup files kept")
    return logger_instance

logger = setup_logger()

# Configure Selenium logging to prevent base64 screenshot data from being logged
selenium_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
selenium_logger.setLevel(logging.WARNING)  # Only show warnings and errors, not debug info

# Also suppress urllib3 debug logs which Selenium uses
urllib3_logger = logging.getLogger('urllib3.connectionpool')
urllib3_logger.setLevel(logging.WARNING)

# Legacy function wrappers for backward compatibility
def classify_post(text: str) -> str:
    """Legacy wrapper for backward compatibility"""
    classifier = PostClassifier(CONFIG)
    result = classifier.classify_post(text)
    return result.post_type

def pick_comment_template(post_type: str, author_name: str = "") -> str:
    """Legacy wrapper for backward compatibility"""
    generator = ExternalCommentGenerator(CONFIG, database=db)
    return generator.generate_comment(post_type, "", author_name)

def already_commented(existing_comments: List[str]) -> bool:
    """Legacy wrapper for backward compatibility"""
    detector = DuplicateDetector(CONFIG)
    return detector.already_commented(existing_comments)

def with_driver_recovery(func):
    """Decorator to automatically recover from driver connection issues"""
    def wrapper(self, *args, **kwargs):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                is_connection_error = any(keyword in error_msg for keyword in [
                    "connection refused", "max retries exceeded", "failed to establish",
                    "connection broken", "session not created", "chrome not reachable"
                ])
                
                if is_connection_error and attempt < max_attempts - 1:
                    logger.warning(f"Connection error in {func.__name__}, reconnecting (attempt {attempt + 1}/{max_attempts})...")
                    try:
                        self.reconnect_driver_if_needed()
                        continue
                    except Exception as reconnect_error:
                        logger.error(f"Failed to reconnect driver: {reconnect_error}")
                        
                raise  # Re-raise the original exception
        return None
    return wrapper

class FacebookAICommentBot:
    def extract_first_image_url(self):
        """Extract the first real image URL from the current Facebook post."""
        try:
            post_element = self.driver.find_element(By.XPATH, "//div[@role='article']")
            img_elements = post_element.find_elements(By.TAG_NAME, "img")
            for img in img_elements:
                src = img.get_attribute("src")
                # Skip emojis, SVGs, icons, and profile images
                if not src:
                    continue
                if any(x in src for x in ["emoji", ".svg", "profile", "static"]):
                    continue
                # Facebook CDN images are usually real post images
                if src.startswith("https://scontent") and src.endswith(".jpg"):
                    return src
                # Accept other http(s) images that aren't SVGs or emojis
                if src.startswith("http") and not any(x in src for x in ["emoji", ".svg", "profile", "static"]):
                    return src
            return None
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None
    def setup_posting_driver(self):
        """Set up a second browser for posting comments (non-headless for Facebook compatibility)."""
        try:
            # Clean up any existing driver first
            if hasattr(self, 'posting_driver') and self.posting_driver:
                try:
                    self.posting_driver.quit()
                except:
                    pass
                self.posting_driver = None
                
            # Clean up any existing temp directory
            if hasattr(self, '_temp_chrome_dir') and self._temp_chrome_dir:
                try:
                    import shutil
                    if os.path.exists(self._temp_chrome_dir):
                        shutil.rmtree(self._temp_chrome_dir)
                        logger.debug(f"[POSTING THREAD] Cleaned up temp directory: {self._temp_chrome_dir}")
                except Exception as e:
                    logger.debug(f"[POSTING THREAD] Failed to cleanup temp directory: {e}")
                self._temp_chrome_dir = None
            
            logger.info("[POSTING THREAD] Setting up Chrome driver for posting...")
            
            # Set environment for Chrome stability
            os.environ['CHROME_LOG_FILE'] = 'nul'
            
            chrome_options = Options()
            # Use same options as main browser but in a minimized window
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # REMOVED --headless=new as Facebook blocks headless browsers
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--start-minimized")  # Start minimized instead of headless
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            # Suppress Chrome log noise
            chrome_options.add_argument("--log-level=3")  # Only fatal errors
            chrome_options.add_argument("--silent")
            # Use a completely separate profile directory for the posting browser
            # This avoids conflicts with the main browser which uses "chrome_data"
            import uuid
            unique_id = str(uuid.uuid4())[:8]  # Short unique ID
            user_data_dir = os.path.join(os.getcwd(), f"chrome_posting_temp_{unique_id}")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument(f"--profile-directory=PostingProfile")
            
            # Store the temp directory for cleanup later
            self._temp_chrome_dir = user_data_dir
            
            service = Service(ChromeDriverManager().install())
            self.posting_driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Test the driver is working
            self.posting_driver.get("https://www.facebook.com")
            logger.info("[POSTING THREAD] ✅ Background posting Chrome driver set up and tested successfully.")
            return True
            
        except Exception as e:
            logger.error(f"[POSTING THREAD] ❌ Failed to setup background posting Chrome Driver: {e}")
            self.posting_driver = None
            return False

    def start_posting_thread(self):
        """Start a background thread to post comments from the queue."""
        self.posting_queue = queue.Queue()
        
        # Setup posting driver for image posting
        logger.info("Setting up dedicated posting driver for image uploads...")
        self.setup_posting_driver()
        
        # Initialize window manager after driver is setup
        # Will be initialized in the worker thread when driver is available
        self.posting_manager = None
        
        self.posting_thread = threading.Thread(target=self._posting_worker, daemon=True)
        self.posting_thread.start()
        logger.info("Background posting thread started.")

    def _posting_worker(self):
        """Optimized worker function for the posting thread."""
        # Wait for main driver to be available with shorter polling
        retry_count = 0
        while retry_count < 30:  # Try for up to 30 seconds
            if hasattr(self, 'driver') and self.driver:
                # Initialize window manager once driver is available
                try:
                    from posting_window_manager import WindowPostingManager
                    self.posting_manager = WindowPostingManager(self.driver, self.config)
                    logger.info("[POSTING THREAD] Window-based posting manager initialized successfully")
                    break
                except Exception as e:
                    logger.error(f"[POSTING THREAD] Failed to initialize posting manager: {e}")
                    self.posting_manager = None
                    break
            else:
                time.sleep(0.5)  # Reduced from 1s to 0.5s for faster startup
                retry_count += 1
                
        if not self.posting_manager:
            logger.warning("[POSTING THREAD] Running without window manager - using fallback method")
            
        # Track posting timing for optimization
        self._posting_stats = {'total_posts': 0, 'avg_time': 0, 'failures': 0}
        
        while True:
            try:
                # Handle multiple formats: (post_url, comment), (post_url, comment, comment_id), (post_url, comment, comment_id, images)
                queue_item = self.posting_queue.get(timeout=1)  # Non-blocking with timeout
                
                start_time = time.time()
                success = False
                images = None
                
                if len(queue_item) == 4:
                    # New format with images
                    post_url, comment, comment_id, images = queue_item
                    logger.info(f"[POSTING THREAD] Posting comment {comment_id} with {len(images) if images else 0} images to: {post_url[:50]}...")
                    
                    # Check if image posting is enabled and we have images
                    if images and self.config.get('ENABLE_IMAGE_POSTING', False):
                        logger.info(f"[POSTING THREAD] 🖼️ Image posting enabled, attaching {len(images)} images")
                        success = self.post_comment_with_image_background(post_url, comment, comment_id, images)
                    elif images and not self.config.get('ENABLE_IMAGE_POSTING', False):
                        logger.warning(f"[POSTING THREAD] ⚠️ Images provided but image posting disabled, posting text only")
                        if hasattr(self, 'posting_manager') and self.posting_manager:
                            success = self.posting_manager.post_comment(post_url, comment, comment_id)
                        else:
                            success = self._post_comment_background(post_url, comment, comment_id)
                    elif hasattr(self, 'posting_manager') and self.posting_manager:
                        # Fallback to window manager without images (for now)
                        success = self.posting_manager.post_comment(post_url, comment, comment_id)
                    else:
                        success = self._post_comment_background(post_url, comment, comment_id)
                        
                elif len(queue_item) == 3:
                    post_url, comment, comment_id = queue_item
                    logger.info(f"[POSTING THREAD] Posting comment {comment_id} to: {post_url[:50]}...")
                    
                    # Use optimized window manager if available
                    if hasattr(self, 'posting_manager') and self.posting_manager:
                        success = self.posting_manager.post_comment(post_url, comment, comment_id)
                    else:
                        success = self._post_comment_background(post_url, comment, comment_id)
                        
                elif len(queue_item) == 2:
                    post_url, comment = queue_item
                    comment_id = None
                    logger.info(f"[POSTING THREAD] Posting comment to: {post_url[:50]}...")
                    
                    # Use optimized window manager if available
                    if hasattr(self, 'posting_manager') and self.posting_manager:
                        success = self.posting_manager.post_comment(post_url, comment, comment_id)
                    else:
                        success = self._post_comment_background(post_url, comment, comment_id)
                else:
                    logger.error(f"[POSTING THREAD] Invalid queue item format: {queue_item}")
                    success = False
                
                # Track performance metrics
                posting_time = time.time() - start_time
                self._update_posting_stats(posting_time, success)
                
                if success:
                    logger.info(f"[POSTING THREAD] ✅ Comment posted in {posting_time:.2f}s")
                else:
                    logger.error(f"[POSTING THREAD] ❌ Comment failed after {posting_time:.2f}s")
                
                self.posting_queue.task_done()
                
            except queue.Empty:
                # Queue timeout - allows thread to remain responsive
                continue
            except Exception as e:
                logger.error(f"[POSTING THREAD] Error posting comment: {e}")
                self.posting_queue.task_done()
                
    def _update_posting_stats(self, posting_time, success):
        """Track posting performance for optimization"""
        self._posting_stats['total_posts'] += 1
        
        if success:
            # Update running average
            current_avg = self._posting_stats['avg_time']
            total_posts = self._posting_stats['total_posts']
            self._posting_stats['avg_time'] = ((current_avg * (total_posts - 1)) + posting_time) / total_posts
        else:
            self._posting_stats['failures'] += 1
            
        # Log performance every 10 posts
        if self._posting_stats['total_posts'] % 10 == 0:
            avg_time = self._posting_stats['avg_time']
            failure_rate = (self._posting_stats['failures'] / self._posting_stats['total_posts']) * 100
            logger.info(f"[PERFORMANCE] Avg posting time: {avg_time:.2f}s, Failure rate: {failure_rate:.1f}%")

    def post_comment_with_image_background(self, post_url, comment, comment_id, images):
        """Post a comment with images using the background posting driver"""
        try:
            # Check if posting driver is available and still valid
            if not hasattr(self, 'posting_driver') or not self.posting_driver:
                logger.warning("[POSTING THREAD] No posting driver available, attempting to create one...")
                self.setup_posting_driver()
                
            # Validate driver is still alive
            if self.posting_driver:
                try:
                    # Test if driver is responsive
                    self.posting_driver.current_url
                except Exception as e:
                    logger.warning(f"[POSTING THREAD] Posting driver appears dead: {e}, recreating...")
                    try:
                        self.posting_driver.quit()
                    except:
                        pass
                    self.setup_posting_driver()
            
            if not self.posting_driver:
                logger.error("[POSTING THREAD] Failed to create posting driver")
                return False
            
            logger.info(f"[POSTING THREAD] 🖼️ Navigating to post with images: {post_url[:50]}...")
            
            # Navigate to the post URL
            self.posting_driver.get(post_url)
            time.sleep(2)  # Wait for page load
            
            # Use multi-image strategy: comment+first image, then image-only posts
            # Create a temporary bot instance with the posting driver for the strategy methods
            temp_bot = FacebookAICommentBot(self.config)
            temp_bot.driver = self.posting_driver
            temp_bot.posting_driver = self.posting_driver  # Ensure it has access to posting driver
            
            try:
                # Decide strategy based on number of images
                if not images or len(images) == 0:
                    # No images - fall back to text-only comment
                    logger.info("[POSTING THREAD] No images provided, posting text-only comment")
                    success = temp_bot.post_comment(comment, 0)
                elif len(images) == 1:
                    # Single image - use existing method
                    logger.info("[POSTING THREAD] Single image detected, using standard method")
                    success = temp_bot.post_comment_with_image(comment, 0, images)
                else:
                    # Multiple images - use new multi-image strategy
                    logger.info(f"[POSTING THREAD] Multiple images detected ({len(images)}), using multi-image strategy")
                    success, results = temp_bot.post_multiple_images_strategy(post_url, comment, comment_id, images)
                    
                    # Log detailed results
                    for post_type, post_success, image_path in results:
                        status = "✅ SUCCESS" if post_success else "❌ FAILED"
                        image_name = image_path.split('/')[-1] if image_path else "unknown"
                        logger.info(f"[POSTING THREAD] {post_type}: {status} - {image_name}")
                
                # Update comment status if we have comment_id
                if comment_id:
                    try:
                        from database import db
                        queue_id = int(comment_id)
                        if success:
                            db.update_comment_status(queue_id, "posted")
                            logger.info(f"[POSTING THREAD] ✅ Comment {comment_id} marked as posted")
                        else:
                            db.update_comment_status(queue_id, "failed")
                            logger.warning(f"[POSTING THREAD] ❌ Comment {comment_id} marked as failed")
                    except Exception as e:
                        logger.error(f"Failed to update comment status: {e}")
                
                return success
                
            except Exception as e:
                logger.error(f"[POSTING THREAD] Failed to post comment with images: {e}")
                if comment_id:
                    try:
                        from database import db
                        queue_id = int(comment_id)
                        db.update_comment_status(queue_id, "failed")
                    except Exception as e:
                        logger.error(f"Failed to update comment status: {e}")
                return False
                
        except Exception as e:
            logger.error(f"[POSTING THREAD] Error in post_comment_with_image_background: {e}")
            return False
    
    def _post_comment_background(self, post_url, comment, comment_id=None):
        """Navigate to post_url in the posting driver and post the comment. Use explicit waits and retry logic for robustness."""
        from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        driver = self.posting_driver
        try:
            driver.get(post_url)
            time.sleep(5)
            
            # Check if we're logged in by looking for login elements
            if "login" in driver.current_url.lower() or len(driver.find_elements(By.XPATH, "//input[@name='email']")) > 0:
                logger.error(f"[POSTING THREAD] Not logged into Facebook in posting browser")
                if comment_id:
                    try:
                        from database import db
                        db.update_comment_status(int(comment_id), "failed", error_message="Not logged into Facebook")
                    except:
                        pass
                return False
            def find_comment_box():
                elements = driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
                if not elements:
                    for fallback_xpath in self.config.get('COMMENT_BOX_FALLBACK_XPATHS', []):
                        elements = driver.find_elements(By.XPATH, fallback_xpath)
                        if elements:
                            break
                return elements[0] if elements else None

            # Wait for comment box to be present
            comment_area = None
            try:
                comment_area = WebDriverWait(driver, 5).until(lambda d: find_comment_box())
            except TimeoutException:
                logger.error(f"[POSTING THREAD] Could not find comment box for: {post_url}")
                # Update database status on failure
                if comment_id:
                    try:
                        from database import db
                        db.update_comment_status(int(comment_id), "failed", error_message="Could not find comment box")
                    except:
                        pass
                return False

            # Robust interaction with retries
            def safe_action(action_fn, max_retries=3):
                for attempt in range(max_retries):
                    try:
                        comment_area = find_comment_box()
                        if not comment_area:
                            raise Exception("Comment box disappeared during action.")
                        action_fn(comment_area)
                        return True
                    except StaleElementReferenceException:
                        logger.warning(f"[POSTING THREAD] Stale element on attempt {attempt+1}, retrying...")
                        time.sleep(1)
                    except Exception as e:
                        logger.warning(f"[POSTING THREAD] Error on attempt {attempt+1}: {e}")
                        time.sleep(1)
                logger.error(f"[POSTING THREAD] Failed action after {max_retries} retries.")
                return False

            # Click
            if not safe_action(lambda el: el.click()):
                # Update database status on failure
                if comment_id:
                    try:
                        from database import db
                        db.update_comment_status(int(comment_id), "failed", error_message="Failed to click comment box")
                    except:
                        pass
                return False
            time.sleep(1)
            # Type comment
            if not safe_action(lambda el: el.send_keys(comment)):
                # Update database status on failure
                if comment_id:
                    try:
                        from database import db
                        db.update_comment_status(int(comment_id), "failed", error_message="Failed to type comment")
                    except:
                        pass
                return False
            time.sleep(0.5)
            # Press RETURN
            if not safe_action(lambda el: el.send_keys(Keys.RETURN)):
                # Update database status on failure
                if comment_id:
                    try:
                        from database import db
                        db.update_comment_status(int(comment_id), "failed", error_message="Failed to submit comment")
                    except:
                        pass
                return False
                
            logger.info(f"[POSTING THREAD] Successfully posted comment to: {post_url}")
            
            # Update database status on success
            if comment_id:
                try:
                    from database import db
                    db.update_comment_status(int(comment_id), "posted")
                    logger.info(f"[POSTING THREAD] Updated comment {comment_id} status to 'posted'")
                except Exception as db_error:
                    logger.error(f"[POSTING THREAD] Failed to update database status: {db_error}")
            
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"[POSTING THREAD] Failed to post comment to {post_url}: {e}")
            
            # Update database status on exception
            if comment_id:
                try:
                    from database import db
                    db.update_comment_status(int(comment_id), "failed", error_message=str(e))
                except:
                    pass
            return False


    def scrape_authors_and_generate_comments(self, scroll_count=5, pause_time=2):
        """
        Scrape Facebook post author names from the current page and generate a personalized comment for each using the class's comment generator.
        Returns a dict: {author_name: comment}
        """
        driver = self.driver
        author_comments = {}

        # Scroll to load more posts
        for _ in range(scroll_count):
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(pause_time)

        articles = driver.find_elements(By.XPATH, "//div[@role='article']")

        for article in articles:
            name = None
            try:
                for tag in ["h2", "h3"]:
                    spans = article.find_elements(By.XPATH, f".//{tag}//span")
                    for span in spans:
                        candidate = span.text.strip()
                        if candidate:
                            name = candidate
                            break
                    if name:
                        break
            except Exception:
                continue

            if name and name not in author_comments:
                # Use the class's comment generator for personalization
                comment = self.comment_generator.personalize_comment("Hi {{author_name}}, thanks for sharing your post!", name)
                author_comments[name] = comment

        return author_comments
    def __init__(self, config=None):
        self.config = {**CONFIG, **(config or {})}
        self.driver = None
        
        # Initialize enhanced systems
        self.classifier = PostClassifier(self.config)
        self.comment_generator = ExternalCommentGenerator(self.config, database=db)
        self.duplicate_detector = DuplicateDetector(self.config)

    def already_commented(self, existing_comments: List[str]) -> bool:
        """Check if Bravo already commented on this post"""
        return self.duplicate_detector.already_commented(existing_comments)

    def is_duplicate_post(self, post_text: str, post_url: str) -> bool:
        """Check if this is a duplicate post"""
        return self.duplicate_detector.is_duplicate_post(post_text, post_url)
    
    def retry_on_failure(self, func, max_retries=3, wait_time=2, check_session=True):
        """
        Generic retry wrapper for WebDriver operations
        
        Args:
            func: Function to execute
            max_retries: Maximum number of retry attempts
            wait_time: Initial wait time between retries (exponential backoff)
            check_session: Whether to check WebDriver session before retry
        
        Returns:
            Result of the function if successful
        
        Raises:
            RuntimeError if all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Check if WebDriver session is still active before trying
                if check_session and self.driver:
                    try:
                        # Quick health check
                        self.driver.execute_script("return 1;")
                    except WebDriverException:
                        logger.error("WebDriver session is dead, cannot retry operation")
                        raise RuntimeError("WebDriver session lost")
                
                # Try to execute the function
                result = func()
                
                if attempt > 0:
                    logger.info(f"✅ Operation succeeded on retry {attempt + 1}")
                
                return result
                
            except WebDriverException as e:
                last_exception = e
                logger.warning(f"WebDriver operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait = wait_time * (attempt + 1)  # Exponential backoff
                    logger.info(f"Waiting {wait} seconds before retry...")
                    time.sleep(wait)
                else:
                    logger.error(f"Operation failed after {max_retries} attempts")
                    
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error during operation: {e}")
                break
        
        raise RuntimeError(f"Operation failed after {max_retries} retries: {last_exception}")

    def setup_driver(self):
        """Setup Chrome driver with connection validation and retry logic"""
        MAX_RETRIES = 5
        RETRY_WAIT = 2
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Attempting to start Chrome driver (attempt {attempt + 1}/{MAX_RETRIES})...")
                
                # Set environment for Chrome stability
                os.environ['CHROME_LOG_FILE'] = 'nul'
                
                chrome_options = Options()
                # Enhanced Chrome arguments for maximum stability and reliability
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                # Additional stability options
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-first-run")
                chrome_options.add_argument("--disable-background-timer-throttling")
                chrome_options.add_argument("--disable-renderer-backgrounding")
                chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                
                # Run in visible mode so you can see what the bot is doing
                # chrome_options.add_argument("--headless")  # Commented out to show browser
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # Suppress Chrome log noise
                chrome_options.add_argument("--log-level=3")  # Only fatal errors
                chrome_options.add_argument("--silent")
                
                # User data and profile settings
                user_data_dir = os.path.join(os.getcwd(), "chrome_data")
                chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
                chrome_options.add_argument(f"--profile-directory={self.config['CHROME_PROFILE']}")
                
                # Set window size for consistent screenshots
                chrome_options.add_argument("--window-size=1920,1080")
                
                # Enable remote debugging for potential future use
                chrome_options.add_argument("--remote-debugging-port=9222")
                chrome_options.add_argument("--remote-debugging-address=127.0.0.1")
                
                service = Service(ChromeDriverManager().install())
                service.start()  # Start service explicitly
                
                # Set timeouts for better connection stability
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.implicitly_wait(10)  # Wait up to 10 seconds for elements
                self.driver.set_page_load_timeout(30)  # 30 second timeout for page loads
                
                # Validate connection by checking session ID
                if not self.driver.session_id:
                    raise WebDriverException("Failed to establish WebDriver session")
                
                # Test the connection with a simple command
                try:
                    self.driver.execute_script("return navigator.userAgent;")
                    logger.info(f"✅ Chrome driver connected successfully (session: {self.driver.session_id[:8]}...)")
                    logger.info("Chrome driver set up successfully in visible mode.")
                    return  # Success!
                    
                except Exception as test_error:
                    logger.error(f"Driver created but not responding: {test_error}")
                    if self.driver:
                        self.driver.quit()
                    raise WebDriverException("Driver health check failed")
                    
            except WebDriverException as e:
                logger.warning(f"WebDriver connection attempt {attempt + 1} failed: {e}")
                
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Waiting {RETRY_WAIT} seconds before retry...")
                    time.sleep(RETRY_WAIT * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to setup Chrome Driver after {MAX_RETRIES} attempts")
                    raise RuntimeError(f"Unable to start WebDriver after {MAX_RETRIES} retries: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error setting up Chrome Driver: {e}")
                raise

    def is_driver_healthy(self):
        """Check if WebDriver connection is still alive"""
        try:
            if not hasattr(self, 'driver') or self.driver is None:
                return False
            self.driver.current_url
            return True
        except Exception as e:
            logger.debug(f"Driver health check failed: {e}")
            return False

    def reconnect_driver_if_needed(self):
        """Reconnect driver if connection is lost"""
        if not self.is_driver_healthy():
            logger.warning("Driver connection lost, attempting to reconnect...")
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.debug(f"Error closing old driver: {e}")
            self.setup_driver()
            logger.info("Driver reconnection completed")


    def random_pause(self, min_time=1, max_time=5):
        delay = random.uniform(min_time, max_time)
        time.sleep(delay)
        logger.debug(f"Paused for {delay:.2f} seconds.")

    def human_mouse_jiggle(self, element, moves=2):
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            
            # Get configuration values
            config = self.config.get('bot_detection_safety', {})
            mouse_config = config.get('mouse_movement', {})
            
            # Use configured values or defaults
            num_moves = random.randint(*mouse_config.get('jiggle_moves', [2, 4]))
            jiggle_range = random.randint(*mouse_config.get('jiggle_range', [3, 8]))
            
            # Enhanced human-like mouse movements
            for move_num in range(num_moves):
                # Get element location for more natural movement
                element_location = element.location
                element_size = element.size
                
                # Calculate natural movement area around the element
                center_x = element_location['x'] + element_size['width'] // 2
                center_y = element_location['y'] + element_size['height'] // 2
                
                # Create natural movement patterns
                if move_num == 0:
                    # First move: gentle approach
                    x_offset = random.randint(-jiggle_range, jiggle_range)
                    y_offset = random.randint(-jiggle_range, jiggle_range)
                elif move_num == 1:
                    # Second move: slight adjustment
                    x_offset = random.randint(-jiggle_range//2, jiggle_range//2)
                    y_offset = random.randint(-jiggle_range//2, jiggle_range//2)
                else:
                    # Additional moves: micro-adjustments
                    x_offset = random.randint(-jiggle_range//3, jiggle_range//3)
                    y_offset = random.randint(-jiggle_range//3, jiggle_range//3)
                
                # Apply natural movement with slight curve
                actions.move_by_offset(x_offset, y_offset).perform()
                
                # Small pause between movements (like human hand tremor)
                time.sleep(random.uniform(0.05, 0.15))
                
                # Return to center with slight overshoot (human-like)
                actions.move_by_offset(-x_offset, -y_offset).perform()
                
                # Micro-pause after returning
                time.sleep(random.uniform(0.02, 0.08))
                
        except Exception as e:
            logger.debug(f"Mouse jiggle failed: {e}")

    def enhanced_human_mouse_movement(self, target_element, start_element=None):
        """Create more sophisticated human-like mouse movements between elements"""
        try:
            actions = ActionChains(self.driver)
            
            # Get configuration values
            config = self.config.get('bot_detection_safety', {})
            mouse_config = config.get('mouse_movement', {})
            
            if start_element:
                # Start from a different element and move naturally to target
                actions.move_to_element(start_element).perform()
                time.sleep(random.uniform(0.1, 0.3))
            
            # Get target element location
            target_location = target_element.location
            target_size = target_element.size
            target_center_x = target_location['x'] + target_size['width'] // 2
            target_center_y = target_location['y'] + target_size['height'] // 2
            
            # Get current mouse position
            current_location = self.driver.execute_script("return [window.innerWidth/2, window.innerHeight/2];")
            current_x, current_y = current_location[0], current_location[1]
            
            # Calculate distance and create natural movement path
            distance_x = target_center_x - current_x
            distance_y = target_center_y - current_y
            total_distance = (distance_x**2 + distance_y**2)**0.5
            
            # Create intermediate waypoints for natural curve
            if total_distance > 100:  # Only for longer movements
                waypoint_range = mouse_config.get('waypoint_count', [2, 4])
                num_waypoints = random.randint(*waypoint_range)
                curve_variation = random.randint(*mouse_config.get('curve_variation', [15, 25]))
                waypoints = []
                
                for i in range(1, num_waypoints + 1):
                    # Create natural curve with slight randomness
                    progress = i / (num_waypoints + 1)
                    curve_offset = curve_variation * (1 - progress)  # Less offset near target
                    
                    waypoint_x = current_x + (distance_x * progress) + random.randint(-curve_offset, curve_offset)
                    waypoint_y = current_y + (distance_y * progress) + random.randint(-curve_offset, curve_offset)
                    
                    waypoints.append((waypoint_x, waypoint_y))
                
                # Move through waypoints with natural timing
                for waypoint in waypoints:
                    actions.move_by_offset(waypoint[0] - current_x, waypoint[1] - current_y).perform()
                    current_x, current_y = waypoint[0], waypoint[1]
                    time.sleep(random.uniform(0.05, 0.15))
            
            # Final approach to target with natural deceleration
            actions.move_to_element(target_element).perform()
            
            # Small final adjustment (like human precision)
            final_offset_x = random.randint(-2, 2)
            final_offset_y = random.randint(-2, 2)
            actions.move_by_offset(final_offset_x, final_offset_y).perform()
            
            # Return to exact center
            actions.move_by_offset(-final_offset_x, -final_offset_y).perform()
            
        except Exception as e:
            logger.debug(f"Enhanced mouse movement failed: {e}")
            # Fallback to simple movement
            actions.move_to_element(target_element).perform()

    def random_scroll(self):
        try:
            # More natural scroll patterns
            scroll_type = random.choice(['smooth', 'jerky', 'gentle'])
            
            if scroll_type == 'smooth':
                # Smooth scroll with natural deceleration
                scroll_amount = random.randint(-400, 400)
                self.driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}});")
                time.sleep(random.uniform(0.5, 1.5))
            elif scroll_type == 'jerky':
                # Jerky scroll (like human scrolling)
                for _ in range(random.randint(2, 4)):
                    small_scroll = random.randint(-100, 100)
                    self.driver.execute_script(f"window.scrollBy(0, {small_scroll});")
                    time.sleep(random.uniform(0.1, 0.3))
            else:  # gentle
                # Gentle scroll with pause
                scroll_amount = random.randint(-200, 200)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.8, 2.0))
                
        except Exception as e:
            logger.debug(f"Random scroll failed: {e}")

    def random_hover_or_click(self):
        try:
            # Get configuration values
            config = self.config.get('bot_detection_safety', {})
            behavior_config = config.get('random_behavior', {})
            
            # Use configured probabilities or defaults
            scroll_prob = behavior_config.get('scroll_probability', 0.4)
            hover_prob = behavior_config.get('hover_probability', 0.3)
            click_prob = behavior_config.get('click_probability', 0.3)
            
            # Normalize probabilities
            total_prob = scroll_prob + hover_prob + click_prob
            if total_prob > 0:
                scroll_prob /= total_prob
                hover_prob /= total_prob
                click_prob /= total_prob
            
            # Choose action based on probabilities
            rand_val = random.random()
            
            if rand_val < scroll_prob:
                # Random scroll
                self.random_scroll()
            elif rand_val < scroll_prob + hover_prob:
                # Random hover on safe elements
                elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//img | //div[@role='article']//span[contains(@class, 'text')]")
                if elements:
                    element = random.choice(elements)
                    if element.is_displayed():
                        actions = ActionChains(self.driver)
                        actions.move_to_element(element).perform()
                        time.sleep(random.uniform(0.5, 1.5))
            else:
                # Random click on safe elements
                safe_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//span[contains(@class, 'text')] | //div[@role='article']//div[contains(@class, 'text')]")
                if safe_elements:
                    element = random.choice(safe_elements)
                    if element.is_displayed() and element.is_enabled():
                        # Natural approach to element
                        self.enhanced_human_mouse_movement(element)
                        element.click()
                        time.sleep(random.uniform(0.3, 0.8))
                
        except Exception as e:
            logger.debug(f"Random hover/click failed: {e}")

    def natural_typing_rhythm(self, text: str) -> List[Tuple[str, float]]:
        """Generate natural typing rhythm with variable speeds"""
        rhythm_pattern = []
        
        # Base typing speed (characters per second)
        base_speed = random.uniform(3.0, 6.0)  # Human typing speed varies
        
        for char in text:
            # Base delay for this character
            base_delay = 1.0 / base_speed
            
            # Add natural variations
            if char in ['.', '!', '?']:
                # Longer pause after sentence endings
                delay = base_delay + random.uniform(0.3, 0.8)
            elif char in [',', ';', ':']:
                # Medium pause after punctuation
                delay = base_delay + random.uniform(0.1, 0.4)
            elif char == ' ':
                # Slight pause after words
                delay = base_delay + random.uniform(0.05, 0.2)
            else:
                # Normal character with slight variation
                delay = base_delay + random.uniform(-0.1, 0.2)
            
            # Ensure minimum delay
            delay = max(delay, 0.05)
            
            rhythm_pattern.append((char, delay))
        
        return rhythm_pattern

    def simulate_human_typing_errors(self, text: str) -> str:
        """Simulate occasional human typing errors and corrections"""
        try:
            # Get configuration values
            config = self.config.get('bot_detection_safety', {})
            error_config = config.get('typing_errors', {})
            
            error_prob = error_config.get('error_probability', 0.05)
            correction_prob = error_config.get('correction_probability', 0.5)
            
            if random.random() < error_prob:  # Configured chance of error
                # Common typing errors
                error_patterns = [
                    ('the', 'teh'),
                    ('and', 'adn'),
                    ('for', 'fro'),
                    ('with', 'wth'),
                    ('that', 'taht'),
                    ('have', 'hvae'),
                    ('this', 'htis'),
                    ('they', 'tehy'),
                    ('will', 'wll'),
                    ('from', 'form')
                ]
                
                for wrong, right in error_patterns:
                    if wrong in text.lower():
                        # Use configured correction probability
                        if random.random() < correction_prob:
                            text = text.replace(wrong, right)
                            logger.debug(f"Simulated typing error: '{wrong}' -> '{right}'")
                            break
        except Exception as e:
            logger.debug(f"Error simulation failed: {e}")
        
        return text

    def is_post_from_today(self):
        # TEMPORARILY DISABLED FOR TESTING - Always return True
        # TODO: Re-implement proper date checking after testing
        return True

    def is_post_accessible(self, post_url: str) -> bool:
        """Check if a post is actually accessible and not broken/removed"""
        try:
            logger.info(f"Validating post accessibility: {post_url}")
            
            # Navigate to the post
            self.driver.get(post_url)
            time.sleep(1.5)  # Wait for page to load
            
            # Check for Facebook error pages
            error_indicators = [
                "This Page Isn't Available",
                "The link may be broken",
                "the page may have been removed",
                "Check to see if the link you're trying to open is correct",
                "Go to Feed",
                "Go back",
                "Visit Help Center",
                "Content Not Found",
                "This content is no longer available",
                "The page you requested cannot be displayed",
                "Sorry, this content isn't available right now",
                "This post is no longer available",
                "This post has been removed",
                "This post is unavailable"
            ]
            
            # Check page title for errors
            page_title = self.driver.title.lower()
            if any(error_word in page_title for error_word in ["not available", "error", "not found", "unavailable"]):
                logger.warning(f"❌ Post has error in title: {post_url}")
                logger.warning(f"   Page title: {self.driver.title}")
                return False
            
            # Check page source for error indicators
            page_text = self.driver.page_source.lower()
            for indicator in error_indicators:
                if indicator.lower() in page_text:
                    logger.warning(f"❌ Post is broken/removed: {post_url}")
                    logger.warning(f"   Found error indicator: {indicator}")
                    return False
            
            # Check if we can find the main post content
            try:
                # Look for the main article element
                article = self.driver.find_element(By.XPATH, "//div[@role='article']")
                if article:
                    # Check if article has meaningful content
                    article_text = article.text.strip()
                    if len(article_text) < 50:  # Too short to be a real post
                        logger.warning(f"❌ Post has insufficient content: {post_url}")
                        logger.warning(f"   Content length: {len(article_text)} characters")
                        return False
                    
                    logger.info(f"✅ Post is accessible: {post_url}")
                    return True
                    
            except Exception as e:
                logger.warning(f"❌ Could not find post content: {post_url}")
                logger.warning(f"   Error: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error validating post accessibility: {post_url}")
            logger.error(f"   Error: {e}")
            return False
        
        return False
        
        # Original implementation (commented out):
        # try:
        #     # Look for date indicators
        #     date_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/permalink/')]//span")
        #     for element in date_elements:
        #         text = element.text.lower()
        #         if any(today_indicator in text for today_indicator in [
        #             "today", "just now", "minute", "hour", "ago"
        #             ]):
        #             return True
        #         return False
        # except Exception:
        #     return True  # Default to True if we can't determine

    def save_processed_post(self, post_url: str, post_text: str = "", post_type: str = "", 
                           comment_generated: bool = False, comment_text: str = "", 
                           error_message: str = ""):
        try:
            db.mark_post_processed(
                post_url=post_url,
                post_text=post_text,
                post_type=post_type,
                comment_generated=comment_generated,
                comment_text=comment_text,
                error_message=error_message
            )
            logger.info(f"Saved processed post: {post_url}")
        except Exception as e:
            logger.error(f"Failed to save processed post: {e}")

    def scroll_and_collect_post_links(self, max_scrolls=5):
        collected = set()
        empty_scroll_count = 0
        max_empty_scrolls = 2  # Stop after 2 consecutive empty scrolls
        
        for scroll_num in range(max_scrolls):
            logger.info(f"Scroll {scroll_num + 1}/{max_scrolls}")
            
            # Wait for dynamic content to load before searching
            try:
                # Wait up to 3 seconds for at least one post link to appear
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//a[contains(@href, '/groups/') or contains(@href, '/photo/') or contains(@href, '/commerce/')]"))
                )
            except TimeoutException:
                logger.debug("No new elements appeared after wait - page might be fully loaded")
            
            # Collect group posts, photo posts, and commerce listings
            # Photo URLs with fbid and any set= parameter (g., a., pcb., etc.)
            post_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/groups/') and contains(@href, '/posts/') and not(contains(@href, 'comment_id')) and string-length(@href) > 60]" +
                " | //a[contains(@href, '/photo/?fbid=') and contains(@href, 'set=')]" +
                " | //a[contains(@href, '/commerce/listing/') and string-length(@href) > 80]"
            )
            
            # Log what we're looking for
            logger.info("🔍 Collecting group posts, photo posts, and commerce listings")
            
            hrefs = [link.get_attribute('href') for link in post_links if link.get_attribute('href')]
            logger.info(f"Found {len(hrefs)} post links on this scroll")
            
            # DEBUG: Log ALL URLs found before filtering
            if hrefs:
                logger.info("🔍 ALL URLs found (before filtering):")
                for i, href in enumerate(hrefs[:10]):  # Show first 10
                    # Show raw URL only for now to avoid confusion
                    logger.info(f"  {i+1}: {href[:150]}...")
                if len(hrefs) > 10:
                    logger.info(f"  ... and {len(hrefs) - 10} more")
                
                # SPECIAL DEBUG: Check for any photo URLs that shouldn't be here
                photo_urls = [href for href in hrefs if '/photo/' in href]
                if photo_urls:
                    logger.error(f"🚨 FOUND {len(photo_urls)} PHOTO URLS DESPITE DISABLING THEM!")
                    for i, photo_url in enumerate(photo_urls[:5]):
                        logger.error(f"  Photo URL {i+1}: {photo_url}")
                    if len(photo_urls) > 5:
                        logger.error(f"  ... and {len(photo_urls) - 5} more photo URLs!")
            
            # Filter out broken/incomplete URLs and clean them
            valid_hrefs = []
            for href in hrefs:
                # For photo URLs, keep essential parameters (fbid, set) but remove tracking params
                if '/photo/' in href and 'fbid=' in href:
                    # Keep photo URLs mostly intact, just remove tracking parameters
                    import re
                    # Remove tracking parameters but keep fbid and set
                    clean_href = re.sub(r'&(__cft__|__tn__|notif_id|notif_t|ref)=[^&]*', '', href)
                    clean_href = re.sub(r'&context=[^&]*', '', clean_href)  # Remove long context param
                else:
                    # For non-photo URLs, remove all query parameters
                    clean_href = href.split('?')[0] if '?' in href else href
                
                # Then validate the cleaned URL
                if self.is_valid_post_url(clean_href):
                    # Check if we haven't already seen this clean URL
                    if clean_href not in collected:
                        valid_hrefs.append(clean_href)
                        logger.info(f"✅ Valid URL (length {len(clean_href)}): {clean_href[:150]}...")
                    else:
                        logger.info(f"⏭️ Skipping duplicate URL: {clean_href[:100]}...")
                else:
                    logger.warning(f"❌ Filtered out invalid URL (length {len(clean_href)}): {clean_href}")
            
            logger.info(f"After filtering: {len(valid_hrefs)} new valid URLs from {len(hrefs)} total")
            
            # Log some example URLs
            if valid_hrefs:
                logger.info(f"Example new valid URLs: {valid_hrefs[:3]}")
                empty_scroll_count = 0  # Reset counter when posts are found
            else:
                empty_scroll_count += 1
                logger.warning(f"No new posts found on scroll {scroll_num + 1} (consecutive empty: {empty_scroll_count})")
                
                # Break if too many empty scrolls
                if empty_scroll_count >= max_empty_scrolls:
                    logger.info(f"Stopping early - {max_empty_scrolls} consecutive scrolls with no new posts")
                    break
            
            collected.update(valid_hrefs)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        final_list = list(collected)
        logger.info(f"Total unique valid post links collected: {len(final_list)}")
        return final_list

    def is_valid_post_url(self, url: str) -> bool:
        """Check if a URL is a valid, complete post URL"""
        if not url or not isinstance(url, str):
            return False
        
        # Must be a Facebook URL
        if not url.startswith('https://www.facebook.com/'):
            return False
        
        # AGGRESSIVE filtering for photo URLs - they're causing the most problems
        if '/photo/' in url:
            # Group photo URLs with any set= are valid even if shorter
            if 'set=' in url:
                # Group photos just need fbid and set=
                if len(url) < 70:
                    logger.warning(f"❌ Photo URL too short: {url}")
                    return False
            else:
                # Non-group photo URLs must be at least 100 characters long
                if len(url) < 100:
                    logger.warning(f"❌ Photo URL too short (likely broken): {url}")
                    return False
            
            # Must have fbid parameter
            if 'fbid=' not in url:
                logger.warning(f"❌ Incomplete photo URL (missing fbid): {url}")
                return False
            
            # Check if fbid has a value
            fbid_match = re.search(r'fbid=([^&]+)', url)
            if not fbid_match or not fbid_match.group(1):
                logger.warning(f"❌ Photo URL with empty fbid: {url}")
                return False
            
            # fbid must be numeric and at least 10 digits
            fbid_value = fbid_match.group(1)
            if not fbid_value.isdigit() or len(fbid_value) < 10:
                logger.warning(f"❌ Photo URL with invalid fbid: {url} (fbid: {fbid_value})")
                return False
        
        # Check for complete post URLs
        if '/posts/' in url:
            # Must have a post ID after /posts/
            post_match = re.search(r'/posts/([^/?]+)', url)
            if not post_match or not post_match.group(1):
                logger.warning(f"❌ Incomplete post URL (missing post ID): {url}")
                return False
            
            # Post ID must be reasonably long
            post_id = post_match.group(1)
            if len(post_id) < 10:
                logger.warning(f"❌ Post URL with suspiciously short ID: {url} (ID: {post_id})")
                return False
        
        # Check for complete commerce URLs
        if '/commerce/listing/' in url:
            # Must have a listing ID
            listing_match = re.search(r'/commerce/listing/([^/?]+)', url)
            if not listing_match or not listing_match.group(1):
                logger.warning(f"❌ Incomplete commerce URL (missing listing ID): {url}")
                return False
        
        # URL must be reasonably long (not just a base path)
        # Exception: Group posts and photo URLs are valid even with shorter URLs
        if '/groups/' in url and '/posts/' in url:
            # Group posts just need the post ID, can be shorter
            if len(url) < 60:
                logger.warning(f"❌ Group post URL too short (likely incomplete): {url}")
                return False
        elif '/photo/' in url and 'fbid=' in url:
            # Photo URLs can be shorter but need fbid parameter
            if len(url) < 50:
                logger.warning(f"❌ Photo URL too short (likely incomplete): {url}")
                return False
        elif len(url) < 80:  # Other URLs need to be longer
            logger.warning(f"❌ URL too short (likely incomplete): {url}")
            return False
        
        # Check for common broken URL patterns
        broken_patterns = [
            r'https://www\.facebook\.com/photo/$',  # Just /photo/ with nothing after
            r'https://www\.facebook\.com/photo/\?$',  # /photo/? with no parameters
            r'https://www\.facebook\.com/photo/\?fbid=$',  # /photo/?fbid= with no value
            r'https://www\.facebook\.com/photo/\?fbid=[^&]*$',  # /photo/?fbid= with no additional params
            r'https://www\.facebook\.com/groups/[^/]+/?$',  # Just group URL with no posts
            r'https://www\.facebook\.com/groups/[^/]+/posts/?$',  # Group posts with no post ID
            r'https://www\.facebook\.com/photo/\?fbid=\d+$',  # Photo with just fbid, no other params
        ]
        
        for pattern in broken_patterns:
            if re.match(pattern, url):
                logger.warning(f"❌ URL matches broken pattern: {url}")
                return False
        
        # Additional check: photo URLs must have a numeric fbid
        if '/photo/' in url and 'fbid=' in url:
            fbid_match = re.search(r'fbid=(\d+)', url)
            if not fbid_match or not fbid_match.group(1).isdigit():
                logger.warning(f"❌ Photo URL with non-numeric fbid: {url}")
                return False
        
        logger.info(f"✅ Valid URL: {url}")
        return True

    def debug_post_structure(self):
        """Debug function to see what elements are available on the page"""
        try:
            logger.info("=== DEBUGGING POST STRUCTURE ===")
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info(f"Page title: {self.driver.title}")
            
            # Check for article elements
            articles = self.driver.find_elements(By.XPATH, "//div[@role='article']")
            logger.info(f"Found {len(articles)} article elements")
            
            # Check for various text elements
            text_elements = self.driver.find_elements(By.XPATH, "//div[@dir='auto']")
            logger.info(f"Found {len(text_elements)} elements with dir='auto'")
            
            for i, elem in enumerate(text_elements[:5]):  # Show first 5
                text = elem.text.strip()
                if text and len(text) > 5:
                    logger.info(f"Element {i+1}: {text[:100]}...")
            
            # Check for images
            images = self.driver.find_elements(By.XPATH, "//img")
            logger.info(f"Found {len(images)} images")
            
            # Check for specific Facebook elements
            fb_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'post')]")
            logger.info(f"Found {len(fb_elements)} elements with 'post' class")
            
            logger.info("=== END DEBUGGING ===")
            
        except Exception as e:
            logger.error(f"Debug function failed: {e}")

    def debug_page_structure(self):
        """Debug method to inspect page structure and find potential comment box elements"""
        try:
            logger.info("🔍 Debugging page structure for comment box elements...")
            
            # Look for all contenteditable elements
            contenteditable_elements = self.driver.find_elements(By.XPATH, "//*[@contenteditable='true']")
            logger.info(f"Found {len(contenteditable_elements)} contenteditable elements")
            for i, elem in enumerate(contenteditable_elements[:5]):  # Show first 5
                try:
                    role = elem.get_attribute('role') or 'none'
                    placeholder = elem.get_attribute('aria-placeholder') or 'none'
                    class_name = elem.get_attribute('class') or 'none'
                    logger.info(f"  Element {i+1}: role='{role}', placeholder='{placeholder}', class='{class_name}'")
                except:
                    logger.info(f"  Element {i+1}: Could not get attributes")
            
            # Look for all textbox role elements
            textbox_elements = self.driver.find_elements(By.XPATH, "//*[@role='textbox']")
            logger.info(f"Found {len(textbox_elements)} textbox role elements")
            for i, elem in enumerate(textbox_elements[:5]):  # Show first 5
                try:
                    contenteditable = elem.get_attribute('contenteditable') or 'none'
                    placeholder = elem.get_attribute('aria-placeholder') or 'none'
                    class_name = elem.get_attribute('class') or 'none'
                    logger.info(f"  Textbox {i+1}: contenteditable='{contenteditable}', placeholder='{placeholder}', class='{class_name}'")
                except:
                    logger.info(f"  Textbox {i+1}: Could not get attributes")
                    
        except Exception as e:
            logger.error(f"Error during page structure debug: {e}")

    def is_valid_text_quality(self, text):
        """Validate extracted text quality to detect scrambled/fragmented text"""
        if not text or len(text) < 10:
            logger.debug("Text too short or empty")
            return False
        
        # Check for scrambled text pattern (too many single characters separated by spaces)
        words = text.split()
        if not words:
            return False
            
        # Count single character "words" 
        single_chars = len([word for word in words if len(word) == 1 and word.isalnum()])
        total_words = len(words)
        
        # If more than 50% are single characters, it's likely scrambled
        if single_chars > total_words * 0.5:
            logger.warning(f"Text appears scrambled: {single_chars}/{total_words} single chars")
            logger.debug(f"Scrambled text sample: {text[:100]}...")
            return False
        
        # Check for reasonable word length distribution
        avg_word_length = sum(len(word) for word in words) / total_words if total_words > 0 else 0
        if avg_word_length < 2:  # Average word length too short
            logger.warning(f"Average word length too short: {avg_word_length}")
            return False
            
        # Check for meaningful content (not just repeated characters)
        if len(set(text.replace(' ', '').lower())) < 5:  # Too few unique characters
            logger.warning("Text has too few unique characters")
            return False
            
        logger.debug(f"Text quality validation passed: {len(text)} chars, {total_words} words, avg length {avg_word_length:.1f}")
        return True

    def extract_text_from_elements(self, elements, method_name):
        """Extract text using JavaScript to get consolidated content from parent containers"""
        extracted_texts = []
        
        for element in elements:
            try:
                # Use multiple JavaScript methods to extract clean text content
                js_methods = [
                    # Method 1: textContent - gets all text including hidden elements
                    "return arguments[0].textContent;",
                    # Method 2: innerText - gets visible text only
                    "return arguments[0].innerText;", 
                    # Method 3: Combined approach - prefer visible text, fallback to textContent
                    """
                    var elem = arguments[0];
                    var text = elem.innerText || elem.textContent || '';
                    return text.trim();
                    """
                ]
                
                for js_code in js_methods:
                    try:
                        # Extract text using JavaScript
                        text = self.driver.execute_script(js_code, element)
                        if text and isinstance(text, str):
                            text = text.strip()
                            
                            # Quick validation - must be substantial and not scrambled
                            if len(text) > 20 and self.is_text_not_scrambled(text):
                                logger.debug(f"JS method extracted: {text[:100]}...")
                                
                                # Apply content filtering
                                filtered_text = self.filter_ui_and_comment_content(text)
                                if filtered_text:
                                    extracted_texts.append(filtered_text)
                                    break  # Success with this element, try next
                                    
                    except Exception as js_e:
                        logger.debug(f"JavaScript extraction failed: {js_e}")
                        continue
                        
                # Fallback to regular .text property if JavaScript fails
                if not extracted_texts or len(extracted_texts) == 0:
                    try:
                        fallback_text = element.text.strip()
                        if fallback_text and len(fallback_text) > 20 and self.is_text_not_scrambled(fallback_text):
                            filtered_text = self.filter_ui_and_comment_content(fallback_text)
                            if filtered_text:
                                extracted_texts.append(filtered_text)
                                logger.debug(f"Fallback extraction: {fallback_text[:100]}...")
                    except Exception as fallback_e:
                        logger.debug(f"Fallback extraction failed: {fallback_e}")
                        
            except Exception as e:
                logger.debug(f"Element processing failed: {e}")
                continue
        
        if not extracted_texts:
            logger.debug(f"No valid text extracted using {method_name}")
            return None
            
        # Find the best text using prioritization strategies
        return self.prioritize_extracted_texts(extracted_texts, method_name)
    
    def is_text_not_scrambled(self, text):
        """Check if text is not scrambled character fragments"""
        if not text or len(text) < 10:
            return False
            
        words = text.split()
        if len(words) < 2:
            return False
            
        # Count words vs single characters
        single_chars = len([word for word in words if len(word) == 1])
        word_ratio = single_chars / len(words) if words else 1
        
        # If more than 50% are single characters, likely scrambled
        if word_ratio > 0.5:
            logger.debug(f"Text appears scrambled: {word_ratio:.1%} single chars")
            return False
            
        return True
    
    def filter_ui_and_comment_content(self, text):
        """Filter out UI elements and comment-like content"""
        if not text:
            return None
            
        # UI text filters
        ui_filters = [
            "Write a comment", "Add a comment", "What's on your mind", "Share your thoughts",
            "Like", "Comment", "Share", "Send", "Reply", "Be the first to comment",
            "View post", "Most relevant", "Top comments", "All comments", "Sort by",
            "See more comments", "Hide comments", "Load more comments"
        ]
        
        # Check for UI text
        if any(ui_filter.lower() in text.lower() for ui_filter in ui_filters):
            logger.debug(f"Filtering out UI text: {text[:50]}...")
            return None
        
        # Comment pattern indicators
        comment_patterns = [
            text.strip().startswith(("@", "Reply to", "Replying to")),
            " replied to " in text.lower() or " commented on " in text.lower(),
            len(text.strip()) < 30 and any(word in text.lower() for word in 
                ["yes", "no", "thanks", "lol", "haha", "great", "nice", "wow", "cool", "awesome"])
        ]
        
        if any(comment_patterns):
            logger.debug(f"Filtering out comment-like text: {text[:50]}...")
            return None
            
        # Clean and normalize
        cleaned_text = ' '.join(text.split())
        return cleaned_text if len(cleaned_text) > 15 else None
    
    def prioritize_extracted_texts(self, texts, method_name):
        """Prioritize extracted texts to find the best post content"""
        if not texts:
            return None
            
        # Strategy 1: Prefer longer, more substantial content
        substantial_texts = [t for t in texts if len(t) > 50]
        if substantial_texts:
            best_text = max(substantial_texts, key=len)
            logger.info(f"Successfully extracted substantial text using {method_name}: {best_text[:100]}...")
            return best_text
            
        # Strategy 2: Take the longest available text
        if texts:
            best_text = max(texts, key=len)
            logger.info(f"Successfully extracted text using {method_name}: {best_text[:100]}...")
            return best_text
            
        return None

    def get_post_text(self):
        """
        Extract the main text of the post for context or logging.
        Tries multiple XPaths for text, photo, shared, event, OCR, and fallback content.
        Enhanced with quality validation to prevent scrambled text.
        """
        logger.info("Attempting to extract post text with quality validation...")
        
        # Quick page load wait
        try:
            logger.debug("Waiting for page to load...")
            time.sleep(0.5)  # Reduced wait time
            
            # Quick wait for article element
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
            )
            logger.debug("Page loaded successfully")
        except Exception as e:
            logger.debug(f"Page load wait failed: {e}")
        
        # Debug post structure only in debug mode
        # self.debug_post_structure()  # Commented out for performance
        
        # Simplified extraction methods - try most effective first
        extraction_methods = [
            # Method 1: Most effective Facebook selectors first
            ("//div[@data-testid='post_message']", "Facebook post message container"),
            ("//div[contains(@class, 'userContent')]", "Facebook user content container"),
            
            # Method 2: Simple article containers
            ("//div[@role='article']//div[@dir='auto']", "Article directional containers"),
            ("//div[@role='article']", "Main article container"),
        ]
        
        # Try each extraction method with quality validation
        for xpath, method_name in extraction_methods:
            try:
                logger.debug(f"Trying method: {method_name}")
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                if elements:
                    logger.debug(f"Found {len(elements)} elements for {method_name}")
                    
                    # Handle image alt text specially using JavaScript
                    if "Image" in method_name and "alt" in method_name:
                        for img_element in elements:
                            try:
                                # Use JavaScript to get alt attribute reliably
                                alt_text = self.driver.execute_script("return arguments[0].alt || arguments[0].getAttribute('alt');", img_element)
                                if alt_text and len(alt_text) > 10 and self.is_text_not_scrambled(alt_text):
                                    filtered_alt = self.filter_ui_and_comment_content(alt_text)
                                    if filtered_alt:
                                        logger.info(f"Successfully extracted image alt text: {filtered_alt[:100]}...")
                                        return filtered_alt
                            except Exception as e:
                                logger.debug(f"Failed to get alt text: {e}")
                        continue
                    
                    # Use improved JavaScript-based text extraction method
                    extracted_text = self.extract_text_from_elements(elements, method_name)
                    if extracted_text:
                        return extracted_text
                        
            except Exception as e:
                logger.debug(f"Method {method_name} failed: {e}")
                continue
        
        # Method 8: OCR on images as last resort
        try:
            logger.info("Trying OCR on images...")
            img_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//img[@src]")
            for img in img_elements:
                src = img.get_attribute('src')
                if src and not src.endswith('emoji'):
                    try:
                        response = requests.get(src, timeout=10)
                        image = Image.open(BytesIO(response.content))
                        ocr_text = pytesseract.image_to_string(image)
                        if ocr_text and len(ocr_text.strip()) > 10:
                            logger.info(f"OCR extracted text: {ocr_text.strip()[:100]}...")
                            return ocr_text.strip()
                    except Exception as ocr_e:
                        logger.debug(f"OCR failed for image: {src} | Reason: {ocr_e}")
        except Exception as e:
            logger.debug(f"OCR method failed: {e}")
        
        # Method 9: Get all visible text in article as absolute fallback
        try:
            logger.info("Trying fallback: all visible text in article...")
            article = self.driver.find_element(By.XPATH, "//div[@role='article']")
            article_text = article.text.strip()
            if article_text and len(article_text) > 20:
                logger.info(f"Fallback extracted text: {article_text[:100]}...")
                return article_text
        except Exception as e:
            logger.debug(f"Fallback method failed: {e}")
        
        # Method 10: Try to get text from any visible element in the post area
        try:
            logger.info("Trying advanced fallback: any visible text in post area...")
            # Look for any div or span with text in the post area
            post_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//*[self::div or self::span or self::p]")
            texts = []
            for element in post_elements:
                try:
                    text = element.text.strip()
                    if text and len(text) > 5 and len(text) < 500:  # Reasonable text length
                        # Filter out common Facebook UI text
                        if not any(ui_text in text.lower() for ui_text in [
                            'like', 'comment', 'share', 'send', 'post', 'facebook', 'privacy', 'settings',
                            'report', 'block', 'unfollow', 'follow', 'message', 'add friend'
                        ]):
                            texts.append(text)
                except:
                    continue
            
            if texts:
                # Combine and clean up the text
                combined_text = ' '.join(texts)
                # Remove duplicates and clean up
                lines = combined_text.split('\n')
                unique_lines = []
                for line in lines:
                    line = line.strip()
                    if line and line not in unique_lines and len(line) > 5:
                        unique_lines.append(line)
                
                final_text = ' '.join(unique_lines)
                if len(final_text) > 20:
                    logger.info(f"Advanced fallback extracted text: {final_text[:100]}...")
                    return final_text
                    
        except Exception as e:
            logger.debug(f"Advanced fallback method failed: {e}")
        
        logger.error("Could not extract post text: All methods failed")
        logger.error("This means the bot cannot process this post")
        return ""
    
    # get_live_screenshot method removed

    def get_existing_comments(self):
        try:
            comment_elements = self.driver.find_elements(By.XPATH, "//div[@aria-label='Comment']//span")
            return [el.text for el in comment_elements if el.text.strip()]
        except Exception:
            return []
    
    def get_post_author(self) -> str:
        """Extract the post author name from Facebook post page."""
        try:
            # Try multiple approaches to find the post author
            author_selectors = [
                # WORKING SELECTOR: Simple h2 + a + href (found in debug)
                "//h2//a[contains(@href, '/')]",
                # Direct approach - Look for the main author link in the post header
                "//div[@role='article']//h2//a[@role='link']",
                "//div[@role='article']//h3//a[@role='link']",
                # Alternative - Look for author spans within header links  
                "//div[@role='article']//h2//a[@role='link']//span[contains(@class,'')]",
                "//div[@role='article']//h3//a[@role='link']//span[contains(@class,'')]",
                # Fallback - Any link that looks like a profile link in the article header
                "//div[@role='article']//a[contains(@href, 'facebook.com/') and @role='link'][1]",
                # Last resort - Look for text content in header area
                "//div[@role='article']//h2//span",
                "//div[@role='article']//h3//span"
            ]

            for selector in author_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        # For link elements, get the text content
                        if element.tag_name == 'a':
                            name = element.text.strip()
                            href = element.get_attribute('href') or ""
                            
                            # Make sure it's a profile link and has valid name
                            if name and self.is_valid_author_name(name) and 'facebook.com/' in href:
                                logger.info(f"✅ Found post author from link: {name} ({href})")
                                return name
                        else:
                            # For span elements, get text content
                            name = element.text.strip()
                            if name and self.is_valid_author_name(name):
                                logger.info(f"✅ Found post author from span: {name}")
                                return name
                                
                except Exception as e:
                    logger.debug(f"Selector failed: {selector} - {e}")
                    continue

            # If no author found, try a more aggressive approach
            try:
                # Look for any profile links in the first part of the article
                profile_links = self.driver.find_elements(By.XPATH, 
                    "//div[@role='article']//a[contains(@href, 'facebook.com/') and @role='link']")
                
                for link in profile_links[:3]:  # Check first 3 profile links
                    name = link.text.strip()
                    href = link.get_attribute('href') or ""
                    if name and self.is_valid_author_name(name) and '/profile/' not in href:
                        logger.info(f"✅ Found post author via fallback: {name}")
                        return name
            except Exception as e:
                logger.debug(f"Fallback profile link search failed: {e}")

            logger.warning("⚠️ Could not extract a valid post author name")
            return ""

        except Exception as e:
            logger.error(f"❌ Error extracting post author: {e}")
            return ""


    def is_valid_author_name(self, name: str) -> bool:
        """Check if the extracted text looks like a valid author name"""
        if not name or len(name) < 2:
            return False
        
        # Skip if it's common UI text
        skip_texts = [
            'like', 'comment', 'share', 'more', 'see more', 'hide', 'report',
            'sponsored', 'admin', 'moderator', 'public figure', 'business',
            'follow', 'unfollow', 'message', 'block', 'privacy', 'settings',
            'minutes ago', 'hours ago', 'yesterday', 'days ago', 'weeks ago'
        ]
        
        name_lower = name.lower()
        if any(skip_text in name_lower for skip_text in skip_texts):
            logger.debug(f"Skipping UI text: {name}")
            return False
        
        # Check if it's too long (probably not a name)
        if len(name) > 50:
            logger.debug(f"Name too long: {name[:30]}...")
            return False
        
        # Check if it contains numbers (suspicious for names)
        if any(char.isdigit() for char in name):
            logger.debug(f"Name contains numbers: {name}")
            return False
        
        # Must contain at least one letter
        if not any(char.isalpha() for char in name):
            logger.debug(f"Name contains no letters: {name}")
            return False
        
        logger.info(f"Valid author name found: {name}")
        return True

    def inject_random_human_behavior(self):
        """Inject random human-like behavior patterns during posting"""
        try:
            # Get configuration values
            config = self.config.get('bot_detection_safety', {})
            behavior_config = config.get('random_behavior', {})
            
            # 30% chance to perform random behavior
            if random.random() < 0.3:
                behavior_type = random.choice(['scroll', 'hover', 'click', 'pause'])
                
                if behavior_type == 'scroll':
                    logger.debug("🔄 Injecting random scroll behavior")
                    self.random_scroll()
                elif behavior_type == 'hover':
                    logger.debug("🔄 Injecting random hover behavior")
                    # Find safe elements to hover over
                    safe_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//img | //div[@role='article']//span[contains(@class, 'text')]")
                    if safe_elements:
                        element = random.choice(safe_elements)
                        if element.is_displayed():
                            actions = ActionChains(self.driver)
                            actions.move_to_element(element).perform()
                            time.sleep(random.uniform(0.3, 0.8))
                elif behavior_type == 'click':
                    logger.debug("🔄 Injecting random click behavior")
                    # Find safe elements to click
                    safe_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//span[contains(@class, 'text')] | //div[@role='article']//div[contains(@class, 'text')]")
                    if safe_elements:
                        element = random.choice(safe_elements)
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            time.sleep(random.uniform(0.2, 0.6))
                elif behavior_type == 'pause':
                    logger.debug("🔄 Injecting random pause behavior")
                    time.sleep(random.uniform(0.5, 1.5))
                    
        except Exception as e:
            logger.debug(f"Random behavior injection failed: {e}")

    def post_comment(self, comment: str, comment_count: int):
        try:
            # Sanitize comment text for ChromeDriver compatibility
            comment = self.sanitize_unicode_for_chrome(comment)
            
            logger.info("Waiting for comment box to appear...")
            # Wait longer for Facebook to fully load
            time.sleep(5)
            
            # Try primary XPath selector first
            elements = self.driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
            logger.info(f"Found {len(elements)} elements matching the primary comment box XPath.")
            
            # If primary selector fails, try fallback selectors
            if len(elements) == 0:
                logger.info("Primary selector failed, trying fallback selectors...")
                for i, fallback_xpath in enumerate(self.config.get('COMMENT_BOX_FALLBACK_XPATHS', [])):
                    try:
                        elements = self.driver.find_elements(By.XPATH, fallback_xpath)
                        if len(elements) > 0:
                            logger.info(f"Found {len(elements)} elements with fallback selector {i+1}: {fallback_xpath}")
                            break
                    except Exception as e:
                        logger.warning(f"Fallback selector {i+1} failed: {e}")
                        continue
                
                # If still no elements, wait a bit more and try again (Facebook might be slow)
                if len(elements) == 0:
                    logger.info("Still no elements found, waiting 3 more seconds and retrying...")
                    time.sleep(3)
                    
                    # Try primary selector again
                    elements = self.driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
                    if len(elements) > 0:
                        logger.info(f"Found {len(elements)} elements on retry with primary selector")
                    else:
                        # Try fallback selectors again
                        for i, fallback_xpath in enumerate(self.config.get('COMMENT_BOX_FALLBACK_XPATHS', [])):
                            try:
                                elements = self.driver.find_elements(By.XPATH, fallback_xpath)
                                if len(elements) > 0:
                                    logger.info(f"Found {len(elements)} elements on retry with fallback selector {i+1}")
                                    break
                            except Exception as e:
                                logger.warning(f"Fallback selector {i+1} retry failed: {e}")
                                continue
            
            if len(elements) == 0:
                current_url = self.driver.current_url
                logger.error(f"No elements found for any comment box XPath selectors")
                logger.error(f"Primary XPath: {self.config['COMMENT_BOX_XPATH']}")
                logger.error(f"Fallback XPaths: {self.config.get('COMMENT_BOX_FALLBACK_XPATHS', [])}")
                logger.error(f"Could not find comment box on: {current_url}")
                # Debug the page structure
                self.debug_page_structure()
                with open("no_comment_box_links.txt", "a", encoding="utf-8") as f:
                    f.write(current_url + "\n")
                raise TimeoutException("No comment box found.")
                
            comment_area = elements[0]
            
            # Enhanced bot detection safety measures
            logger.info("🛡️ Applying enhanced bot detection safety measures...")
            
            # Get configuration values
            config = self.config.get('bot_detection_safety', {})
            natural_pauses = config.get('natural_pauses', {})
            
            # Random pre-interaction behavior
            if random.random() < 0.4:
                self.random_scroll()
            else:
                self.random_hover_or_click()
            
            # Natural mouse movement to comment area
            self.human_mouse_jiggle(comment_area, moves=3)
            
            # Random delay before clicking (configured)
            pre_click_range = natural_pauses.get('pre_click', [0.5, 2.0])
            time.sleep(random.uniform(*pre_click_range))
            
            # Click with natural timing
            comment_area.click()
            
            # Random delay after clicking (configured)
            post_click_range = natural_pauses.get('post_click', [0.3, 1.5])
            time.sleep(random.uniform(*post_click_range))
            
            # Enhanced human-like typing with natural patterns
            logger.info("⌨️ Typing comment with enhanced human-like patterns...")
            
            # Simulate occasional typing errors (very rare)
            comment_with_errors = self.simulate_human_typing_errors(comment)
            
            # Split comment into natural chunks (sentences or phrases)
            comment_chunks = self._split_comment_naturally(comment_with_errors)
            
            for chunk_index, chunk in enumerate(comment_chunks):
                # Type each chunk with natural timing
                for char_index, char in enumerate(chunk):
                    comment_area.send_keys(char)
                    
                    # Natural typing delays using configuration
                    if char_index == 0 and chunk_index > 0:
                        # Longer pause between chunks (like thinking)
                        chunk_pause_range = natural_pauses.get('chunk_boundary', [0.8, 2.5])
                        time.sleep(random.uniform(*chunk_pause_range))
                    elif char in ['.', '!', '?']:
                        # Natural pause after sentence endings
                        sentence_pause_range = natural_pauses.get('sentence_end', [0.3, 0.8])
                        time.sleep(random.uniform(*sentence_pause_range))
                    elif char in [',', ';', ':']:
                        # Natural pause after punctuation
                        punct_pause_range = natural_pauses.get('punctuation', [0.1, 0.4])
                        time.sleep(random.uniform(*punct_pause_range))
                    elif char == ' ':
                        # Slight pause after words
                        word_pause_range = natural_pauses.get('word_boundary', [0.05, 0.2])
                        time.sleep(random.uniform(*word_pause_range))
                    elif random.random() < 0.15:  # 15% chance of small delay
                        # Random micro-pauses (like human typing)
                        time.sleep(random.uniform(0.05, 0.25))
                    
                    # Occasional "typo" correction simulation (very rare)
                    if random.random() < 0.02:  # 2% chance
                        comment_area.send_keys(Keys.BACKSPACE)
                        time.sleep(random.uniform(0.1, 0.3))
                        comment_area.send_keys(char)
                
                # Natural pause between chunks
                if chunk_index < len(comment_chunks) - 1:
                    chunk_pause_range = natural_pauses.get('chunk_boundary', [0.5, 1.5])
                    time.sleep(random.uniform(*chunk_pause_range))
                
                # Inject random human behavior between chunks (occasionally)
                if random.random() < 0.2:  # 20% chance
                    self.inject_random_human_behavior()
            
            # Enhanced random pause before posting (configured)
            logger.info("⏳ Natural pause before posting...")
            pre_post_range = natural_pauses.get('pre_post', [2.0, 5.0])
            time.sleep(random.uniform(*pre_post_range))
            
            # Final random behavior injection before posting
            if random.random() < 0.4:  # 40% chance
                self.inject_random_human_behavior()
            
            # Post the comment with enhanced reliability
            try:
                # First try the standard Enter key
                comment_area.send_keys(Keys.RETURN)
                logger.info(f"✅ Sent RETURN key for comment {comment_count + 1}")
            except Exception as key_error:
                logger.warning(f"Standard RETURN key failed: {key_error}")
                
                # Fallback: Try to find and click the Post button
                try:
                    logger.info("Attempting to find and click Post button...")
                    
                    # Common Facebook Post button selectors
                    post_button_selectors = [
                        "//div[@aria-label='Post' and @role='button']",
                        "//div[@aria-label='Comment' and @role='button']",
                        "//button[contains(@aria-label, 'Post')]",
                        "//button[contains(@aria-label, 'Comment')]",
                        "//div[contains(@class, 'x1i10hfl') and @role='button' and @tabindex='0']",
                        "//div[@role='button' and contains(., 'Post')]"
                    ]
                    
                    button_found = False
                    for selector in post_button_selectors:
                        try:
                            # Wait for button to be clickable
                            wait = WebDriverWait(self.driver, 3)
                            post_button = wait.until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            
                            # Use JavaScript click for reliability
                            self.driver.execute_script("arguments[0].click();", post_button)
                            logger.info(f"✅ Clicked Post button using selector: {selector}")
                            button_found = True
                            break
                            
                        except (TimeoutException, NoSuchElementException):
                            continue
                        except Exception as btn_error:
                            logger.debug(f"Button selector {selector} failed: {btn_error}")
                            continue
                    
                    if not button_found:
                        # Last resort: Try JavaScript Enter key simulation
                        logger.info("Post button not found, simulating Enter key via JavaScript...")
                        self.driver.execute_script("""
                            var event = new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true
                            });
                            arguments[0].dispatchEvent(event);
                        """, comment_area)
                        logger.info("✅ Dispatched Enter key event via JavaScript")
                        
                except Exception as fallback_error:
                    logger.error(f"All posting methods failed: {fallback_error}")
                    raise
            
            logger.info(f"✅ Posted comment {comment_count + 1}: {comment[:50]}...")
            
            # Wait for comment to post with natural timing
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            logger.error(f"Failed to post comment: {e}")
            raise

    def sanitize_unicode_for_chrome(self, text: str) -> str:
        """
        Sanitize Unicode characters that ChromeDriver can't handle (non-BMP characters).
        Converts problematic emojis and Unicode to safe alternatives.
        """
        try:
            # Replace common problematic emojis with text equivalents
            emoji_replacements = {
                '✨': '*',       # Sparkles
                '💎': 'diamond', # Diamond  
                '💍': 'ring',    # Ring
                '👑': 'crown',   # Crown
                '🌟': '*',       # Star
                '⭐': '*',       # Star
                '💫': '*',       # Dizzy star
                '🔥': 'fire',    # Fire
                '❤️': 'love',    # Heart
                '💖': 'love',    # Sparkling heart
                '😍': ':)',      # Heart eyes
                '🤩': ':)',      # Star eyes
                '👍': 'thumbs up', # Thumbs up
                '💯': '100',     # 100 emoji
                '🎉': '!',       # Party
                '🏆': 'trophy',  # Trophy
            }
            
            # Apply emoji replacements
            sanitized = text
            for emoji, replacement in emoji_replacements.items():
                sanitized = sanitized.replace(emoji, replacement)
            
            # Remove any remaining non-BMP characters (Unicode > U+FFFF)
            # Keep only Basic Multilingual Plane characters
            sanitized = ''.join(char for char in sanitized if ord(char) <= 0xFFFF)
            
            if sanitized != text:
                logger.info(f"[UNICODE] Sanitized comment text for ChromeDriver compatibility")
                logger.debug(f"[UNICODE] Original: {text[:50]}...")
                logger.debug(f"[UNICODE] Sanitized: {sanitized[:50]}...")
            
            return sanitized
            
        except Exception as e:
            logger.warning(f"[UNICODE] Error sanitizing text, using original: {e}")
            return text

    def post_comment_with_image(self, comment: str, comment_count: int, image_paths: List[str] = None):
        """
        Enhanced version of post_comment that supports image attachments.
        Falls back to text-only if image upload fails.
        """
        try:
            # Sanitize comment text for ChromeDriver compatibility
            comment = self.sanitize_unicode_for_chrome(comment)
            
            logger.info(f"🖼️ Starting comment with {len(image_paths) if image_paths else 0} images")
            
            # First, activate the comment box using existing logic
            logger.info("Waiting for comment box to appear...")
            time.sleep(5)
            
            # Find comment box using existing selectors
            elements = self.driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
            logger.info(f"Found {len(elements)} elements matching the primary comment box XPath.")
            
            if len(elements) == 0:
                # Try fallback selectors
                logger.info("Primary selector failed, trying fallback selectors...")
                for i, fallback_xpath in enumerate(self.config.get('COMMENT_BOX_FALLBACK_XPATHS', [])):
                    try:
                        elements = self.driver.find_elements(By.XPATH, fallback_xpath)
                        if len(elements) > 0:
                            logger.info(f"Found {len(elements)} elements with fallback selector {i+1}")
                            break
                    except Exception as e:
                        logger.warning(f"Fallback selector {i+1} failed: {e}")
                        continue
            
            if len(elements) == 0:
                logger.error("No comment box found")
                raise TimeoutException("No comment box found.")
                
            comment_area = elements[0]
            
            # Click to activate the comment box
            logger.info("Activating comment box...")
            comment_area.click()
            time.sleep(random.uniform(1, 2))
            
            # NEW: Attach images if provided
            if image_paths and len(image_paths) > 0:
                success = self._attach_images_to_comment(image_paths)
                if success:
                    logger.info("✅ Images attached successfully")
                    # Wait for upload to complete
                    time.sleep(3)
                    
                    # IMPORTANT: Re-find comment box as DOM may have changed
                    logger.info("Re-finding comment box after image upload...")
                    elements = self.driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
                    if len(elements) == 0:
                        # Try fallbacks again
                        for fallback_xpath in self.config.get('COMMENT_BOX_FALLBACK_XPATHS', []):
                            elements = self.driver.find_elements(By.XPATH, fallback_xpath)
                            if len(elements) > 0:
                                break
                    
                    if len(elements) > 0:
                        comment_area = elements[0]
                        # Click to ensure focus is back on text area
                        comment_area.click()
                        time.sleep(0.5)
                else:
                    logger.warning("⚠️ Image attachment failed, continuing with text only")
            
            # Type the comment text using existing human-like typing logic
            logger.info("⌨️ Typing comment text...")
            
            # Enhanced human-like typing with natural patterns
            comment_with_errors = self.simulate_human_typing_errors(comment)
            comment_chunks = self._split_comment_naturally(comment_with_errors)
            
            for chunk_index, chunk in enumerate(comment_chunks):
                for char_index, char in enumerate(chunk):
                    comment_area.send_keys(char)
                    
                    # Natural typing delays
                    if char in ['.', '!', '?']:
                        time.sleep(random.uniform(0.3, 0.8))
                    elif char in [',', ';', ':']:
                        time.sleep(random.uniform(0.1, 0.4))
                    elif char == ' ':
                        time.sleep(random.uniform(0.05, 0.2))
                    elif random.random() < 0.15:
                        time.sleep(random.uniform(0.05, 0.25))
            
            # Pause before posting
            logger.info("⏳ Natural pause before posting...")
            time.sleep(random.uniform(2.0, 4.0))
            
            # Submit the comment
            try:
                comment_area.send_keys(Keys.RETURN)
                logger.info(f"✅ Posted comment {comment_count + 1} with {len(image_paths) if image_paths else 0} images")
            except Exception as key_error:
                logger.warning(f"Enter key failed: {key_error}, trying Post button...")
                # Try clicking Post button as fallback
                self._click_post_button()
            
            # Wait for post to process
            time.sleep(random.uniform(2, 4))
            
            # Return success
            return True
            
        except Exception as e:
            logger.error(f"Failed to post comment with images: {e}")
            # If image posting failed completely, try regular text-only posting
            if image_paths and len(image_paths) > 0:
                logger.info("Falling back to text-only comment...")
                try:
                    self.post_comment(comment, comment_count)
                    return True  # Fallback succeeded
                except Exception as fallback_error:
                    logger.error(f"Fallback text-only comment also failed: {fallback_error}")
                    return False
            else:
                return False
    
    def _attach_images_to_comment(self, image_paths: List[str]) -> bool:
        """
        Attach images to the current comment being composed.
        Returns True if successful, False otherwise.
        """
        try:
            logger.info(f"🎯 Attempting to attach {len(image_paths)} images")
            
            # Look for file input element - it may be hidden
            # Facebook typically has input[type='file'] for image uploads
            file_input_selectors = [
                "//input[@type='file' and contains(@accept, 'image')]",
                "//input[@type='file'][@multiple]",
                "//div[@aria-label='Attach a photo or video']//input[@type='file']",
                "//form//input[@type='file']",
                "//div[contains(@class, 'comment')]//input[@type='file']"
            ]
            
            file_input = None
            for selector in file_input_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        file_input = elements[0]
                        logger.info(f"Found file input with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not file_input:
                # Try to trigger the file input to appear by clicking photo icon
                logger.info("File input not found, trying to click photo attachment button...")
                
                photo_button_selectors = [
                    "//div[@aria-label='Attach a photo or video']",
                    "//div[@aria-label='Photo/Video']",
                    "//button[@aria-label='Attach a photo or video']",
                    "//div[contains(@aria-label, 'photo')]",
                    "//i[contains(@style, 'background-image')]//parent::div[@role='button']"
                ]
                
                for selector in photo_button_selectors:
                    try:
                        photo_button = self.driver.find_element(By.XPATH, selector)
                        photo_button.click()
                        logger.info(f"Clicked photo button: {selector}")
                        time.sleep(1)
                        
                        # Now try to find file input again
                        for file_selector in file_input_selectors:
                            elements = self.driver.find_elements(By.XPATH, file_selector)
                            if elements:
                                file_input = elements[0]
                                logger.info(f"Found file input after clicking button")
                                break
                        
                        if file_input:
                            break
                            
                    except Exception as e:
                        logger.debug(f"Photo button selector {selector} failed: {e}")
                        continue
            
            if not file_input:
                logger.error("Could not find file input element for image upload")
                return False
            
            # Prepare full file paths
            import os
            full_paths = []
            for path in image_paths:
                if os.path.isabs(path):
                    full_path = path
                else:
                    # Assume images are in uploads directory
                    full_path = os.path.join(os.getcwd(), path)
                
                if os.path.exists(full_path):
                    full_paths.append(full_path)
                    logger.info(f"✅ Found image file: {full_path}")
                else:
                    logger.warning(f"⚠️ Image file not found: {full_path}")
            
            if not full_paths:
                logger.error("No valid image files found")
                return False
            
            # Send file paths to the input element
            # For multiple files, join with \n
            file_paths_string = "\n".join(full_paths)
            
            logger.info(f"Sending file paths to input element...")
            file_input.send_keys(file_paths_string)
            
            # Wait for upload to process
            logger.info("Waiting for images to upload...")
            time.sleep(3)
            
            # Verify upload by checking for image preview elements
            preview_selectors = [
                "//div[contains(@class, 'preview')]//img",
                "//div[@role='presentation']//img",
                "//div[contains(@aria-label, 'Remove photo')]",
                "//div[contains(@class, 'x1n2onr6')]//img"
            ]
            
            preview_found = False
            for selector in preview_selectors:
                previews = self.driver.find_elements(By.XPATH, selector)
                if previews:
                    logger.info(f"✅ Found {len(previews)} image preview(s)")
                    preview_found = True
                    break
            
            if not preview_found:
                logger.warning("Could not verify image upload via preview")
            
            return True
            
        except Exception as e:
            logger.error(f"Error attaching images: {e}")
            return False

    def post_image_only(self, post_url, image_path):
        """
        Post a single image as a comment without any text.
        Used for follow-up images after the main comment+image post.
        """
        try:
            logger.info(f"[IMAGE-ONLY] Posting image-only comment: {image_path.split('/')[-1]}")
            
            # Ensure we're on the right post
            current_url = self.posting_driver.current_url
            if post_url not in current_url:
                logger.info(f"[IMAGE-ONLY] Navigating to post: {post_url[:50]}...")
                self.posting_driver.get(post_url)
                time.sleep(3)  # Wait for page load
            
            # Find comment box using existing selectors from post_comment
            logger.info("[IMAGE-ONLY] Looking for comment box...")
            elements = self.posting_driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
            
            if len(elements) == 0:
                # Try fallback selectors
                logger.info("[IMAGE-ONLY] Primary selector failed, trying fallback selectors...")
                for i, fallback_xpath in enumerate(self.config.get('COMMENT_BOX_FALLBACK_XPATHS', [])):
                    try:
                        elements = self.posting_driver.find_elements(By.XPATH, fallback_xpath)
                        if len(elements) > 0:
                            logger.info(f"[IMAGE-ONLY] Found comment box with fallback selector {i+1}")
                            break
                    except Exception as e:
                        logger.debug(f"[IMAGE-ONLY] Fallback selector {i+1} failed: {e}")
                        continue
            
            if len(elements) == 0:
                logger.error("[IMAGE-ONLY] Could not find comment box")
                return False
                
            comment_area = elements[0]
            
            # Click to activate the comment box
            logger.info("[IMAGE-ONLY] Activating comment box...")
            comment_area.click()
            time.sleep(2)
            
            # Attach the image using existing image attachment logic
            success = self._attach_images_to_comment([image_path])
            if not success:
                logger.error("[IMAGE-ONLY] Failed to attach image")
                return False
            
            logger.info("[IMAGE-ONLY] Image attached, waiting for upload to complete...")
            time.sleep(3)  # Wait for upload to complete
            
            # Submit the comment (image-only, no text)
            logger.info("[IMAGE-ONLY] Submitting image-only comment...")
            comment_area.send_keys(Keys.RETURN)
            
            # Wait for post to process
            time.sleep(2)
            
            logger.info("[IMAGE-ONLY] ✅ Image-only comment posted successfully")
            return True
            
        except Exception as e:
            logger.error(f"[IMAGE-ONLY] Failed to post image-only comment: {e}")
            return False

    def post_multiple_images_strategy(self, post_url, comment, comment_id, images):
        """
        Post multiple images using the strategy:
        1. First post: comment text + first image
        2. Subsequent posts: image-only (no text)
        
        Returns: (overall_success, results_list)
        """
        try:
            if not images or len(images) == 0:
                logger.warning("[MULTI-IMAGE] No images provided")
                return False, []
            
            logger.info(f"[MULTI-IMAGE] Starting multi-image strategy: 1 comment + {len(images)-1} image-only posts")
            results = []
            
            # Step 1: Post first comment with first image
            logger.info(f"[MULTI-IMAGE] Step 1/1: Posting comment with first image")
            first_image_success = self.post_comment_with_image(comment, 0, [images[0]])
            results.append(('comment_with_image', first_image_success, images[0]))
            
            if not first_image_success:
                logger.error("[MULTI-IMAGE] First comment+image failed, aborting remaining images")
                return False, results
            
            # Step 2: Post remaining images as image-only posts
            if len(images) > 1:
                logger.info(f"[MULTI-IMAGE] Posting {len(images)-1} additional image-only posts")
                
                for i, image_path in enumerate(images[1:], 2):
                    logger.info(f"[MULTI-IMAGE] Step {i}/{len(images)}: Posting image-only")
                    
                    # Small delay between posts to avoid rate limiting
                    time.sleep(2)
                    
                    image_success = self.post_image_only(post_url, image_path)
                    results.append(('image_only', image_success, image_path))
                    
                    if image_success:
                        logger.info(f"[MULTI-IMAGE] ✅ Image-only {i-1}/{len(images)-1} posted successfully")
                    else:
                        logger.warning(f"[MULTI-IMAGE] ❌ Image-only {i-1}/{len(images)-1} failed, continuing with remaining images")
            
            # Calculate overall success
            successful_posts = sum(1 for _, success, _ in results if success)
            total_posts = len(results)
            overall_success = successful_posts > 0  # Success if at least one post worked
            
            logger.info(f"[MULTI-IMAGE] Strategy complete: {successful_posts}/{total_posts} posts successful")
            return overall_success, results
            
        except Exception as e:
            logger.error(f"[MULTI-IMAGE] Error in multi-image strategy: {e}")
            return False, results if 'results' in locals() else []
    
    def _click_post_button(self):
        """Helper method to click the Post button"""
        try:
            post_button_selectors = [
                "//div[@aria-label='Post' and @role='button']",
                "//div[@aria-label='Comment' and @role='button']",
                "//button[contains(@aria-label, 'Post')]",
                "//button[contains(@aria-label, 'Comment')]"
            ]
            
            for selector in post_button_selectors:
                try:
                    wait = WebDriverWait(self.driver, 3)
                    post_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.driver.execute_script("arguments[0].click();", post_button)
                    logger.info(f"✅ Clicked Post button")
                    return True
                except:
                    continue
            
            logger.warning("Could not find Post button")
            return False
            
        except Exception as e:
            logger.error(f"Error clicking post button: {e}")
            return False

    def _split_comment_naturally(self, comment: str) -> List[str]:
        """Split comment into natural chunks for more human-like typing"""
        # Split by sentences first
        sentences = re.split(r'([.!?]+)', comment)
        
        # Reconstruct sentences with punctuation
        reconstructed = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                reconstructed.append(sentences[i] + sentences[i + 1])
            else:
                reconstructed.append(sentences[i])
        
        # If no sentences found, split by commas or natural breaks
        if len(reconstructed) <= 1:
            # Split by commas, but keep chunks reasonable length
            chunks = comment.split(',')
            reconstructed = []
            current_chunk = ""
            
            for chunk in chunks:
                if len(current_chunk + chunk) < 80:  # Keep chunks under 80 chars
                    current_chunk += ("," + chunk) if current_chunk else chunk
                else:
                    if current_chunk:
                        reconstructed.append(current_chunk)
                    current_chunk = chunk
            
            if current_chunk:
                reconstructed.append(current_chunk)
        
        # Ensure we have at least one chunk
        if not reconstructed:
            reconstructed = [comment]
        
        return reconstructed
    
    def get_live_screenshot(self):
        """
        Capture and return a screenshot of the current browser window.
        Used by the API endpoint /bot/live-screenshot for monitoring.
        """
        try:
            if not self.driver:
                logger.error("No driver instance available for screenshot")
                return None
                
            # Get screenshot as PNG bytes
            screenshot = self.driver.get_screenshot_as_png()
            logger.debug("Successfully captured live screenshot")
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    def perform_startup_health_checks(self):
        """
        Perform comprehensive health checks before starting bot operations
        
        Returns:
            bool: True if all checks pass, False otherwise
        """
        logger.info("=" * 60)
        logger.info("🏥 Starting health checks...")
        logger.info("=" * 60)
        
        checks_passed = True
        
        # Check 1: WebDriver Session
        logger.info("1️⃣ Checking WebDriver session...")
        try:
            if not self.driver or not self.driver.session_id:
                logger.error("❌ No WebDriver session")
                return False
                
            # Test WebDriver responsiveness
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            logger.info(f"✅ WebDriver is responsive (User-Agent: {user_agent[:50]}...)")
        except Exception as e:
            logger.error(f"❌ WebDriver not responding: {e}")
            return False
        
        # Check 2: Facebook Login Status
        logger.info("2️⃣ Checking Facebook login status...")
        try:
            self.driver.get("https://www.facebook.com")
            time.sleep(3)
            
            # Check for login indicators
            login_indicators = [
                "//div[@role='navigation']",  # Main navigation bar
                "//div[@aria-label='Your profile']",  # Profile button
                "//div[@aria-label='Account']",  # Account menu
                "//a[contains(@href, '/friends')]",  # Friends link
                "//a[contains(@href, '/groups')]"  # Groups link
            ]
            
            logged_in = False
            for indicator in login_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements:
                        logged_in = True
                        logger.info(f"✅ Facebook login confirmed (found: {indicator})")
                        break
                except:
                    continue
            
            if not logged_in:
                # Check if we're on login page
                if "login" in self.driver.current_url.lower() or "Log in" in self.driver.title:
                    logger.error("❌ Not logged into Facebook - redirected to login page")
                    logger.error("Please log into Facebook manually in Chrome first")
                    return False
                else:
                    logger.warning("⚠️ Could not confirm login status, but not on login page. Proceeding...")
                    
        except Exception as e:
            logger.error(f"❌ Failed to check Facebook login: {e}")
            return False
        
        # Check 3: Network Connectivity
        logger.info("3️⃣ Checking network connectivity...")
        try:
            import socket
            socket.create_connection(("www.facebook.com", 443), timeout=5)
            logger.info("✅ Network connection to Facebook is working")
        except Exception as e:
            logger.error(f"❌ Network connection failed: {e}")
            return False
        
        # Check 4: Chrome Profile
        logger.info("4️⃣ Checking Chrome profile...")
        try:
            profile_dir = os.path.join(os.getcwd(), "chrome_data")
            if os.path.exists(profile_dir):
                logger.info(f"✅ Chrome profile directory exists: {profile_dir}")
            else:
                logger.warning(f"⚠️ Chrome profile directory not found: {profile_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify Chrome profile: {e}")
        
        # Check 5: Required Configuration
        logger.info("5️⃣ Checking configuration...")
        required_config = ['POST_URL', 'COMMENT_BOX_XPATH', 'templates']
        for key in required_config:
            if key not in self.config or not self.config[key]:
                logger.error(f"❌ Missing required configuration: {key}")
                checks_passed = False
            else:
                logger.info(f"✅ Configuration '{key}' is present")
        
        # Final Summary
        logger.info("=" * 60)
        if checks_passed:
            logger.info("✅ All health checks passed! Bot is ready to start.")
        else:
            logger.error("❌ Some health checks failed. Please fix issues before proceeding.")
        logger.info("=" * 60)
        
        return checks_passed
    
    def run(self):
        logger.info("FacebookAICommentBot starting...")
        try:
            self.setup_driver()
            
            # Perform health checks before proceeding
            if not self.perform_startup_health_checks():
                logger.error("Startup health checks failed. Exiting...")
                if self.driver:
                    self.driver.quit()
                return
            
            self.start_posting_thread()
            url = self.config['POST_URL']
            self.driver.get(url)
            logger.info(f"Loaded Facebook URL: {url}")

            if '/groups/' in url and '/posts/' not in url:
                logger.info("Detected group URL. Entering continuous scan mode for today's posts.")
                while True:
                    logger.info("Starting a new scan cycle for today's posts...")
                    
                    # Navigate back to the group feed to get fresh content
                    logger.info("Refreshing group feed to check for new posts...")
                    self.driver.get(url)
                    time.sleep(2)  # Wait for page to load
                    
                    all_post_links = self.scroll_and_collect_post_links()
                    logger.info(f"Collected {len(all_post_links)} post links from feed.")
                    new_posts = 0
                    
                    for post_url in all_post_links:
                        if db.is_post_processed(post_url):
                            logger.debug(f"Skipping already processed post: {post_url}")
                            continue
                            
                        logger.info(f"🔍 Processing post: {post_url}")
                        retry_count = 0
                        
                        while retry_count < 3:
                            try:
                                # Store original URL for database/UI
                                original_post_url = post_url
                                
                                # For photo URLs, keep the original URL with parameters
                                if '/photo/' in post_url and 'fbid=' in post_url:
                                    # Photo URLs need their parameters to work properly
                                    navigation_url = post_url
                                    logger.debug(f"Using photo URL with parameters: {navigation_url}")
                                else:
                                    # For other URLs, remove query parameters for navigation but keep original for storage
                                    navigation_url = post_url.split('?')[0] if '?' in post_url else post_url
                                    logger.debug(f"Navigation URL: {navigation_url}, Original: {original_post_url}")
                                
                                self.driver.get(navigation_url)
                                logger.debug(f"Navigated to: {navigation_url}")
                                logger.debug(f"Will store as: {original_post_url}")
                                
                                # Verify we're on the right page after navigation
                                actual_url = self.driver.current_url
                                logger.debug(f"Actual page after navigation: {actual_url[:100]}...")
                                
                                # Validate URL consistency for debugging
                                if '/photo/' in original_post_url and '/photo/' not in actual_url:
                                    logger.warning(f"⚠️ URL mismatch detected!")
                                    logger.warning(f"Original: {original_post_url}")
                                    logger.warning(f"Navigation: {navigation_url}")
                                    logger.warning(f"Actual: {actual_url}")
                                elif '/posts/' in original_post_url and '/posts/' not in actual_url:
                                    logger.warning(f"⚠️ Post URL mismatch detected!")
                                    logger.warning(f"Original: {original_post_url}")
                                    logger.warning(f"Actual: {actual_url}")
                                
                                # Quick wait for Facebook's dynamic loading
                                time.sleep(0.5)  # Further reduced for faster processing
                                
                                # Image extraction will be handled by the CRM ingestion process
                                logger.debug("Getting post text")
                                post_text = self.get_post_text()
                                logger.debug(f"Extracted post text: {post_text[:100] if post_text else 'None'}...")
                                
                                # Handle posts with minimal text but images
                                if not post_text or len(post_text.strip()) < 10:
                                    # Extract images first to see if this is an image-only post
                                    logger.info("Minimal text found, checking for images...")
                                    post_images = self.extract_first_image_url()
                                    images_list = [post_images] if post_images else []
                                    
                                    if images_list:
                                        logger.info(f"Image-only post detected with {len(images_list)} images")
                                        post_text = "Image-only post"
                                        post_type = "general"
                                        
                                        # Generate AI comment for image post
                                        generator = ExternalCommentGenerator(self.config, database=db)
                                        ai_comment = generator.generate_comment(post_type, "Beautiful image post", "")
                                        
                                        # Add to queue with image - use original URL
                                        images_json = json.dumps(images_list)
                                        queue_id = db.add_to_comment_queue(
                                            post_url=original_post_url,
                                            post_text=post_text,
                                            comment_text=ai_comment,
                                            post_type=post_type,
                                            post_images=images_json,
                                            post_author=self.get_post_author(),
                                            post_engagement="Image post"
                                        )
                                        
                                        if queue_id:
                                            logger.info(f"Image-only post added to queue with ID: {queue_id}")
                                            new_posts += 1
                                        
                                        db.save_processed_post(original_post_url, post_text, post_type, ai_comment)
                                        break
                                    else:
                                        logger.info(f"No meaningful content found, skipping post: {original_post_url}")
                                        db.save_processed_post(original_post_url, "", "skipped", "")
                                        continue
                                
                                # Extract images from the post
                                logger.debug("Extracting images from post...")
                                post_images = self.extract_first_image_url()
                                images_list = [post_images] if post_images else []
                                logger.debug(f"Found {len(images_list)} images")
                                
                                # Classify the post type
                                logger.debug("Classifying post type...")
                                classifier = PostClassifier(self.config)
                                classification = classifier.classify_post(post_text)
                                post_type = classification.category
                                logger.debug(f"Post classified as: {post_type} (confidence: {classification.confidence:.2f})")
                                
                                # Generate AI comment
                                logger.debug("Generating AI comment...")
                                generator = ExternalCommentGenerator(self.config, database=db)
                                
                                # Try to extract author name for personalization
                                post_author = self.get_post_author()
                                ai_comment = generator.generate_comment(post_type, post_text, post_author)
                                logger.debug(f"Generated comment: {ai_comment[:100]}...")
                                
                                # Convert images list to JSON for database storage
                                images_json = json.dumps(images_list) if images_list else None
                                
                                # Add to comment queue for approval - use original URL
                                logger.debug("Adding to comment approval queue...")
                                queue_id = db.add_to_comment_queue(
                                    post_url=original_post_url,
                                    post_text=post_text,
                                    comment_text=ai_comment,
                                    post_type=post_type,
                                    post_images=images_json,
                                    post_author=post_author,
                                    post_engagement=f"Score: {classification.confidence:.2f}"
                                )
                                
                                if queue_id:
                                    logger.info(f"✅ Added to queue (ID: {queue_id})")
                                    new_posts += 1
                                else:
                                    logger.error("Failed to add comment to queue")
                                
                                # Mark post as processed - use original URL
                                db.save_processed_post(original_post_url, post_text, post_type, ai_comment)
                                logger.debug(f"Post processed successfully: {original_post_url}")
                                
                                break  # Success, exit retry loop
                                
                            except Exception as e:
                                if 'stale element reference' in str(e).lower():
                                    logger.warning(f"Stale element error, retrying ({retry_count+1}/3)...")
                                    retry_count += 1
                                    time.sleep(3)  # Longer wait before retry
                                    continue
                                else:
                                    logger.error(f"Failed to process post: {original_post_url} | Error: {e}")
                                    break
                                    
                    logger.info(f"Scan cycle complete. Processed {new_posts} new posts. Next scan in 3 seconds...")
                    time.sleep(3)
                    
        except Exception as e:
            logger.critical(f"Bot execution failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed.")
            if hasattr(self, 'posting_driver') and self.posting_driver:
                self.posting_driver.quit()
                logger.info("Background posting browser closed.")


# Example for testing:
if __name__ == "__main__":
    bot = FacebookAICommentBot()
    bot.run()