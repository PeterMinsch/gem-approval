import pytesseract
from PIL import Image
import requests
from io import BytesIO
import os
import random
import time
import logging
from datetime import datetime
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException
)
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

from bravo_config import CONFIG

load_dotenv()

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    log_filename = f'logs/facebook_comment_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

def contains_any(text, keywords):
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)

def contains_brand(text, brands):
    return any(re.search(rf"\b{re.escape(brand)}\b", text, re.IGNORECASE) for brand in brands)

def contains_modifier(text, modifiers):
    text_lower = text.lower()
    return any(mod in text_lower for mod in modifiers)

def already_commented(existing_comments):
    for c in existing_comments:
        if ("bravo creations" in c.lower() or
            CONFIG["phone"] in c or
            "bravocreations.com" in c):
            return True
    return False

def classify_post(text):
    if contains_any(text, CONFIG["negative_keywords"]):
        return "skip"
    if contains_brand(text, CONFIG["brand_blacklist"]):
        if not contains_modifier(text, CONFIG["allowed_brand_modifiers"]):
            return "skip"
    if contains_any(text, CONFIG["service_keywords"]):
        return "service"
    if contains_any(text, CONFIG["iso_keywords"]):
        return "iso"
    return "skip"

def pick_comment_template(post_type):
    if post_type == "service":
        return random.choice(CONFIG["templates"]["service"])
    elif post_type == "iso":
        return random.choice(CONFIG["templates"]["iso"])
    else:
        return None

class FacebookAICommentBot:
    def __init__(self, config=None):
        self.config = {**CONFIG, **(config or {})}
        self.driver = None

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.binary_location = "C:/Program Files/Google/Chrome/Application/chrome.exe"
            user_data_dir = os.path.join(os.getcwd(), "chrome_data")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument(f"--profile-directory={self.config['CHROME_PROFILE']}")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome driver set up successfully.")
        except Exception as e:
            logger.error(f"Failed to setup Chrome Driver: {e}")
            raise

    def random_pause(self, min_time=1, max_time=5):
        delay = random.uniform(min_time, max_time)
        time.sleep(delay)
        logger.debug(f"Paused for {delay:.2f} seconds.")

    def human_mouse_jiggle(self, element, moves=2):
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            for _ in range(moves):
                x_offset = random.randint(-15, 15)
                y_offset = random.randint(-15, 15)
                actions.move_by_offset(x_offset, y_offset).perform()
                self.random_pause(0.3, 1)
            actions.move_to_element(element).perform()
            self.random_pause(0.3, 1)
            logger.debug(f"Performed mouse jiggle with {moves} moves.")
        except Exception as e:
            logger.error(f"Mouse jiggle failed: {e}")

    def human_type(self, element, text):
        words = text.split()
        for w_i, word in enumerate(words):
            if random.random() < 0.05:
                fake_word = random.choice(["aaa", "zzz", "hmm"])
                for c in fake_word:
                    element.send_keys(c)
                    time.sleep(random.uniform(0.08, 0.35))
                for _ in fake_word:
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.06, 0.25))
            for char in word:
                if random.random() < 0.05:
                    wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                    element.send_keys(wrong_char)
                    time.sleep(random.uniform(0.08, 0.35))
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.06, 0.25))
                element.send_keys(char)
                time.sleep(random.uniform(0.08, 0.35))
            if w_i < len(words) - 1:
                element.send_keys(" ")
                time.sleep(random.uniform(0.08, 0.3))
            if random.random() < 0.03:
                element.send_keys(Keys.ARROW_LEFT)
                time.sleep(random.uniform(0.1, 0.3))
                element.send_keys(Keys.ARROW_RIGHT)
                time.sleep(random.uniform(0.1, 0.3))
        self.random_pause(0.5, 1.5)
        logger.debug("Completed human-like typing.")

    def random_scroll(self):
        scroll_direction = random.choice(["up", "down"])
        scroll_distance = random.randint(200, 800)
        if scroll_direction == "down":
            self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            logger.debug(f"Scrolling down {scroll_distance} pixels.")
        else:
            self.driver.execute_script(f"window.scrollBy(0, -{scroll_distance});")
            logger.debug(f"Scrolling up {scroll_distance} pixels.")
        self.random_pause(1, 3)

    def random_hover_or_click(self):
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        if not all_links:
            return
        if random.random() < 0.5:
            random_link = random.choice(all_links)
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(random_link).perform()
                logger.debug("Hovering over a random link.")
                self.random_pause(1, 3)
                if random.random() < 0.2:
                    random_link.click()
                    logger.debug("Clicked a random link. Going back in 3 seconds.")
                    time.sleep(3)
                    self.driver.back()
                    self.random_pause(1, 3)
            except Exception as e:
                logger.debug(f"Random hover/click failed: {e}")

    def is_post_from_today(self):
        from datetime import datetime
        try:
            timestamp_elements = self.driver.find_elements(By.XPATH, "//a[@aria-label or @data-tooltip-content or @title] | //span[@aria-label or @data-tooltip-content or @title]")
            today = datetime.now().date()
            for el in timestamp_elements:
                label = el.get_attribute('aria-label') or el.get_attribute('data-tooltip-content') or el.get_attribute('title')
                if label:
                    try:
                        if 'Just now' in label or 'm' in label or 'h' in label or 'minute' in label or 'hour' in label:
                            return True
                        dt = datetime.strptime(label.split(' at ')[0], "%A, %B %d, %Y")
                        if dt.date() == today:
                            return True
                    except Exception:
                        continue
            return False
        except Exception as e:
            logger.warning(f"Could not determine post date: {e}")
            return False

    def load_processed_posts(self, filename="processed_posts.txt"):
        if not os.path.exists(filename):
            return set()
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())

    def save_processed_post(self, post_url, filename="processed_posts.txt"):
        with open(filename, "a", encoding="utf-8") as f:
            f.write(post_url + "\n")

    def scroll_and_collect_post_links(self, max_scrolls=20):
        collected = set()
        for _ in range(max_scrolls):
            post_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/groups/') and contains(@href, '/posts/')]"
                " | //a[contains(@href, '/photo/?fbid=')]"
                " | //a[contains(@href, '/commerce/listing/')]"
            )
            hrefs = [link.get_attribute('href') for link in post_links if link.get_attribute('href')]
            collected.update(hrefs)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        return list(collected)

    def get_post_text(self):
        """
        Extract the main text of the post for context or logging.
        Tries multiple XPaths for text, photo, shared, event, OCR, and fallback content.
        """
        # Try text post
        try:
            post_element = self.driver.find_element(By.XPATH, "//div[@data-ad-preview='message']")
            text = post_element.text.strip()
            if text:
                return text
        except Exception:
            pass
        # Try photo post (alt text)
        try:
            img_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//img[@alt]")
            for img in img_elements:
                alt = img.get_attribute('alt')
                if alt and len(alt.strip()) > 0 and 'may contain' not in alt:
                    return alt.strip()
        except Exception:
            pass
        # Try shared post (look for nested message)
        try:
            shared = self.driver.find_element(By.XPATH, "//div[@data-ad-preview='message']//div[@dir='auto']")
            shared_text = shared.text.strip()
            if shared_text:
                return shared_text
        except Exception:
            pass
        # Try event post (event name and details)
        try:
            event_title = self.driver.find_element(By.XPATH, "//div[@role='main']//span[contains(@class, 'event-title')]" )
            event_details = self.driver.find_element(By.XPATH, "//div[@role='main']//div[contains(@class, 'event-time')]" )
            event_text = f"{event_title.text.strip()} {event_details.text.strip()}"
            if event_text.strip():
                return event_text.strip()
        except Exception:
            pass
        # Try OCR on images in the post
        try:
            img_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']//img[@src]")
            for img in img_elements:
                src = img.get_attribute('src')
                if src:
                    try:
                        response = requests.get(src, timeout=10)
                        image = Image.open(BytesIO(response.content))
                        ocr_text = pytesseract.image_to_string(image)
                        if ocr_text and ocr_text.strip():
                            return ocr_text.strip()
                    except Exception as ocr_e:
                        logger.warning(f"OCR failed for image: {src} | Reason: {ocr_e}")
        except Exception:
            pass
        # Try fallback: get visible paragraph text in article
        try:
            paragraphs = self.driver.find_elements(By.XPATH, "//div[@role='article']//p")
            combined = ' '.join([p.text for p in paragraphs if p.text.strip()])
            if combined:
                return combined
        except Exception:
            pass
        # Try fallback: get all visible text in article
        try:
            article = self.driver.find_element(By.XPATH, "//div[@role='article']")
            article_text = article.text.strip()
            if article_text:
                return article_text
        except Exception:
            pass
        logger.error("Could not extract post text: No known selectors matched.")
        return ""

    def get_existing_comments(self):
        try:
            comment_elements = self.driver.find_elements(By.XPATH, "//div[@aria-label='Comment']//span")
            return [el.text for el in comment_elements if el.text.strip()]
        except Exception:
            return []

    def post_comment(self, comment: str, comment_count: int):
        try:
            logger.info("Waiting up to 25 seconds for comment box to appear...")
            time.sleep(3)
            elements = self.driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
            logger.info(f"Found {len(elements)} elements matching the comment box XPath.")
            if len(elements) == 0:
                current_url = self.driver.current_url
                logger.error(f"No elements found for XPath: {self.config['COMMENT_BOX_XPATH']}")
                logger.error(f"Could not find comment box on: {current_url}")
                with open("no_comment_box_links.txt", "a", encoding="utf-8") as f:
                    f.write(current_url + "\n")
                raise TimeoutException("No comment box found.")
            comment_area = elements[0]
            if random.random() < 0.4:
                self.random_scroll()
            else:
                self.random_hover_or_click()
            self.human_mouse_jiggle(comment_area, moves=3)
            comment_area.click()
            self.random_pause(0.5, 2.0)
            self.human_type(comment_area, comment)
            self.random_pause(0.5, 2.0)
            comment_area.send_keys(Keys.RETURN)
            self.random_pause(0.5, 2.0)
            logger.info(f"Comment {comment_count} posted: '{comment}'")
        except TimeoutException:
            logger.warning(f"Comment {comment_count} posting timeout - element not found")
            raise
        except NoSuchElementException:
            logger.warning(f"Comment {comment_count} posting element not found")
            raise
        except Exception as e:
            logger.error(f"Error during comment posting for comment count {comment_count}: {e}")
            raise

    def generate_comment(self, post_text: str, existing_comments=None) -> str:
        if existing_comments is None:
            existing_comments = []
        if already_commented(existing_comments):
            logger.info("Bravo already commented. Skipping post.")
            return None
        post_type = classify_post(post_text)
        if post_type == "skip":
            logger.info("Post filtered out by negative/brand logic. Skipping post.")
            return None
        comment = pick_comment_template(post_type)
        logger.info(f"Generated comment: {comment}")
        return comment

    def run(self):
        try:
            self.setup_driver()
            url = self.config['POST_URL']
            self.driver.get(url)
            logger.info(f"Loaded Facebook URL: {url}")

            if '/groups/' in url and '/posts/' not in url:
                logger.info("Detected group URL. Entering continuous scan mode for today's posts.")
                while True:
                    logger.info("Starting a new scan cycle for today's posts...")
                    time.sleep(5)
                    processed = self.load_processed_posts()
                    all_post_links = self.scroll_and_collect_post_links()
                    logger.info(f"Collected {len(all_post_links)} post links from feed.")
                    new_posts = 0
                    for post_url in all_post_links:
                        if post_url in processed:
                            logger.info(f"Skipping already processed post: {post_url}")
                            continue
                        logger.info(f"Navigating to post: {post_url}")
                        retry_count = 0
                        while retry_count < 3:
                            try:
                                self.driver.get(post_url)
                                time.sleep(5)
                                if not self.is_post_from_today():
                                    logger.info(f"Skipping post not from today: {post_url}")
                                    break
                                post_text = self.get_post_text()
                                if not post_text.strip():
                                    logger.info(f"No post text found, marking as processed: {post_url}")
                                    self.save_processed_post(post_url)
                                    break
                                existing_comments = self.get_existing_comments()
                                comment = self.generate_comment(post_text, existing_comments)
                                if not comment:
                                    logger.info(f"Skipping post (filtered or duplicate): {post_url}")
                                    self.save_processed_post(post_url)
                                    break
                                try:
                                    self.post_comment(comment, 1)
                                    logger.info(f"Successfully commented on post: {post_url}")
                                    self.save_processed_post(post_url)
                                    new_posts += 1
                                except Exception as e:
                                    if 'stale element reference' in str(e).lower():
                                        logger.warning(f"Stale element error while posting comment, retrying ({retry_count+1}/3)...")
                                        retry_count += 1
                                        time.sleep(2)
                                        continue
                                    else:
                                        logger.warning(f"Failed to comment on post: {post_url} | Reason: {e}")
                                break
                            except Exception as e:
                                if 'stale element reference' in str(e).lower():
                                    logger.warning(f"Stale element error while loading post, retrying ({retry_count+1}/3)...")
                                    retry_count += 1
                                    time.sleep(2)
                                    continue
                                else:
                                    logger.warning(f"Failed to process post: {post_url} | Reason: {e}")
                                    break
                    logger.info(f"Scan cycle complete. Commented on {new_posts} new posts. Waiting 15 minutes before next scan...")
                    time.sleep(15 * 60)
        except Exception as e:
            logger.critical(f"Bot execution failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed.")

# Example for testing:
if __name__ == "__main__":
    # # Simulate a post and comments
    # post_text = "ISO: Who makes this ring in stock? Need CAD or casting help."
    # existing_comments = ["Looks great!", "Bravo Creations can help!"]
    # post_type = classify_post(post_text)
    # comment = pick_comment_template(post_type)
    # if comment:
    #     print("Bot would comment:", comment)
    # else:
    #     print("Bot would skip this post.")

    #
    bot = FacebookAICommentBot()
    bot.run()
