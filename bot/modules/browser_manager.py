"""
Browser Manager Module
Handles WebDriver setup, login, navigation, and browser lifecycle
"""

import os
import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Chrome WebDriver instances and browser operations"""
    
    def __init__(self, config: dict):
        """
        Initialize BrowserManager with configuration
        
        Args:
            config: Configuration dictionary with browser settings
        """
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.posting_driver: Optional[webdriver.Chrome] = None
        self._temp_chrome_dir: Optional[str] = None
    
    def setup_driver(self) -> webdriver.Chrome:
        """
        Setup main Chrome driver with connection validation and retry logic
        
        Returns:
            Configured Chrome WebDriver instance
            
        Raises:
            RuntimeError: If driver setup fails after all retries
        """
        MAX_RETRIES = 5
        RETRY_WAIT = 2
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Attempting to start Chrome driver (attempt {attempt + 1}/{MAX_RETRIES})...")
                
                # Set environment for Chrome stability
                os.environ['CHROME_LOG_FILE'] = 'nul'
                
                chrome_options = Options()
                # Use PROVEN working configuration from posting driver
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-popup-blocking")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--silent")
                
                # User data and profile settings
                user_data_dir = os.path.join(os.getcwd(), "chrome_data")
                chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
                chrome_options.add_argument(f"--profile-directory={self.config.get('CHROME_PROFILE', 'Default')}")
                
                # Set window size
                chrome_options.add_argument("--window-size=1920,1080")
                
                # Connection pool optimization arguments
                chrome_options.add_argument("--max-connections-per-host=10")
                chrome_options.add_argument("--max-connections-per-proxy=8") 
                chrome_options.add_argument("--aggressive-cache-discard")
                chrome_options.add_argument("--disable-background-networking")
                
                # Enable remote debugging on main port
                chrome_options.add_argument("--remote-debugging-port=9222")
                chrome_options.add_argument("--remote-debugging-address=127.0.0.1")
                
                service = Service(ChromeDriverManager().install())
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                # PERFORMANCE FIX: Reduced implicit wait to prevent 73-second delays
                # Use explicit waits (WebDriverWait) for specific elements instead
                self.driver.implicitly_wait(1)  # Reduced from 10 seconds
                self.driver.set_page_load_timeout(30)
                
                # Validate connection
                if not self.driver.session_id:
                    raise WebDriverException("Failed to establish WebDriver session")
                
                # Test the connection
                try:
                    self.driver.execute_script("return navigator.userAgent;")
                    logger.info(f"✅ Chrome driver connected successfully (session: {self.driver.session_id[:8]}...)")
                    return self.driver
                    
                except Exception as test_error:
                    logger.error(f"Driver created but not responding: {test_error}")
                    if self.driver:
                        self.driver.quit()
                    raise WebDriverException("Driver health check failed")
                    
            except WebDriverException as e:
                logger.warning(f"WebDriver connection attempt {attempt + 1} failed: {e}")
                
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Waiting {RETRY_WAIT} seconds before retry...")
                    time.sleep(RETRY_WAIT * (attempt + 1))
                else:
                    logger.error(f"Failed to setup Chrome Driver after {MAX_RETRIES} attempts")
                    raise RuntimeError(f"Unable to start WebDriver after {MAX_RETRIES} retries: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error setting up Chrome Driver: {e}")
                raise
    
    def setup_posting_driver(self) -> webdriver.Chrome:
        """
        Set up a second browser for posting comments
        
        Returns:
            Configured Chrome WebDriver instance for posting
        """
        try:
            # Clean up any existing driver first
            if self.posting_driver:
                try:
                    self.posting_driver.quit()
                except:
                    pass
                self.posting_driver = None
                
            # Clean up any existing temp directory
            if self._temp_chrome_dir:
                try:
                    import shutil
                    if os.path.exists(self._temp_chrome_dir):
                        shutil.rmtree(self._temp_chrome_dir)
                        logger.debug(f"Cleaned up temp directory: {self._temp_chrome_dir}")
                except Exception as e:
                    logger.debug(f"Failed to cleanup temp directory: {e}")
                self._temp_chrome_dir = None
            
            logger.info("Setting up Chrome driver for posting...")
            
            # Set environment for Chrome stability
            os.environ['CHROME_LOG_FILE'] = 'nul'
            
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--start-minimized")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--silent")
            
            # Use a separate profile directory
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            user_data_dir = os.path.join(os.getcwd(), f"chrome_posting_temp_{unique_id}")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument(f"--profile-directory=PostingProfile")
            
            self._temp_chrome_dir = user_data_dir
            
            service = Service(ChromeDriverManager().install())
            self.posting_driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Test the driver
            self.posting_driver.get("https://www.facebook.com")
            logger.info("✅ Background posting Chrome driver set up successfully.")
            return self.posting_driver
            
        except Exception as e:
            logger.error(f"❌ Failed to setup background posting Chrome Driver: {e}")
            self.posting_driver = None
            return None
    
    def login_to_facebook(self, username: str, password: str) -> bool:
        """
        Login to Facebook using provided credentials
        
        Args:
            username: Facebook username/email
            password: Facebook password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info("Navigating to Facebook login page...")
            self.driver.get("https://www.facebook.com")
            time.sleep(2)
            
            # Check if already logged in
            if "login" not in self.driver.current_url.lower():
                logger.info("Already logged in to Facebook")
                return True
            
            # Find and fill email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_field.clear()
            email_field.send_keys(username)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.ID, "pass")
            password_field.clear()
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login was successful
            if "login" not in self.driver.current_url.lower():
                logger.info("✅ Successfully logged in to Facebook")
                return True
            else:
                logger.error("❌ Failed to login to Facebook")
                return False
                
        except Exception as e:
            logger.error(f"Error during Facebook login: {e}")
            return False
    
    def navigate_to_group(self, group_url: str) -> bool:
        """
        Navigate to a Facebook group
        
        Args:
            group_url: URL of the Facebook group
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            logger.info(f"Navigating to group: {group_url}")
            self.driver.get(group_url)
            time.sleep(3)
            
            # Check if we're on the group page
            if "/groups/" in self.driver.current_url:
                logger.info("✅ Successfully navigated to group")
                return True
            else:
                logger.error("❌ Failed to navigate to group")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to group: {e}")
            return False
    
    def get_driver_status(self) -> dict:
        """
        Get current status of WebDriver instances
        
        Returns:
            Dictionary with driver status information
        """
        return {
            'main_driver': self.driver is not None,
            'posting_driver': self.posting_driver is not None,
            'session_id': self.driver.session_id if self.driver else None
        }
    
    def cleanup_drivers(self):
        """
        Clean up WebDriver instances and temporary directories
        """
        # Clean up main driver
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Main driver closed")
            except Exception as e:
                logger.debug(f"Error closing main driver: {e}")
            self.driver = None
        
        # Clean up posting driver
        if self.posting_driver:
            try:
                self.posting_driver.quit()
                logger.info("Posting driver closed")
            except Exception as e:
                logger.debug(f"Error closing posting driver: {e}")
            self.posting_driver = None
        
        # Clean up temp directory
        if self._temp_chrome_dir and os.path.exists(self._temp_chrome_dir):
            try:
                import shutil
                shutil.rmtree(self._temp_chrome_dir)
                logger.debug(f"Cleaned up temp directory: {self._temp_chrome_dir}")
            except Exception as e:
                logger.debug(f"Failed to cleanup temp directory: {e}")
            self._temp_chrome_dir = None
    
    def is_driver_healthy(self) -> bool:
        """
        Check if main WebDriver connection is still alive
        
        Returns:
            True if driver is healthy, False otherwise
        """
        try:
            if not self.driver:
                return False
            self.driver.current_url
            return True
        except Exception as e:
            logger.debug(f"Driver health check failed: {e}")
            return False
    
    def reconnect_driver_if_needed(self):
        """
        Reconnect driver if connection is lost
        """
        if not self.is_driver_healthy():
            logger.warning("Driver connection lost, attempting to reconnect...")
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.debug(f"Error closing old driver: {e}")
            self.setup_driver()
            logger.info("Driver reconnection completed")