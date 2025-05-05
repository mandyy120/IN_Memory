#!/usr/bin/env python3
"""
Google OAuth Redirect URI Updater

This script automatically updates the redirect URIs in Google Cloud Console
whenever a new ngrok tunnel is created. It should be run after starting ngrok.

Usage:
    python update_oauth_uris.py

Requirements:
    - google-auth
    - google-api-python-client
    - requests

Setup:
    1. Create a service account in Google Cloud Console with appropriate permissions
    2. Download the service account key as JSON
    3. Save it as 'service-account.json' in the same directory as this script
    4. Add the service account email to your OAuth client as an editor
"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime

# Configuration
NGROK_API_URL = "http://localhost:4040/api/tunnels"
OAUTH_CLIENT_ID = "311723313181-pp08rji8pjkl9jd1vdq33tisumlfavjm.apps.googleusercontent.com"

def get_ngrok_url():
    """Get the current ngrok public URL"""
    try:
        response = requests.get(NGROK_API_URL)
        if response.status_code != 200:
            print(f"Error: Failed to get ngrok tunnels. Status code: {response.status_code}")
            return None
        
        data = response.json()
        tunnels = data.get('tunnels', [])
        
        if not tunnels:
            print("Error: No active ngrok tunnels found")
            return None
        
        # Find the HTTPS tunnel
        for tunnel in tunnels:
            if tunnel.get('proto') == 'https':
                return tunnel.get('public_url')
        
        # If no HTTPS tunnel, use the first one
        return tunnels[0].get('public_url')
    
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        return None

def update_redirect_uris_manually():
    """
    Provide instructions for manually updating redirect URIs
    since we can't do it programmatically without a service account
    """
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        print("Failed to get ngrok URL. Make sure ngrok is running.")
        return False
    
    redirect_uri = f"{ngrok_url}/oauth2callback"
    js_origin = ngrok_url
    
    print("\n" + "=" * 80)
    print("GOOGLE OAUTH CONFIGURATION UPDATE REQUIRED")
    print("=" * 80)
    print(f"\nYour current ngrok URL is: {ngrok_url}")
    print("\nYou need to update your Google Cloud OAuth configuration with these values:")
    print("\n1. Authorized JavaScript origins:")
    print(f"   {js_origin}")
    print("\n2. Authorized redirect URIs:")
    print(f"   {redirect_uri}")
    print("\nFollow these steps:")
    print("1. Go to https://console.cloud.google.com/apis/credentials")
    print("2. Find your OAuth 2.0 Client ID and click 'Edit'")
    print("3. Add or update the JavaScript origins and redirect URIs with the values above")
    print("4. Click 'Save'")
    print("\nAfter updating, your OAuth flow should work correctly.")
    print("=" * 80)
    
    # Create a file with the current configuration for reference
    with open('current_oauth_config.txt', 'w') as f:
        f.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Ngrok URL: {ngrok_url}\n\n")
        f.write("Authorized JavaScript origins:\n")
        f.write(f"{js_origin}\n\n")
        f.write("Authorized redirect URIs:\n")
        f.write(f"{redirect_uri}\n")
    
    print(f"\nThis information has been saved to 'current_oauth_config.txt' for reference.")
    
    # Ask if the user wants to open the Google Cloud Console
    open_console = input("\nWould you like to open the Google Cloud Console now? (y/n): ")
    if open_console.lower() == 'y':
        url = "https://console.cloud.google.com/apis/credentials"
        try:
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', url])
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['start', url], shell=True)
            else:  # Linux
                subprocess.run(['xdg-open', url])
        except Exception as e:
            print(f"Error opening browser: {e}")
            print(f"Please manually navigate to: {url}")
    
    return True

def main():
    """Main function"""
    print("Google OAuth Redirect URI Updater")
    print("=================================")
    
    # Check if ngrok is running
    try:
        requests.get(NGROK_API_URL)
    except requests.exceptions.ConnectionError:
        print("Error: ngrok is not running. Please start ngrok first.")
        print("Example: ngrok http 5001")
        return
    
    # Update redirect URIs
    update_redirect_uris_manually()

if __name__ == "__main__":
    main()
