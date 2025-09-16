"""
Browser Manager Module
Handles WebDriver setup, login, navigation, and browser lifecycle
"""

import os
import time
import logging
import platform
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
                
                # Copy session cookies from main driver to enable auto-login (if main driver available)
                logger.debug(f"🔍 Checking drivers for cookie copy - Main driver: {self.driver is not None}, Posting driver: {self.posting_driver is not None}")
                
                if self.driver:
                    if self._copy_session_cookies():
                        logger.info("✅ Background posting Chrome driver set up successfully with auto-login.")
                    else:
                        logger.warning("⚠️ Cookie copying failed - check debug logs above")
                        logger.info("✅ Background posting Chrome driver set up successfully (manual login may be required).")
                else:
                    logger.info("ℹ️ Main driver not yet available - posting driver ready for manual login or later cookie sync")
                    logger.info("✅ Background posting Chrome driver set up successfully (manual login may be required).")
                    
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
    
    def sync_posting_driver_session(self) -> bool:
        """
        Sync session cookies from main driver to posting driver after both are available

        Returns:
            True if sync successful, False otherwise
        """
        if not self.driver or not self.posting_driver:
            logger.warning("Cannot sync sessions: one or both drivers not available")
            return False

        logger.info("🔄 Syncing session cookies to posting driver...")
        success = self._copy_session_cookies()

        if success:
            logger.info("🎉 Session sync successful - posting driver now logged in!")
        else:
            logger.warning("⚠️ Session sync failed - posting driver may require manual login")

        return success

    def sync_main_driver_session(self) -> bool:
        """
        Sync session cookies from posting driver to main driver when posting driver is logged in

        Returns:
            True if sync successful, False otherwise
        """
        if not self.driver or not self.posting_driver:
            logger.warning("Cannot sync sessions: one or both drivers not available")
            return False

        logger.info("🔄 Syncing session cookies from posting driver to main driver...")
        success = self._copy_session_cookies_reverse()

        if success:
            logger.info("🎉 Reverse session sync successful - main driver now logged in!")
            # Navigate to the group page after successful login
            try:
                target_url = self.config.get("POST_URL", "https://www.facebook.com/groups/5440421919361046")
                logger.info(f"Navigating to: {target_url}")
                self.driver.get(target_url)
                time.sleep(3)
                logger.info("✅ Successfully navigated to Facebook group after login")
            except Exception as e:
                logger.warning(f"Failed to navigate after login: {e}")
        else:
            logger.warning("⚠️ Reverse session sync failed - main driver still needs login")

        return success
    
    def _copy_session_cookies(self) -> bool:
        """
        Copy session cookies from main driver to posting driver for auto-login
        
        Returns:
            True if cookies copied successfully, False otherwise
        """
        logger.debug("🚀 _copy_session_cookies() method started")
        try:
            if not self.driver or not self.posting_driver:
                logger.warning("Cannot copy cookies: one or both drivers not available")
                logger.debug(f"Driver states - Main: {self.driver is not None}, Posting: {self.posting_driver is not None}")
                return False
            
            logger.info("🔄 Attempting to copy session cookies for auto-login...")
            
            # Store current main driver URL to restore later
            main_current_url = self.driver.current_url
            
            # Navigate main driver to Facebook base page to get all cookies
            if not main_current_url.startswith("https://www.facebook.com"):
                logger.debug("Main driver not on Facebook, navigating...")
                self.driver.get("https://www.facebook.com")
                time.sleep(3)
            
            # Get all cookies from main driver
            main_cookies = self.driver.get_cookies()
            logger.info(f"📋 Found {len(main_cookies)} cookies in main driver")
            
            if len(main_cookies) == 0:
                logger.warning("⚠️ No cookies found in main driver - user may not be logged in")
                return False
            
            # Navigate posting driver to Facebook base page before adding cookies
            self.posting_driver.get("https://www.facebook.com")
            time.sleep(2)
            
            # Copy cookies to posting driver
            copied_count = 0
            failed_cookies = []
            important_cookies = []
            
            for cookie in main_cookies:
                try:
                    cookie_name = cookie.get('name', 'unknown')
                    
                    # Track important Facebook session cookies
                    if cookie_name in ['c_user', 'xs', 'datr', 'sb', 'fr', 'presence']:
                        important_cookies.append(cookie_name)
                    
                    # Create a clean cookie dict
                    clean_cookie = {
                        'name': cookie_name,
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.facebook.com')
                    }
                    
                    # Add optional fields if they exist and are valid
                    if 'path' in cookie and cookie['path']:
                        clean_cookie['path'] = cookie['path']
                    if 'secure' in cookie:
                        clean_cookie['secure'] = cookie['secure']
                    if 'httpOnly' in cookie:
                        clean_cookie['httpOnly'] = cookie['httpOnly']
                    if 'expiry' in cookie and cookie['expiry'] is not None:
                        clean_cookie['expiry'] = cookie['expiry']
                    
                    self.posting_driver.add_cookie(clean_cookie)
                    copied_count += 1
                    logger.debug(f"✅ Copied cookie: {cookie_name} (domain: {clean_cookie['domain']})")
                    
                except Exception as cookie_error:
                    failed_cookies.append(cookie_name)
                    logger.debug(f"❌ Failed to copy cookie {cookie_name}: {cookie_error}")
            
            logger.info(f"✅ Successfully copied {copied_count}/{len(main_cookies)} cookies")
            logger.debug(f"🔑 Important session cookies found: {important_cookies}")
            
            if failed_cookies:
                logger.warning(f"❌ Failed cookies: {', '.join(failed_cookies)}")
                
            # Check if critical session cookies were copied
            if not any(cookie in important_cookies for cookie in ['c_user', 'xs']):
                logger.warning("⚠️ Critical session cookies (c_user, xs) may be missing!")
            
            # Refresh the posting driver to apply cookies
            logger.debug("🔄 Refreshing posting driver to apply cookies...")
            self.posting_driver.refresh()
            time.sleep(3)
            
            # Check if login was successful with multiple methods
            page_source = self.posting_driver.page_source.lower()
            current_url = self.posting_driver.current_url.lower()
            
            # Debug: Log key information for troubleshooting
            logger.debug(f"🔍 Login verification - Current URL: {current_url}")
            logger.debug(f"🔍 Page source length: {len(page_source)} characters")
            
            # Check for specific key indicators with detailed logging
            login_checks = {
                "home_in_source": "home" in page_source,
                "newsfeed_in_source": "newsfeed" in page_source,
                "timeline_in_source": "timeline" in page_source,
                "profile_in_source": "profile" in page_source,
                "navigation_menu": "navigation" in page_source and "menu" in page_source,
                "home_in_url": "/home" in current_url,
                "no_login_form": not ("login" in page_source and "password" in page_source and "email" in page_source)
            }
            
            # Log each check result
            for check_name, result in login_checks.items():
                logger.debug(f"🔍 {check_name}: {result}")
            
            # Check for Facebook-specific logged-in elements
            fb_logged_in_indicators = [
                'data-testid="feed_story"' in page_source,
                'role="main"' in page_source and 'feed' in page_source,
                'composer' in page_source,
                'notifications' in page_source and 'messages' in page_source,
                current_url.startswith('https://www.facebook.com') and 'login' not in current_url
            ]
            
            logger.debug(f"🔍 Facebook-specific checks: {fb_logged_in_indicators}")
            
            # Multiple login verification checks
            login_indicators = list(login_checks.values()) + fb_logged_in_indicators
            is_logged_in = any(login_indicators)
            
            # Additional check: look for specific login failure indicators
            login_failure_signs = [
                "log in to facebook" in page_source,
                "enter your email" in page_source,
                "enter your password" in page_source,
                'input[name="email"]' in page_source,
                'input[name="pass"]' in page_source,
                "/login" in current_url
            ]
            
            has_login_failure = any(login_failure_signs)
            logger.debug(f"🔍 Login failure indicators: {login_failure_signs} -> {has_login_failure}")
            
            # Final determination
            if is_logged_in and not has_login_failure:
                logger.info("🎉 Auto-login successful - posting driver logged in!")
                success = True
            else:
                logger.warning("⚠️ Cookie copy completed but login verification failed")
                logger.debug(f"🔍 Login indicators passed: {sum(login_indicators)}/{len(login_indicators)}")
                logger.debug(f"🔍 Login failure detected: {has_login_failure}")
                success = False
            
            # Restore main driver to original URL if changed
            if main_current_url != self.driver.current_url:
                logger.debug("Restoring main driver to original URL...")
                self.driver.get(main_current_url)
            
            return success
                
        except Exception as e:
            logger.error(f"❌ Failed to copy session cookies: {e}")
            return False

    def _copy_session_cookies_reverse(self) -> bool:
        """
        Copy session cookies from posting driver to main driver (reverse direction)
        Uses timeout-resistant approach to handle Chrome renderer issues.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug("🚀 _copy_session_cookies_reverse() method started")

            # Get cookies from posting driver
            logger.info("📋 Getting cookies from posting driver...")
            posting_cookies = self.posting_driver.get_cookies()

            logger.info(f"📋 Found {len(posting_cookies)} cookies in posting driver")

            if not posting_cookies:
                logger.warning("⚠️ No cookies found in posting driver")
                return False

            # Try to navigate to Facebook with timeout protection
            navigation_success = False
            try:
                logger.debug("🌐 Attempting to navigate to Facebook (with timeout protection)...")

                # Set a shorter page load timeout to avoid hanging
                original_timeout = self.driver.timeouts.page_load
                self.driver.set_page_load_timeout(15)  # 15 second timeout

                self.driver.get("https://www.facebook.com")
                navigation_success = True
                logger.debug("✅ Successfully navigated to Facebook")

                # Restore original timeout
                self.driver.set_page_load_timeout(original_timeout)

            except Exception as nav_error:
                logger.warning(f"⚠️ Navigation to Facebook failed: {nav_error}")
                logger.info("🔄 Continuing with cookie copy without navigation...")

                # Restore original timeout in case it was changed
                try:
                    self.driver.set_page_load_timeout(original_timeout)
                except:
                    pass

            # Copy each cookie to main driver (works regardless of navigation success)
            successful_copies = 0
            logger.info("🍪 Copying cookies from posting driver...")

            for cookie in posting_cookies:
                try:
                    # Filter cookies to only Facebook domains if possible
                    if navigation_success or not cookie.get('domain') or 'facebook' in cookie.get('domain', ''):
                        self.driver.add_cookie(cookie)
                        logger.debug(f"✅ Copied cookie: {cookie['name']} (domain: {cookie.get('domain', 'unknown')})")
                        successful_copies += 1
                    else:
                        logger.debug(f"⚠️ Skipped cookie (domain mismatch): {cookie['name']}")
                except Exception as e:
                    logger.debug(f"⚠️ Failed to copy cookie {cookie['name']}: {e}")
                    continue

            logger.info(f"✅ Successfully copied {successful_copies}/{len(posting_cookies)} cookies to main driver")

            # If we have some cookies, try a gentle refresh (with timeout protection)
            if successful_copies > 0:
                try:
                    logger.debug("🔄 Refreshing page to apply cookies...")
                    self.driver.refresh()
                    time.sleep(2)
                except Exception as refresh_error:
                    logger.warning(f"⚠️ Page refresh failed: {refresh_error}")

            # Verify the login worked by checking for critical cookies
            try:
                main_cookies = self.driver.get_cookies()
                main_cookie_names = [c['name'] for c in main_cookies]

                critical_cookies = ['fr', 'sb', 'datr']
                found_critical = [name for name in critical_cookies if name in main_cookie_names]

                logger.debug(f"🔑 Session cookies found: {found_critical}")

                # Consider it successful if we copied some cookies
                success = successful_copies > 0 and len(found_critical) > 0

                if success:
                    logger.info("🎉 Reverse session sync successful - cookies applied!")
                else:
                    logger.warning("⚠️ Session sync completed but may not be fully successful")

                return success

            except Exception as verify_error:
                logger.warning(f"⚠️ Cookie verification failed: {verify_error}")
                # Still consider it successful if we copied cookies
                return successful_copies > 0

        except Exception as e:
            logger.error(f"❌ Failed to copy session cookies in reverse: {e}")
            return False

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

    def _attempt_auto_login(self):
        """
        Attempt automatic login using environment variables if available
        """
        import os

        try:
            # Get credentials from environment variables
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