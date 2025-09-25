"""
Browser Manager Module
Handles WebDriver setup, login, navigation, and browser lifecycle
"""

import os
import time
import logging
import asyncio
from typing import Optional, Literal
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class BrowserOperation(Enum):
    """Enum for tracking current browser operation state"""
    IDLE = "idle"
    POSTING = "posting"
    MESSAGING = "messaging"
    SCANNING = "scanning"


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

        # Browser operation state management
        self.current_operation: BrowserOperation = BrowserOperation.IDLE
        self.operation_lock = asyncio.Lock()
        self._last_url: Optional[str] = None
        self._operation_timeout = 30  # seconds

    async def request_browser_for_operation(self, operation: BrowserOperation, timeout: Optional[float] = None) -> bool:
        """
        Request exclusive access to the posting browser for a specific operation.

        Args:
            operation: The type of operation requesting browser access
            timeout: Optional timeout in seconds (defaults to self._operation_timeout)

        Returns:
            True if browser access granted, False if timeout or conflict
        """
        timeout = timeout or self._operation_timeout

        try:
            # Try to acquire lock with timeout
            await asyncio.wait_for(self.operation_lock.acquire(), timeout=timeout)

            # Check if we can safely switch operations
            if self.current_operation != BrowserOperation.IDLE:
                logger.warning(f"Browser busy with {self.current_operation.value}, requested for {operation.value}")
                self.operation_lock.release()
                return False

            # Store current URL for restoration
            if self.posting_driver and hasattr(self.posting_driver, 'current_url'):
                try:
                    self._last_url = self.posting_driver.current_url
                except Exception as e:
                    logger.debug(f"Could not get current URL: {e}")
                    self._last_url = None

            # Set new operation state
            self.current_operation = operation
            logger.info(f"🔒 Browser locked for {operation.value} operation")
            return True

        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for browser access for {operation.value}")
            return False
        except Exception as e:
            logger.error(f"Error requesting browser for {operation.value}: {e}")
            return False

    def release_browser_from_operation(self, operation: BrowserOperation, restore_url: bool = True) -> None:
        """
        Release browser access after completing an operation.

        Args:
            operation: The operation that is releasing the browser
            restore_url: Whether to restore the previous URL
        """
        try:
            if self.current_operation != operation:
                logger.warning(f"Operation mismatch: expected {operation.value}, current {self.current_operation.value}")

            # Restore previous URL if requested and available
            if restore_url and self._last_url and self.posting_driver:
                try:
                    if self.posting_driver.current_url != self._last_url:
                        logger.info(f"🔄 Restoring URL: {self._last_url}")
                        self.posting_driver.get(self._last_url)
                        time.sleep(1)  # Allow page to load
                except Exception as e:
                    logger.warning(f"Could not restore URL {self._last_url}: {e}")

            # Reset state
            self.current_operation = BrowserOperation.IDLE
            self._last_url = None

            # Release lock
            if self.operation_lock.locked():
                self.operation_lock.release()
                logger.info(f"🔓 Browser released from {operation.value} operation")

        except Exception as e:
            logger.error(f"Error releasing browser from {operation.value}: {e}")

    def get_posting_browser_for_messaging(self) -> Optional[webdriver.Chrome]:
        """
        Get the posting browser for messaging operations.
        Should only be called after successful request_browser_for_operation.

        Returns:
            Posting browser instance if available and operation is MESSAGING
        """
        if self.current_operation != BrowserOperation.MESSAGING:
            logger.error(f"Invalid browser access: current operation is {self.current_operation.value}, not messaging")
            return None

        if not self.posting_driver:
            logger.error("Posting driver not available for messaging")
            return None

        return self.posting_driver

    def request_browser_for_posting_sync(self, timeout: Optional[float] = None) -> bool:
        """
        Synchronous wrapper for requesting browser for posting operations.
        Uses asyncio to handle the async lock.

        Returns:
            True if browser access granted, False otherwise
        """
        try:
            # Create event loop if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async method
            return loop.run_until_complete(
                self.request_browser_for_operation(BrowserOperation.POSTING, timeout)
            )
        except Exception as e:
            logger.error(f"Error in sync posting browser request: {e}")
            return False

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

                # CRITICAL FIX: Use EXACT same configuration as working diagnostic script
                # These 5 flags are proven to work on your server + single-process to avoid renderer timeouts
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--single-process")  # Eliminate renderer timeouts

                # Use temporary profile (same as diagnostic)
                import tempfile
                user_data_dir = tempfile.mkdtemp(prefix="chrome_main_profile_")
                chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

                logger.info(f"🔧 Using proven Chrome config with temp profile: {user_data_dir}")

                service = Service(ChromeDriverManager().install())

                # CRITICAL FIX: Simple Chrome driver creation with minimal overhead
                logger.info("🔧 Creating Chrome driver with minimal configuration...")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

                # Minimal timeout configuration
                self.driver.implicitly_wait(1)
                self.driver.set_page_load_timeout(30)

                # Set shorter connection timeouts if available
                try:
                    self.driver.command_executor._timeout = 20
                    self.driver.command_executor.keep_alive = False
                except Exception:
                    pass  # Ignore if these attributes don't exist
                
                # Validate connection
                if not self.driver.session_id:
                    raise WebDriverException("Failed to establish WebDriver session")
                
                # ENHANCED: Test connection with crash detection
                try:
                    logger.info("🧪 Testing Chrome driver connection...")

                    # Test 1: Basic script execution
                    user_agent = self.driver.execute_script("return navigator.userAgent;")
                    logger.info(f"✅ Chrome responding - User Agent: {user_agent[:50]}...")
                    logger.info(f"✅ Session ID: {self.driver.session_id[:8]}...")

                    # Test 2: Wait 5 seconds and check if Chrome is still alive
                    logger.info("⏱️ Testing Chrome stability (5 second wait)...")
                    time.sleep(5)

                    # Test 3: Try another command to ensure it's still responsive
                    title = self.driver.execute_script("return document.title || 'No title';")
                    logger.info(f"✅ Chrome still responsive after 5s: {title}")

                    # Attempt automatic login if credentials are available
                    self._attempt_auto_login()

                    logger.info("✅ Chrome driver fully validated and ready")
                    return self.driver

                except Exception as test_error:
                    logger.error(f"❌ CHROME CRASH DETECTED: {test_error}")

                    # Enhanced crash diagnosis
                    if "session deleted" in str(test_error):
                        logger.error("🔍 CRASH ANALYSIS: Chrome browser process died unexpectedly")
                        logger.error("    Possible causes:")
                        logger.error("    - Missing system dependencies (libgconf, libxss1, etc.)")
                        logger.error("    - Insufficient memory or disk space")
                        logger.error("    - Incompatible Chrome flags for server environment")
                        logger.error("    - Container resource limits")

                        # Check if Chrome process still exists
                        try:
                            import psutil
                            chrome_processes = [p for p in psutil.process_iter(['pid', 'name']) if 'chrome' in p.info['name'].lower()]
                            logger.info(f"🔍 Active Chrome processes: {len(chrome_processes)}")
                            for proc in chrome_processes[:3]:  # Show first 3
                                logger.info(f"    PID {proc.info['pid']}: {proc.info['name']}")
                        except ImportError:
                            logger.info("🔍 psutil not available for process checking")
                        except Exception as proc_error:
                            logger.error(f"🔍 Process check failed: {proc_error}")

                    if self.driver:
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None

                    raise WebDriverException(f"Chrome crash detected: {test_error}")
                    
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
                    
                # Note: No cleanup of persistent profile directory - we want to keep login sessions
                
                logger.info("Setting up Chrome driver for posting...")
                
                # Set environment for Chrome stability
                os.environ['CHROME_LOG_FILE'] = 'nul'
                
                chrome_options = Options()
                chrome_options.add_argument("--headless")  # Run in headless mode
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-popup-blocking")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--silent")

                # Safe memory optimization flags for low-RAM server (posting browser)
                chrome_options.add_argument("--disable-background-networking") # No background requests
                chrome_options.add_argument("--disable-sync")               # No Chrome sync
                chrome_options.add_argument("--disable-default-apps")       # No default apps

                # Cache-disabling flags to prevent unnecessary file creation
                chrome_options.add_argument("--disable-http-cache")          # No web page caching
                chrome_options.add_argument("--aggressive-cache-discard")    # Immediately discard cache
                chrome_options.add_argument("--disable-gpu-sandbox")         # No GPU cache files
                chrome_options.add_argument("--disable-software-rasterizer") # No software rendering cache
                chrome_options.add_argument("--disable-background-timer-throttling") # No background timers
                chrome_options.add_argument("--disable-renderer-backgrounding") # No background renderer
                chrome_options.add_argument("--disable-backgrounding-occluded-windows") # No hidden window cache
                chrome_options.add_argument("--disable-client-side-phishing-detection") # No phishing cache
                chrome_options.add_argument("--disable-component-update")   # No component updates
                chrome_options.add_argument("--disable-hang-monitor")       # No hang detection files
                chrome_options.add_argument("--disable-prompt-on-repost")   # No repost prompts
                chrome_options.add_argument("--no-default-browser-check")   # No default browser files

                # Aggressive memory optimization for Docker containers with limited RAM
                chrome_options.add_argument("--memory-pressure-off")        # Disable memory pressure detection
                chrome_options.add_argument("--max_old_space_size=512")     # Limit V8 heap to 512MB
                chrome_options.add_argument("--disable-background-media")   # No background media processing
                chrome_options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees") # Disable heavy features
                chrome_options.add_argument("--disable-ipc-flooding-protection") # Reduce IPC overhead
                chrome_options.add_argument("--disable-renderer-priority-management") # Simplify process management
                chrome_options.add_argument("--disable-smooth-scrolling")   # Reduce animation overhead
                chrome_options.add_argument("--disable-threaded-animation") # Single-threaded animations
                chrome_options.add_argument("--disable-threaded-scrolling") # Single-threaded scrolling
                chrome_options.add_argument("--disable-composited-antialiasing") # Reduce compositing overhead

                # Add Unicode/emoji handling flags
                chrome_options.add_argument("--lang=en-US")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                chrome_options.add_experimental_option("prefs", {
                    "intl.accept_languages": "en-US,en",
                    "profile.default_content_setting_values.notifications": 2
                })

                # Use persistent profile to maintain login sessions
                user_data_dir = os.path.join(os.getcwd(), "chrome_persistent_profile")
                os.makedirs(user_data_dir, exist_ok=True)
                chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
                chrome_options.add_argument(f"--profile-directory=PostingProfile")
                
                # Use different remote debugging port to avoid conflicts
                chrome_options.add_argument("--remote-debugging-port=9223")
                
                # Store persistent profile path for reference
                self._persistent_chrome_dir = user_data_dir
                
                service = Service(ChromeDriverManager().install())
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
    
    def _is_password_reconfirmation_page(self) -> bool:
        """Check if current page is a password re-confirmation page"""
        try:
            # Look for password field with autofocus (your specific element)
            password_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input[name="pass"][autofocus="1"]')
            if password_fields:
                # Also check there's no email field (distinguishes from full login)
                email_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input[name="email"]')
                if not email_fields:
                    logger.info("🔐 Detected password re-confirmation page")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Error checking password reconfirmation: {e}")
            return False

    def _is_full_login_page(self) -> bool:
        """Check if current page is a full login page with email+password"""
        try:
            email_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input[name="email"]')
            password_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input[name="pass"]')
            return bool(email_fields and password_fields)
        except Exception as e:
            logger.debug(f"Error checking full login page: {e}")
            return False

    def _handle_password_reconfirmation(self, password: str) -> bool:
        """Handle password re-confirmation page"""
        try:
            logger.info("🔐 Handling password re-confirmation...")

            # Find the password field with autofocus
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="pass"][autofocus="1"]'))
            )

            # Clear and enter password
            password_field.clear()
            password_field.send_keys(password)

            # Submit by pressing Enter
            password_field.send_keys(Keys.RETURN)

            # Wait for redirect
            time.sleep(5)

            # Check if we're no longer on login page
            current_url = self.driver.current_url.lower()
            if "/login" not in current_url:
                logger.info("✅ Password re-confirmation successful")
                return True
            else:
                logger.error("❌ Password re-confirmation failed")
                return False

        except Exception as e:
            logger.error(f"❌ Error during password re-confirmation: {e}")
            return False

    def _handle_full_login(self, username: str, password: str) -> bool:
        """Handle full login page with email and password"""
        try:
            logger.info("🔑 Handling full login...")

            # Find and fill email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="email"]'))
            )
            email_field.clear()
            email_field.send_keys(username)

            # Find and fill password field
            password_field = self.driver.find_element(By.CSS_SELECTOR, 'input[name="pass"]')
            password_field.clear()
            password_field.send_keys(password)

            # Try to find and click login button, or use Enter
            try:
                login_button = self.driver.find_element(By.NAME, "login")
                login_button.click()
            except:
                # Fallback: press Enter on password field
                password_field.send_keys(Keys.RETURN)

            # Wait for login to complete
            time.sleep(5)

            # Check if login was successful
            current_url = self.driver.current_url.lower()
            if "/login" not in current_url:
                logger.info("✅ Full login successful")
                return True
            else:
                logger.error("❌ Full login failed")
                return False

        except Exception as e:
            logger.error(f"❌ Error during full login: {e}")
            return False

    def login_to_facebook(self, username: str, password: str) -> bool:
        """
        Enhanced login to Facebook with support for both full login and password re-confirmation

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

            # Check what type of page we're on
            current_url = self.driver.current_url.lower()

            # Check if already fully logged in
            if "/login" not in current_url:
                logger.info("Already logged in to Facebook")
                return True

            # Determine what type of login page we're on
            if self._is_password_reconfirmation_page():
                return self._handle_password_reconfirmation(password)
            elif self._is_full_login_page():
                return self._handle_full_login(username, password)
            else:
                logger.error("❌ Unknown login page type")
                return False
                
        except Exception as e:
            logger.error(f"Error during Facebook login: {e}")
            return False
    
    def navigate_to_group(self, group_url: str) -> bool:
        """
        Navigate to a Facebook group with automatic login handling

        Args:
            group_url: URL of the Facebook group

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            logger.info(f"Navigating to group: {group_url}")

            # CRITICAL FIX: Copy authentication from working posting driver BEFORE navigation
            if self.posting_driver and self.driver:
                logger.info("🔄 Copying authentication cookies from posting driver to main driver...")
                try:
                    # Navigate main driver to Facebook base page first
                    self.driver.set_page_load_timeout(30)  # Shorter timeout for base page
                    self.driver.get("https://www.facebook.com")
                    time.sleep(2)

                    # Get cookies from posting driver (which is already authenticated)
                    self.posting_driver.get("https://www.facebook.com")
                    time.sleep(1)
                    posting_cookies = self.posting_driver.get_cookies()
                    logger.info(f"📋 Found {len(posting_cookies)} cookies in posting driver")

                    # Copy important authentication cookies to main driver
                    copied_count = 0
                    for cookie in posting_cookies:
                        try:
                            cookie_name = cookie.get('name', 'unknown')
                            # Focus on critical Facebook auth cookies
                            if cookie_name in ['c_user', 'xs', 'datr', 'sb', 'fr', 'presence', 'dpr', 'wd']:
                                clean_cookie = {
                                    'name': cookie_name,
                                    'value': cookie['value'],
                                    'domain': cookie.get('domain', '.facebook.com')
                                }
                                self.driver.add_cookie(clean_cookie)
                                copied_count += 1
                                logger.debug(f"✅ Copied cookie: {cookie_name}")
                        except Exception as e:
                            logger.debug(f"Failed to copy cookie {cookie_name}: {e}")

                    logger.info(f"✅ Copied {copied_count} authentication cookies to main driver")

                    # Restore longer timeout for group navigation
                    self.driver.set_page_load_timeout(90)

                except Exception as e:
                    logger.warning(f"Cookie copying failed, proceeding without auth: {e}")

            # Now navigate to the group with authentication and retry logic
            logger.info(f"🎯 Navigating to group with authentication: {group_url}")

            # Retry logic for navigation
            max_nav_retries = 3
            for nav_attempt in range(max_nav_retries):
                try:
                    logger.info(f"Navigation attempt {nav_attempt + 1}/{max_nav_retries}")
                    self.driver.get(group_url)
                    time.sleep(3)
                    break  # Success, exit retry loop
                except Exception as nav_error:
                    logger.warning(f"Navigation attempt {nav_attempt + 1} failed: {nav_error}")
                    if nav_attempt == max_nav_retries - 1:
                        # Last attempt failed
                        logger.error(f"All {max_nav_retries} navigation attempts failed")
                        return False
                    else:
                        # Wait before retry
                        time.sleep(5)

            current_url = self.driver.current_url.lower()

            # Check if we got redirected to login page
            if "/login" in current_url and "next=" in current_url:
                logger.warning("🔐 Group access requires authentication - attempting login...")

                # Get credentials from environment
                username = os.environ.get('FACEBOOK_USERNAME')
                password = os.environ.get('FACEBOOK_PASSWORD')

                if username and password:
                    # Determine what type of login page we're on
                    if self._is_password_reconfirmation_page():
                        logger.info("🔐 Detected password re-confirmation for group access")
                        if self._handle_password_reconfirmation(password):
                            logger.info("✅ Password re-confirmation successful, retrying group access")
                            # Wait for redirect and check final URL
                            time.sleep(3)
                            if "/groups/" in self.driver.current_url:
                                logger.info("✅ Successfully navigated to group after authentication")
                                return True
                        else:
                            logger.error("❌ Password re-confirmation failed")
                            return False
                    elif self._is_full_login_page():
                        logger.info("🔑 Detected full login required for group access")
                        if self._handle_full_login(username, password):
                            logger.info("✅ Full login successful, retrying group access")
                            # Navigate to group again after login
                            self.driver.get(group_url)
                            time.sleep(3)
                            if "/groups/" in self.driver.current_url:
                                logger.info("✅ Successfully navigated to group after login")
                                return True
                        else:
                            logger.error("❌ Full login failed")
                            return False
                    else:
                        logger.error("❌ Unknown login page type for group access")
                        return False
                else:
                    logger.error("❌ No Facebook credentials available for group authentication")
                    return False

            # Check if we're on the group page
            elif "/groups/" in current_url:
                logger.info("✅ Successfully navigated to group")
                return True
            else:
                logger.error(f"❌ Failed to navigate to group - unexpected URL: {self.driver.current_url}")
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