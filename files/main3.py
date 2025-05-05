from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import os
import threading
import time
from final2 import KnowledgeRetrieval
from corpus2 import generate_corpus

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Global variables for tracking progress
processing_status = {
    "progress": 0,
    "status": "idle",
    "error": None
}

# Initialize the KnowledgeRetrieval system at startup
try:
    knowledge_system = KnowledgeRetrieval()
    print("Knowledge system class initialized successfully.")
    
    try:
        knowledge_system.load_data(local=True, file_path="/home/mandeep/Pictures/corpus/uploads/repository_generated.txt")
        print("Knowledge system data loaded successfully!")
    except Exception as e:
        print(f"Warning: Initial knowledge system load failed: {e}")
        print("System will be available once data is uploaded.")
        
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize KnowledgeRetrieval: {e}")
    print("Application may not function correctly.")

# Default to local file loading, but this could be configured
# through environment variables or a config file
try:
    knowledge_system.load_data(local=True, file_path="repository2.txt")
    print("Knowledge system initialized successfully!")
except Exception as e:
    print(f"Warning: Initial knowledge system load failed: {e}")
    print("System will be available once data is uploaded.")

def reset_processing_status():
    global processing_status
    processing_status = {
        "progress": 0,
        "status": "idle",
        "error": None
    }

@app.route('/')
def home_page():
    """Serve the home page (query interface)"""
    return render_template('home.html')

@app.route('/data-input')
def data_input_page():
    """Serve the data input page"""
    return render_template('data_input.html')

@app.route('/query', methods=['POST'])
def handle_query():
    """Process query requests from the query interface with enhanced multilingual support"""
    data = request.get_json()
    user_query = data.get('query', '').strip()
    
    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400
    
    try:
        # First detect the language of the query
        source_lang = knowledge_system.detect_language(user_query)
        print(f"Detected query language: {source_lang}")
        
        # Log the original query for debugging
        print(f"Original query ({source_lang}): {user_query}")
        
        # Generate the original description using the knowledge system
        # The generate_description method in KnowledgeRetrieval will handle translation internally
        original_description = knowledge_system.generate_description(user_query)
        
        # For debugging - log the generated description
        print(f"Generated description length: {len(original_description)} characters")
        
        # Rephrase using Mistral AI if available, with proper language handling
        try:
            rephrased_description = knowledge_system.rephrase_with_mistral(original_description)
            print(f"Rephrased description length: {len(rephrased_description)} characters")
        except Exception as rephrase_error:
            print(f"Error in rephrasing: {rephrase_error}")
            # Fallback to original description if rephrasing fails
            rephrased_description = original_description
        
        # Ensure both descriptions are in the original query language
        result_lang = knowledge_system.detect_language(original_description)
        if result_lang != source_lang:
            print(f"Warning: Result language ({result_lang}) differs from query language ({source_lang})")
            # Try to translate back to source language if needed
            try:
                original_description = knowledge_system.translate_text(original_description, result_lang, source_lang)
            except Exception as translate_error:
                print(f"Translation error: {translate_error}")
                # Continue with what we have if translation fails
        
        # Do the same check for rephrased description
        rephrased_lang = knowledge_system.detect_language(rephrased_description)
        if rephrased_lang != source_lang:
            print(f"Warning: Rephrased language ({rephrased_lang}) differs from query language ({source_lang})")
            try:
                rephrased_description = knowledge_system.translate_text(rephrased_description, rephrased_lang, source_lang)
            except Exception as translate_error:
                print(f"Translation error: {translate_error}")
                # Continue with what we have if translation fails
        
        return jsonify({
            "original_description": original_description,
            "rephrased_description": rephrased_description,
            "detected_language": source_lang
        })
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        # Try to send error message in detected language if possible
        try:
            source_lang = knowledge_system.detect_language(user_query)
            error_message = f"Error processing query: {str(e)}"
            
            if source_lang != 'en':
                error_message = knowledge_system.translate_text(error_message, 'en', source_lang)
                
            return jsonify({
                "error": error_message,
                "detected_language": source_lang
            }), 500
        except:
            # Fallback to simple English error
            return jsonify({"error": f"Error processing query: {str(e)}"}), 500

@app.route('/progress', methods=['GET'])
def get_progress():
    """Return the current processing status and progress"""
    global processing_status
    return jsonify(processing_status)

def process_file_async(file_path, output_file):
    """Process the file in a separate thread and update progress"""
    global processing_status
    global knowledge_system
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            file_content = f.read()
        
        processing_status["status"] = "reading"
        processing_status["progress"] = 10
        time.sleep(1)  # Just to make progress visible
        
        # Generate corpus from the file content
        processing_status["status"] = "generating_corpus"
        processing_status["progress"] = 30
        
        # Call the generate_corpus function from corpus.py
        generate_corpus(file_content, output_file=output_file, status_callback=update_status)
        
        processing_status["status"] = "loading_knowledge"
        processing_status["progress"] = 70
        
        # Update existing knowledge system instead of replacing it
        try:
            knowledge_system.load_data(local=True, file_path=output_file, append=True)
            
            # Explicitly save the updated backend tables
            knowledge_system.save_backend_tables()
            
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

def update_status(status_info):
    """Update the global processing status with provided information"""
    global processing_status
    
    if status_info and isinstance(status_info, dict):
        for key, value in status_info.items():
            processing_status[key] = value

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
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
            
            # Define output file path
            output_file_path = os.path.join('uploads', 'repository_generated.txt')
            
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
        import crawling
        
        # Update status
        processing_status["status"] = "crawling"
        processing_status["progress"] = 20
        
        # Get content from crawling.py
        content = crawling.crawl(url)
        
        # Create a safe filename from the URL for the raw content
        safe_url = url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_')
        raw_content_file = os.path.join('uploads', f"crawled_{safe_url[:50]}.txt")
        
        # Save raw crawled content to the URL-specific file
        with open(raw_content_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Raw crawled content saved to: {raw_content_file}")
        
        # Update status
        processing_status["status"] = "processing_content"
        processing_status["progress"] = 40
        
        # Define output file path for corpus2.py's output
        output_file_path = os.path.join('uploads', 'repository_generated.txt')
        
        # Generate corpus from the crawled content and save to repository_generated.txt
        generate_corpus(content, output_file=output_file_path, status_callback=update_status)
        
        # Load the generated corpus into the knowledge system
        processing_status["status"] = "loading_knowledge"
        processing_status["progress"] = 90
        
        # Update existing knowledge system instead of replacing it
        knowledge_system.load_data(local=True, file_path=output_file_path, append=True)
        
        # Save the updated backend tables
        knowledge_system.save_backend_tables()
        
        processing_status["status"] = "complete"
        processing_status["progress"] = 100
        
        print(f"Web crawling complete. Knowledge system updated and saved.")
        
    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error in web crawling: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"})

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

# Add a new route to test language detection and translation
@app.route('/test-language', methods=['POST'])
def test_language():
    """Test endpoint for language detection and translation"""
    global knowledge_system
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "Text is required"}), 400
            
        # Detect language
        detected_lang = knowledge_system.detect_language(text)
        
        # If not English, translate to English
        translated_text = text
        if detected_lang != 'en':
            translated_text = knowledge_system.translate_text(text, detected_lang, 'en')
            
        return jsonify({
            "original_text": text,
            "detected_language": detected_lang,
            "translated_text": translated_text
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
    
    app.run(host='0.0.0.0', port=5000, debug=True)