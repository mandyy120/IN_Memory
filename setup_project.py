#!/usr/bin/env python3
"""
Comprehensive setup script for Intellichat In-memory LLM project.
This script:
1. Installs all required dependencies
2. Sets up MongoDB
3. Installs and configures ngrok
4. Updates project paths
"""

import os
import sys
import subprocess
import platform
import json
import getpass
import re
from pathlib import Path
import shutil

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_step(message):
    """Print a step message with formatting"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {message} ==={Colors.ENDC}\n")

def print_success(message):
    """Print a success message with formatting"""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_warning(message):
    """Print a warning message with formatting"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.ENDC}")

def print_error(message):
    """Print an error message with formatting"""
    print(f"{Colors.RED}✗ {message}{Colors.ENDC}")

def run_command(command, shell=False):
    """Run a command and return its output"""
    try:
        if isinstance(command, str) and not shell:
            command = command.split()
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=shell)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    print_step("Checking Python version")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8 or higher is required. You have Python {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")

def setup_virtual_environment():
    """Set up a virtual environment"""
    print_step("Setting up virtual environment")
    
    # Check if venv exists
    if os.path.exists("venv"):
        response = input("Virtual environment already exists. Recreate? (y/n): ").lower()
        if response == 'y':
            shutil.rmtree("venv")
        else:
            print_warning("Using existing virtual environment")
            return
    
    # Create venv
    run_command([sys.executable, "-m", "venv", "venv"])
    print_success("Virtual environment created")
    
    # Determine the pip path
    if platform.system() == "Windows":
        pip_path = os.path.join("venv", "Scripts", "pip")
    else:
        pip_path = os.path.join("venv", "bin", "pip")
    
    # Upgrade pip
    run_command([pip_path, "install", "--upgrade", "pip"])
    print_success("Pip upgraded to latest version")

def install_python_dependencies():
    """Install Python dependencies"""
    print_step("Installing Python dependencies")
    
    # Determine the pip path
    if platform.system() == "Windows":
        pip_path = os.path.join("venv", "Scripts", "pip")
    else:
        pip_path = os.path.join("venv", "bin", "pip")
    
    # List of required packages
    requirements = [
        "flask",
        "flask-cors",
        "pymongo",
        "requests",
        "google-auth",
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "google-api-python-client",
        "python-docx",
        "PyPDF2",
        "boto3",
        "slackclient",
        "playwright",
        "fake_useragent",
        "python-dotenv"
    ]
    
    # Install each package
    for package in requirements:
        print(f"Installing {package}...")
        run_command([pip_path, "install", package])
    
    # Install playwright browsers
    print("Installing Playwright browsers...")
    if platform.system() == "Windows":
        playwright_path = os.path.join("venv", "Scripts", "playwright")
    else:
        playwright_path = os.path.join("venv", "bin", "playwright")
    run_command([playwright_path, "install", "chromium"])
    
    print_success("All Python dependencies installed")

def setup_mongodb():
    """Install and set up MongoDB"""
    print_step("Setting up MongoDB")
    
    system = platform.system()
    
    if system == "Linux":
        # Check if MongoDB is already installed
        if run_command("which mongod", shell=True):
            print_warning("MongoDB is already installed")
        else:
            # Install MongoDB on Linux
            distro = run_command("lsb_release -is", shell=True).lower()
            
            if "ubuntu" in distro or "debian" in distro:
                print("Installing MongoDB on Ubuntu/Debian...")
                run_command("sudo apt-get update", shell=True)
                run_command("sudo apt-get install -y mongodb", shell=True)
                run_command("sudo systemctl start mongodb", shell=True)
                run_command("sudo systemctl enable mongodb", shell=True)
            elif "fedora" in distro or "centos" in distro or "rhel" in distro:
                print("Installing MongoDB on Fedora/CentOS/RHEL...")
                run_command('sudo echo -e "[mongodb-org-6.0]\nname=MongoDB Repository\nbaseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/6.0/x86_64/\ngpgcheck=1\nenabled=1\ngpgkey=https://www.mongodb.org/static/pgp/server-6.0.asc" | sudo tee /etc/yum.repos.d/mongodb-org-6.0.repo', shell=True)
                run_command("sudo yum install -y mongodb-org", shell=True)
                run_command("sudo systemctl start mongod", shell=True)
                run_command("sudo systemctl enable mongod", shell=True)
            else:
                print_warning(f"Unsupported Linux distribution: {distro}")
                print("Please install MongoDB manually: https://docs.mongodb.com/manual/administration/install-on-linux/")
    
    elif system == "Darwin":  # macOS
        # Check if MongoDB is already installed via Homebrew
        if run_command("which mongod", shell=True):
            print_warning("MongoDB is already installed")
        else:
            # Check if Homebrew is installed
            if not run_command("which brew", shell=True):
                print("Installing Homebrew...")
                run_command('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"', shell=True)
            
            # Install MongoDB via Homebrew
            print("Installing MongoDB via Homebrew...")
            run_command("brew tap mongodb/brew", shell=True)
            run_command("brew install mongodb-community", shell=True)
            run_command("brew services start mongodb-community", shell=True)
    
    elif system == "Windows":
        print_warning("Automatic MongoDB installation on Windows is not supported")
        print("Please download and install MongoDB manually from: https://www.mongodb.com/try/download/community")
        print("After installation, make sure MongoDB is running as a service")
    
    # Create database and collections
    try:
        # Check if pymongo is installed
        import pymongo
        
        # Connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        
        # Create database
        db = client["KnowledgeBase"]
        
        # Create collections
        db.create_collection("entities")
        db.create_collection("tokens")
        db.create_collection("metadata")
        
        print_success("MongoDB database and collections created")
    except ImportError:
        print_warning("pymongo not installed, skipping database creation")
    except Exception as e:
        print_error(f"Error creating MongoDB database: {e}")
    
    # Update config.json with MongoDB settings
    config = {
        "use_mongodb": True,
        "connection_string": "mongodb://localhost:27017",
        "db_name": "KnowledgeBase"
    }
    
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print_success("MongoDB configuration saved to config.json")

def setup_ngrok():
    """Install and configure ngrok"""
    print_step("Setting up ngrok")
    
    system = platform.system()
    
    # Check if ngrok is already installed
    ngrok_installed = False
    if system == "Windows":
        ngrok_installed = os.path.exists(os.path.expanduser("~\\ngrok.exe"))
    else:
        ngrok_installed = bool(run_command("which ngrok", shell=True))
    
    if ngrok_installed:
        print_warning("ngrok is already installed")
    else:
        # Install ngrok
        if system == "Linux" or system == "Darwin":
            print("Installing ngrok...")
            run_command("curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null", shell=True)
            run_command('echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list', shell=True)
            run_command("sudo apt update", shell=True)
            run_command("sudo apt install ngrok", shell=True)
        elif system == "Windows":
            print_warning("Automatic ngrok installation on Windows is not supported")
            print("Please download and install ngrok manually from: https://ngrok.com/download")
    
    # Configure ngrok
    print("\nTo configure ngrok, you need an authtoken from ngrok.com")
    print("If you don't have an account, please sign up at: https://dashboard.ngrok.com/signup")
    print("After signing up, get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken")
    
    authtoken = input("\nEnter your ngrok authtoken (press Enter to skip): ").strip()
    
    if authtoken:
        run_command(f"ngrok config add-authtoken {authtoken}", shell=True)
        print_success("ngrok configured with your authtoken")
    else:
        print_warning("ngrok configuration skipped")
    
    print("\nTo use ngrok with your application, run:")
    print("  ngrok http 5001")
    print("Then update your Google Cloud Console OAuth credentials with the ngrok URL")

def update_project_paths():
    """Update project paths in configuration files"""
    print_step("Updating project paths")
    
    # Get current directory
    current_dir = os.path.abspath(os.getcwd())
    
    # Default repository path
    default_repo_path = os.path.join(current_dir, "uploads", "repository_generated.txt")
    
    # Ask user for repository path
    print(f"Default repository path: {default_repo_path}")
    repo_path = input("Enter repository path (press Enter to use default): ").strip()
    
    if not repo_path:
        repo_path = default_repo_path
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    
    # Update main2.py with the new repository path
    try:
        with open("main2.py", "r") as f:
            content = f.read()
        
        # Replace repository path
        pattern = r'app_config\.get\("repository_file", "[^"]+"\)'
        replacement = f'app_config.get("repository_file", "{repo_path}")'
        content = re.sub(pattern, replacement, content)
        
        with open("main2.py", "w") as f:
            f.write(content)
        
        print_success(f"Repository path updated to: {repo_path}")
    except Exception as e:
        print_error(f"Error updating repository path in main2.py: {e}")
    
    # Create app_config.json with the repository path
    app_config = {
        "repository_file": repo_path
    }
    
    with open("app_config.json", "w") as f:
        json.dump(app_config, f, indent=2)
    
    print_success("Configuration saved to app_config.json")

def update_google_credentials():
    """Update Google OAuth credentials"""
    print_step("Updating Google OAuth credentials")
    
    print("To use Google Drive integration, you need OAuth credentials from Google Cloud Console")
    print("If you don't have a project, create one at: https://console.cloud.google.com/")
    print("Then create OAuth credentials at: https://console.cloud.google.com/apis/credentials")
    
    client_id = input("\nEnter your Google OAuth Client ID (press Enter to skip): ").strip()
    client_secret = input("Enter your Google OAuth Client Secret (press Enter to skip): ").strip()
    
    if client_id and client_secret:
        try:
            with open("main2.py", "r") as f:
                content = f.read()
            
            # Replace client ID
            pattern_id = r'GOOGLE_CLIENT_ID = "[^"]+"'
            replacement_id = f'GOOGLE_CLIENT_ID = "{client_id}"'
            content = re.sub(pattern_id, replacement_id, content)
            
            # Replace client secret
            pattern_secret = r'GOOGLE_CLIENT_SECRET = "[^"]+"'
            replacement_secret = f'GOOGLE_CLIENT_SECRET = "{client_secret}"'
            content = re.sub(pattern_secret, replacement_secret, content)
            
            with open("main2.py", "w") as f:
                f.write(content)
            
            print_success("Google OAuth credentials updated")
        except Exception as e:
            print_error(f"Error updating Google OAuth credentials: {e}")
    else:
        print_warning("Google OAuth credentials update skipped")

def create_startup_script():
    """Create a startup script"""
    print_step("Creating startup script")
    
    system = platform.system()
    
    if system == "Windows":
        # Create batch file for Windows
        with open("start_app.bat", "w") as f:
            f.write("@echo off\n")
            f.write("echo Starting the application...\n")
            f.write("call venv\\Scripts\\activate\n")
            f.write("python main2.py\n")
            f.write("pause\n")
        
        print_success("Created start_app.bat")
    else:
        # Create shell script for Linux/macOS
        with open("start_app.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("echo \"Starting the application...\"\n")
            f.write("source venv/bin/activate\n")
            f.write("python main2.py\n")
        
        # Make the script executable
        os.chmod("start_app.sh", 0o755)
        
        print_success("Created start_app.sh")

def main():
    """Main function to run the setup"""
    print(f"{Colors.BLUE}{Colors.BOLD}")
    print("=" * 80)
    print("                Intellichat In-memory LLM - Setup Script")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    # Check Python version
    check_python_version()
    
    # Set up virtual environment
    setup_virtual_environment()
    
    # Install Python dependencies
    install_python_dependencies()
    
    # Set up MongoDB
    setup_mongodb()
    
    # Set up ngrok
    setup_ngrok()
    
    # Update project paths
    update_project_paths()
    
    # Update Google credentials
    update_google_credentials()
    
    # Create startup script
    create_startup_script()
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}")
    print("=" * 80)
    print("                Setup completed successfully!")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    # Print instructions
    system = platform.system()
    if system == "Windows":
        print("\nTo start the application, run:")
        print("  start_app.bat")
    else:
        print("\nTo start the application, run:")
        print("  ./start_app.sh")
    
    print("\nTo use ngrok for public access, run in a separate terminal:")
    print("  ngrok http 5001")
    
    print("\nThen update your Google Cloud Console OAuth credentials with the ngrok URL")
    print("Add both the base URL and the callback URL (base URL + '/oauth2callback')")

if __name__ == "__main__":
    main()
