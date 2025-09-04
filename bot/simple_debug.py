import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
options.add_argument("--disable-popup-blocking")
options.add_argument("--disable-notifications")
options.add_argument("--user-data-dir=C:\\Users\\petem\\personal\\gem-approval\\bot\\chrome_data")
options.add_argument("--profile-directory=Default")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    driver.get("https://www.facebook.com/groups/5440421919361046")
    time.sleep(8)
    
    # Look specifically for photo links with fbid
    photo_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'fbid=')]")
    print(f"Found {len(photo_links)} photo links with fbid")
    
    for i, link in enumerate(photo_links[:5]):
        href = link.get_attribute('href')
        print(f"{i+1}: {href}")
    
    # Look for set=gm specifically  
    gm_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'set=gm')]")
    print(f"\nFound {len(gm_links)} links with set=gm")
    
    for i, link in enumerate(gm_links[:5]):
        href = link.get_attribute('href')
        print(f"{i+1}: {href}")
        
    time.sleep(3)
    
except Exception as e:
    print(f"Error: {e}")
finally:
    driver.quit()