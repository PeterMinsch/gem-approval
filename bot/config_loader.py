"""
Dynamic configuration loader that merges database settings with base config
This module ensures the classifier uses settings from the database instead of hardcoded values
"""
from bravo_config import CONFIG
from database import db
import logging

logger = logging.getLogger(__name__)

def get_dynamic_config():
    """
    Load configuration with database overrides.
    Returns merged config with database settings taking precedence.
    Falls back to hardcoded CONFIG if database is unavailable.
    """
    # Start with base config
    config = CONFIG.copy()
    
    # Load settings from database
    try:
        db_settings = db.get_settings()
        
        if db_settings:
            logger.info("Loading keyword settings from database")
            
            # Override keyword lists from database
            keyword_fields = [
                'negative_keywords', 
                'service_keywords', 
                'iso_keywords', 
                'brand_blacklist', 
                'allowed_brand_modifiers'
            ]
            
            for field in keyword_fields:
                if field in db_settings and db_settings[field]:
                    # Database returns these as lists already (JSON deserialized)
                    config[field] = db_settings[field]
                    logger.debug(f"Loaded {len(db_settings[field])} {field} from database")
            
            # Update rate limit settings
            if 'scan_refresh_minutes' in db_settings and db_settings['scan_refresh_minutes']:
                config['rate_limits']['scan_refresh_minutes'] = db_settings['scan_refresh_minutes']
                config['post_processing']['cycle_wait_time'] = db_settings['scan_refresh_minutes'] * 60
                logger.debug(f"Set scan_refresh_minutes to {db_settings['scan_refresh_minutes']}")
                
            if 'max_comments_per_account_per_day' in db_settings and db_settings['max_comments_per_account_per_day']:
                config['rate_limits']['per_account_per_day'] = db_settings['max_comments_per_account_per_day']
                logger.debug(f"Set max_comments_per_account_per_day to {db_settings['max_comments_per_account_per_day']}")
            
            # Update other settings if present
            if 'register_url' in db_settings and db_settings['register_url']:
                config['register_url'] = db_settings['register_url']
                
            if 'phone' in db_settings and db_settings['phone']:
                config['phone'] = db_settings['phone']
                
            if 'ask_for' in db_settings and db_settings['ask_for']:
                config['ask_for'] = db_settings['ask_for']
                
            logger.info("Successfully loaded configuration from database")
        else:
            logger.warning("No settings found in database, using hardcoded defaults")
            
    except Exception as e:
        logger.warning(f"Failed to load database settings, using hardcoded defaults: {e}")
    
    return config

def get_cached_dynamic_config():
    """
    Get dynamic config with caching to avoid repeated database calls.
    Cache expires after 5 minutes or on explicit refresh.
    """
    # For now, just return fresh config
    # Future enhancement: Add caching with TTL
    return get_dynamic_config()