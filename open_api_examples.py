#!/usr/bin/env python3
"""
Open API Examples Page

This script opens the API examples page in a browser.
"""

import os
import sys
import json
import requests
import webbrowser

# Ngrok API URL (local)
NGROK_API_URL = "http://localhost:4040/api/tunnels"

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

def main():
    """Main function"""
    print("Opening API Examples Page")
    print("========================")
    
    # Check if ngrok is running
    try:
        ngrok_url = get_ngrok_url()
        if not ngrok_url:
            print("Error: Could not detect ngrok URL. Make sure ngrok is running.")
            print("Example: ngrok http 5001")
            return
        
        # Open the API examples page in a browser
        api_examples_url = f"{ngrok_url}/api-examples"
        print(f"Opening {api_examples_url} in browser...")
        webbrowser.open(api_examples_url)
        
        print("\nShare this URL with users who need to access your API:")
        print(f"{api_examples_url}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure ngrok is running with: ngrok http 5001")

if __name__ == "__main__":
    main()
