import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Configures and returns a Selenium WebDriver instance."""
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Commented out for debugging/visibility as per plan notes, can be enabled later
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Error setting up driver: {e}")
        return None

def extract_emails_from_text(text):
    """Finds all distinct emails in a text string."""
    if not text:
        return []
    # Regex for email
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    # Filter out common false positives if necessary (like png, jpg, etc if regex catches them incorrectly, though this regex is decent)
    unique_emails = list(set([e.lower() for e in emails]))
    return unique_emails

def scroll_to_footer(driver):
    """Scrolls down the page to ensure footer is loaded."""
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5) # Wait for page to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    except Exception as e:
        print(f"Error scrolling: {e}")

def scrape_google_search(keyword, num_results=10):
    """Searches Google and visits results to find emails."""
    driver = setup_driver()
    if not driver:
        return []

    results_data = []
    
    try:
        print(f"Searching Google for '{keyword}'...")
        driver.get("https://www.google.com")
        time.sleep(2)
        
        # Accept Cookies if popped up (Basic attempt)
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "tout accepter" in btn.text.lower() or "accept all" in btn.text.lower():
                    btn.click()
                    time.sleep(1)
                    break
        except: pass

        # Search
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)

        # Collect Links
        links = []
        page_num = 0
        while len(links) < num_results:
            search_results = driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for res in search_results:
                try:
                    anchor = res.find_element(By.TAG_NAME, "a")
                    link = anchor.get_attribute("href")
                    title = res.find_element(By.TAG_NAME, "h3").text
                    
                    if link and "google.com" not in link and link not in [l['link'] for l in links]:
                        links.append({'title': title, 'link': link})
                        if len(links) >= num_results:
                            break
                except:
                    continue
            
            if len(links) >= num_results:
                break
                
            # Next page? (Simplified: classic google pagination might be infinite scroll now or "Next" button)
            # For now, let's stick to first page results or try to scroll down on google result page
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                # Try to find "More results" or "Next"
                next_btn = driver.find_element(By.ID, "pnnext")
                next_btn.click()
                time.sleep(2)
            except:
                print("No more pages or infinite scroll reached limits.")
                break

        print(f"Found {len(links)} links. Visiting sites...")

        # Visit each site
        for item in links:
            url = item['link']
            name = item['title']
            print(f"Visiting: {name} ({url})")
            
            try:
                driver.get(url)
                time.sleep(3) # Initial load
                
                # Scroll to footer
                scroll_to_footer(driver)
                
                # Get text
                body_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Extract emails
                emails = extract_emails_from_text(body_text)
                found_email = emails[0] if emails else None
                
                if found_email:
                    print(f"   -> Found Email: {found_email}")
                else:
                    print("   -> No email found.")
                
                results_data.append({
                    'name': name,
                    'website': url,
                    'email': found_email,
                    'snippet': f"Scraped from Google for {keyword}" 
                })
                
            except Exception as e:
                print(f"   -> Failed to visit {url}: {e}")
                results_data.append({
                    'name': name,
                    'website': url,
                    'email': None,
                    'snippet': f"Error accessing site: {str(e)}"
                })

    finally:
        driver.quit()
        
    return results_data
