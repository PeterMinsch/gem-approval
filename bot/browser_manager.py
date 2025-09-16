import asyncio
import os
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from typing import Dict, Optional
import logging
from browser_recovery import BrowserRecovery

logger = logging.getLogger(__name__)

class MessengerBrowserManager:
    def __init__(self, max_concurrent: int = 3):
        self.main_bot_browser = None
        self.messenger_browsers: Dict[str, webdriver.Firefox] = {}
        self.max_concurrent = max_concurrent
        self.request_queue = asyncio.Queue()
        self.recovery = BrowserRecovery(self)
        # NEW: Persistent browser for all messenger automation
        self.persistent_browser: Optional[webdriver.Firefox] = None
        self._browser_ready = False
        
    def get_messenger_browser(self, session_id: str) -> webdriver.Firefox:
        """Get persistent browser - with auto-restart capability"""
        try:
            # Try to get the persistent browser
            return self.get_persistent_browser()
            
        except Exception as e:
            logger.warning(f"⚠️ Persistent browser failed: {e}")
            logger.info("🔄 Attempting to restart persistent browser...")
            
            # Try to restart the persistent browser
            try:
                self.start_persistent_browser()
                return self.get_persistent_browser()
            except Exception as restart_error:
                logger.error(f"❌ Failed to restart persistent browser: {restart_error}")
                raise Exception(f"Persistent browser not available and restart failed: {restart_error}")
    
    def _create_messenger_browser(self, session_id: str) -> webdriver.Firefox:
        """Create messenger browser using EXACT same config as working posting driver"""
        
        try:
            logger.info(f"🔄 Creating Firefox browser for messenger session {session_id}")

            firefox_options = Options()
            # Run in headless mode for server environment
            # firefox_options.add_argument("--headless")  # Temporarily disable headless for testing

            # Disable notifications and automation detection
            firefox_options.set_preference("dom.webnotifications.enabled", False)
            firefox_options.set_preference("dom.push.enabled", False)

            # Set window size
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")

            # Disable automation indicators
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)

            # Performance optimizations
            firefox_options.set_preference("browser.cache.disk.enable", False)
            firefox_options.set_preference("browser.cache.memory.enable", False)

            # Use Firefox snap browser and GeckoDriver
            # Let Firefox auto-detect binary location
            service = Service("/usr/local/bin/geckodriver")

            browser = webdriver.Firefox(service=service, options=firefox_options)
            
            # Set implicit wait and page load timeout
            browser.implicitly_wait(1)
            browser.set_page_load_timeout(30)
            
            # Test the browser
            browser.get("https://www.facebook.com")
            logger.info(f"✅ Chrome browser created successfully for session {session_id}")
            return browser
            
        except Exception as e:
            logger.error(f"❌ Failed to create Chrome browser for session {session_id}: {e}")
            raise Exception(f"Failed to create Chrome browser: {e}")
    
    def _is_browser_alive(self, browser: webdriver.Firefox) -> bool:
        """Check if browser is still responsive"""
        try:
            browser.current_url
            return True
        except:
            return False
    
    def _cleanup_browser(self, session_id: str):
        """Clean up browser resources"""
        if session_id in self.messenger_browsers:
            try:
                self.messenger_browsers[session_id].quit()
            except:
                pass
            del self.messenger_browsers[session_id]
    
    def start_persistent_browser(self):
        """Start persistent browser for messenger automation - call this on API startup"""
        if self.persistent_browser and self._is_browser_alive(self.persistent_browser):
            logger.info("✅ Persistent browser already running")
            return True
            
        try:
            logger.info("🚀 Starting persistent messenger browser...")

            firefox_options = Options()
            # Run in headless mode for server environment
            # firefox_options.add_argument("--headless")  # Temporarily disable headless for testing

            # Disable notifications and automation detection
            firefox_options.set_preference("dom.webnotifications.enabled", False)
            firefox_options.set_preference("dom.push.enabled", False)

            # Set window size
            firefox_options.add_argument("--width=1200")
            firefox_options.add_argument("--height=800")

            # Disable automation indicators
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)

            # Performance optimizations
            firefox_options.set_preference("browser.cache.disk.enable", False)
            firefox_options.set_preference("browser.cache.memory.enable", False)

            # Use Firefox snap browser and GeckoDriver
            # Let Firefox auto-detect binary location
            service = Service("/usr/local/bin/geckodriver")

            self.persistent_browser = webdriver.Firefox(service=service, options=firefox_options)
            
            # Set timeouts
            self.persistent_browser.implicitly_wait(1)
            self.persistent_browser.set_page_load_timeout(30)
            
            # Navigate to Facebook for login
            self.persistent_browser.get("https://www.facebook.com")
            time.sleep(2)
            
            # Check if login is needed
            if "login" in self.persistent_browser.current_url.lower():
                logger.info("🔐 MANUAL LOGIN REQUIRED for persistent browser")
                logger.info("📱 Please log into Facebook in the browser window that just opened")
                logger.info("✅ Once logged in, the browser will stay open for all messenger automation")
                self._browser_ready = False
            else:
                logger.info("✅ Already logged in!")
                self._browser_ready = True
            
            logger.info("✅ Persistent messenger browser started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start persistent browser: {e}")
            if self.persistent_browser:
                try:
                    self.persistent_browser.quit()
                except:
                    pass
                self.persistent_browser = None
            return False
    
    def get_persistent_browser(self) -> webdriver.Firefox:
        """Get the persistent browser, ensuring it's ready for use"""
        logger.debug(f"🔍 Checking persistent browser - browser exists: {self.persistent_browser is not None}")
        
        if not self.persistent_browser:
            raise Exception("Persistent browser not available - browser is None")
            
        browser_alive = self._is_browser_alive(self.persistent_browser)
        logger.debug(f"🔍 Browser alive check result: {browser_alive}")
        
        if not browser_alive:
            raise Exception("Persistent browser not available - browser not responding")
        
        # Check if login is still needed
        try:
            current_url = self.persistent_browser.current_url
            if "login" in current_url.lower():
                self._browser_ready = False
                raise Exception("Browser needs manual login - please log in and try again")
            else:
                self._browser_ready = True
        except Exception as e:
            if "needs manual login" in str(e):
                raise
            # Browser might be on a different page, which is fine
            pass
            
        return self.persistent_browser
    
    def is_browser_ready(self) -> bool:
        """Check if persistent browser is ready for automation"""
        if not self.persistent_browser or not self._is_browser_alive(self.persistent_browser):
            return False
        
        try:
            current_url = self.persistent_browser.current_url
            if "login" in current_url.lower():
                return False
            return True
        except:
            return False

    def cleanup_all(self):
        """Cleanup all browsers including persistent browser"""
        # Clean up session browsers
        for session_id in list(self.messenger_browsers.keys()):
            self._cleanup_browser(session_id)
        
        # Clean up persistent browser
        if self.persistent_browser:
            try:
                self.persistent_browser.quit()
                logger.info("🧹 Persistent browser cleaned up")
            except:
                pass
            self.persistent_browser = None
            self._browser_ready = False