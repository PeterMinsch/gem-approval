"""
Safety Monitor Module
Handles rate limiting, duplicate detection, and safety checks
"""

import time
import logging
from typing import List, Dict, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SafetyMonitor:
    """Monitors and enforces safety constraints"""
    
    def __init__(self, config: dict):
        """
        Initialize SafetyMonitor
        
        Args:
            config: Configuration dictionary with safety settings
        """
        self.config = config
        self.action_history: List[dict] = []
        self.processed_posts: Set[str] = set()
        self.last_action_time = None
    
    def check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits
        
        Returns:
            True if safe to proceed, False if rate limit reached
        """
        # Check time since last action
        if self.last_action_time:
            time_diff = time.time() - self.last_action_time
            min_interval = self.config.get('MIN_ACTION_INTERVAL', 30)  # 30 seconds default
            
            if time_diff < min_interval:
                logger.warning(f"Rate limit: Only {time_diff:.1f}s since last action (min: {min_interval}s)")
                return False
        
        # Check actions per hour
        one_hour_ago = time.time() - 3600
        recent_actions = [a for a in self.action_history if a.get('timestamp', 0) > one_hour_ago]
        max_per_hour = self.config.get('MAX_ACTIONS_PER_HOUR', 20)
        
        if len(recent_actions) >= max_per_hour:
            logger.warning(f"Rate limit: {len(recent_actions)} actions in last hour (max: {max_per_hour})")
            return False
            
        return True
    
    def record_action(self, action_type: str, details: dict):
        """
        Record an action for rate limiting and monitoring
        
        Args:
            action_type: Type of action (comment, scan, etc.)
            details: Additional details about the action
        """
        action_record = {
            'timestamp': time.time(),
            'action_type': action_type,
            'details': details
        }
        
        self.action_history.append(action_record)
        self.last_action_time = time.time()
        
        # Keep only last 100 actions to prevent memory bloat
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-100:]
            
        logger.debug(f"Recorded action: {action_type}")
    
    def check_blacklist(self, text: str) -> bool:
        """
        Check if text contains blacklisted content
        
        Args:
            text: Text to check
            
        Returns:
            True if text is safe, False if blacklisted
        """
        if not text:
            return True
            
        text_lower = text.lower()
        
        # Check negative keywords
        negative_keywords = self.config.get('negative_keywords', [])
        for keyword in negative_keywords:
            if keyword.lower() in text_lower:
                logger.warning(f"Blacklisted keyword found: {keyword}")
                return False
                
        # Check brand blacklist
        brand_blacklist = self.config.get('brand_blacklist', [])
        for brand in brand_blacklist:
            if brand.lower() in text_lower:
                # Check if there are allowed modifiers
                modifiers = self.config.get('allowed_brand_modifiers', [])
                has_modifier = any(mod.lower() in text_lower for mod in modifiers)
                if not has_modifier:
                    logger.warning(f"Blacklisted brand without modifier: {brand}")
                    return False
                    
        return True
    
    def is_safe_to_comment(self) -> bool:
        """
        Check if it's safe to post a comment
        
        Returns:
            True if safe to comment, False otherwise
        """
        # Check rate limits
        if not self.check_rate_limit():
            return False
            
        # Check if we've had too many failures recently
        one_hour_ago = time.time() - 3600
        recent_failures = [
            a for a in self.action_history 
            if (a.get('timestamp', 0) > one_hour_ago and 
                a.get('action_type') == 'comment' and 
                a.get('details', {}).get('success') is False)
        ]
        
        if len(recent_failures) > 5:
            logger.warning(f"Too many recent failures: {len(recent_failures)}")
            return False
            
        return True
    
    def add_processed_post(self, post_id: str):
        """
        Mark a post as processed
        
        Args:
            post_id: ID or URL of the processed post
        """
        self.processed_posts.add(post_id)
    
    def is_post_processed(self, post_id: str) -> bool:
        """
        Check if a post has already been processed
        
        Args:
            post_id: ID or URL of the post
            
        Returns:
            True if already processed, False otherwise
        """
        return post_id in self.processed_posts
    
    def get_safety_stats(self) -> dict:
        """
        Get safety monitoring statistics
        
        Returns:
            Dictionary with safety statistics
        """
        return {
            'processed_posts': len(self.processed_posts),
            'actions_today': len([a for a in self.action_history 
                                if a.get('timestamp', 0) > time.time() - 86400]),
            'last_action': self.last_action_time,
            'rate_limit_status': 'OK'  # Will be implemented
        }