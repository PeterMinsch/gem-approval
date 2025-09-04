import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Simple script to debug what's on the Facebook page
options = webdriver.ChromeOptions()
options.add_argument("--disable-popup-blocking")
options.add_argument("--disable-notifications")
options.add_argument("--user-data-dir=C:\\Users\\petem\\personal\\gem-approval\\bot\\chrome_data")
options.add_argument("--profile-directory=Default")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    print("Navigating to Facebook group...")
    driver.get("https://www.facebook.com/groups/5440421919361046")
    
    # Wait for page to load
    time.sleep(10)
    
    print("Page title:", driver.title)
    print("Current URL:", driver.current_url)
    
    # Check if we're logged in
    if "login" in driver.current_url.lower():
        print("NOT LOGGED IN - Redirected to login page")
    else:
        print("Appears to be logged in")
    
    # Look for ANY links on the page
    all_links = driver.find_elements(By.TAG_NAME, "a")
    print(f"Found {len(all_links)} total links on page")
    
    # Look for Facebook post-related links
    post_related_links = []
    for link in all_links:
        href = link.get_attribute('href')
        if href and ('posts/' in href or 'photo/' in href or 'fbid=' in href):
            post_related_links.append(href)
    
    print(f"Found {len(post_related_links)} post-related links:")
    for i, link in enumerate(post_related_links[:10]):  # Show first 10
        print(f"  {i+1}: {link}")
    
    # Test our specific XPath
    xpath_results = driver.find_elements(
        By.XPATH,
        "//a[contains(@href, '/groups/') and contains(@href, '/posts/') and not(contains(@href, 'comment_id')) and string-length(@href) > 60] | //a[contains(@href, '/photo/?fbid=') and contains(@href, 'set=gm.')] | //a[contains(@href, '/commerce/listing/') and string-length(@href) > 80]"
    )
    print(f"Our XPath found {len(xpath_results)} matching elements")
    
finally:
    try:
        input("Press Enter to close browser...")
    except:
        print("Closing browser...")
    driver.quit()