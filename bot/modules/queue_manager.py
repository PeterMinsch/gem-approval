"""
Queue Manager Module
Handles approval queue and posting queue management
"""

import queue
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages comment approval and posting queues"""
    
    def __init__(self, config: dict, database=None):
        """
        Initialize QueueManager
        
        Args:
            config: Configuration dictionary
            database: Database connection (optional)
        """
        self.config = config
        self.db = database
        self.approval_queue: List[dict] = []
        self.posting_queue = queue.Queue()
    
    def add_to_approval_queue(self, comment_data: dict) -> str:
        """
        Add a comment to the approval queue
        
        Args:
            comment_data: Dictionary containing comment information
            
        Returns:
            Comment ID
        """
        comment_id = str(uuid.uuid4())[:8]
        comment_data['id'] = comment_id
        comment_data['status'] = 'pending'
        comment_data['created_at'] = datetime.now()
        
        self.approval_queue.append(comment_data)
        
        if self.db:
            try:
                self.db.add_to_comment_queue(
                    post_url=comment_data.get('post_url', ''),
                    comment_text=comment_data.get('comment', ''),
                    post_text=comment_data.get('post_text', ''),
                    author_name=comment_data.get('author_name', ''),
                    post_type=comment_data.get('post_type', 'general'),
                    images_json=comment_data.get('images', '[]')
                )
            except Exception as e:
                logger.error(f"Failed to add to database queue: {e}")
        
        logger.info(f"Added comment {comment_id} to approval queue")
        return comment_id
    
    def get_pending_comments(self) -> List[dict]:
        """
        Get all pending comments awaiting approval
        
        Returns:
            List of pending comment dictionaries
        """
        if self.db:
            try:
                return self.db.get_pending_comments()
            except Exception as e:
                logger.error(f"Failed to get pending comments from database: {e}")
        
        # Fallback to in-memory queue
        return [c for c in self.approval_queue if c.get('status') == 'pending']
    
    def approve_comment(self, comment_id: str, edited_text: Optional[str] = None) -> bool:
        """
        Approve a comment for posting
        
        Args:
            comment_id: ID of the comment to approve
            edited_text: Optional edited comment text
            
        Returns:
            True if approved successfully, False otherwise
        """
        try:
            if self.db:
                status = self.db.update_comment_status(
                    int(comment_id), 
                    'approved', 
                    edited_comment=edited_text
                )
                return status
            else:
                # Update in-memory queue
                for comment in self.approval_queue:
                    if comment.get('id') == comment_id:
                        comment['status'] = 'approved'
                        if edited_text:
                            comment['comment'] = edited_text
                        return True
                        
        except Exception as e:
            logger.error(f"Failed to approve comment {comment_id}: {e}")
            
        return False
    
    def reject_comment(self, comment_id: str, reason: str) -> bool:
        """
        Reject a comment
        
        Args:
            comment_id: ID of the comment to reject
            reason: Reason for rejection
            
        Returns:
            True if rejected successfully, False otherwise
        """
        try:
            if self.db:
                return self.db.update_comment_status(
                    int(comment_id), 
                    'rejected', 
                    error_message=reason
                )
            else:
                # Update in-memory queue
                for comment in self.approval_queue:
                    if comment.get('id') == comment_id:
                        comment['status'] = 'rejected'
                        comment['rejection_reason'] = reason
                        return True
                        
        except Exception as e:
            logger.error(f"Failed to reject comment {comment_id}: {e}")
            
        return False
    
    def add_to_posting_queue(self, comment_data: dict) -> bool:
        """
        Add approved comment to posting queue
        
        Args:
            comment_data: Comment data to post
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            post_url = comment_data.get('post_url')
            comment_text = comment_data.get('comment')
            comment_id = comment_data.get('id')
            images = comment_data.get('images', [])
            
            if images:
                self.posting_queue.put((post_url, comment_text, comment_id, images))
            else:
                self.posting_queue.put((post_url, comment_text, comment_id))
                
            logger.info(f"Added comment {comment_id} to posting queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to posting queue: {e}")
            return False
    
    def get_queue_stats(self) -> dict:
        """
        Get statistics about the queues
        
        Returns:
            Dictionary with queue statistics
        """
        return {
            'pending': len(self.approval_queue),
            'posting_queue_size': self.posting_queue.qsize(),
            'approved_today': 0,  # Will be implemented
            'rejected_today': 0   # Will be implemented
        }