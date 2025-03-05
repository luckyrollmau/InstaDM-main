from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import csv
import time
import os
import io
import shutil
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import pickle
from datetime import datetime
import json
import logging
from logging.config import dictConfig
from werkzeug.utils import secure_filename
import threading
import random

# Configure Flask logging
dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }
    },
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# Create Flask app after logging config
app = Flask(__name__)
app.logger.setLevel(logging.WARNING)  # Only show warnings and errors

# Constants
HISTORY_FILE = "message_history.json"
SESSION_FILE = "session.pkl"
SCREENSHOTS_DIR = "screenshots"
LOG_FILE = "dm_log.csv"
PROGRESS_FILE = "progress.txt"
CHROME_PROFILE_DIR = "chrome_profiles"

# Global state
CURRENT_STATUS = {
    "current": 0,
    "total": 0,
    "messages": [],
    "original_messages": []  # Store original CSV data for download
}

# Track usernames that have already received messages
sent_messages_log = set()

# Create necessary directories
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)

def clear_browser_cache(profile_path):
    """
    Comprehensively clear browser cache and user data
    
    Args:
        profile_path (str): Path to Chrome user profile directory
    """
    try:
        # List of potential cache and data directories to clear
        cache_dirs = [
            os.path.join(profile_path, 'Cache'),
            os.path.join(profile_path, 'Default', 'Cache'),
            os.path.join(profile_path, 'Default', 'Code Cache'),
            os.path.join(profile_path, 'Default', 'Service Worker'),
            os.path.join(profile_path, 'Default', 'Session Storage'),
            os.path.join(profile_path, 'Default', 'Local Storage')
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    print(f"Removed cache directory: {cache_dir}")
                except Exception as e:
                    print(f"Could not remove {cache_dir}: {e}")
        
        # Clear specific cache files
        cache_files = [
            os.path.join(profile_path, 'Default', 'Cookies'),
            os.path.join(profile_path, 'Default', 'Cookies-journal'),
            os.path.join(profile_path, 'Default', 'Web Data')
        ]
        
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                    print(f"Removed cache file: {cache_file}")
                except Exception as e:
                    print(f"Could not remove {cache_file}: {e}")
    
    except Exception as e:
        print(f"Comprehensive cache clearing failed: {e}")

def initialize_driver(headless=False):
    """Initialize the Chrome WebDriver with configurable headless setting and cache clearing."""
    # Create a unique profile directory
    profile_name = f"instagram_profile_{int(time.time())}"
    profile_path = os.path.join(CHROME_PROFILE_DIR, profile_name)
    os.makedirs(profile_path, exist_ok=True)
    
    # Clear cache before creating new profile
    clear_browser_cache(profile_path)
    
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={profile_path}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Randomize user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")

    if headless:
        chrome_options.add_argument("--headless")
        print("Headless mode is enabled.")
    else:
        print("Headless mode is NOT enabled.")  # Log this statement

    print("Initializing ChromeDriver...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    print("ChromeDriver initialized successfully!")
    return driver

# Rest of the functions remain the same as in your original script...

def login_and_save_session(username, password):
    """Login and save the session cookies to a file using non-headless mode."""
    driver = initialize_driver(headless=False)  # Disable headless mode for login
    try:
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(2)

        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        time.sleep(60)  # Wait for login completion
        
        cookies = driver.get_cookies()
        with open(SESSION_FILE, "wb") as file:
            pickle.dump(cookies, file)
        
        print("Session saved successfully!")
    except Exception as e:
        print(f"Error during login: {e}")
        raise
    finally:
        driver.quit()


# Helper Functions
def load_message_history():
    """Load the message history for the current logged-in account."""
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_to_history(username, target_username, status, message_text):
    """Save message attempt to history."""
    history = load_message_history()
    
    if username not in history:
        history[username] = []
    
    history[username].append({
        "target_username": target_username,
        "status": status,
        "message": message_text,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def check_if_messaged(username, target_username):
    """Check if a target user has already been messaged by this account."""
    history = load_message_history()
    if username in history:
        return any(msg["target_username"] == target_username 
                  and msg["status"] == "Message sent successfully" 
                  for msg in history[username])
    return False

def get_todays_dm_count(session_username):
    """Get count of DMs sent today for the current session user."""
    if not session_username:
        print("No session username provided")
        return 0
        
    try:
        history = load_message_history()
        if session_username not in history:
            print(f"No history found for user: {session_username}")
            return 0
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"Counting messages since: {today_start}")
        
        count = sum(1 for msg in history[session_username]
                   if (datetime.fromisoformat(msg["timestamp"]) >= today_start 
                       and msg["status"] == "Message sent successfully"))
        
        print(f"Found {count} messages today for {session_username}")
        return count
    except Exception as e:
        print(f"Error counting today's DMs: {e}")
        return 0

def fix_csv_delimiter_and_format(file_path):
    """
    Check and fix the delimiter in a CSV file.
    Ensures proper 'username,message' format and handles commas within messages.
    Returns path to the fixed CSV file.
    """
    fixed_file_path = file_path.replace(".csv", "_fixed.csv")
    
    try:
        # First, detect the delimiter and read the file
        with open(file_path, 'r', newline='', encoding='utf-8-sig') as infile:
            # Read a sample to detect delimiter
            sample = infile.read(1024)
            infile.seek(0)
            
            # Check for common delimiters
            possible_delimiters = [',', ';', '\t', '|']
            delimiter = ','  # default
            for d in possible_delimiters:
                if d in sample:
                    delimiter = d
                    break
            
            # Use csv module to properly handle quoted fields
            reader = csv.reader(infile, delimiter=delimiter)
            header = next(reader, None)
            
            # Verify and standardize header
            if not header or len(header) < 2:
                header = ["username", "message"]
            else:
                # Clean header names
                header = [h.strip().lower() for h in header]
                # Find username and message columns
                username_col = next((i for i, h in enumerate(header) if 'user' in h), 0)
                message_col = next((i for i, h in enumerate(header) if 'message' in h or 'text' in h), 1)
            
            # Write the standardized CSV
            with open(fixed_file_path, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile, delimiter=',', quoting=csv.QUOTE_ALL)
                writer.writerow(["username", "message"])
                
                for row in reader:
                    if len(row) >= max(username_col + 1, message_col + 1):
                        username = row[username_col].strip()
                        message = row[message_col].strip()
                        
                        # Skip empty rows
                        if not username or not message:
                            continue
                            
                        # Write the row with proper quoting
                        writer.writerow([username, message])
        
        print(f"CSV successfully standardized and saved to: {fixed_file_path}")
        return fixed_file_path
        
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        if os.path.exists(fixed_file_path):
            os.remove(fixed_file_path)
        raise


# Chrome Setup Functions
def get_chrome_path():
    chrome_path = os.getenv("CHROME_PATH")
    if not chrome_path:
        if os.name == 'nt':  # Windows
            chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        elif os.name == 'posix':  # macOS/Linux
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    print(f"Resolved Chrome path: {chrome_path}")
    return chrome_path


def locate_element_with_fallback(driver, xpaths, wait_time=10):
    """Try multiple XPATH selectors until one finds an element."""
    for xpath in xpaths:
        try:
            element = WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            return element
        except:
            continue
    raise Exception("None of the provided XPATHs could locate an element.")


import random

def human_delay(min_sec=1, max_sec=3):
    """Random delay to mimic human behavior"""
    time.sleep(random.uniform(min_sec, max_sec))

def send_dm(target_username, message_text, follow_first=False):
   driver = None
   try:
       if target_username in sent_messages_log:
           return f"Skipped - already sent this session"

       driver = initialize_driver(headless=False)
       human_delay(random.uniform(1.5, 4.5), random.uniform(4, 8))
       driver.get("https://www.instagram.com")
       human_delay(2, 6)

       try:
           with open(SESSION_FILE, "rb") as file:
               cookies = pickle.load(file)
               for cookie in cookies:
                   driver.add_cookie(cookie)
               driver.refresh()
               human_delay(1.5, 4.5)
       except Exception as e:
           return "Session error"

       profile_url = f"https://www.instagram.com/{target_username}/"
       driver.get(profile_url)
       human_delay(3, 7)

       if "Page Not Found" in driver.title:
           return "Profile not found"


       if follow_first:
           try:
               follow_button_xpaths = [
                   "//div[contains(@class, 'ap3a') and text()='Follow']",
                   "//div[@dir='auto' and text()='Follow']"
               ]
               for xpath in follow_button_xpaths:
                   try:
                       follow_button = WebDriverWait(driver, 5).until(
                           EC.element_to_be_clickable((By.XPATH, xpath))
                       )
                       human_delay(1, 3)
                       follow_button.click()
                       human_delay(2, 4)
                       break
                   except:
                       continue
           except Exception as e:
               print(f"Follow error: {str(e)}")

       message_button_xpaths = [
           "//div[contains(@class, 'x1i10hfl') and contains(text(), 'Message')]",
           "//div[contains(@role, 'button') and text()='Message']"
       ]

       message_clicked = False
       for xpath in message_button_xpaths:
           try:
               message_button = WebDriverWait(driver, 5).until(
                   EC.element_to_be_clickable((By.XPATH, xpath))
               )
               if message_button.text.strip().lower() == "message":
                   human_delay(1, 3)
                   message_button.click()
                   message_clicked = True
                   human_delay(2, 4)
                   break
           except:
               continue

       if not message_clicked:
           return "Could not click message button"

       notification_buttons = [
           "//button[contains(@class, '_a9--')]",
           "//button[text()='Not Now']",
           "//div[text()='Not Now']",
       ]

       human_delay(1, 3)
       for button_xpath in notification_buttons:
           try:
               not_now = driver.find_element(By.XPATH, button_xpath)
               human_delay(0.5, 2)
               not_now.click()
               human_delay(1, 3)
               break
           except:
               continue

       message_box_selectors = [
           "//div[@role='textbox']",
           "//div[contains(@aria-label, 'Message')]",
           "//textarea[contains(@placeholder, 'Message')]"
       ]
       
       message_sent = False
       for selector in message_box_selectors:
           try:
               message_box = WebDriverWait(driver, 15).until(
                   EC.presence_of_element_located((By.XPATH, selector))
               )
               human_delay(1, 2)
               message_box.click()
               human_delay(1, 2)
               
               typing_style = random.choice(['normal', 'fast', 'slow', 'variable'])
               for char in message_text:
                   message_box.send_keys(char)
                   if typing_style == 'normal':
                       human_delay(0.08, 0.2)
                   elif typing_style == 'fast':
                       human_delay(0.05, 0.12)
                   elif typing_style == 'slow':
                       human_delay(0.15, 0.3)
                   else:  # variable
                       human_delay(0.05, 0.35)
                   
                   if random.random() < 0.08:  # 8% chance for pause
                       human_delay(0.4, 1.2)
               
               human_delay(1, 3)
               message_box.send_keys(Keys.RETURN)
               human_delay(2, 4)
               
               try:
                   WebDriverWait(driver, 5).until(
                       EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{message_text[:20]}')]"))
                   )
                   message_sent = True
                   human_delay(2, 4)
                   break
               except:
                   continue
               
           except:
               continue

       if message_sent:
           sent_messages_log.add(target_username)
           return "Message sent successfully"
       else:
           return "Message verification failed"

   except Exception as e:
       if driver:
           try:
               screenshot_path = os.path.join(SCREENSHOTS_DIR, f"error_{target_username}_{int(time.time())}.png")
               driver.save_screenshot(screenshot_path)
           except:
               pass
       return f"Error: {str(e)}"

   finally:
       if driver:
           driver.quit()


@app.route("/")
def home():
    return render_template("index_DMv4.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    login_and_save_session(username, password)
    return redirect(url_for("home"))

@app.route("/get_current_status")
def get_current_status():
    print("Status check called") # Debug log
    session_username = None
    try:
        with open(SESSION_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                if cookie.get('name') == 'ds_user_id':
                    session_username = cookie.get('value')
                    break
        print(f"Session username found: {session_username}")
    except Exception as e:
        print(f"Error getting session: {e}")
        session_username = None
    
    todays_count = get_todays_dm_count(session_username) if session_username else 0
    print(f"Today's count: {todays_count}")
    
    response_data = {
        "current": CURRENT_STATUS["current"],
        "total": CURRENT_STATUS["total"],
        "messages": CURRENT_STATUS["messages"],
        "today_count": todays_count
    }
    print(f"Sending response: {response_data}")
    return jsonify(response_data)

@app.route("/get_remaining_messages")
def get_remaining_messages():
    processed_usernames = set()

    # Track successfully sent messages from this session
    for msg in CURRENT_STATUS["messages"]:
        if msg["status"] == "Message sent successfully" or msg["status"] == "Already messaged previously":
            processed_usernames.add(msg["username"])

    # Only include messages that weren't processed
    remaining_messages = []
    total = len(CURRENT_STATUS["original_messages"])
    filtered = 0
    
    for msg in CURRENT_STATUS["original_messages"]:
        if msg["username"] not in processed_usernames and msg["username"] != "SYSTEM":
            remaining_messages.append(msg)
        else:
            filtered += 1

    print(f"Total messages: {total}")
    print(f"Filtered out: {filtered}")
    print(f"Remaining: {len(remaining_messages)}")

    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_ALL)
    writer.writerow(['username', 'message'])
    
    for msg in remaining_messages:
        username = msg["username"].strip()
        message = msg.get("message", "").strip()
        if username and message:  # Only write non-empty rows
            writer.writerow([username, message])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-disposition": "attachment; filename=remaining_messages.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )

@app.route("/reset_status", methods=["POST"])
def reset_status():
    global CURRENT_STATUS
    print("Reset status called") # Debug log
    CURRENT_STATUS = {"current": 0, "total": 0, "messages": [], "original_messages": []}
    return jsonify({"status": "reset"})


@app.route("/send_bulk_dms", methods=["POST"])
def send_bulk_dms():
    print("Send bulk DMs called")
    global CURRENT_STATUS
    CURRENT_STATUS = {"current": 0, "total": 0, "messages": [], "original_messages": []}
    
    try:
        # Get session username
        session_username = None
        try:
            with open(SESSION_FILE, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    if cookie.get('name') == 'ds_user_id':
                        session_username = cookie.get('value')
                        break
        except Exception as e:
            print(f"Session error: {str(e)}")
            return jsonify({"error": "Not logged in"}), 401

        if not session_username:
            return jsonify({"error": "Not logged in"}), 401

        # Get form data
        csv_file = request.files.get("csv_file")
        if not csv_file:
            return jsonify({"error": "No file uploaded"}), 400

        try:
            message_delay = int(request.form["message_delay"])
            num_dms = int(request.form["num_dms"])
        except (KeyError, ValueError) as e:
            return jsonify({"error": "Invalid form data"}), 400

        follow_users = request.form.get("follow_users") == "true"

        # Process CSV file
        try:
            csv_file_path = os.path.join('uploads', secure_filename(csv_file.filename))
            os.makedirs('uploads', exist_ok=True)
            csv_file.save(csv_file_path)
        except Exception as e:
            print(f"File save error: {str(e)}")
            return jsonify({"error": "Failed to save file"}), 500

        # Fix CSV format and delimiter
        try:
            fixed_csv_path = fix_csv_delimiter_and_format(csv_file_path)
            print(f"Using fixed file: {fixed_csv_path}")
        except Exception as e:
            print(f"CSV processing error: {str(e)}")
            if os.path.exists(csv_file_path):
                os.remove(csv_file_path)
            return jsonify({"error": "Failed to process CSV file"}), 500

        # Process messages
        messages_to_send = []
        skipped_users = []
        try:
            with open(fixed_csv_path, 'r', newline='', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                next(csv_reader)  # Skip header
                for row in csv_reader:
                    if len(row) >= 2:
                        username, message = row[0].strip(), row[1].strip()
                        CURRENT_STATUS["original_messages"].append({
                            "username": username,
                            "message": message
                        })
                        if check_if_messaged(session_username, username):
                            skipped_users.append(username)
                            CURRENT_STATUS["messages"].append({
                                "username": username,
                                "status": "Already messaged previously",
                                "message": message
                            })
                        else:
                            messages_to_send.append((username, message))
                            
            print(f"Total rows in CSV: {len(CURRENT_STATUS['original_messages'])}")
            print(f"Skipped users: {len(skipped_users)}")
            print(f"Messages to send: {len(messages_to_send)}")
            print(f"Skipped usernames: {', '.join(skipped_users)}")

        except Exception as e:
            print(f"Message processing error: {str(e)}")
            return jsonify({"error": "Failed to process messages"}), 500

        CURRENT_STATUS["total"] = min(len(messages_to_send), num_dms)
        
        def send_messages():
            messages_sent = 0
            for username, message in messages_to_send:
                if CURRENT_STATUS.get("stopped", False):
                    print("Stop signal received - terminating")
                    return
            
                if messages_sent >= num_dms:
                    break

                try:
                    if not CURRENT_STATUS.get("stopped", False):  # Check again before sending
                        status = send_dm(username, message, follow_first=follow_users)
                    
                        if status == "Message sent successfully":
                            save_to_history(session_username, username, status, message)
                            messages_sent += 1
                            CURRENT_STATUS["current"] = messages_sent

                        CURRENT_STATUS["messages"].append({
                            "username": username,
                            "status": status,
                            "message": message
                        })

                        # Add breaks only if not stopped
                        if not CURRENT_STATUS.get("stopped", False):
                            if messages_sent > 0 and messages_sent % random.randint(5, 10) == 0:
                                long_delay = random.uniform(60, 120)
                                print(f"Taking a longer break: {long_delay:.2f} seconds")
                                time.sleep(long_delay)
                            else:
                                actual_delay = random.uniform(message_delay, message_delay + 15)
                                print(f"Regular delay: {actual_delay:.2f} seconds")
                                time.sleep(actual_delay)

                except Exception as e:
                    print(f"Error sending message to {username}: {str(e)}")
                    if not CURRENT_STATUS.get("stopped", False):
                        CURRENT_STATUS["messages"].append({
                            "username": username,
                            "status": f"Error: {str(e)}",
                            "message": message
                        })

            # Clean up files
            try:
                if os.path.exists(csv_file_path):
                    os.remove(csv_file_path)
                if os.path.exists(fixed_csv_path) and fixed_csv_path != csv_file_path:
                    os.remove(fixed_csv_path)
            except Exception as e:
                print(f"Cleanup error: {str(e)}")

        # Start the sending process in a background thread
        thread = threading.Thread(target=send_messages)
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "started",
            "total": CURRENT_STATUS["total"],
            "message": "DM sending process started"
        })

    except Exception as e:
        print(f"Unexpected error in send_bulk_dms: {str(e)}")
        # Clean up files if they exist
        if 'csv_file_path' in locals() and os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        if 'fixed_csv_path' in locals() and os.path.exists(fixed_csv_path):
            os.remove(fixed_csv_path)
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500
        

@app.route("/stop_process", methods=["POST"])
def stop_process():
    global CURRENT_STATUS
    CURRENT_STATUS["stopped"] = True

    # Get session username
    try:
        with open(SESSION_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                if cookie.get('name') == 'ds_user_id':
                    session_username = cookie.get('value')
                    break
    except:
        return jsonify({"error": "Not logged in"})

    CURRENT_STATUS["messages"].append({
        "username": "SYSTEM",
        "status": "Process stopped by user",
        "message": ""
    })
    
    # Ensure we return a response
    return jsonify({
        "status": "stopped", 
        "current": CURRENT_STATUS["current"],
        "message": "Process successfully stopped"
    })

if __name__ == "__main__":
    app.run(debug=True)
