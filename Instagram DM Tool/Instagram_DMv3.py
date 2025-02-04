from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import csv
import time
import os
import io
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
    Ensures proper 'username,message' format for processing.
    """
    fixed_file_path = file_path.replace(".csv", "_fixed.csv")
    
    with open(file_path, 'r', newline='', encoding='utf-8-sig') as infile:
        content = infile.readlines()
        
        # Check for semicolon delimiter or invalid format
        if ';' in content[0]:
            print("Detected semicolon delimiter, fixing the file...")
        elif "username" not in content[0] or "message" not in content[0]:
            print("Missing header or invalid format, fixing the file...")
        else:
            print("CSV format is correct. No changes needed.")
            return file_path  # File is already correct
        
        # Fix the file
        with open(fixed_file_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile, delimiter=',')
            
            # Ensure correct header
            writer.writerow(["username", "message"])
            
            for line in content[1:]:  # Skip header in old file if exists
                parts = line.strip().split(';') if ';' in line else line.strip().split(',')
                
                if len(parts) >= 2:
                    username = parts[0].strip()
                    message = parts[1].strip()
                    writer.writerow([username, message])
        
        print(f"Fixed CSV saved to: {fixed_file_path}")
        return fixed_file_path


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

def initialize_driver(headless=False):
    """Initialize the Chrome WebDriver with configurable headless setting."""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    if headless:
        chrome_options.add_argument("--headless")
        print("Headless mode is enabled.")
    else:
        print("Headless mode is NOT enabled.")  # Log this statement

    print("Initializing ChromeDriver...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    print("ChromeDriver initialized successfully!")
    return driver

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

def send_dm(target_username, message_text, follow_first=False):
    """Send a DM to the specified username by navigating to their profile."""
    driver = None
    try:
        print(f"\n=== Starting DM process for {target_username} ===")
        
        if target_username in sent_messages_log:
            print(f"Skipping {target_username} - message already sent.")
            return f"Skipped {target_username} - message already sent."

        driver = initialize_driver(headless=True)
        print("Driver initialized successfully")
        
        # Initial setup and cookie loading
        driver.get("https://www.instagram.com")
        time.sleep(3)
        print("Loaded Instagram homepage")

        try:
            with open(SESSION_FILE, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(3)
            print("Session cookies loaded successfully")
        except FileNotFoundError:
            print("ERROR: Session file not found")
            return "Session not found. Please log in first."
        except Exception as e:
            print(f"ERROR loading cookies: {str(e)}")
            return f"Error loading session: {str(e)}"

        # Navigate to profile
        profile_url = f"https://www.instagram.com/{target_username}/"
        driver.get(profile_url)
        time.sleep(5)
        print(f"Navigated to profile: {profile_url}")

        if "Page Not Found" in driver.title or "Sorry, this page isn't available." in driver.page_source:
            return "Profile not found or not accessible"

        # Follow user if requested
        if follow_first:
            try:
                follow_button_xpaths = [
                    "//div[contains(@class, 'ap3a') and contains(@class, 'aaco') and contains(@class, 'aacw') and contains(@class, 'aad6') and contains(@class, '_aade') and text()='Follow']",
                    "//div[contains(@class, 'ap3a') and text()='Follow']",
                    "//div[@dir='auto' and text()='Follow']"
                ]
                
                followed = False
                for xpath in follow_button_xpaths:
                    try:
                        follow_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        follow_button.click()
                        followed = True
                        print("Followed user successfully")
                        time.sleep(2)
                        break
                    except Exception:
                        continue

                if not followed:
                    print("Could not follow user - might already be following")
            except Exception as e:
                print(f"WARNING: Could not follow user: {str(e)}")

        # Click Message button with retry logic
        message_button_xpaths = [
            "//div[contains(@class, 'x1i10hfl') and contains(@class, 'xjqpnuy') and contains(@class, 'xa49m3k') and contains(@role, 'button') and contains(text(), 'Message')]",
            "//div[contains(@role, 'button') and text()='Message']",
            "//div[contains(@class, '_acan') and text()='Message']"
        ]

        message_button_clicked = False

        # Step 1: Click the message button
        for xpath in message_button_xpaths:
            try:
                message_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                if message_button.text.strip().lower() == "message":
                    message_button.click()
                    message_button_clicked = True
                    print("Clicked message button successfully")
                    time.sleep(3)
                    break
            except Exception as e:
                print(f"Failed with xpath {xpath}: {e}")
                continue

        if not message_button_clicked:
            return "Could not click message button"

        # Step 2: Handle notification popup if it appears
        notification_buttons = [
            "//button[contains(@class, '_a9--')]",
            "//button[text()='Not Now']",
            "//button[contains(text(), 'Not Now')]",
            "//div[text()='Not Now']",
        ]

        time.sleep(2)  # Wait for notification
        for button_xpath in notification_buttons:
            try:
                not_now_button = driver.find_element(By.XPATH, button_xpath)
                not_now_button.click()
                print("Notification popup handled")
                time.sleep(2)
                break
            except:
                continue

        # Continue with the rest of your message sending code...


        # Verify chat window
        try:
            chat_indicators = [
                "//div[@role='textbox']",
                "//div[contains(@aria-label, 'Message')]",
                "//textarea[contains(@placeholder, 'Message')]"
            ]
            
            in_chat = False
            for indicator in chat_indicators:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, indicator))
                    )
                    in_chat = True
                    print("Successfully verified chat window is open")
                    break
                except Exception:
                    continue
            
            if not in_chat:
                print("Could not verify chat window is open")
                return "Failed to open chat window"

        except Exception as e:
            print(f"Error verifying chat window: {str(e)}")
            return "Failed to verify chat window"

        # Check for message requests restriction
        if "You can send more messages after your invite is accepted" in driver.page_source:
            print("Message requests restriction detected")
            return "Message in requests"

        # Send message
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
                
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                
                message_box.click()
                time.sleep(1)
                message_box.send_keys(message_text)
                time.sleep(1)
                message_box.send_keys(Keys.RETURN)
                time.sleep(3)
                
                try:
                    message_sent = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{message_text[:20]}')]"))
                    )
                    print(f"Message sent successfully using selector: {selector}")
                    break
                except Exception:
                    print("Message not appearing in chat, trying next method")
                    continue
                
            except Exception as e:
                print(f"Failed with selector {selector}, trying next...")
                continue

        if not message_sent:
            # JavaScript attempt
            try:
                success = driver.execute_script("""
                    var messageBox = document.querySelector('div[role="textbox"]');
                    if (messageBox) {
                        messageBox.click();
                        messageBox.focus();
                        return true;
                    }
                    return false;
                """)
                
                if success:
                    time.sleep(1)
                    webdriver.ActionChains(driver).send_keys(message_text).send_keys(Keys.RETURN).perform()
                    
                    try:
                        message_sent = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{message_text[:20]}')]"))
                        )
                        print("Message sent successfully using JavaScript method")
                    except Exception:
                        print("Message not appearing in chat after JavaScript method")
                        return "Failed to verify message was sent"
                        
            except Exception as e:
                print(f"JavaScript message attempt failed: {str(e)}")
                return "Could not send message using any available method"

        if message_sent:
            print("Message delivery confirmed")
            sent_messages_log.add(target_username)
            return "Message sent successfully"
        else:
            return "Failed to verify message was sent"

    except Exception as e:
        error_msg = f"ERROR in send_dm: {str(e)}"
        print(error_msg)
        if driver:
            try:
                screenshot_filename = f"error_screenshot_{target_username}_{int(time.time())}.png"
                screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_filename)
                driver.save_screenshot(screenshot_path)
                print(f"Error screenshot saved to {screenshot_path}")
            except Exception as screenshot_error:
                print(f"Could not save error screenshot: {str(screenshot_error)}")
        return error_msg

    finally:
        if driver:
            driver.quit()
            print("Driver closed successfully")


@app.route("/")
def home():
    return render_template("indexv2.html")

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
    session_username = None
    try:
        with open(SESSION_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                if cookie.get('name') == 'ds_user_id':
                    session_username = cookie.get('value')
                    break
    except:
        return jsonify({"error": "Not logged in"})

    remaining_messages = []
    
    # Add failed messages from current batch
    failed_usernames = set()
    for msg in CURRENT_STATUS["messages"]:
        if msg["status"] != "Message sent successfully" and msg["status"] != "Already messaged":
            remaining_messages.append({
                "username": msg["username"],
                "message": msg.get("message", "")
            })
            failed_usernames.add(msg["username"])
    
    # Add messages that weren't attempted yet
    if "original_messages" in CURRENT_STATUS:
        not_attempted = [msg for msg in CURRENT_STATUS["original_messages"]
                        if msg["username"] not in failed_usernames]
        remaining_messages.extend(not_attempted)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['username', 'message'])  # Header
    
    for msg in remaining_messages:
        writer.writerow([msg["username"], msg.get("message", "")])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=remaining_messages.csv"}
    )

@app.route("/reset_status", methods=["POST"])
def reset_status():
    global CURRENT_STATUS
    print("Reset status called") # Debug log
    CURRENT_STATUS = {"current": 0, "total": 0, "messages": [], "original_messages": []}
    return jsonify({"status": "reset"})

@app.route("/send_bulk_dms", methods=["POST"])
def send_bulk_dms():
    print("Send bulk DMs called") # Debug log
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
                        if not check_if_messaged(session_username, username):
                            messages_to_send.append((username, message))
        except Exception as e:
            print(f"Message processing error: {str(e)}")
            return jsonify({"error": "Failed to process messages"}), 500

        CURRENT_STATUS["total"] = min(len(messages_to_send), num_dms)
        
        def send_messages():
            messages_sent = 0
            for username, message in messages_to_send:
                if messages_sent >= num_dms:
                    break

                try:
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

                    time.sleep(message_delay)
                except Exception as e:
                    print(f"Error sending message to {username}: {str(e)}")
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
    session_username = None
    try:
        with open(SESSION_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                if cookie.get('name') == 'ds_user_id':
                    session_username = cookie.get('value')
                    break
    except:
        return jsonify({"error": "Not logged in"})

    # Update status to show process was stopped
    CURRENT_STATUS["messages"].append({
        "username": "SYSTEM",
        "status": "Process stopped by user",
        "message": ""
    })
    
    return jsonify({"status": "stopped", "current": CURRENT_STATUS["current"]})

if __name__ == "__main__":
    app.run(debug=True)
