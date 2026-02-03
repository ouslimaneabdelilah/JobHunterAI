import time
import re
import pandas as pd
import requests
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def find_emails_in_site(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)
        return list(set(emails)) 
    except:
        return []

def search_companies(city, keyword, max_results=100):
    location_query = f"{city}, Morocco"
    search_query = keyword
    
    results = []
    
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=en")
    
    print("\n[INFO] Initializing Chrome Driver...")
    try:
        # Try to get the latest driver (requires internet)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        print("[WARNING] Could not download latest driver (likely offline). Trying default system driver...")
        try:
            # Fallback to system PATH driver or cached one
            driver = webdriver.Chrome(options=options)
        except Exception as e2:
            print(f"[ERROR] Could not initialize Chrome Driver: {e2}")
            print("Please ensure you have Google Chrome installed and 'chromedriver' in your PATH (or internet access).")
            return []
    
    print("\n[INFO] Press Ctrl+C at any time to STOP scraping and save collected data.\n")
    
    try:
        driver.get("https://www.google.com/maps")
        
        try:
            consent_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "form[action*='consent'] button, button[aria-label='Accept all'], button[aria-label='Tout accepter']"))
            )
            consent_button.click()
            time.sleep(2)
        except:
            pass

        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
        except:
            try:
                search_input = driver.find_element(By.NAME, "q")
            except:
                search_input = driver.find_element(By.CSS_SELECTOR, "input#searchboxinput")

        search_input.send_keys(location_query)
        search_input.send_keys(Keys.ENTER)
        time.sleep(3) 

        try:
            search_input = driver.find_element(By.ID, "searchboxinput")
        except:
            pass
            
        search_input.send_keys(Keys.CONTROL + "a")
        search_input.send_keys(Keys.DELETE)
        time.sleep(1)
        search_input.send_keys(search_query)
        search_input.send_keys(Keys.ENTER)
        
        time.sleep(5)

        try:
            scrollable_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']"))
            )
            
            last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            
            scroll_attempts = 0
            max_scroll_attempts = 50 
            
            while scroll_attempts < max_scroll_attempts:
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                time.sleep(2)
                new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                
                items_loaded = driver.find_elements(By.CLASS_NAME, "hfpxzc")
                if len(items_loaded) >= max_results:
                    break
                    
                if new_height == last_height:
                    time.sleep(2)
                    new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                    if new_height == last_height:
                        break
                last_height = new_height
                scroll_attempts += 1
                
        except Exception:
            pass

        total_items_found = len(driver.find_elements(By.CLASS_NAME, "hfpxzc"))

        for i in range(total_items_found):
            if i >= max_results:
                break
                
            try:
                items = driver.find_elements(By.CLASS_NAME, "hfpxzc")
                if i >= len(items):
                    break 
                
                item = items[i]
                
                driver.execute_script("arguments[0].scrollIntoView(true);", item)
                time.sleep(0.5)
                
                item.click()
                time.sleep(2) 
                
                name = "N/A"
                try:
                    name = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text
                except:
                    name = item.get_attribute("aria-label")

                website = None
                try:
                    website_elem = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
                    website = website_elem.get_attribute("href")
                except:
                    pass

                snippet = ""

                found_emails = []
                if website:
                    found_emails = find_emails_in_site(website)
                
                email_str = found_emails[0] if found_emails else None

                email_str = found_emails[0] if found_emails else None

                record = {
                    "name": name,
                    "website": website,
                    "email": email_str,
                    "snippet": name 
                }
                
                # Strict Filtering as requested by user
                if name != "N/A" and website and email_str:
                    results.append(record)
                    print(f"   Saved: {name}")
                else:
                    missing = []
                    if name == "N/A": missing.append("Name")
                    if not website: missing.append("Website")
                    if not email_str: missing.append("Email")
                    print(f"   Skipped: {name} (Missing: {', '.join(missing)})")

            except Exception:
                continue

    except KeyboardInterrupt:
        print("\n\n>>> STOPPING BY USER REQUEST. Saving collected data wait... <<<\n")
        
    finally:
        driver.quit()
        
    return results
