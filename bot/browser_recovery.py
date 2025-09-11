import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BrowserRecovery:
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.failure_counts: Dict[str, int] = {}
        self.max_failures = 3
        
    def handle_browser_failure(self, session_id: str, error: Exception):
        """Handle browser failures with recovery"""
        self.failure_counts[session_id] = self.failure_counts.get(session_id, 0) + 1
        
        logger.error(f"Browser failure for session {session_id}: {error}")
        
        if self.failure_counts[session_id] >= self.max_failures:
            logger.error(f"Max failures reached for session {session_id}, disabling")
            return False
            
        # Clean up and recreate browser
        self.browser_manager._cleanup_browser(session_id)
        time.sleep(2)  # Brief pause before recreation
        
        try:
            new_browser = self.browser_manager._create_messenger_browser(session_id)
            self.browser_manager.messenger_browsers[session_id] = new_browser
            logger.info(f"Browser recreated for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to recreate browser for session {session_id}: {e}")
            return False
    
    def reset_failure_count(self, session_id: str):
        """Reset failure count after successful operation"""
        if session_id in self.failure_counts:
            del self.failure_counts[session_id]