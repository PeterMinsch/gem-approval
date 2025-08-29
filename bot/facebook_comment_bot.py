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
import uuid
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException
)
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

from bravo_config import CONFIG
from database import db

load_dotenv()

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
                # Use new v1.x+ client initialization
                self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                if self.openai_client.api_key:
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
        
        # Extract first name (first word)
        name_parts = full_name.split()
        logger.info(f"🔍 Name parts: {name_parts}")
        
        if not name_parts:
            logger.warning(f"❌ No name parts found after splitting: {full_name}")
            return ""
        
        first_name = name_parts[0]
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
    os.makedirs('logs', exist_ok=True)
    log_filename = f'logs/facebook_comment_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

# Legacy function wrappers for backward compatibility
def classify_post(text: str) -> str:
    """Legacy wrapper for backward compatibility"""
    classifier = PostClassifier(CONFIG)
    result = classifier.classify_post(text)
    return result.post_type

def pick_comment_template(post_type: str, author_name: str = "") -> str:
    """Legacy wrapper for backward compatibility"""
    generator = CommentGenerator(CONFIG)
    return generator.generate_comment(post_type, "", author_name)

def already_commented(existing_comments: List[str]) -> bool:
    """Legacy wrapper for backward compatibility"""
    detector = DuplicateDetector(CONFIG)
    return detector.already_commented(existing_comments)

class FacebookAICommentBot:
    def __init__(self, config=None):
        self.config = {**CONFIG, **(config or {})}
        self.driver = None
        
        # Initialize enhanced systems
        self.classifier = PostClassifier(self.config)
        self.comment_generator = CommentGenerator(self.config)
        self.duplicate_detector = DuplicateDetector(self.config)

    def already_commented(self, existing_comments: List[str]) -> bool:
        """Check if Bravo already commented on this post"""
        return self.duplicate_detector.already_commented(existing_comments)

    def is_duplicate_post(self, post_text: str, post_url: str) -> bool:
        """Check if this is a duplicate post"""
        return self.duplicate_detector.is_duplicate_post(post_text, post_url)

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.binary_location = "C:/Program Files/Google/Chrome/Application/chrome.exe"
            user_data_dir = os.path.join(os.getcwd(), "chrome_data")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument(f"--profile-directory={self.config['CHROME_PROFILE']}")
            
            # Run in visible mode so you can see what the bot is doing
            # chrome_options.add_argument("--headless")  # Commented out to show browser
            # chrome_options.add_argument("--no-sandbox")  # Commented out to show browser
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Set window size for consistent screenshots
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Enable remote debugging for potential future use
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--remote-debugging-address=127.0.0.1")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome driver set up successfully in visible mode.")
        except Exception as e:
            logger.error(f"Failed to setup Chrome Driver: {e}")
            raise

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
            time.sleep(3)  # Wait for page to load
            
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
        
        for scroll_num in range(max_scrolls):
            logger.info(f"Scroll {scroll_num + 1}/{max_scrolls}")
            
            # TEMPORARILY DISABLE PHOTO URLS - they're causing too many problems
            # Only collect group post URLs for now
            post_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/groups/') and contains(@href, '/posts/') and string-length(@href) > 80]"
                " | //a[contains(@href, '/commerce/listing/') and string-length(@href) > 80]"
            )
            
            # Log what we're looking for
            logger.info("🔍 Only collecting group posts and commerce listings (photo URLs temporarily disabled)")
            
            hrefs = [link.get_attribute('href') for link in post_links if link.get_attribute('href')]
            logger.info(f"Found {len(hrefs)} post links on this scroll")
            
            # DEBUG: Log ALL URLs found before filtering
            if hrefs:
                logger.info("🔍 ALL URLs found (before filtering):")
                for i, href in enumerate(hrefs[:10]):  # Show first 10
                    logger.info(f"  {i+1}: {href}")
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
                if self.is_valid_post_url(href):
                    # Clean the URL by removing query parameters for consistent processing
                    clean_href = href.split('?')[0] if '?' in href else href
                    valid_hrefs.append(clean_href)
                else:
                    logger.warning(f"❌ Filtered out broken URL: {href}")
            
            logger.info(f"After filtering: {len(valid_hrefs)} valid URLs from {len(hrefs)} total")
            
            # Log some example URLs
            if valid_hrefs:
                logger.info(f"Example valid URLs: {valid_hrefs[:3]}")
            
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
            # Photo URLs must be at least 100 characters long
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
        if len(url) < 80:  # Increased minimum length
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

    def get_post_text(self):
        """
        Extract the main text of the post for context or logging.
        Tries multiple XPaths for text, photo, shared, event, OCR, and fallback content.
        """
        logger.info("Attempting to extract post text...")
        
        # Wait for page to fully load
        try:
            logger.info("Waiting for page to load...")
            time.sleep(3)  # Wait for dynamic content to load
            
            # Wait for article element to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
            )
            logger.info("Page loaded successfully")
        except Exception as e:
            logger.warning(f"Page load wait failed: {e}")
        
        # First, debug the page structure
        self.debug_post_structure()
        
        # Try multiple text extraction methods with better logging
        extraction_methods = [
            # Method 1: Modern Facebook post text (2024-2025)
            ("//div[@data-ad-preview='message']", "standard post text"),
            ("//div[contains(@class, 'x1iorvi4')]", "modern Facebook text class"),
            ("//div[contains(@class, 'x1n2onr6')]", "Facebook content container"),
            ("//div[contains(@class, 'x1lliihq')]", "Facebook text wrapper"),
            
            # Method 2: Alternative post text selectors
            ("//div[contains(@class, 'post')]//div[@dir='auto']", "post text with dir attribute"),
            ("//div[@role='article']//div[@dir='auto']", "article text with dir attribute"),
            ("//div[@role='article']//div[contains(@class, 'x1iorvi4')]", "article with modern class"),
            
            # Method 3: Generic text content with modern classes
            ("//div[@role='article']//span[contains(@class, 'text')]", "text span elements"),
            ("//div[@role='article']//div[contains(@class, 'text')]", "text div elements"),
            ("//div[@role='article']//div[contains(@class, 'x1iorvi4')]", "modern text div"),
            ("//div[@role='article']//span[contains(@class, 'x1iorvi4')]", "modern text span"),
            
            # Method 4: Photo post alt text and captions
            ("//div[@role='article']//img[@alt]", "image alt text"),
            ("//div[@role='article']//div[contains(@class, 'caption')]", "photo caption"),
            ("//div[@role='article']//div[contains(@class, 'description')]", "photo description"),
            ("//div[@role='article']//div[contains(@class, 'x1iorvi4')]//img[@alt]", "modern photo alt text"),
            
            # Method 5: Shared post content
            ("//div[@data-ad-preview='message']//div[@dir='auto']", "shared post text"),
            ("//div[contains(@class, 'shared-content')]//div[@dir='auto']", "shared content text"),
            ("//div[contains(@class, 'x1iorvi4')]//div[contains(@class, 'shared')]", "modern shared content"),
            ("//div[@role='article']//div[contains(@class, 'shared')]", "article shared content"),
            
            # Method 6: Event post
            ("//div[@role='main']//span[contains(@class, 'event-title')]", "event title"),
            
            # Method 7: Generic visible text
            ("//div[@role='article']//p", "paragraph text"),
            ("//div[@role='article']//span", "span text"),
            ("//div[@role='article']//div", "div text"),
            
            # Method 8: New Facebook structure (2025)
            ("//div[contains(@class, 'x1n2onr6')]//div[contains(@class, 'x1iorvi4')]", "new Facebook structure"),
            ("//div[contains(@class, 'x1lliihq')]//div[contains(@class, 'x1iorvi4')]", "Facebook text container"),
            ("//div[contains(@class, 'x1iorvi4')]//span", "modern text span"),
            ("//div[contains(@class, 'x1iorvi4')]//div", "modern text div"),
        ]
        
        for xpath, method_name in extraction_methods:
            try:
                logger.info(f"Trying method: {method_name}")
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                if elements:
                    logger.info(f"Found {len(elements)} elements for {method_name}")
                    
                    # Extract text from all elements
                    texts = []
                    for element in elements:
                        try:
                            text = element.text.strip()
                            if text and len(text) > 10:  # Only meaningful text
                                # Clean up the text (remove extra whitespace, normalize)
                                text = ' '.join(text.split())  # Normalize whitespace
                                if text and len(text) > 10:  # Check again after cleaning
                                    texts.append(text)
                        except Exception as e:
                            logger.debug(f"Failed to extract text from element: {e}")
                            continue
                    
                    if texts:
                        # Combine all meaningful text
                        combined_text = ' '.join(texts)
                        logger.info(f"Successfully extracted text using {method_name}: {combined_text[:100]}...")
                        return combined_text
                        
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
    
    def get_live_screenshot(self):
        """Get a live screenshot of the current browser view"""
        try:
            if not self.driver:
                return None
            
            # Take screenshot
            screenshot = self.driver.get_screenshot_as_png()
            
            # Convert to base64 for easy transmission
            import base64
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
            
            return {
                "screenshot": f"data:image/png;base64,{screenshot_b64}",
                "url": self.driver.current_url,
                "title": self.driver.title,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get live screenshot: {e}")
            return None

    def get_existing_comments(self):
        try:
            comment_elements = self.driver.find_elements(By.XPATH, "//div[@aria-label='Comment']//span")
            return [el.text for el in comment_elements if el.text.strip()]
        except Exception:
            return []
    
    def get_post_author(self) -> str:
        """Extract the author name from the current post with current Facebook selectors"""
        try:
            # Updated selectors based on the provided HTML structure
            author_selectors = [
                # Target the specific span with Facebook's current classes
                "//span[contains(@class, 'x193iq5w') and contains(@class, 'xeuugli')]",
                "//span[contains(@class, 'x193iq5w')]",
                "//span[contains(@class, 'xeuugli')]",
                
                # More specific - target spans within article that have these classes
                "//div[@role='article']//span[contains(@class, 'x193iq5w') and contains(@class, 'xeuugli')]",
                "//div[@role='article']//span[contains(@class, 'x193iq5w')]",
                
                # Fallback to original selectors
                "//div[@role='article']//h3//a[@role='link']",
                "//div[@role='article']//a[@role='link' and contains(@href, '/profile.php')]",
                "//div[@role='article']//a[@role='link']//span",
            ]
            
            for selector in author_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    
                    # Check each element found
                    for element in elements:
                        if element and element.text.strip():
                            author_name = element.text.strip()
                            
                            # Clean up the author name
                            author_name = author_name.replace('\n', ' ').strip()
                            
                            # Validate it looks like a real name
                            if self.is_valid_author_name(author_name):
                                logger.info(f"Found post author using selector '{selector}': {author_name}")
                                return author_name
                                
                except Exception as e:
                    logger.debug(f"Author selector failed: {selector} - {e}")
                    continue
            
            logger.warning("Could not extract post author name using any selector")
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting post author: {e}")
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
            
            # Post the comment
            comment_area.send_keys(Keys.RETURN)
            logger.info(f"✅ Posted comment {comment_count + 1}: {comment[:50]}...")
            
            # Wait for comment to post with natural timing
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            logger.error(f"Failed to post comment: {e}")
            raise

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

    def run(self):
        try:
            self.setup_driver()
            url = self.config['POST_URL']
            self.driver.get(url)
            logger.info(f"Loaded Facebook URL: {url}")

            if '/groups/' in url and '/posts/' not in url:
                logger.info("Detected group URL. Entering continuous scan mode for today's posts.")
                while True:
                    logger.info("Starting a new scan cycle for today's posts...")
                    time.sleep(5)
                    all_post_links = self.scroll_and_collect_post_links()
                    logger.info(f"Collected {len(all_post_links)} post links from feed.")
                    new_posts = 0
                    for post_url in all_post_links:
                        if db.is_post_processed(post_url):
                            logger.info(f"Skipping already processed post: {post_url}")
                            continue
                        logger.info(f"Navigating to post: {post_url}")
                        retry_count = 0
                        while retry_count < 3:
                            try:
                                # Try to clean up the URL first (remove tracking parameters)
                                clean_url = post_url.split('?')[0] if '?' in post_url else post_url
                                logger.info(f"Cleaned URL: {clean_url}")
                                
                                # ADDITIONAL SAFETY CHECK: Block any photo URLs that somehow got through
                                if '/photo/' in clean_url:
                                    logger.warning(f"🚫 BLOCKING photo URL that got through filtering: {clean_url}")
                                    self.save_processed_post(post_url, post_text="", post_type="skip", 
                                                           error_message="Photo URL blocked by safety filter")
                                    break
                                
                                # Check if URL is too short (likely broken)
                                if len(clean_url) < 80:
                                    logger.warning(f"🚫 BLOCKING suspiciously short URL: {clean_url}")
                                    self.save_processed_post(post_url, post_text="", post_type="skip", 
                                                           error_message="URL too short - likely broken")
                                    break
                                
                                self.driver.get(clean_url)
                                time.sleep(5)
                                
                                # Validate post accessibility before processing
                                if not self.is_post_accessible(clean_url):
                                    logger.info(f"❌ Skipping broken/removed post: {post_url}")
                                    self.save_processed_post(post_url, post_text="", post_type="skip", 
                                                           error_message="Post is broken/removed")
                                    break
                                
                                if not self.is_post_from_today():
                                    logger.info(f"Skipping post not from today: {post_url}")
                                    break
                                
                                post_text = self.get_post_text()
                                if not post_text.strip():
                                    logger.info(f"No post text found, marking as processed: {post_url}")
                                    self.save_processed_post(post_url, post_text="", error_message="No text extracted")
                                    break
                                
                                existing_comments = self.get_existing_comments()
                                logger.info(f"Found {len(existing_comments)} existing comments")
                                
                                # Extract author name for personalized comments
                                logger.info("🔍 Extracting post author name...")
                                post_author = self.get_post_author()
                                logger.info(f"🔍 Raw author name extracted: '{post_author}' (type: {type(post_author)})")
                                
                                if post_author:
                                    logger.info(f"✅ Post author found: {post_author}")
                                else:
                                    logger.warning("⚠️ No author name extracted, will use generic greeting")
                                
                                # Classify the post to determine the appropriate comment type
                                classification = self.classifier.classify_post(post_text)
                                logger.info(f"Post classified as: {classification.post_type} (score: {classification.confidence_score:.2f})")
                                
                                # Check if we should skip this post
                                if classification.should_skip:
                                    logger.info(f"Post filtered out. Reasoning: {'; '.join(classification.reasoning)}")
                                    self.save_processed_post(post_url, post_text=post_text, post_type="skip")
                                    break
                                
                                # Check if we already commented
                                if self.duplicate_detector.already_commented(existing_comments):
                                    logger.info("Bravo already commented. Skipping post.")
                                    self.save_processed_post(post_url, post_text=post_text, post_type="skip")
                                    break
                                
                                # Generate personalized comment using the updated method
                                logger.info(f"🔍 Generating comment for type: {classification.post_type}")
                                logger.info(f"🔍 Using author name: '{post_author}'")

                                # Use the comment generator directly with proper name handling
                                comment = self.comment_generator.generate_comment(classification.post_type, post_text, post_author)

                                if comment:
                                    logger.info(f"✅ Generated comment: {comment[:100]}...")
                                    
                                    # Check if author name was actually used in personalization
                                    if post_author:
                                        first_name = self.comment_generator.extract_first_name(post_author)
                                        if first_name and first_name in comment:
                                            logger.info(f"✅ First name '{first_name}' found in final comment")
                                        elif "Hi there!" in comment:
                                            logger.info(f"ℹ️ Using generic greeting (name validation failed)")
                                        else:
                                            logger.info(f"ℹ️ Comment generated with different personalization")
                                    else:
                                        logger.info(f"ℹ️ Comment generated without author name (generic greeting)")
                                else:
                                    logger.error("❌ Failed to generate comment")
                                
                                if not comment:
                                    logger.info(f"Skipping post (filtered or duplicate): {post_url}")
                                    logger.info(f"Post text length: {len(post_text)} characters")
                                    logger.info(f"Post text preview: {post_text[:200]}...")
                                    self.save_processed_post(post_url, post_text=post_text, post_type="skip")
                                    break
                                
                                logger.info(f"Generated comment: {comment[:100]}...")
                                
                                # Add to comment queue instead of posting directly
                                # ENSURE ALL PARAMETERS ARE STRINGS (not lists)
                                safe_post_url = str(post_url) if post_url else ""
                                safe_post_text = str(post_text) if post_text else ""
                                safe_comment_text = str(comment) if comment else ""
                                safe_post_type = classification.post_type
                                
                                logger.info(f"Parameter types before DB call:")
                                logger.info(f"  post_url: {type(safe_post_url)} = {safe_post_url[:50]}...")
                                logger.info(f"  post_text: {type(safe_post_text)} = {safe_post_text[:50]}...")
                                logger.info(f"  comment_text: {type(safe_comment_text)} = {safe_comment_text[:50]}...")
                                logger.info(f"  post_type: {type(safe_post_type)} = {safe_post_type}")
                                
                                try:
                                    queue_id = db.add_to_comment_queue(
                                        post_url=safe_post_url, 
                                        post_text=safe_post_text, 
                                        comment_text=safe_comment_text, 
                                        post_type=safe_post_type,
                                        post_screenshot="",          # ← Use empty string instead of None
                                        post_images="",              # ← Use empty string instead of None  
                                        post_author=post_author if post_author else "",  # ← Use actual author name
                                        post_engagement=""           # ← Use empty string instead of None
                                    )
                                    logger.info(f"🔄 Adding comment to approval queue: {post_url}")
                                    logger.info(f"🔄 Adding to comment queue: {safe_post_type} - {safe_post_url[:50]}...")
                                    logger.info(f"📝 Comment text: {safe_comment_text[:50]}...")
                                except Exception as db_error:
                                    logger.error(f"Failed to add comment to queue: {db_error}")
                                    logger.error(f"❌ Failed to add comment to database queue")
                                    logger.error(f"❌ Failed to queue comment for approval: {post_url}")
                                    # Continue processing instead of crashing
                                    self.save_processed_post(post_url, post_text=post_text, post_type="service", 
                                                           error_message=f"Database error: {db_error}")
                                    continue
                                if queue_id:
                                    logger.info(f"✅ Successfully added comment to queue (ID: {queue_id}): {post_url}")
                                    self.save_processed_post(post_url, post_text=post_text, post_type="service", 
                                                           comment_generated=True, comment_text=comment)
                                    new_posts += 1
                                else:
                                    logger.error(f"❌ Failed to add comment to queue: {post_url}")
                                    self.save_processed_post(post_url, post_text=post_text, post_type="service", 
                                                           error_message="Failed to queue comment")
                                break
                            except Exception as e:
                                if 'stale element reference' in str(e).lower():
                                    logger.warning(f"Stale element error while loading post, retrying ({retry_count+1}/3)...")
                                    retry_count += 1
                                    time.sleep(2)
                                    continue
                                else:
                                    logger.warning(f"Failed to process post: {post_url} | Reason: {e}")
                                    break
                    logger.info(f"Scan cycle complete. Commented on {new_posts} new posts. Starting next scan in 30 seconds...")
                    time.sleep(30)
        except Exception as e:
            logger.critical(f"Bot execution failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed.")

# Example for testing:
if __name__ == "__main__":
    # # Simulate a post and comments
    # post_text = "ISO: Who makes this ring in stock? Need CAD or casting help."
    # existing_comments = ["Looks great!", "Bravo Creations can help!"]
    # post_type = classify_post(post_text)
    # comment = pick_comment_template(post_type)
    # if comment:
    #     print("Bot would comment:", comment)
    # else:
    #     print("Bot would skip this post.")

    #
    bot = FacebookAICommentBot()
    bot.run()
