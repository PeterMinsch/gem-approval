"""
URL Normalization Utility
Provides centralized URL normalization for consistent duplicate detection across all bot modules
"""

import re
import logging

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize Facebook URLs for consistent duplicate detection and storage.
    
    This is the single source of truth for URL normalization across the entire bot.
    All modules should use this function to ensure consistent duplicate detection.
    
    Args:
        url: Raw Facebook URL that may contain tracking parameters
        
    Returns:
        Normalized URL string
        
    Rules:
        - For photo URLs (/photo/ with fbid=): Remove tracking params but keep fbid and set
        - For all other URLs: Remove all query parameters and fragments
        - Tracking params removed: __cft__, __tn__, notif_id, notif_t, ref, context
    """
    if not url:
        return url
        
    # For photo URLs, preserve fbid and set parameters but remove tracking
    if '/photo/' in url and 'fbid=' in url:
        # Remove tracking parameters but keep fbid and set
        norm_url = re.sub(r'&(__cft__(?:\[[^\]]*\])?|__tn__|notif_id|notif_t|ref)=[^&]*', '', url)
        norm_url = re.sub(r'&context=[^&]*', '', norm_url)
        return norm_url
    else:
        # For non-photo URLs, remove all query parameters and fragments
        norm_url = url.split('?')[0].split('#')[0] if url else url
        return norm_url