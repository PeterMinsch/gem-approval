import asyncio
import os
import time
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from typing import Dict, Optional
import logging
from browser_recovery import BrowserRecovery

logger = logging.getLogger(__name__)

class MessengerBrowserManager:
    def __init__(self, max_concurrent: int = 3):
        self.main_bot_browser = None
        self.messenger_browsers: Dict[str, webdriver.Chrome] = {}
        self.max_concurrent = max_concurrent
        self.request_queue = asyncio.Queue()
        self.recovery = BrowserRecovery(self)
        # NEW: Persistent browser for all messenger automation
        self.persistent_browser: Optional[webdriver.Chrome] = None
        self._browser_ready = False

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
        
    def get_messenger_browser(self, session_id: str) -> webdriver.Chrome:
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
    
    def _create_messenger_browser(self, session_id: str) -> webdriver.Chrome:
        """Create messenger browser using EXACT same config as working posting driver"""
        
        try:
            logger.info(f"🔄 Creating Chrome browser for messenger session {session_id}")

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

            browser = webdriver.Chrome(service=service, options=chrome_options)
            
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
    
    def _is_browser_alive(self, browser: webdriver.Chrome) -> bool:
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

            chrome_options = Options()
            # Run in headless mode for server environment
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1200,800")
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

            self.persistent_browser = webdriver.Chrome(service=service, options=chrome_options)
            
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
    
    def get_persistent_browser(self) -> webdriver.Chrome:
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