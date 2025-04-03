import os
import csv
import time
import random
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# Global control flags and log storage for connection process
connection_running = False
connection_paused = False
connection_stop = False
connection_logs = []  # List of dicts for report
connection_log_text = []  # List of log strings for live display

# Helper function to add logs
def add_log(message):
    global connection_log_text
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"{timestamp} - {message}"
    print(log_message)
    connection_log_text.append(log_message)

# ---------------------------------
# Scraping Endpoint
# ---------------------------------
@app.route('/')
def index():
    add_log("Serving the home page. Enjoy the view!")
    return render_template('index.html')

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    add_log("[SCRAPE] Received scraping request. Hang tight!")
    
    # Retrieve form data
    linkedin_email = request.form.get('linkedinEmail')
    linkedin_password = request.form.get('linkedinPassword')
    company_url = request.form.get('companyUrl')
    designation_keywords = request.form.get('designationKeywords')
    scroll_count = request.form.get('scrollCount')
    
    if not linkedin_email or not linkedin_password:
        add_log("[SCRAPE ERROR] Missing LinkedIn credentials.")
        return jsonify({"error": "LinkedIn email and password are required."}), 400
    
    try:
        scroll_count = int(scroll_count)
    except ValueError:
        add_log("[SCRAPE ERROR] Scroll count is not a number!")
        return "Scroll count must be a number.", 400
    
    designation_filter = designation_keywords.split(';')[0].strip()
    add_log(f"[SCRAPE] Using designation filter: {designation_filter}")
    
    # Selenium Setup for Scraping
    add_log("[SCRAPE] Launching browser for scraping...")
    CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service)
    
    try:
        add_log("[SCRAPE] Opening LinkedIn login page...")
        driver.get("https://www.linkedin.com/login")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "username")))
        
        add_log("[SCRAPE] Logging in...")
        driver.find_element(By.ID, "username").send_keys(linkedin_email)
        driver.find_element(By.ID, "password").send_keys(linkedin_password + Keys.RETURN)
        
        add_log("[SCRAPE] Submitted login form. Complete any 2FA if prompted...")
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.global-nav__me-photo"))
        )
        
        add_log("[SCRAPE] Login successful!")
        
        if not company_url.endswith("/people/"):
            company_url = company_url.rstrip("/") + "/people/"
        
        add_log(f"[SCRAPE] Navigating to the company's People page: {company_url}")
        driver.get(company_url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5)
        
        try:
            add_log(f"[SCRAPE] Applying designation filter: {designation_filter}")
            search_field = driver.find_element(By.ID, "people-search-keywords")
            search_field.clear()
            search_field.send_keys(designation_filter + Keys.RETURN)
            time.sleep(5)
        except Exception as e:
            add_log(f"[SCRAPE WARNING] Could not apply designation filter: {e}")
        
        add_log(f"[SCRAPE] Scrolling down {scroll_count} times...")
        for i in range(scroll_count):
            add_log(f" [SCRAPE] Scrolling... iteration {i+1}")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        
        add_log("[SCRAPE] Finished scrolling. Starting to scrape profiles...")
        
        scraped_data = []
        profile_containers = driver.find_elements(By.CSS_SELECTOR, "ul.org-people-profiles-module__profile-list li")
        add_log(f"[SCRAPE] Found {len(profile_containers)} profile containers (primary selector).")
        
        if len(profile_containers) == 0:
            add_log("[SCRAPE] Trying fallback selector (generic li)...")
            profile_containers = driver.find_elements(By.CSS_SELECTOR, "li")
            add_log(f"[SCRAPE] Found {len(profile_containers)} li elements.")
        
        for container in profile_containers:
            try:
                name_element = container.find_element(By.CSS_SELECTOR, "div.lt-line-clamp--single-line")
                name = name_element.text.strip()
            except Exception:
                name = ""
            
            try:
                job_element = container.find_element(By.CSS_SELECTOR, "div.lt-line-clamp--multi-line")
                job_title = job_element.text.strip()
            except Exception:
                job_title = ""
            
            try:
                link_element = container.find_element(By.TAG_NAME, "a")
                profile_url = link_element.get_attribute("href")
            except Exception:
                profile_url = ""
            
            if name and profile_url:
                scraped_data.append({
                    "Name": name,
                    "LinkedIn URL": profile_url,
                    "Designation": job_title
                })
                add_log(f" [SCRAPE DATA] {name} | {profile_url} | {job_title}")
        
        add_log(f"[SCRAPE] Total profiles scraped: {len(scraped_data)}")
        
        today = datetime.now().strftime("%Y-%m-%d")
        file_keyword = designation_filter.replace(" ", "_") if designation_filter else "Keyword"
        
        try:
            parts = company_url.rstrip('/').split('/')
            company_name = parts[-2] if len(parts) >= 2 else "Company"
        except Exception:
            company_name = "Company"
        
        file_name = f"{today}_{company_name}_{file_keyword}.csv"
        download_folder = os.path.expanduser("~/Downloads")
        output_path = os.path.join(download_folder, file_name)
        
        add_log(f"[SCRAPE] Saving scraped data to CSV file: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Name", "LinkedIn URL", "Designation"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in scraped_data:
                writer.writerow(row)
    
    except Exception as e:
        add_log(f"[SCRAPE ERROR] {e}")
        driver.quit()
        return jsonify({"error": str(e)}), 500
    
    driver.quit()
    add_log("[SCRAPE] Scraping completed successfully!")
    
    return jsonify({
        "message": f"Scraping completed! CSV file saved at: {output_path}", 
        "profiles_scraped": len(scraped_data)
    }), 200

# ---------------------------------
# Connection Request Automation Endpoint
# ---------------------------------
@app.route('/start-connection', methods=['POST'])
def start_connection():
    global connection_running, connection_paused, connection_stop, connection_logs, connection_log_text
    
    connection_running = True
    connection_paused = False
    connection_stop = False
    connection_logs = []
    connection_log_text = []  # Reset live log buffer
    
    add_log("[CONNECTION] Starting connection requests process...")
    
    # Retrieve form data for connection requests
    connection_urls_text = request.form.get('connection_urls')
    message_template = request.form.get('message_template', "{first_name}, Happy to connect!")
    
    if not connection_urls_text:
        add_log("[CONNECTION ERROR] No profile URLs provided.")
        return jsonify({"error": "No profile URLs provided."}), 400
    
    # Parse URLs from text area (split on commas or newlines)
    urls = [url.strip() for url in connection_urls_text.replace(',', '\n').splitlines() if url.strip()]
    
    if not urls:
        add_log("[CONNECTION ERROR] No valid profile URLs found.")
        return jsonify({"error": "No valid profile URLs found."}), 400
    
    add_log(f"[CONNECTION] Processing {len(urls)} profile URLs.")
    
    # Selenium setup for connection requests
    CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service)
    
    # Login for connection requests
    linkedin_email = request.form.get('linkedinEmail')
    linkedin_password = request.form.get('linkedinPassword')
    
    if not linkedin_email or not linkedin_password:
        driver.quit()
        add_log("[CONNECTION ERROR] LinkedIn credentials missing for connection requests.")
        return jsonify({"error": "LinkedIn email and password are required for connection requests."}), 400
    
    try:
        add_log("[CONNECTION] Logging into LinkedIn...")
        driver.get("https://www.linkedin.com/login")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "username")))
        
        driver.find_element(By.ID, "username").send_keys(linkedin_email)
        driver.find_element(By.ID, "password").send_keys(linkedin_password + Keys.RETURN)
        
        add_log("[CONNECTION] Submitted login form. Complete any 2FA if prompted...")
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.global-nav__me-photo"))
        )
        
        add_log("[CONNECTION] Login successful!")
    
    except Exception as e:
        driver.quit()
        add_log(f"[CONNECTION ERROR] Login failed: {e}")
        return jsonify({"error": f"Login failed: {str(e)}"}), 500
    
    # Process each connection URL
    for url in urls:
        if connection_stop:
            add_log("[CONNECTION] Process stopped by user.")
            break
        
        while connection_paused:
            add_log("[CONNECTION] Process paused. Waiting to resume...")
            time.sleep(1)
        
        add_log(f"[CONNECTION] Processing profile URL: {url}")
        log_entry = {
            "LinkedIn URL": url,
            "Name": "",
            "Designation": "",
            "Request Status": "",
            "Error Details": "",
            "Timestamp": ""
        }
        
        try:
            driver.get(url)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            try:
                full_name_elem = driver.find_element(By.CSS_SELECTOR, "h1.break-words")
                full_name = full_name_elem.text.strip()
                first_name = full_name.split()[0]
            except Exception as e:
                first_name = "there"
                add_log(f"[CONNECTION WARNING] Could not extract name: {e}")
            
            try:
                # Use a flexible selector for designation
                designation_elem = driver.find_element(By.CSS_SELECTOR, "h2.mt1.t-18.t-black.t-normal.break-words")
                designation = designation_elem.text.strip()
            except Exception as e:
                designation = ""
                add_log(f"[CONNECTION WARNING] Could not extract designation: {e}")
            
            personalized_message = message_template.replace("{first_name}", first_name)
            add_log(f"[CONNECTION] Sending connection request to {first_name} with message: '{personalized_message}'")
            
            # Attempt to click the "Connect" button
            try:
                try:
                    connect_button = driver.find_element(By.XPATH, "//span[@class='artdeco-button__text' and contains(text(), 'Connect')]/ancestor::button")
                except Exception as e:
                    # If not found, try clicking the "More" button first
                    more_button = driver.find_element(By.XPATH, "//button[contains(@aria-label,'More actions') or contains(., 'More')]")
                    more_button.click()
                    time.sleep(2)
                    connect_button = driver.find_element(By.XPATH, "//span[@class='artdeco-button__text' and contains(text(), 'Connect')]/ancestor::button")
                
                connect_button.click()
                time.sleep(2)
            
            except Exception as e:
                raise Exception("Connect button not found.")
            
            # Click "Add a note" if available
            try:
                add_note_button = driver.find_element(By.XPATH, "//span[@class='artdeco-button__text' and contains(text(), 'Add a note')]/ancestor::button")
                add_note_button.click()
                time.sleep(2)
            except Exception as e:
                add_log("[CONNECTION INFO] 'Add a note' option not available; proceeding without note.")
            
            # Enter the personalized message
            try:
                note_textarea = driver.find_element(By.ID, "custom-message")
                note_textarea.clear()
                note_textarea.send_keys(personalized_message)
                time.sleep(1)
            except Exception as e:
                add_log("[CONNECTION INFO] Note textarea not found; skipping note entry.")
            
            # Click the "Send" button
            try:
                send_button = driver.find_element(By.XPATH, "//span[@class='artdeco-button__text' and contains(text(), 'Send')]/ancestor::button")
                send_button.click()
                add_log(f"[CONNECTION SUCCESS] Connection request sent to {first_name}.")
                log_entry["Request Status"] = "Success"
            except Exception as e:
                raise Exception("Send button not found or connection request not sent.")
        
        except Exception as e:
            error_msg = str(e)
            add_log(f"[CONNECTION ERROR] Failed to send request for {url}: {error_msg}")
            log_entry["Request Status"] = "Error"
            log_entry["Error Details"] = error_msg
        
        log_entry["Name"] = first_name if 'first_name' in locals() else ""
        log_entry["Designation"] = designation
        log_entry["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection_logs.append(log_entry)
        
        # Random delay between 2 and 19 seconds
        delay = random.randint(2, 19)
        add_log(f"[CONNECTION] Waiting for {delay} seconds before next request...\n")
        time.sleep(delay)
    
    driver.quit()
    add_log("[CONNECTION] Connection requests process completed.")
    
    # Generate CSV report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_filename = f"connection_report_{timestamp}.csv"
    download_folder = os.path.expanduser("~/Downloads")
    report_path = os.path.join(download_folder, report_filename)
    
    try:
        with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["LinkedIn URL", "Name", "Designation", "Request Status", "Error Details", "Timestamp"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for log in connection_logs:
                writer.writerow(log)
        
        add_log(f"[CONNECTION] Report generated at: {report_path}")
    except Exception as e:
        add_log(f"[CONNECTION ERROR] Failed to generate report: {e}")
        report_path = "Report generation failed."
    
    return jsonify({
        "message": "Connection requests process completed.",
        "report_path": report_path,
        "profiles_processed": len(connection_logs),
        "logs": connection_log_text
    }), 200

# ---------------------------------
# Process Control Endpoints
# ---------------------------------
@app.route('/pause-connection', methods=['POST'])
def pause_connection():
    global connection_paused
    connection_paused = True
    add_log("[CONNECTION] Process paused by user.")
    return jsonify({"message": "Connection process paused."}), 200

@app.route('/resume-connection', methods=['POST'])
def resume_connection():
    global connection_paused
    connection_paused = False
    add_log("[CONNECTION] Process resumed by user.")
    return jsonify({"message": "Connection process resumed."}), 200

@app.route('/stop-connection', methods=['POST'])
def stop_connection():
    global connection_stop, connection_running
    connection_stop = True
    connection_running = False
    add_log("[CONNECTION] Process stopped by user.")
    return jsonify({"message": "Connection process stopped."}), 200

# Optional: Endpoint to fetch live logs for connection process
@app.route('/connection-logs', methods=['GET'])
def get_connection_logs():
    return jsonify({"logs": connection_log_text}), 200

if __name__ == '__main__':
    add_log("Starting the LinkedIn Scraper & Connection App... Get ready!")
    app.run(debug=True)