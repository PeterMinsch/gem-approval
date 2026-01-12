"""
Browser Manager Module
Handles WebDriver setup, login, navigation, and browser lifecycle
"""

import os
import time
import logging
import platform
import json
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

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

    def _find_chrome_binary(self) -> str:
        """Find Chrome binary path based on operating system"""
        system = platform.system().lower()

        if system == 'linux':
            # Common Chrome paths on Linux
            linux_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
                '/snap/bin/chromium',
                '/opt/google/chrome/chrome',
                '/usr/local/bin/google-chrome',
                '/usr/local/bin/chromium'
            ]

            for path in linux_paths:
                if os.path.exists(path):
                    logger.info(f"Found Chrome binary at: {path}")
                    return path

            # If no binary found, return None to let selenium auto-detect
            logger.warning("No Chrome binary found in common locations, letting selenium auto-detect")
            return None

        elif system == 'windows':
            # Windows Chrome paths
            windows_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
            ]

            for path in windows_paths:
                if os.path.exists(path):
                    logger.info(f"Found Chrome binary at: {path}")
                    return path

        elif system == 'darwin':  # macOS
            mac_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium'
            ]

            for path in mac_paths:
                if os.path.exists(path):
                    logger.info(f"Found Chrome binary at: {path}")
                    return path

        logger.warning(f"No Chrome binary found for {system}, letting selenium auto-detect")
        return None

    def _find_chromedriver_binary(self) -> str:
        """Find ChromeDriver binary path based on operating system"""
        system = platform.system().lower()

        if system == 'linux':
            # Common ChromeDriver paths on Linux
            linux_paths = [
                '/usr/bin/chromedriver',
                '/usr/local/bin/chromedriver',
                '/opt/chromedriver/chromedriver',
                './chromedriver'
            ]

            for path in linux_paths:
                if os.path.exists(path):
                    logger.info(f"Found ChromeDriver at: {path}")
                    return path

        elif system == 'windows':
            # Windows ChromeDriver paths
            windows_paths = [
                "chromedriver.exe",
                "C:\\chromedriver\\chromedriver.exe",
                "C:\\tools\\chromedriver.exe"
            ]

            for path in windows_paths:
                if os.path.exists(path):
                    logger.info(f"Found ChromeDriver at: {path}")
                    return path

        logger.info("No ChromeDriver found in common locations, letting selenium auto-detect")
        return None
    
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

                chrome_options = Options()
                # Run in headless mode for server environment
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-popup-blocking")
                chrome_options.add_argument("--disable-translate")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")

                # Configure user data directory for main browser (persistent sessions)
                chrome_data_dir = os.path.join(os.getcwd(), "chrome_data")
                chrome_options.add_argument(f"--user-data-dir={chrome_data_dir}")
                chrome_options.add_argument("--profile-directory=Default")
                logger.info(f"Main browser using user data directory: {chrome_data_dir}")

                # Auto-detect Chrome binary based on OS
                chrome_binary = self._find_chrome_binary()
                if chrome_binary:
                    chrome_options.binary_location = chrome_binary
                else:
                    logger.info("Using selenium auto-detection for Chrome binary")

                # Auto-detect ChromeDriver based on OS
                chromedriver_path = self._find_chromedriver_binary()
                if chromedriver_path:
                    service = Service(chromedriver_path)
                else:
                    # Let Selenium try to find ChromeDriver automatically
                    service = Service()

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

                    # Attempt automatic login if credentials are available
                    self._attempt_auto_login()

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
        Set up a second browser for posting comments with retry logic
        
        Returns:
            Configured Chrome WebDriver instance for posting
        """
        MAX_RETRIES = 3
        RETRY_WAIT = 3
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Setting up posting driver (attempt {attempt + 1}/{MAX_RETRIES})...")
                
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

                chrome_options = Options()
                # Run in NON-headless mode for posting browser to avoid Facebook bot detection
                # (Virtual display via Xvfb handles the visual output)
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-popup-blocking")
                chrome_options.add_argument("--disable-translate")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")

                # Configure separate user data directory for posting browser
                import uuid
                unique_id = uuid.uuid4().hex[:8]
                self._temp_chrome_dir = os.path.join(os.getcwd(), f"chrome_posting_temp_{unique_id}")
                os.makedirs(self._temp_chrome_dir, exist_ok=True)
                chrome_options.add_argument(f"--user-data-dir={self._temp_chrome_dir}")
                chrome_options.add_argument("--profile-directory=Default")
                logger.info(f"Posting browser using isolated user data directory: {self._temp_chrome_dir}")

                # Auto-detect Chrome binary based on OS
                chrome_binary = self._find_chrome_binary()
                if chrome_binary:
                    chrome_options.binary_location = chrome_binary
                else:
                    logger.info("Using selenium auto-detection for Chrome binary")

                # Auto-detect ChromeDriver based on OS
                chromedriver_path = self._find_chromedriver_binary()
                if chromedriver_path:
                    service = Service(chromedriver_path)
                else:
                    # Let Selenium try to find ChromeDriver automatically
                    service = Service()

                self.posting_driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Test the driver and copy session cookies for auto-login
                self.posting_driver.get("https://www.facebook.com")
                
                # Test driver health
                self.posting_driver.execute_script("return navigator.userAgent;")
                logger.info(f"✅ Posting driver connected successfully (session: {self.posting_driver.session_id[:8]}...)")
                
                # Independent authentication for posting driver
                logger.info("🔑 Setting up independent authentication for posting driver...")
                username = os.environ.get('FACEBOOK_USERNAME')
                password = os.environ.get('FACEBOOK_PASSWORD')

                if username and password:
                    # Create a temporary browser manager instance to use login method
                    temp_driver = self.posting_driver
                    original_driver = self.driver
                    self.driver = temp_driver  # Temporarily switch for login

                    try:
                        if self.login_to_facebook(username, password):
                            logger.info("✅ Independent login successful for posting driver")
                        else:
                            logger.warning("⚠️ Independent login failed for posting driver")
                    finally:
                        self.driver = original_driver  # Restore original driver
                else:
                    logger.warning("⚠️ No credentials available for posting driver login")

                logger.info("✅ Background posting Chrome driver set up successfully.")
                    
                return self.posting_driver
                
            except Exception as e:
                logger.warning(f"Posting driver setup attempt {attempt + 1} failed: {e}")
                
                # Cleanup failed driver
                if self.posting_driver:
                    try:
                        self.posting_driver.quit()
                    except:
                        pass
                    self.posting_driver = None
                
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Waiting {RETRY_WAIT} seconds before retry...")
                    time.sleep(RETRY_WAIT * (attempt + 1))
                else:
                    logger.error(f"❌ Failed to setup posting driver after {MAX_RETRIES} attempts")
                    return None

        return None

    def is_posting_driver_logged_in(self) -> bool:
        """Check if posting driver is logged in and can access Facebook"""
        if not self.posting_driver:
            return False

        try:
            # Store current posting driver as temp main driver for login check
            original_driver = self.driver
            self.driver = self.posting_driver

            try:
                # Use the same robust login verification
                is_logged_in = self._is_fully_logged_in()
                logger.debug(f"🔍 Posting driver login status: {is_logged_in}")
                return is_logged_in
            finally:
                self.driver = original_driver

        except Exception as e:
            logger.debug(f"🔍 Posting driver login check failed: {e}")
            return False
    

    


    def login_to_facebook(self, username: str, password: str) -> bool:
        """
        Login to Facebook using provided credentials
        Handles both full login and password re-confirmation scenarios

        Args:
            username: Facebook username/email
            password: Facebook password

        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info("Navigating to Facebook login page...")
            self.driver.get("https://www.facebook.com")
            time.sleep(3)

            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()

            # Check what type of authentication is needed
            logger.debug(f"Current URL: {current_url}")

            # Check if fully logged in (can access main content)
            if self._is_fully_logged_in():
                logger.info("General Facebook login detected - testing group access...")
                # Test actual group access instead of just general login
                group_url = self.config.get("POST_URL", "https://www.facebook.com/groups/5440421919361046")
                if self._can_access_group(group_url):
                    logger.info("✅ Already fully logged in to Facebook with group access")
                    return True
                else:
                    logger.warning("⚠️ General login detected but no group access - need authentication")

            # Check for password re-confirmation page
            if self._is_password_reconfirmation_page():
                logger.info("Detected password re-confirmation page")
                return self._handle_password_reconfirmation(password)

            # Check for full login page
            if self._is_full_login_page():
                logger.info("Detected full login page")
                return self._handle_full_login(username, password)

            logger.warning("Unknown Facebook page state - attempting full login")
            return self._handle_full_login(username, password)

        except Exception as e:
            logger.error(f"Error during Facebook login: {e}")
            return False

    def _is_fully_logged_in(self) -> bool:
        """Check if user is fully logged in and can access content"""
        try:
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()

            # Not logged in if on login page
            if "login" in current_url:
                logger.debug(f"🔍 Login check: On login page (URL: {current_url})")
                return False

            # Check for explicit login form elements (more reliable than page content)
            login_form_elements = [
                len(self.driver.find_elements(By.CSS_SELECTOR, "input[data-testid='royal-email']")) > 0,
                len(self.driver.find_elements(By.CSS_SELECTOR, "input[data-testid='royal-pass']")) > 0,
                len(self.driver.find_elements(By.CSS_SELECTOR, "button[data-testid='royal-login-button']")) > 0,
                len(self.driver.find_elements(By.NAME, "email")) > 0 and len(self.driver.find_elements(By.NAME, "pass")) > 0
            ]

            if any(login_form_elements):
                logger.debug("🔍 Login check: Login form elements detected")
                return False

            # Look for logged-in indicators (improved detection)
            logged_in_indicators = [
                "data-testid" in page_source and ("nav" in page_source or "navigation" in page_source),
                '"profile"' in page_source or '"home"' in page_source,
                "newsfeed" in page_source or "feed" in page_source,
                '"notifications"' in page_source and '"messages"' in page_source,
                "facebook.com" in current_url and "checkpoint" not in current_url and "help" not in current_url
            ]

            is_logged_in = any(logged_in_indicators)
            logger.debug(f"🔍 Login check: Logged-in indicators: {logged_in_indicators}, Result: {is_logged_in}")
            return is_logged_in
        except Exception as e:
            logger.debug(f"🔍 Login check failed: {e}")
            return False

    def _can_access_group(self, group_url: str) -> bool:
        """Test if we can actually access the target group (more reliable than general login check)"""
        try:
            logger.info(f"🔍 Testing group access: {group_url}")

            # Store current URL to restore later
            original_url = self.driver.current_url

            # Try to access the group
            self.driver.get(group_url)
            time.sleep(3)

            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()

            # Check if redirected to login
            if "login" in current_url:
                logger.info("❌ Group access test: Redirected to login")
                return False

            # Check for group-specific indicators
            group_access_indicators = [
                "/groups/" in current_url and "login" not in current_url,
                "group" in page_source and ("post" in page_source or "member" in page_source),
                "data-testid" in page_source and "feed" in page_source,
                "compose" in page_source or "write something" in page_source.replace(" ", ""),
                "share" in page_source and "comment" in page_source
            ]

            # Check for access denial indicators
            access_denied_indicators = [
                "join group" in page_source,
                "request to join" in page_source,
                "group is private" in page_source,
                "not authorized" in page_source,
                "blocked" in page_source
            ]

            has_access = any(group_access_indicators) and not any(access_denied_indicators)

            logger.info(f"🔍 Group access indicators: {group_access_indicators}")
            logger.info(f"🔍 Access denied indicators: {access_denied_indicators}")
            logger.info(f"🔍 Group access result: {has_access}")

            return has_access

        except Exception as e:
            logger.error(f"❌ Group access test failed: {e}")
            return False

    def _is_password_reconfirmation_page(self) -> bool:
        """Check if this is a password re-confirmation page"""
        try:
            page_source = self.driver.page_source.lower()

            # Look for password re-confirmation indicators
            reconfirm_indicators = [
                "enter your password to continue" in page_source,
                "confirm your password" in page_source,
                "please enter your password" in page_source
            ]

            # Check if password field exists but no email field
            has_password_field = len(self.driver.find_elements(By.NAME, "pass")) > 0
            has_email_field = len(self.driver.find_elements(By.NAME, "email")) > 0 or len(self.driver.find_elements(By.ID, "email")) > 0

            return any(reconfirm_indicators) or (has_password_field and not has_email_field)
        except:
            return False

    def _is_full_login_page(self) -> bool:
        """Check if this is a full login page with email and password"""
        try:
            # Look for both email and password fields using confirmed selectors
            has_email_field = (
                len(self.driver.find_elements(By.CSS_SELECTOR, "input[data-testid='royal-email']")) > 0 or
                len(self.driver.find_elements(By.NAME, "email")) > 0 or
                len(self.driver.find_elements(By.ID, "email")) > 0
            )
            has_password_field = (
                len(self.driver.find_elements(By.CSS_SELECTOR, "input[data-testid='royal-pass']")) > 0 or
                len(self.driver.find_elements(By.NAME, "pass")) > 0
            )

            return has_email_field and has_password_field
        except:
            return False

    def _handle_password_reconfirmation(self, password: str) -> bool:
        """Handle password re-confirmation page using updated selectors"""
        try:
            logger.info("Handling password re-confirmation...")

            # Find password field using the confirmed selector
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "pass"))
            )
            password_field.clear()
            password_field.send_keys(password)
            logger.debug("✅ Password entered")

            # Find and click submit button using the confirmed selector
            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-testid='sec_ac_button']"))
            )
            submit_button.click()
            logger.debug("✅ Submit button clicked")

            # Wait for page to process
            time.sleep(5)

            # Verify success
            if self._is_fully_logged_in():
                logger.info("✅ Password re-confirmation successful!")
                return True
            else:
                logger.error("❌ Password re-confirmation failed")
                return False

        except Exception as e:
            logger.error(f"Error during password re-confirmation: {e}")
            return False

    def _handle_full_login(self, username: str, password: str) -> bool:
        """Handle full login page with email and password using confirmed Facebook selectors"""
        try:
            logger.info("Handling full login...")

            # Try multiple selectors for email field (prioritizing confirmed ones)
            email_field = None
            email_selectors = [
                (By.CSS_SELECTOR, "input[data-testid='royal-email']"),  # ✅ Confirmed Facebook selector
                (By.ID, "email"),  # ✅ Confirmed from your elements
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "input[type='text'][name='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='Email']")
            ]

            for selector_type, selector_value in email_selectors:
                try:
                    email_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    logger.debug(f"✅ Email field found with selector: {selector_type}={selector_value}")
                    break
                except:
                    continue

            if not email_field:
                logger.error("❌ Could not find email field")
                return False

            email_field.clear()
            email_field.send_keys(username)
            logger.debug("✅ Email entered")

            # Find password field using confirmed selectors
            password_field = None
            password_selectors = [
                (By.CSS_SELECTOR, "input[data-testid='royal-pass']"),  # ✅ Confirmed Facebook selector
                (By.ID, "pass"),  # ✅ Confirmed from your elements
                (By.NAME, "pass"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]

            for selector_type, selector_value in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    logger.debug(f"✅ Password field found with selector: {selector_type}={selector_value}")
                    break
                except:
                    continue

            if not password_field:
                logger.error("❌ Could not find password field")
                return False

            password_field.clear()
            password_field.send_keys(password)
            logger.debug("✅ Password entered")

            # Find and click login button using confirmed selectors
            login_button = None
            login_selectors = [
                (By.CSS_SELECTOR, "button[data-testid='royal-login-button']"),  # ✅ Confirmed Facebook selector
                (By.NAME, "login"),  # ✅ Confirmed from your elements
                (By.ID, "u_0_b_Ra"),  # ✅ Your specific button ID (may change)
                (By.CSS_SELECTOR, "button[name='login']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']")
            ]

            for selector_type, selector_value in login_selectors:
                try:
                    login_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    logger.debug(f"✅ Login button found with selector: {selector_type}={selector_value}")
                    break
                except:
                    continue

            if not login_button:
                logger.error("❌ Could not find login button")
                return False

            login_button.click()
            logger.debug("✅ Login button clicked")

            # Wait for login to complete
            time.sleep(5)

            # Verify success
            if self._is_fully_logged_in():
                logger.info("✅ Full login successful!")
                return True
            else:
                logger.error("❌ Full login failed")
                return False

        except Exception as e:
            logger.error(f"Error during full login: {e}")
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
                import time
                # Force cleanup with retry logic for Windows file locks
                for attempt in range(3):
                    try:
                        shutil.rmtree(self._temp_chrome_dir)
                        logger.info(f"✅ Cleaned up posting browser temp directory: {self._temp_chrome_dir}")
                        break
                    except PermissionError as e:
                        if attempt < 2:
                            logger.debug(f"Retrying temp directory cleanup (attempt {attempt + 1}): {e}")
                            time.sleep(1)
                        else:
                            logger.warning(f"⚠️ Could not fully cleanup temp directory: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup temp directory: {e}")
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

    def _load_cookies_from_file(self) -> bool:
        """
        Load cookies from cookies.json file if it exists

        Returns:
            True if cookies loaded successfully and login verified, False otherwise
        """
        try:
            # Look for cookies.json in the bot directory
            bot_dir = os.path.dirname(os.path.dirname(__file__))
            cookies_path = os.path.join(bot_dir, 'cookies.json')

            if not os.path.exists(cookies_path):
                logger.debug(f"No cookies file found at {cookies_path}")
                return False

            logger.info(f"🍪 Found cookies file at {cookies_path}")

            with open(cookies_path, 'r') as f:
                cookies = json.load(f)

            if not cookies:
                logger.warning("Cookies file is empty")
                return False

            # First navigate to Facebook to set the domain
            self.driver.get("https://www.facebook.com")
            time.sleep(2)

            # Add each cookie
            cookies_added = 0
            for cookie in cookies:
                try:
                    # Selenium requires specific cookie format
                    selenium_cookie = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.facebook.com'),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', True),
                    }

                    # Only add expiry if it's not a session cookie
                    if not cookie.get('session', False) and 'expirationDate' in cookie:
                        selenium_cookie['expiry'] = int(cookie['expirationDate'])

                    self.driver.add_cookie(selenium_cookie)
                    cookies_added += 1
                except Exception as e:
                    logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")

            logger.info(f"🍪 Added {cookies_added}/{len(cookies)} cookies")

            # Refresh page to apply cookies
            self.driver.refresh()
            time.sleep(3)

            # Verify login worked
            if self._is_logged_in():
                logger.info("✅ Cookie login successful!")
                return True
            else:
                logger.warning("⚠️ Cookies loaded but login not verified")
                return False

        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False

    def _attempt_auto_login(self):
        """
        Attempt automatic login using cookies file first, then environment variables
        """
        try:
            # First try loading cookies from file
            if self._load_cookies_from_file():
                logger.info("✅ Logged in via cookies file!")
                return

            # Fall back to username/password login
            username = os.environ.get('FACEBOOK_USERNAME')
            password = os.environ.get('FACEBOOK_PASSWORD')

            if not username or not password:
                logger.debug("No Facebook credentials found in environment variables - skipping auto-login")
                return

            logger.info("🔑 Facebook credentials found - attempting automatic login...")

            # Use the existing login method
            if self.login_to_facebook(username, password):
                logger.info("✅ Automatic login successful!")
            else:
                logger.warning("⚠️ Automatic login failed - manual login may be required")

        except Exception as e:
            logger.warning(f"⚠️ Auto-login attempt failed: {e}")
            logger.debug("Manual login may be required")