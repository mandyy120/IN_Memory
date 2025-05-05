from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import os
import sys
import threading
import time
import subprocess
import hashlib
import requests
import datetime
from final2 import KnowledgeRetrieval
from text import process_file  # Changed from corpus2 import generate_corpus
import json
import io
# Import the new Gdrive module
import Gdrive
# Import message broker for streaming API
try:
    from message_broker import broker as message_broker
except ImportError:
    print("Message broker not available. Streaming API will use direct processing.")
    message_broker = None
try:
    import boto3
except ImportError:
    print("boto3 not installed. AWS S3 functionality will not work.")
try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv not installed. AWS S3 and Slack functionality will not work.")
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    print("slack_sdk not installed. Slack functionality will not work.")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for sessions
# Configure session to be more secure
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
CORS(app, resources={r"/*": {"origins": "*"}})

# Global variables for tracking progress
processing_status = {
    "progress": 0,
    "status": "idle",
    "error": None
}

# MongoDB configuration
def get_app_config():
    """Get application configuration from config file or environment variables."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    # Default configuration
    config = {
        "connection_string": "mongodb://localhost:27017",
        "db_name": "KnowledgeBase",
        "repository_file": "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"
    }

    # Try to load from config file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"Error loading config file: {e}")

    # Override with environment variables if present
    if os.environ.get("MONGODB_CONNECTION_STRING"):
        config["connection_string"] = os.environ.get("MONGODB_CONNECTION_STRING")
    if os.environ.get("MONGODB_DB_NAME"):
        config["db_name"] = os.environ.get("MONGODB_DB_NAME")
    if os.environ.get("REPOSITORY_FILE"):
        config["repository_file"] = os.environ.get("REPOSITORY_FILE")

    return config

# Initialize the KnowledgeRetrieval system at startup
try:
    # Get application configuration
    app_config = get_app_config()
    connection_string = app_config.get("connection_string", "mongodb://localhost:27017")
    db_name = app_config.get("db_name", "KnowledgeBase")
    repository_file = app_config.get("repository_file")

    # Initialize with MongoDB
    print(f"Initializing KnowledgeRetrieval with MongoDB: {db_name}")
    knowledge_system = KnowledgeRetrieval(
        mongo_connection_string=connection_string,
        mongo_db_name=db_name
    )

    print("Knowledge system class initialized successfully.")

    # Load data from repository file if specified
    if repository_file and os.path.exists(repository_file):
        print(f"Using repository file from config: {repository_file}")
        knowledge_system.load_data(local=True, file_path=repository_file, save_to_db=True, process_source="main")

    print("Knowledge system initialized successfully!")

except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize KnowledgeRetrieval: {e}")
    print("Application may not function correctly.")

# Data loading is now handled during initialization

# Google Drive API constants
MIME_TYPES = {
    'txt': "text/plain",
    'pdf': "application/pdf",
    'docx': "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

# Google OAuth configuration
GOOGLE_CLIENT_ID = "311723313181-pp08rji8pjkl9jd1vdq33tisumlfavjm.apps.googleusercontent.com"  # Replace with your actual client ID
GOOGLE_CLIENT_SECRET = "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"  # Replace with your actual client secret
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_PROVIDER_X509_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"

# Function to get the redirect URI based on the request
def get_redirect_uri():
    """Get the redirect URI based on the request host"""
    # Always use the current host dynamically
    host = request.host_url.rstrip('/')

    # For ngrok URLs, ensure we're using https
    if 'ngrok-free.app' in host:
        # Extract the ngrok subdomain
        if host.startswith('http://'):
            host = 'https://' + host[7:]

    redirect_uri = f"{host}/oauth2callback"
    print(f"DEBUG - Using dynamic redirect URI: {redirect_uri}")

    # Log additional information for debugging
    print(f"DEBUG - Request host: {request.host}")
    print(f"DEBUG - Request scheme: {request.scheme}")
    print(f"DEBUG - Request URL: {request.url}")
    print(f"DEBUG - Request headers: {dict(request.headers)}")

    return redirect_uri

# Store OAuth tokens (in a real application, this would be in a database)
# We'll use a dictionary with session IDs as keys
oauth_tokens = {}

# Helper function to get a unique session ID for the current user
def get_user_session_id():
    """Get a unique session ID for the current user"""
    # Make the session permanent so it doesn't expire when the browser is closed
    session.permanent = True

    # Check if a session ID exists, if not create one
    if 'user_session_id' not in session:
        # Generate a random session ID
        session['user_session_id'] = hashlib.md5(os.urandom(32)).hexdigest()
        print(f"Created new session ID: {session['user_session_id']}")
    else:
        print(f"Using existing session ID: {session['user_session_id']}")

    return session['user_session_id']

# AWS S3 constants
AWS_CREDENTIALS_FILE = '.env'

# Slack constants
SLACK_CREDENTIALS_FILE = '.env'

def reset_processing_status():
    global processing_status
    processing_status = {
        "progress": 0,
        "status": "idle",
        "error": None,
        "total_files": 0,
        "processed_files": 0,
        "current_file": ""
    }
# Simplified language detection function for English-only processing
def detect_language(_):
    """
    Always returns 'en' since we only support English now.

    Parameters:
    _ (str): Text to analyze (ignored)

    Returns:
    str: Always 'en' for English
    """
    return 'en'  # Always return English
@app.route('/')
def home_page():
    """Serve the home page (query interface)"""
    return render_template('home.html')

@app.route('/data-input')
def data_input_page():
    """Serve the data input page"""
    return render_template('data_input.html')

@app.route('/api-examples')
def api_examples_page():
    """Serve the API examples page"""
    return render_template('api_examples.html')

@app.route('/current-ngrok-url')
def current_ngrok_url():
    """Return the current ngrok URL"""
    # Get the current host URL
    host_url = request.host_url.rstrip('/')

    # For ngrok URLs, ensure we're using https
    if 'ngrok-free.app' in host_url:
        if host_url.startswith('http://'):
            host_url = 'https://' + host_url[7:]

    return jsonify({"url": host_url})

@app.route('/query', methods=['POST'])
def handle_query():
    """Process query requests from the query interface (English only)"""
    data = request.get_json()
    user_query = data.get('query', '').strip()
    use_local = data.get('use_local', False)  # New parameter to control local rephrasing

    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        # Log the query for debugging
        print(f"Processing query: {user_query}")
        if use_local:
            print("Using local rephrasing (no API calls)")

        # Check if query starts with 'local ' and remove it if present
        if user_query.lower().startswith('local '):
            user_query = user_query[6:].strip()
            use_local = True
            print("Detected 'local' command in query, using local rephrasing")

        # Generate description using the standard method
        # For original description, include topics and PMI
        if hasattr(knowledge_system, 'generate_description') and 'include_topics_and_pmi' in knowledge_system.generate_description.__code__.co_varnames:
            # If the method supports the include_topics_and_pmi parameter
            original_description = knowledge_system.generate_description(user_query, include_topics_and_pmi=True)
            # Generate a clean version without topics and PMI for rephrasing
            clean_description = knowledge_system.generate_description(user_query, include_topics_and_pmi=False)
        else:
            # Fallback to the old method
            original_description = knowledge_system.generate_description(user_query)
            clean_description = original_description

        print(f"Generated description length: {len(original_description)} characters")

        # Rephrase using Mistral AI if available
        try:
            if hasattr(knowledge_system, 'rephrase_with_mistral'):
                # Check if the method accepts the use_api parameter
                if 'use_api' in knowledge_system.rephrase_with_mistral.__code__.co_varnames:
                    # Use the clean description (without topics and PMI) for rephrasing
                    rephrased_description = knowledge_system.rephrase_with_mistral(
                        clean_description,
                        use_api=not use_local,  # If use_local is True, use_api should be False
                        use_cache=True
                    )
                else:
                    # Fallback to the old method without parameters
                    rephrased_description = knowledge_system.rephrase_with_mistral(clean_description)
                print(f"Rephrased description length: {len(rephrased_description)} characters")
            else:
                rephrased_description = clean_description
        except Exception as rephrase_error:
            print(f"Error in rephrasing: {rephrase_error}")
            # Fallback to original description if rephrasing fails
            rephrased_description = clean_description

        return jsonify({
            "original_description": original_description,
            "rephrased_description": rephrased_description,
            "detected_language": "en",  # Always English
            "used_local_rephrasing": use_local  # Indicate whether local rephrasing was used
        })
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        return jsonify({"error": f"Error processing query: {str(e)}"}), 500

@app.route('/progress', methods=['GET'])
def get_progress():
    """Return the current processing status and progress"""
    global processing_status
    return jsonify(processing_status)

@app.route('/file-progress', methods=['GET'])
def get_file_progress():
    """Return the current file processing status and progress"""
    global processing_status
    return jsonify(processing_status)

def process_file_async(file_path, output_file):
    """Process a single file in a separate thread and update progress"""
    global processing_status
    global knowledge_system

    try:
        processing_status["status"] = "reading"
        processing_status["progress"] = 10
        time.sleep(1)  # Just to make progress visible

        # Generate corpus from the file content using text.py's process_file function
        processing_status["status"] = "generating_corpus"
        processing_status["progress"] = 30

        # Call the process_file function from text.py
        process_file(file_path, output_file)

        # Update progress
        processing_status["status"] = "processing_content"
        processing_status["progress"] = 60

        processing_status["status"] = "loading_knowledge"
        processing_status["progress"] = 70

        # Update existing knowledge system instead of replacing it
        try:
            # Load the processed data - let the system handle checking for new data
            knowledge_system.load_data(local=True, file_path=output_file, append=True, save_to_db=True, process_source="main")

            processing_status["status"] = "complete"
            processing_status["progress"] = 100

            print(f"File processing complete. Knowledge system updated and saved.")

        except Exception as e:
            processing_status["status"] = "error"
            processing_status["error"] = f"Error in knowledge system processing: {str(e)}"
            print(f"Error in knowledge system: {e}")

    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error in file processing: {e}")

def process_multiple_files_async(file_paths, output_file):
    """Process multiple files in a separate thread and update progress"""
    global processing_status
    global knowledge_system

    try:
        total_files = len(file_paths)
        processing_status["total_files"] = total_files
        processing_status["processed_files"] = 0
        processing_status["status"] = "processing_multiple_files"
        processing_status["progress"] = 5

        # Create a temporary file for each file's processed content
        temp_output_files = []

        # Process each file individually
        for i, file_path in enumerate(file_paths):
            file_name = os.path.basename(file_path)
            processing_status["status"] = f"processing_file_{i+1}_of_{total_files}"
            processing_status["current_file"] = file_name
            processing_status["progress"] = 5 + (i * 70 // total_files)

            # Create a temporary output file for this file
            temp_output = os.path.join(os.path.dirname(output_file), f"temp_output_{i}_{int(time.time())}.txt")

            try:
                # Process the file
                process_file(file_path, temp_output)
                temp_output_files.append(temp_output)

                # Update progress
                processing_status["processed_files"] = i + 1
                processing_status["progress"] = 5 + ((i + 1) * 70 // total_files)

            except Exception as e:
                print(f"Error processing file {file_name}: {e}")
                # Continue with other files even if one fails

        # Combine all processed files into the final output file
        processing_status["status"] = "combining_files"
        processing_status["progress"] = 75

        # If the output file already exists, we'll append to it
        # Otherwise, we'll create a new one
        if not os.path.exists(output_file):
            # Create an empty file
            with open(output_file, 'w', encoding='utf-8') as f:
                pass

        # Append each temp file to the output file
        for temp_file in temp_output_files:
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                with open(temp_file, 'r', encoding='utf-8') as src:
                    content = src.read()

                    with open(output_file, 'a', encoding='utf-8') as dest:
                        dest.write(content)
                        dest.write("\n\n")  # Add some separation between files

                # Clean up the temp file
                try:
                    os.remove(temp_file)
                except:
                    pass  # Ignore errors in cleanup

        # Load the combined data into the knowledge system
        processing_status["status"] = "loading_knowledge"
        processing_status["progress"] = 85

        try:
            # Load the processed data - let the system handle checking for new data
            knowledge_system.load_data(local=True, file_path=output_file, append=True, save_to_db=True, process_source="main")

            processing_status["status"] = "complete"
            processing_status["progress"] = 100

            print(f"Multiple files processing complete. Knowledge system updated and saved.")

        except Exception as e:
            processing_status["status"] = "error"
            processing_status["error"] = f"Error in knowledge system processing: {str(e)}"
            print(f"Error in knowledge system: {e}")

        # Clean up the temporary directory
        try:
            if file_paths and len(file_paths) > 0:
                temp_dir = os.path.dirname(file_paths[0])
                if os.path.exists(temp_dir) and 'temp_' in temp_dir:
                    import shutil
                    shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary directory: {e}")

    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error in multiple files processing: {e}")

def update_status(status_info):
    """Update the global processing status with provided information"""
    global processing_status

    if status_info and isinstance(status_info, dict):
        for key, value in status_info.items():
            processing_status[key] = value

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle single file upload and processing (legacy route)"""
    global processing_status

    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # If user does not select file, browser might send empty file without filename
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        try:
            # Reset processing status
            reset_processing_status()
            processing_status["status"] = "starting"

            # Create uploads directory if it doesn't exist
            os.makedirs('uploads', exist_ok=True)

            # Save the file
            input_file_path = os.path.join('uploads', file.filename)
            file.save(input_file_path)

            # Define output file path - use the configured repository file if available
            output_file_path = app_config.get("repository_file", "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt")

            # Start processing in a separate thread to not block the response
            processing_thread = threading.Thread(
                target=process_file_async,
                args=(input_file_path, output_file_path)
            )
            processing_thread.start()

            return jsonify({
                "message": "File uploaded and processing started.",
                "status": "processing"
            })

        except Exception as e:
            reset_processing_status()
            processing_status["status"] = "error"
            processing_status["error"] = str(e)
            return jsonify({"error": f"Error processing file: {str(e)}"}), 500

    return jsonify({"error": "Unknown error occurred"}), 500

@app.route('/upload-multiple', methods=['POST'])
def upload_multiple_files():
    """Handle multiple file uploads and processing"""
    global processing_status

    # Check if the post request has the files part
    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist('files')

    # Check if any files were selected
    if not files or files[0].filename == '':
        return jsonify({"error": "No files selected"}), 400

    try:
        # Reset processing status
        reset_processing_status()
        processing_status["status"] = "starting"
        processing_status["total_files"] = len(files)
        processing_status["processed_files"] = 0

        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)

        # Create a temporary directory for the uploaded files
        temp_dir = os.path.join('uploads', 'temp_' + str(int(time.time())))
        os.makedirs(temp_dir, exist_ok=True)

        # Save all files
        file_paths = []
        for file in files:
            if file and file.filename:
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)
                file_paths.append(file_path)

        # Define output file path - use the configured repository file if available
        output_file_path = app_config.get("repository_file", "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt")

        # Start processing in a separate thread to not block the response
        processing_thread = threading.Thread(
            target=process_multiple_files_async,
            args=(file_paths, output_file_path)
        )
        processing_thread.start()

        return jsonify({
            "message": f"{len(files)} files uploaded and processing started.",
            "status": "processing"
        })

    except Exception as e:
        reset_processing_status()
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        return jsonify({"error": f"Error processing files: {str(e)}"}), 500

@app.route('/start-crawl', methods=['POST'])
def start_crawl():
    """Handle web crawling requests"""
    global processing_status

    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400

        # Reset processing status
        reset_processing_status()
        processing_status["status"] = "starting_crawl"
        processing_status["progress"] = 5

        # Start crawling in a separate thread
        threading.Thread(
            target=crawl_website,
            args=(url,)
        ).start()

        return jsonify({"message": "Crawling started"})
    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        return jsonify({"error": str(e)}), 500

def crawl_website(url):
    """Crawl website and process the content"""
    global processing_status
    global knowledge_system

    try:
        # Import the crawling module here to avoid circular imports
        # This now uses the adapter for crawling2.py
        import crawling

        # Update status
        processing_status["status"] = "crawling"
        processing_status["progress"] = 20

        # Get content from crawling.py (which now uses crawling2.py)
        content = crawling.crawl(url)

        # Create a safe filename from the URL for the raw content
        safe_url = url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_')
        raw_content_file = os.path.join('uploads', f"crawled_{safe_url[:50]}.txt")

        # Save raw crawled content to the URL-specific file with proper encoding
        with open(raw_content_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Raw crawled content saved to: {raw_content_file}")

        # Check if we got meaningful content
        if content.startswith("No content was retrieved from"):
            processing_status["status"] = "error"
            processing_status["error"] = content
            print(f"Crawling error: {content}")
            return  # Exit the function early

        # Update status
        processing_status["status"] = "processing_content"
        processing_status["progress"] = 40

        # Define output file path - use the configured repository file if available
        output_file_path = app_config.get("repository_file", "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt")

        # Process the crawled content using text.py's process_file function
        process_file(raw_content_file, output_file_path)

        # Load the generated corpus into the knowledge system
        processing_status["status"] = "loading_knowledge"
        processing_status["progress"] = 90

        # Update existing knowledge system - let the system handle checking for new data
        knowledge_system.load_data(local=True, file_path=output_file_path, append=True, save_to_db=True)

        processing_status["status"] = "complete"
        processing_status["progress"] = 100

        print(f"Web crawling complete. Knowledge system updated and saved.")

    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error in web crawling: {e}")

# New Google Drive integration endpoints
@app.route('/save-credentials', methods=['POST'])
def save_credentials():
    """Save user credentials securely"""
    try:
        data = request.get_json()
        credential_type = data.get('credentialType')
        credentials = data.get('credentials')

        if not credential_type or not credentials:
            return jsonify({"error": "Missing credential type or credentials"}), 400

        # Create credentials directory if it doesn't exist
        os.makedirs('user_credentials', exist_ok=True)

        # Save credentials based on type
        if credential_type == 'google':
            # Save Google Drive credentials
            with open('user_credentials/google_credentials.json', 'w') as f:
                json.dump(credentials, f, indent=2)

            # For immediate use, update the service account file path
            global SERVICE_ACCOUNT_FILE
            SERVICE_ACCOUNT_FILE = 'user_credentials/google_credentials.json'

        elif credential_type == 'aws':
            # Save AWS S3 credentials to .env file
            with open('user_credentials/aws_credentials.env', 'w') as f:
                f.write(f"AWS_ACCESS_KEY_ID={credentials.get('awsAccessKey', '')}\n")
                f.write(f"AWS_SECRET_ACCESS_KEY={credentials.get('awsSecretKey', '')}\n")
                f.write(f"AWS_DEFAULT_REGION={credentials.get('awsRegion', 'us-east-1')}\n")
                f.write(f"S3_BUCKET_NAME={credentials.get('awsBucket', '')}\n")

            # For immediate use, update the AWS credentials file path
            global AWS_CREDENTIALS_FILE
            AWS_CREDENTIALS_FILE = 'user_credentials/aws_credentials.env'

        elif credential_type == 'slack':
            # Save Slack credentials to .env file
            with open('user_credentials/slack_credentials.env', 'w') as f:
                f.write(f"SLACK_BOT_TOKEN={credentials.get('slackBotToken', '')}\n")

            # For immediate use, update the Slack credentials file path
            global SLACK_CREDENTIALS_FILE
            SLACK_CREDENTIALS_FILE = 'user_credentials/slack_credentials.env'

        elif credential_type == 'api':
            # Save API credentials
            with open('user_credentials/api_credentials.json', 'w') as f:
                json.dump(credentials, f, indent=2)

        elif credential_type == 'db':
            # Save database credentials
            with open('user_credentials/db_credentials.json', 'w') as f:
                json.dump(credentials, f, indent=2)

        else:
            return jsonify({"error": f"Unknown credential type: {credential_type}"}), 400

        return jsonify({"message": f"{credential_type.capitalize()} credentials saved successfully"})

    except Exception as e:
        print(f"Error saving credentials: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-drive-file-types', methods=['GET'])
def get_drive_file_types():
    """Return available file types for Google Drive fetching"""
    return jsonify(list(MIME_TYPES.keys()))

@app.route('/get-drive-user-info', methods=['GET'])
def get_drive_user_info():
    """Get Google Drive user information"""
    # Get the user's session ID
    user_id = get_user_session_id()

    # Check if we have a token for this user
    if user_id not in oauth_tokens:
        return jsonify({"error": "Not authorized. Please connect to Google Drive first."}), 401

    # Get the token and user info
    token_info = oauth_tokens[user_id]
    user_info = token_info.get('user_info', {})

    # Return user info
    return jsonify({
        "isConnected": True,
        "email": user_info.get('email', 'Unknown'),
        "name": user_info.get('name', 'Unknown'),
        "picture": user_info.get('picture', '')
    })

@app.route('/get-drive-files', methods=['GET'])
def get_drive_files():
    """Get files from Google Drive using the stored OAuth token"""
    # Get the user's session ID
    user_id = get_user_session_id()

    # Check if we have a token for this user
    if user_id not in oauth_tokens:
        return jsonify({"error": "Not authorized. Please connect to Google Drive first."}), 401

    # Get the token
    token_info = oauth_tokens[user_id]
    access_token = token_info.get('access_token')

    if not access_token:
        return jsonify({"error": "Invalid token. Please reconnect to Google Drive."}), 401

    # Get the file type filter, folder ID, and global search flag from the query parameters
    file_type = request.args.get('type', 'all')
    folder_id = request.args.get('folder', 'root')
    global_search = request.args.get('global', 'false').lower() == 'true'

    try:
        # Use the Gdrive module to list files
        result = Gdrive.list_files(access_token, file_type, folder_id, global_search)
        return jsonify(result)
    except Exception as e:
        print(f"Error listing Drive files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/fetch-from-drive', methods=['POST'])
def fetch_from_drive():
    """Handle Google Drive document fetching using the new Gdrive.py module"""
    global processing_status
    # Get the user's session ID
    user_id = get_user_session_id()

    try:
        # Check if we have a token for this user
        if user_id not in oauth_tokens:
            return jsonify({"error": "Not authorized. Please connect to Google Drive first."}), 401

        # Get the token
        token_info = oauth_tokens[user_id]
        access_token = token_info.get('access_token')

        if not access_token:
            return jsonify({"error": "Invalid token. Please reconnect to Google Drive."}), 401

        data = request.get_json()
        selected_files = data.get('selectedFiles', [])

        if not selected_files:
            return jsonify({"error": "No files selected. Please select files to process."}), 400

        # Reset processing status
        reset_processing_status()
        processing_status["status"] = "starting_drive_fetch"
        processing_status["progress"] = 5
        processing_status["total_files"] = len(selected_files)

        # Start drive fetching in a separate thread
        threading.Thread(
            target=process_drive_files,
            args=(selected_files, access_token)
        ).start()

        return jsonify({"message": "Google Drive fetch started", "fileCount": len(selected_files)})
    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        return jsonify({"error": str(e)}), 500

@app.route('/fetch-from-s3', methods=['POST'])
def fetch_from_s3():
    """Handle AWS S3 document fetching"""
    global processing_status

    try:
        data = request.get_json()
        file_types = data.get('fileTypes', [])

        if not file_types or not isinstance(file_types, list):
            return jsonify({"error": "File types must be provided as a list"}), 400

        # Validate file types
        for ft in file_types:
            if ft not in MIME_TYPES:
                return jsonify({"error": f"Unsupported file type: {ft}"}), 400

        # Reset processing status
        reset_processing_status()
        processing_status["status"] = "starting_s3_fetch"
        processing_status["progress"] = 5

        # Start S3 fetching in a separate thread
        threading.Thread(
            target=fetch_s3_files_async,
            args=(file_types,)
        ).start()

        return jsonify({"message": "AWS S3 fetch started"})
    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        return jsonify({"error": str(e)}), 500

@app.route('/fetch-from-slack', methods=['POST'])
def fetch_from_slack():
    """
    Handle Slack message and file fetching

    Expected JSON payload:
    {
        "sources": ["public", "private", "dm"],  // Types of channels to fetch from
        "dataTypes": ["messages", "files"],      // Types of data to fetch
        "slackBotToken": "xoxb-your-token"      // Optional Slack bot token
    }
    """
    global processing_status

    try:
        data = request.get_json()
        sources = data.get('sources', [])
        data_types = data.get('dataTypes', [])
        slack_token = data.get('slackBotToken')  # Optional bot token

        if not sources or not isinstance(sources, list):
            return jsonify({"error": "Sources must be provided as a list"}), 400

        if not data_types or not isinstance(data_types, list):
            return jsonify({"error": "Data types must be provided as a list"}), 400

        # Validate sources
        valid_sources = ['public', 'private', 'dm']
        for source in sources:
            if source not in valid_sources:
                return jsonify({"error": f"Unsupported source: {source}"}), 400

        # Validate data types
        valid_data_types = ['messages', 'files']
        for data_type in data_types:
            if data_type not in valid_data_types:
                return jsonify({"error": f"Unsupported data type: {data_type}"}), 400

        # Reset processing status
        reset_processing_status()
        processing_status["status"] = "starting_slack_fetch"
        processing_status["progress"] = 5

        # Start Slack fetching in a separate thread
        threading.Thread(
            target=fetch_slack_data_async,
            args=(sources, data_types, slack_token)
        ).start()

        return jsonify({"message": "Slack fetch started"})
    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        return jsonify({"error": str(e)}), 500

def fetch_slack_data_async(sources, data_types, provided_token=None):
    """
    Process Slack data in a separate thread

    Args:
        sources (list): List of channel types to fetch from (public, private, dm)
        data_types (list): List of data types to fetch (messages, files)
        provided_token (str, optional): Slack bot token provided in the API call
    """
    global processing_status
    global knowledge_system

    try:
        processing_status["status"] = "initializing_slack_api"
        processing_status["progress"] = 10

        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)

        # Define output file path for collected texts
        output_file_path = os.path.join('uploads', 'collected_slack_texts.txt')

        # Determine which Slack token to use
        slack_token = None

        # 1. Use token provided in the API call if available
        if provided_token:
            slack_token = provided_token
            print("Using Slack token provided in API call")
        else:
            # 2. Check for user credentials
            user_credentials_path = 'user_credentials/slack_credentials.env'
            if os.path.exists(user_credentials_path):
                # Use user-provided credentials
                credential_file = user_credentials_path
                # Load the Slack token from the credentials file
                from dotenv import load_dotenv
                load_dotenv(credential_file)
                slack_token = os.getenv("SLACK_BOT_TOKEN")
                print("Using Slack token from user credentials")
            else:
                # 3. Fall back to default credentials
                credential_file = SLACK_CREDENTIALS_FILE
                # Load the Slack token from the credentials file
                from dotenv import load_dotenv
                load_dotenv(credential_file)
                slack_token = os.getenv("SLACK_BOT_TOKEN")
                print("Using Slack token from default credentials")

        if not slack_token:
            processing_status["status"] = "error"
            processing_status["error"] = "Missing Slack Bot Token. Please provide a token in the API call or save it in credentials."
            return

        # Convert sources and data_types lists to comma-separated strings
        sources_str = ','.join(sources)
        data_types_str = ','.join(data_types)

        # Run the slack_integration.py script with the selected sources and data types
        processing_status["status"] = "running_slack_integration"
        processing_status["progress"] = 20

        try:
            # Create a temporary copy of slack_integration.py with the correct output path
            with open('slack_integration.py', 'r') as f:
                script_content = f.read()

            # Replace the FETCHED_DATA_PATH with our repository path
            repository_path = "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"
            modified_script = script_content.replace(
                'FETCHED_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "augmentoolkit", "original", "saved_pages", "fetched_data.txt"))',
                f'FETCHED_DATA_PATH = "{repository_path}"'
            )

            # Write the modified script to a temporary file
            temp_script_path = 'temp_slack_integration.py'
            with open(temp_script_path, 'w') as f:
                f.write(modified_script)

            # Set environment variables for the script
            env = os.environ.copy()
            env["SLACK_BOT_TOKEN"] = slack_token

            # Run the modified script
            cmd = [sys.executable, temp_script_path, sources_str, data_types_str]
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate()

            # Clean up the temporary script
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)

            if process.returncode != 0:
                processing_status["status"] = "error"
                processing_status["error"] = f"Slack integration failed: {stderr}"
                return

            # Extract the output file path from the script's output
            output_path = None
            for line in stdout.splitlines():
                if line.startswith("[SLACK_FETCH_RESULT_PATH]"):
                    output_path = line.split("[SLACK_FETCH_RESULT_PATH]")[1].strip()
                    break

            if not output_path or not os.path.exists(output_path):
                processing_status["status"] = "error"
                processing_status["error"] = "Failed to get output from Slack integration"
                return

            # Copy the content to our output file
            with open(output_path, 'r', encoding='utf-8') as src:
                with open(output_file_path, 'w', encoding='utf-8') as dest:
                    dest.write(src.read())

            processing_status["status"] = "slack_data_fetched"
            processing_status["progress"] = 70

        except Exception as script_error:
            processing_status["status"] = "error"
            processing_status["error"] = f"Error running Slack integration: {str(script_error)}"
            return

        # Process the collected texts
        if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
            processing_status["status"] = "processing_slack_content"
            processing_status["progress"] = 75

            # Define output file path for knowledge system
            knowledge_output_path = "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"

            # Process the Slack content
            process_file(output_file_path, knowledge_output_path)

            # Load the generated corpus into the knowledge system
            processing_status["status"] = "loading_knowledge"
            processing_status["progress"] = 90

            # Update existing knowledge system
            knowledge_system.load_data(local=True, file_path=knowledge_output_path, append=True)

            # Save the updated backend tables
            knowledge_system.save_backend_tables()

            processing_status["status"] = "complete"
            processing_status["progress"] = 100

            print(f"Slack data processing complete. Knowledge system updated and saved.")
        else:
            processing_status["status"] = "error"
            processing_status["error"] = "No content was retrieved from Slack"
            print("No content was retrieved from Slack")

    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error in Slack data processing: {e}")

def fetch_s3_files_async(file_types):
    """Process AWS S3 files in a separate thread"""
    global processing_status
    global knowledge_system

    try:
        processing_status["status"] = "initializing_s3_api"
        processing_status["progress"] = 10

        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)

        # Define output file path for collected texts
        output_file_path = os.path.join('uploads', 'collected_s3_texts.txt')

        # Check for user credentials first
        user_credentials_path = 'user_credentials/aws_credentials.env'
        if os.path.exists(user_credentials_path):
            # Use user-provided credentials
            credential_file = user_credentials_path
        else:
            # Fall back to default credentials
            credential_file = AWS_CREDENTIALS_FILE

        # Load environment variables from the credentials file
        from dotenv import load_dotenv
        load_dotenv(credential_file)

        # Get AWS credentials from environment variables
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        bucket_name = os.getenv("S3_BUCKET_NAME")

        if not aws_access_key or not aws_secret_key or not bucket_name:
            processing_status["status"] = "error"
            processing_status["error"] = "Missing AWS credentials or bucket name"
            return

        # Initialize AWS S3 client
        try:
            import boto3
            s3 = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )

            # Delete previous output if any
            if os.path.exists(output_file_path):
                os.remove(output_file_path)

            processing_status["status"] = "listing_s3_objects"
            processing_status["progress"] = 20

            total_files_processed = 0
            total_files_found = 0

            # Process each selected type
            for file_type_index, ft in enumerate(file_types):
                processing_status["status"] = f"searching_{ft}_files"

                # List files in the S3 bucket
                paginator = s3.get_paginator('list_objects_v2')

                files = []
                for page in paginator.paginate(Bucket=bucket_name):
                    for obj in page.get('Contents', []):
                        key = obj['Key']
                        ext = os.path.splitext(key)[1]

                        if ext.lstrip('.') == ft:  # Match the selected file types
                            files.append({
                                'key': key,
                                'size': obj['Size']
                            })

                total_files_found += len(files)
                print(f"[INFO] Found {len(files)} {ft} files in S3 bucket")

                # Update status with file count
                processing_status["status"] = f"found_{len(files)}_{ft}_files"
                current_progress = 20 + (file_type_index * 5)
                processing_status["progress"] = min(current_progress, 30)

                processing_status["status"] = f"downloading_{ft}_files"

                # Process files of this type
                for file in files:
                    key = file['key']
                    file_name = os.path.basename(key)

                    try:
                        # Download file content
                        processing_status["current_file"] = file_name

                        # Get the object from S3
                        file_obj = s3.get_object(Bucket=bucket_name, Key=key)
                        body = file_obj['Body'].read()
                        fh = io.BytesIO(body)

                        # Save content to the output file
                        with open(output_file_path, 'a', encoding='utf-8') as out:
                            out.write(f"\n\n--- {file_name} ---\n\n")

                            # Process based on file type
                            if ft == 'txt':
                                content = fh.read().decode('utf-8')
                                out.write(content)

                            elif ft == 'pdf':
                                # Import here to avoid potential import issues
                                from PyPDF2 import PdfReader
                                reader = PdfReader(fh)
                                for page in reader.pages:
                                    # Extract text
                                    extracted_text = page.extract_text() or ""
                                    out.write(extracted_text)

                            elif ft == 'docx':
                                # Import here to avoid potential import issues
                                from docx import Document
                                # Save as temporary file
                                temp_file = "temp.docx"
                                with open(temp_file, "wb") as temp:
                                    temp.write(fh.read())

                                # Process docx
                                doc = Document(temp_file)
                                for para in doc.paragraphs:
                                    out.write(para.text + '\n')

                                # Remove temporary file
                                if os.path.exists(temp_file):
                                    os.remove(temp_file)

                        # Update progress
                        total_files_processed += 1
                        if total_files_found > 0:
                            current_progress = 30 + (total_files_processed / total_files_found * 40)
                            processing_status["progress"] = min(int(current_progress), 70)

                    except Exception as file_error:
                        print(f"Error processing {file_name}: {file_error}")
                        continue

            # Process the collected texts using text.py
            if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
                processing_status["status"] = "processing_s3_content"
                processing_status["progress"] = 75

                # Define output file path for knowledge system
                knowledge_output_path = "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"

                # Process the S3 content
                process_file(output_file_path, knowledge_output_path)

                # Load the generated corpus into the knowledge system
                processing_status["status"] = "loading_knowledge"
                processing_status["progress"] = 90

                # Update existing knowledge system
                knowledge_system.load_data(local=True, file_path=knowledge_output_path, append=True)

                # Save the updated backend tables
                knowledge_system.save_backend_tables()

                processing_status["status"] = "complete"
                processing_status["progress"] = 100

                print(f"S3 file processing complete. Knowledge system updated and saved.")
            else:
                processing_status["status"] = "error"
                processing_status["error"] = "No content was retrieved from AWS S3"
                print("No content was retrieved from AWS S3")

        except Exception as s3_api_error:
            print(f"Error with AWS S3 API: {s3_api_error}")
            processing_status["status"] = "error"
            processing_status["error"] = f"Error with AWS S3 API: {str(s3_api_error)}"

    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error in S3 file processing: {e}")

def process_drive_files(selected_files, access_token):
    """Process Google Drive files in a separate thread"""
    global processing_status
    global knowledge_system

    try:
        processing_status["status"] = "initializing_drive_api"
        processing_status["progress"] = 10

        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)

        processing_status["status"] = "fetching_from_drive"
        processing_status["progress"] = 30

        try:
            # Use the new Gdrive.py module to fetch data
            output_file_path = Gdrive.fetch_data(selected_files, access_token)

            if not output_file_path or not os.path.exists(output_file_path):
                processing_status["status"] = "error"
                processing_status["error"] = "No content was retrieved from Google Drive"
                return

            processing_status["status"] = "processing_drive_content"
            processing_status["progress"] = 75

            # Define output file path for knowledge system
            knowledge_output_path = app_config.get("repository_file", "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt")

            # Process the drive content
            process_file(output_file_path, knowledge_output_path)

            # Load the generated corpus into the knowledge system
            processing_status["status"] = "loading_knowledge"
            processing_status["progress"] = 90

            # Update existing knowledge system
            knowledge_system.load_data(local=True, file_path=knowledge_output_path, append=True)

            # Save the updated backend tables
            knowledge_system.save_backend_tables()

            processing_status["status"] = "complete"
            processing_status["progress"] = 100

            print(f"Drive file processing complete. Knowledge system updated and saved.")

        except Exception as drive_error:
            print(f"Error with Google Drive API: {drive_error}")
            processing_status["status"] = "error"
            processing_status["error"] = f"Error with Google Drive API: {str(drive_error)}"

    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error in Drive file processing: {e}")

@app.route('/api/streaming', methods=['POST'])
def streaming_api():
    """
    Unified streaming API for data ingestion from multiple sources.

    This endpoint accepts data from various sources (file upload, URL, Google Drive, S3, Slack)
    and processes it in a unified way. It supports both manual triggers and automated events.

    Expected JSON payload:
    {
        "source": "url|file|gdrive|s3|slack",
        "uri": "URI or identifier for the data source",
        "trigger": "manual|event",
        "eventId": "Optional event identifier for event-driven ingestion",
        "metadata": {
            // Optional additional metadata
            // For Slack source, you can include:
            "slack": {
                "channelTypes": ["public", "private", "dm"],  // Types of channels to fetch from
                "dataTypes": ["messages", "files"],           // Types of data to fetch
                "slackBotToken": "xoxb-your-token"           // Optional Slack bot token
            }
        }
    }
    """
    global processing_status

    try:
        # Get the request data
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["source", "uri"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Extract data from the request
        source = data.get("source").lower()
        uri = data.get("uri")
        trigger = data.get("trigger", "manual").lower()
        event_id = data.get("eventId")
        metadata = data.get("metadata", {})

        # Validate source
        valid_sources = ["url", "file", "gdrive", "s3", "slack"]
        if source not in valid_sources:
            return jsonify({"error": f"Invalid source. Must be one of: {', '.join(valid_sources)}"}), 400

        # Reset processing status
        reset_processing_status()
        processing_status["status"] = f"starting_{source}_ingestion"
        processing_status["progress"] = 5
        processing_status["source"] = source
        processing_status["trigger"] = trigger
        if event_id:
            processing_status["eventId"] = event_id

        # Prepare task data
        task_data = {
            "source": source,
            "uri": uri,
            "trigger": trigger,
            "metadata": metadata
        }

        # Add source-specific data
        if source == "gdrive":
            # For Google Drive, we need to include the access token
            user_id = get_user_session_id()

            # Check if we have a token for this user
            if user_id not in oauth_tokens:
                return jsonify({"error": "Not authorized. Please connect to Google Drive first."}), 401

            # Get the token
            token_info = oauth_tokens[user_id]
            access_token = token_info.get('access_token')

            if not access_token:
                return jsonify({"error": "Invalid token. Please reconnect to Google Drive."}), 401

            # Add access token to task data
            task_data["access_token"] = access_token

        # Use message broker if available, otherwise process directly
        if message_broker:
            # Queue the task in the message broker
            task_id = message_broker.queue_task(task_data)

            return jsonify({
                "message": f"Data ingestion queued for {source}",
                "status": "queued",
                "source": source,
                "trigger": trigger,
                "taskId": task_id
            })
        else:
            # Process directly based on source
            if source == "url":
                # Start URL crawling in a separate thread
                threading.Thread(
                    target=crawl_website,
                    args=(uri,)
                ).start()

            elif source == "file":
                # For file source, URI should be a path to a local file
                if not os.path.exists(uri):
                    return jsonify({"error": f"File not found: {uri}"}), 404

                # Define output file path
                output_file_path = app_config.get("repository_file", "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt")

                # Start file processing in a separate thread
                threading.Thread(
                    target=process_file_async,
                    args=(uri, output_file_path)
                ).start()

            elif source == "gdrive":
                # For Google Drive, URI should be a file ID or a list of file IDs
                if isinstance(uri, str):
                    file_ids = [uri]
                elif isinstance(uri, list):
                    file_ids = uri
                else:
                    return jsonify({"error": "Invalid URI format for Google Drive. Expected string or list of file IDs"}), 400

                # Start Google Drive fetching in a separate thread
                threading.Thread(
                    target=process_drive_files,
                    args=(file_ids, access_token)
                ).start()

            elif source == "s3":
                # For S3, URI should be in the format "s3://bucket-name/path/to/file"
                if not uri.startswith("s3://"):
                    return jsonify({"error": "Invalid S3 URI format. Expected s3://bucket-name/path/to/file"}), 400

                # Parse the S3 URI
                s3_parts = uri[5:].split("/", 1)
                if len(s3_parts) < 2:
                    return jsonify({"error": "Invalid S3 URI format. Expected s3://bucket-name/path/to/file"}), 400

                # Extract file type
                file_ext = os.path.splitext(s3_parts[1])[1].lstrip('.')
                if not file_ext:
                    return jsonify({"error": "Could not determine file type from S3 URI"}), 400

                # Start S3 fetching in a separate thread
                threading.Thread(
                    target=fetch_s3_files_async,
                    args=([file_ext],)
                ).start()

            elif source == "slack":
                # For Slack, we need additional parameters
                slack_params = metadata.get("slack", {})

                # Get channel types (public, private, dm)
                channel_types = slack_params.get("channelTypes", ["public"])
                if not isinstance(channel_types, list):
                    channel_types = [channel_types]

                # Get data types (messages, files)
                data_types = slack_params.get("dataTypes", ["messages"])
                if not isinstance(data_types, list):
                    data_types = [data_types]

                # Get Slack bot token if provided
                slack_token = slack_params.get("slackBotToken")

                # Start Slack fetching in a separate thread
                threading.Thread(
                    target=fetch_slack_data_async,
                    args=(channel_types, data_types, slack_token)
                ).start()

            return jsonify({
                "message": f"Data ingestion started for {source}",
                "status": "processing",
                "source": source,
                "trigger": trigger,
                "requestId": hashlib.md5(f"{source}-{uri}-{time.time()}".encode()).hexdigest()
            })

    except Exception as e:
        print(f"Error in streaming API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"})

@app.route('/status', methods=['GET'])
def check_status():
    """Check the status of streaming tasks and overall processing"""
    global processing_status

    # Get task ID from query parameter if provided
    task_id = request.args.get('task_id')

    # Check if message broker is available
    broker_available = message_broker is not None

    # Get queue size if broker is available
    queue_size = len(message_broker.tasks) if broker_available else 0

    # Check if workers are running
    # For simplicity, we'll just check if the worker process exists
    workers_running = False
    try:
        # Use ps to check if streaming_worker.py is running
        ps_output = subprocess.check_output(["ps", "aux"]).decode("utf-8")
        workers_running = "start_streaming_workers.py" in ps_output

        if not workers_running:
            print("Workers not detected. Please start them with: python start_streaming_workers.py")
    except Exception as e:
        print(f"Error checking worker status: {e}")

    # Build status response
    status_info = {
        "current_status": processing_status,
        "streaming_api": {
            "broker_available": broker_available,
            "queue_size": queue_size,
            "workers_running": workers_running
        },
        "system_info": {
            "time": datetime.datetime.now().isoformat(),
            "api_version": "1.0"
        }
    }

    # Add task-specific information if requested
    if task_id and broker_available:
        # This is a simple implementation - in a real system, you would store task status in a database
        status_info["task"] = {
            "id": task_id,
            "status": "unknown",  # We don't track individual tasks in this simple implementation
            "message": "Task status tracking is limited in the current implementation"
        }

    return jsonify(status_info)

@app.route('/clear-queue', methods=['POST'])
def clear_queue():
    """Clear all tasks from the streaming queue"""
    global message_broker

    # Check if message broker is available
    if message_broker is None:
        return jsonify({"error": "Message broker not available"}), 500

    try:
        # Clear the queue
        message_broker.clear_queue()

        return jsonify({
            "message": "Queue cleared successfully",
            "queue_size": 0,
            "time": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error clearing queue: {e}")
        return jsonify({"error": f"Error clearing queue: {str(e)}"}), 500

@app.route('/debug-redirect-uri', methods=['GET'])
def debug_redirect_uri():
    """Debug endpoint to check the redirect URI"""
    redirect_uri = get_redirect_uri()
    return jsonify({
        "redirect_uri": redirect_uri,
        "host": request.host,
        "host_url": request.host_url,
        "url_root": request.url_root,
        "base_url": request.base_url,
        "path": request.path,
        "full_path": request.full_path,
        "url": request.url,
        "remote_addr": request.remote_addr
    })

@app.route('/debug-session', methods=['GET'])
def debug_session():
    """Debug endpoint to check the session information"""
    # Get the user's session ID
    user_id = get_user_session_id()

    # Check if we have a token for this user
    has_token = user_id in oauth_tokens

    # Get the number of active sessions
    active_sessions = len(oauth_tokens)

    # Return session debug info
    return jsonify({
        "session_id": user_id,
        "has_google_token": has_token,
        "active_sessions": active_sessions,
        "session_keys": list(session.keys())
    })

@app.route('/authorize-google')
def authorize_google():
    """Start the Google OAuth flow"""
    # Make sure we have a session ID for this user
    # This call ensures the session is created and permanent
    get_user_session_id()

    # Generate a random state parameter for security
    state = hashlib.md5(os.urandom(32)).hexdigest()

    # Create the authorization URL
    auth_url = f"{GOOGLE_AUTH_URI}?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={get_redirect_uri()}&scope={GOOGLE_DRIVE_SCOPE}&access_type=offline&state={state}&prompt=consent"

    # Store the state in the session
    session['oauth_state'] = state

    # Redirect to the authorization URL
    return redirect(auth_url)

@app.route('/disconnect-google', methods=['POST'])
def disconnect_google():
    """Disconnect Google Drive by removing the stored token"""
    # Get the user's session ID
    user_id = get_user_session_id()

    # Remove the token if it exists
    if user_id in oauth_tokens:
        del oauth_tokens[user_id]
        return jsonify({"status": "success", "message": "Disconnected from Google Drive"})
    else:
        return jsonify({"status": "info", "message": "Not connected to Google Drive"})

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback from Google"""
    # Check if there's an error
    if request.args.get('error'):
        error = request.args.get('error')
        return render_template('oauth_error.html', error=error)

    # Get the authorization code
    code = request.args.get('code')
    if not code:
        return render_template('oauth_error.html', error="No authorization code received")

    # Exchange the code for an access token
    try:
        # Get the redirect URI based on the request
        redirect_uri = get_redirect_uri()

        # Prepare the token request
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

        # Make the request
        response = requests.post(GOOGLE_TOKEN_URI, data=token_data)
        token_info = response.json()

        if 'error' in token_info:
            return render_template('oauth_error.html', error=token_info['error'])

        # Store the tokens using the user's session ID
        user_id = get_user_session_id()
        oauth_tokens[user_id] = token_info

        # Get user information
        try:
            # Use the access token to get user info
            access_token = token_info.get('access_token')
            user_info_response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )

            if user_info_response.status_code == 200:
                user_info = user_info_response.json()
                # Store user info with the token
                oauth_tokens[user_id]['user_info'] = user_info
        except Exception as e:
            print(f"Error getting user info: {e}")

        # Return success page
        return render_template('oauth_success.html')

    except Exception as e:
        return render_template('oauth_error.html', error=str(e))

# Add a new endpoint to manually save the backend tables
@app.route('/save-tables', methods=['POST'])
def save_tables():
    """Save the current backend tables"""
    global knowledge_system

    try:
        knowledge_system.save_backend_tables()
        return jsonify({"status": "success", "message": "Backend tables saved successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error saving backend tables: {str(e)}"}), 500

# Add MongoDB configuration endpoint
@app.route('/mongodb-config', methods=['GET', 'POST'])
def mongodb_config():
    """Get or update MongoDB configuration"""
    global knowledge_system

    if request.method == 'GET':
        # Return current MongoDB configuration
        return jsonify({
            "use_mongodb": knowledge_system.use_mongodb if hasattr(knowledge_system, 'use_mongodb') else False,
            "connection_string": knowledge_system.mongo_connection_string if hasattr(knowledge_system, 'mongo_connection_string') else "mongodb://localhost:27017",
            "db_name": knowledge_system.mongo_db_name if hasattr(knowledge_system, 'mongo_db_name') else "KnowledgeBase"
        })

    elif request.method == 'POST':
        # Update MongoDB configuration
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Get configuration values
        use_mongodb = data.get('use_mongodb', False)
        connection_string = data.get('connection_string', "mongodb://localhost:27017")
        db_name = data.get('db_name', "KnowledgeBase")

        # Save configuration to file
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        config = {
            "use_mongodb": use_mongodb,
            "connection_string": connection_string,
            "db_name": db_name
        }

        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            return jsonify({"error": f"Error saving configuration: {str(e)}"}), 500

        # Reinitialize knowledge system with new configuration
        try:
            # Create a new KnowledgeRetrieval instance with the new configuration
            new_knowledge_system = KnowledgeRetrieval(
                use_mongodb=use_mongodb,
                mongo_connection_string=connection_string,
                mongo_db_name=db_name
            )

            # Load data from the same source as the current system
            # This assumes the data is available in the standard location
            new_knowledge_system.load_data(
                local=True,
                file_path=app_config.get("repository_file", "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"),
                append=True
            )

            # Replace the global instance
            knowledge_system = new_knowledge_system

            return jsonify({
                "status": "success",
                "message": f"MongoDB configuration updated. Using {'MongoDB' if use_mongodb else 'local storage'}."
            })

        except Exception as e:
            return jsonify({"error": f"Error reinitializing knowledge system: {str(e)}"}), 500

# Add a simplified route to test language detection (always returns English)
@app.route('/test-language', methods=['POST'])
def test_language():
    """Test endpoint for language detection (English only)"""
    global knowledge_system

    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({"error": "Text is required"}), 400

        return jsonify({
            "original_text": text,
            "detected_language": "en",  # Always English
            "translated_text": text,     # No translation needed
            "is_english": True
        })

    except Exception as e:
        return jsonify({"error": f"Error testing language: {str(e)}"}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    # Create or update the HTML template files
    with open('templates/home.html', 'w', encoding='utf-8') as f:
        with open('home.html', 'r', encoding='utf-8') as source:
            f.write(source.read())

    with open('templates/data_input.html', 'w', encoding='utf-8') as f:
        with open('data_input.html', 'r', encoding='utf-8') as source:
            f.write(source.read())

    # Copy oauth_callback.html if it exists
    if os.path.exists('oauth_callback.html'):
        with open('templates/oauth_callback.html', 'w', encoding='utf-8') as f:
            with open('oauth_callback.html', 'r', encoding='utf-8') as source:
                f.write(source.read())

    # Make sure OAuth templates exist
    if not os.path.exists('templates/oauth_success.html'):
        with open('templates/oauth_success.html', 'w', encoding='utf-8') as f:
            f.write('''<!DOCTYPE html>
<html>
<head>
    <title>OAuth Success</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #4285f4;
        }
        .success {
            color: #0f9d58;
            font-weight: bold;
        }
        button {
            background-color: #4285f4;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #3367d6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Google Drive Authorization</h1>
        <p class="success">Authorization successful!</p>
        <p>You have successfully connected to Google Drive. You can now close this window and return to the application.</p>
        <button onclick="window.close()">Close Window</button>
        <p>If the window doesn't close automatically, you can close it manually and return to the application.</p>
    </div>
</body>
</html>''')

    if not os.path.exists('templates/oauth_error.html'):
        with open('templates/oauth_error.html', 'w', encoding='utf-8') as f:
            f.write('''<!DOCTYPE html>
<html>
<head>
    <title>OAuth Error</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #ea4335;
        }
        .error {
            color: #ea4335;
            font-weight: bold;
        }
        .help {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
        code {
            background-color: #f1f3f4;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: monospace;
        }
        button {
            background-color: #4285f4;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover {
            background-color: #3367d6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Authorization Error</h1>
        <p class="error">Error: {{ error }}</p>
        <p>There was a problem authorizing with Google Drive. Please try again or contact the administrator.</p>

        <button onclick="window.location.href='/data-input'">Return to Data Input</button>

        <div class="help" id="errorHelp">
            <h3>Troubleshooting</h3>
            <p>If you're experiencing issues with Google Drive authorization, try the following:</p>
            <ul>
                <li>Make sure you're using a valid Google account</li>
                <li>Check that you have granted the necessary permissions</li>
                <li>Try clearing your browser cookies and cache</li>
                <li>Try using a different browser</li>
            </ul>
            <p>For developers: Make sure the redirect URI in the Google Cloud Console matches the one used by the application.</p>
            <p>JavaScript Origin: <code id="jsOrigin">https://your-domain.com</code></p>
            <p>Redirect URI: <code id="redirectUri">https://your-domain.com/oauth2callback</code></p>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Set the origins and redirect URIs
            document.getElementById('jsOrigin').textContent = window.location.origin;
            document.getElementById('redirectUri').textContent = window.location.origin + '/oauth2callback';
        });
    </script>
</body>
</html>''')

    # Use port 5001 to avoid conflicts
    app.run(host='0.0.0.0', port=5001, debug=True)