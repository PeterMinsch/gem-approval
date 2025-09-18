import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging

logger = logging.getLogger(__name__)

class MessengerAutomation:
    def __init__(self, browser_manager=None, browser: webdriver.Chrome = None, source_browser: webdriver.Chrome = None):
        """
        Initialize MessengerAutomation - now supports both shared browser manager and dedicated browser.

        Args:
            browser_manager: BrowserManager instance for shared browser access (preferred)
            browser: Dedicated browser instance (legacy mode)
            source_browser: Source browser for session copying (legacy)
        """
        self.browser_manager = browser_manager
        self.browser = browser  # Will be set dynamically when using shared browser
        self.source_browser = source_browser
        self.wait = None  # Will be initialized when browser is available
        self._using_shared_browser = browser_manager is not None
        
    async def send_message_with_images(self, recipient: str, message: str, image_paths: list = None):
        """Send message first, then images separately - much cleaner approach"""
        start_time = time.time()

        # Request shared browser access if using browser manager
        browser_acquired = False
        if self._using_shared_browser:
            from modules.browser_manager import BrowserOperation
            browser_acquired = await self.browser_manager.request_browser_for_operation(
                BrowserOperation.MESSAGING, timeout=15
            )
            if not browser_acquired:
                return {"status": "error", "error": "Could not acquire browser for messaging - posting operation in progress"}

            # Get the shared browser instance
            self.browser = self.browser_manager.get_posting_browser_for_messaging()
            if not self.browser:
                self.browser_manager.release_browser_from_operation(BrowserOperation.MESSAGING, restore_url=False)
                return {"status": "error", "error": "Posting browser not available for messaging"}

            # Initialize WebDriverWait with the shared browser
            self.wait = WebDriverWait(self.browser, 10)

        try:
            # Navigate to messenger if not already there
            await self._navigate_to_messenger()

            # Find or start conversation
            await self._open_conversation(recipient)

            # Send text message FIRST (clean and simple)
            await self._send_text_message(message)

            # Send images SEPARATELY (one by one, when UI is clean)
            if image_paths:
                for image_path in image_paths:
                    await self._send_single_image(image_path)

            duration = time.time() - start_time
            return {"status": "success", "duration": f"{duration:.2f}s"}

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            # Always re-enable link clicks after automation, regardless of success/failure
            try:
                await self._enable_link_clicks()
            except:
                pass  # Don't let cleanup errors affect the main result

            # Release shared browser if we acquired it
            if self._using_shared_browser and browser_acquired:
                from modules.browser_manager import BrowserOperation
                self.browser_manager.release_browser_from_operation(
                    BrowserOperation.MESSAGING, restore_url=True
                )
    
    async def _navigate_to_messenger(self):
        """Navigate to Facebook Messenger"""
        current_url = self.browser.current_url
        if "messenger.com" not in current_url:
            self.browser.get("https://www.messenger.com/")
            await asyncio.sleep(1)  # Allow page load
    
    async def _open_conversation(self, recipient: str):
        """Find and open conversation with recipient"""
        try:
            # Try to navigate directly to conversation
            if recipient.startswith("http"):
                # Direct URL provided (e.g., from messenger URL)
                conversation_url = recipient
            else:
                # Assume it's a Facebook ID - use Facebook messenger format
                conversation_url = f"https://www.facebook.com/messages/t/{recipient}"
            
            logger.info(f"Opening conversation: {conversation_url}")
            self.browser.get(conversation_url)
            await asyncio.sleep(3)  # Allow conversation to load
            
            # Check if we're logged in (should not happen with persistent browser)
            if "login" in self.browser.current_url.lower():
                logger.error("Persistent browser not logged in - this should not happen!")
                raise Exception("Persistent browser needs login - please restart API server and log in")
            
        except Exception as e:
            logger.warning(f"Direct navigation failed, trying search: {e}")
            # Fallback to search method
            await self._search_and_open_conversation(recipient)
    
    async def _search_and_open_conversation(self, recipient: str):
        """Search for recipient and open conversation"""
        try:
            # Look for search box
            search_selectors = [
                "input[placeholder*='Search']",
                "input[aria-label*='Search']",
                "input[data-testid*='search']"
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not search_box:
                raise Exception("Could not find search box")
            
            search_box.clear()
            search_box.send_keys(recipient)
            await asyncio.sleep(1)  # Allow search results
            
            # Click first result
            first_result = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='button']"))
            )
            first_result.click()
            await asyncio.sleep(1)  # Allow conversation load
            
        except Exception as e:
            logger.error(f"Search method failed: {e}")
            raise Exception(f"Could not open conversation with {recipient}")
    
    async def _disable_link_clicks(self):
        """Disable link clicks during automation to prevent unwanted navigation"""
        try:
            disable_script = """
            // Disable all link clicks temporarily
            window.messengerAutomationClickHandler = function(e) {
                if (e.target.tagName === 'A' || e.target.closest('a')) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Link click prevented during messenger automation');
                    return false;
                }
            };
            document.addEventListener('click', window.messengerAutomationClickHandler, true);
            """
            self.browser.execute_script(disable_script)
            logger.debug("🚫 Disabled link clicks during automation")
        except Exception as e:
            logger.debug(f"Could not disable link clicks: {e}")
    
    async def _enable_link_clicks(self):
        """Re-enable link clicks after automation is complete"""
        try:
            enable_script = """
            if (window.messengerAutomationClickHandler) {
                document.removeEventListener('click', window.messengerAutomationClickHandler, true);
                delete window.messengerAutomationClickHandler;
            }
            """
            self.browser.execute_script(enable_script)
            logger.debug("✅ Re-enabled link clicks after automation")
        except Exception as e:
            logger.debug(f"Could not re-enable link clicks: {e}")

    async def _send_text_message(self, message: str):
        """Send text message only - clean and simple"""
        try:
            # Disable link clicks to prevent unwanted navigation
            await self._disable_link_clicks()
            
            # Common message box selectors for Messenger
            message_selectors = [
                "div[role='textbox']",
                "div[contenteditable='true']",
                "div[data-testid='message-text-input']",
                "div[aria-label*='message']"
            ]
            
            message_box = None
            for selector in message_selectors:
                try:
                    message_box = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not message_box:
                raise Exception("Could not find message input box")
            
            # Clear existing content
            message_box.clear()
            
            # Type message
            message_box.click()  # Focus the element
            message_box.send_keys(message)
            
            logger.info(f"Message typed: {message[:50]}...")
            
            # Send the message immediately
            await self._send_message()
            
        except Exception as e:
            logger.error(f"Failed to send text message: {e}")
            raise
    
    async def _send_single_image(self, image_path: str):
        """Send a single image separately - much simpler when message box is empty"""
        try:
            logger.info(f"Sending image: {image_path}")
            
            # Check if file exists first - handle path resolution
            import os
            
            # Try different path resolutions since API server runs from bot/ directory
            possible_paths = [
                image_path,  # Original path
                os.path.join("bot", image_path) if not image_path.startswith("bot/") else image_path,  # Add bot/ prefix
                image_path.replace("uploads/", "bot/uploads/") if "uploads/" in image_path else image_path,  # Fix uploads path
            ]
            
            actual_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    actual_path = path
                    logger.debug(f"Found image at: {actual_path}")
                    break
            
            if not actual_path:
                logger.error(f"Image file does not exist at any of these paths: {possible_paths}")
                return
                
            # Use the resolved path
            image_path = actual_path
                
            # Simple attachment selectors - message box should be empty now
            attachment_selectors = [
                "div[aria-label*='Attach'][role='button']",
                "button[aria-label*='Attach']",
                "[aria-label*='Attach a file']",
                "input[type='file']"  # Sometimes directly visible
            ]
            
            for i, selector in enumerate(attachment_selectors):
                try:
                    logger.debug(f"Trying selector {i+1}: {selector}")
                    
                    if selector == "input[type='file']":
                        # Direct file input
                        file_input = self.browser.find_element(By.CSS_SELECTOR, selector)
                        if file_input.is_displayed():
                            file_input.send_keys(image_path)
                            logger.info(f"✅ Image sent directly via file input: {image_path}")
                            await asyncio.sleep(2)  # Wait for upload
                            await self._send_message()  # Send the image
                            return
                    else:
                        # Attachment button
                        attach_buttons = self.browser.find_elements(By.CSS_SELECTOR, selector)
                        
                        for button in attach_buttons:
                            if button.is_displayed() and button.is_enabled():
                                logger.info(f"Found attachment button with selector: {selector}")
                                
                                # Simple click
                                try:
                                    button.click()
                                    logger.info("✅ Successfully clicked attachment button")
                                except:
                                    self.browser.execute_script("arguments[0].click();", button)
                                    logger.info("✅ Used JavaScript click")
                                    
                                await asyncio.sleep(2)  # Wait for file dialog
                                
                                # Look for file input with detailed debugging
                                try:
                                    file_input = self.browser.find_element(By.CSS_SELECTOR, "input[type='file']")
                                    logger.info(f"Found file input after clicking attachment button")
                                    file_input.send_keys(image_path)
                                    logger.info(f"✅ Image uploaded: {image_path}")
                                    await asyncio.sleep(2)  # Wait for upload
                                    await self._send_message()  # Send the image
                                    return
                                except Exception as e:
                                    logger.debug(f"No file input found after click: {e}")
                                    # Check if we opened a menu instead
                                    try:
                                        menu_items = self.browser.find_elements(By.CSS_SELECTOR, "[role='menuitem'], [role='option']")
                                        if menu_items:
                                            logger.debug(f"Found {len(menu_items)} menu items - attachment might have opened a menu")
                                            for item in menu_items:
                                                text = item.get_attribute('innerText') or ''
                                                if 'file' in text.lower() or 'attach' in text.lower():
                                                    logger.info(f"Clicking menu item: {text}")
                                                    item.click()
                                                    await asyncio.sleep(1)
                                                    try:
                                                        file_input = self.browser.find_element(By.CSS_SELECTOR, "input[type='file']")
                                                        file_input.send_keys(image_path)
                                                        logger.info(f"✅ Image uploaded via menu: {image_path}")
                                                        await asyncio.sleep(2)
                                                        await self._send_message()
                                                        return
                                                    except:
                                                        continue
                                    except:
                                        pass
                                    continue
                                    
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            logger.error(f"Failed to upload image: {image_path}")
            
        except Exception as e:
            logger.error(f"Error sending image {image_path}: {e}")

    
    async def _send_message(self):
        """Send the message"""
        try:
            # Try Enter key first (most reliable)
            message_box = self.browser.find_element(By.CSS_SELECTOR, "div[role='textbox'], div[contenteditable='true']")
            message_box.send_keys(Keys.RETURN)
            logger.info("Message sent via Enter key")
            await asyncio.sleep(0.3)
            return
            
        except Exception as e:
            logger.warning(f"Enter key failed, trying send button: {e}")
            
            # Fallback to send button
            send_selectors = [
                "button[aria-label*='Send']",
                "div[aria-label*='Send']",
                "button[data-testid*='send']",
                "svg[data-testid*='send']"
            ]
            
            for selector in send_selectors:
                try:
                    send_button = self.browser.find_element(By.CSS_SELECTOR, selector)
                    send_button.click()
                    logger.info("Message sent via send button")
                    await asyncio.sleep(0.3)
                    return
                except:
                    continue
            
            logger.warning("Could not find send button, message may not be sent")
    
    async def _auto_login(self, source_browser=None):
        """Copy login session from source browser or fallback to credentials"""
        try:
            # Option 1: Copy session from existing logged-in browser
            if source_browser:
                logger.info("Copying login session from main browser...")
                return await self._copy_login_session(source_browser)
            
            # Option 2: Fallback to credential login
            logger.info("Attempting credential-based login...")
            
            # Navigate to login page if not already there
            if "login" not in self.browser.current_url.lower():
                self.browser.get("https://www.facebook.com")
                await asyncio.sleep(2)
            
            # Get credentials from environment
            try:
                import os
                username = os.environ.get('FACEBOOK_USERNAME')
                password = os.environ.get('FACEBOOK_PASSWORD')
            except:
                username = None
                password = None
            
            if not username or not password:
                logger.error("No Facebook credentials found. Set FACEBOOK_USERNAME and FACEBOOK_PASSWORD environment variables")
                return False
            
            # Find and fill email field
            try:
                email_field = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
                email_field.clear()
                email_field.send_keys(username)
            except TimeoutException:
                logger.error("Could not find email field")
                return False
            
            # Find and fill password field
            try:
                password_field = self.browser.find_element(By.ID, "pass")
                password_field.clear()
                password_field.send_keys(password)
            except:
                logger.error("Could not find password field")
                return False
            
            # Click login button
            try:
                login_button = self.browser.find_element(By.NAME, "login")
                login_button.click()
                await asyncio.sleep(5)  # Wait for login to complete
            except:
                logger.error("Could not find or click login button")
                return False
            
            # Check if login was successful
            if "login" not in self.browser.current_url.lower():
                logger.info("✅ Successfully logged in to Facebook")
                return True
            else:
                logger.error("❌ Login failed - still on login page")
                return False
                
        except Exception as e:
            logger.error(f"Auto-login error: {e}")
            return False
    
    async def _copy_login_session(self, source_browser):
        """Copy login cookies from source browser to current browser"""
        try:
            logger.info("Copying login session from source browser...")
            
            # Check if source browser is logged in
            source_url = source_browser.current_url
            if "facebook.com" not in source_url:
                # Navigate source to Facebook to get cookies
                source_browser.get("https://www.facebook.com")
                await asyncio.sleep(2)
            
            # Get cookies from source browser
            try:
                cookies = source_browser.get_cookies()
                logger.info(f"Found {len(cookies)} cookies from source browser")
            except Exception as e:
                logger.error(f"Could not get cookies from source browser: {e}")
                return False
            
            # Navigate target browser to Facebook
            self.browser.get("https://www.facebook.com")
            await asyncio.sleep(2)
            
            # Add cookies to target browser
            cookies_added = 0
            for cookie in cookies:
                try:
                    # Clean up cookie to avoid issues
                    clean_cookie = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie['domain']
                    }
                    # Add optional fields if they exist
                    if 'path' in cookie:
                        clean_cookie['path'] = cookie['path']
                    if 'secure' in cookie:
                        clean_cookie['secure'] = cookie['secure']
                    
                    self.browser.add_cookie(clean_cookie)
                    cookies_added += 1
                except Exception as e:
                    logger.debug(f"Could not add cookie {cookie.get('name', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Added {cookies_added} cookies to messenger browser")
            
            # Refresh to apply login session
            self.browser.refresh()
            await asyncio.sleep(3)
            
            # Check if login was successful
            if "login" not in self.browser.current_url.lower():
                logger.info("✅ Successfully copied login session")
                return True
            else:
                logger.warning("⚠️ Session copy didn't work, login still required")
                return False
                
        except Exception as e:
            logger.error(f"Failed to copy login session: {e}")
            return False
    
    async def _manual_login_pause(self):
        """Pause for manual login - most reliable method"""
        try:
            logger.info("⏸️ MANUAL LOGIN REQUIRED")
            logger.info("🌐 Please log into Facebook in the browser window that just opened")
            logger.info("✋ After logging in successfully, return to this terminal and press Enter")
            
            # Make sure we're on Facebook login page
            if "facebook.com" not in self.browser.current_url:
                self.browser.get("https://www.facebook.com")
                await asyncio.sleep(2)
            
            # Wait for manual login
            print("\n" + "="*60)
            print("🔐 MANUAL LOGIN REQUIRED")
            print("📱 Please log into Facebook in the browser window")
            print("✅ Press Enter here AFTER you've logged in successfully")
            print("="*60)
            
            # This will pause execution until user presses Enter
            input("Press Enter after logging in: ")
            
            # Check if login was successful
            await asyncio.sleep(2)
            self.browser.refresh()
            await asyncio.sleep(3)
            
            if "login" not in self.browser.current_url.lower():
                logger.info("✅ Manual login successful!")
                return True
            else:
                logger.error("❌ Still on login page - please try logging in again")
                return False
                
        except Exception as e:
            logger.error(f"Manual login pause error: {e}")
            return False