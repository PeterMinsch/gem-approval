"""
Facebook Selectors Module
Centralized location for all CSS selectors and XPath expressions
"""


class FacebookSelectors:
    """Contains all Facebook DOM selectors"""
    
    # Post selectors
    POST_CONTAINER = "//div[@role='article']"
    POST_TEXT = ".//div[@data-ad-preview='message']"
    POST_AUTHOR = ".//strong[contains(@class, 'x1h6gzvc')]"
    POST_TIMESTAMP = ".//a[@role='link']//span[contains(text(), 'h') or contains(text(), 'm') or contains(text(), 'd')]"
    POST_PERMALINK = ".//a[contains(@href, '/groups/') and contains(@href, '/posts/')]"
    
    # Comment selectors
    COMMENT_BUTTON = ".//div[@aria-label='Leave a comment' or @aria-label='Comment']"
    COMMENT_BOX = "//div[@contenteditable='true' and @role='textbox']"
    COMMENT_SUBMIT = "//div[@aria-label='Comment' and @role='button']"
    EXISTING_COMMENTS = ".//div[@aria-label='Comment']//span[contains(@class, 'x193iq5w')]"
    
    # Image selectors
    POST_IMAGES = ".//img[contains(@src, 'scontent')]"
    IMAGE_UPLOAD_BUTTON = "//div[@aria-label='Attach a photo or video']"
    IMAGE_INPUT = "//input[@type='file' and @accept='image/*,video/*']"
    
    # Navigation selectors
    LOGIN_EMAIL = "//input[@id='email']"
    LOGIN_PASSWORD = "//input[@id='pass']"
    LOGIN_BUTTON = "//button[@name='login']"
    GROUP_FEED = "//div[@role='feed']"
    
    # Popup/Dialog selectors
    CLOSE_POPUP = "//div[@aria-label='Close']"
    DIALOG_DISMISS = "//div[@role='dialog']//div[@aria-label='Close']"
    
    # Action selectors
    LIKE_BUTTON = ".//div[@aria-label='Like']"
    SHARE_BUTTON = ".//div[@aria-label='Share']"
    MORE_OPTIONS = ".//div[@aria-label='More']"
    
    # Status indicators
    LOADING_SPINNER = "//div[@role='progressbar']"
    ERROR_MESSAGE = "//div[@role='alert']"
    SUCCESS_INDICATOR = "//div[contains(@class, 'success')]"
    
    @classmethod
    def get_selector(cls, selector_name: str) -> str:
        """
        Get a selector by name
        
        Args:
            selector_name: Name of the selector
            
        Returns:
            Selector string or empty string if not found
        """
        return getattr(cls, selector_name.upper(), "")