#!/usr/bin/env python3
"""
Google OAuth Test User Manager

This script helps you manage test users for your Google OAuth application.
It provides instructions on how to add test users to your Google Cloud project.

Usage:
    python add_test_users.py
"""

import sys
import subprocess
import webbrowser

def main():
    """Main function"""
    print("Google OAuth Test User Manager")
    print("=============================")
    
    print("\nTo allow specific users to access your unverified OAuth application, you need to add them as test users.")
    print("\nFollow these steps:")
    
    print("\n1. Go to the OAuth consent screen in Google Cloud Console")
    print("   https://console.cloud.google.com/apis/credentials/consent")
    
    print("\n2. Scroll down to the 'Test users' section")
    
    print("\n3. Click 'ADD USERS'")
    
    print("\n4. Enter the email addresses of the users you want to allow access")
    print("   (You can add up to 100 test users)")
    
    print("\n5. Click 'SAVE'")
    
    print("\nAfter adding test users, they will be able to access your application.")
    print("They will still see a warning that the app is unverified, but they can proceed.")
    
    # Ask if the user wants to open the Google Cloud Console
    open_console = input("\nWould you like to open the Google Cloud Console now? (y/n): ")
    if open_console.lower() == 'y':
        url = "https://console.cloud.google.com/apis/credentials/consent"
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening browser: {e}")
            print(f"Please manually navigate to: {url}")
    
    print("\nNote: If you plan to make your application available to the general public,")
    print("you will need to go through Google's verification process.")
    print("See: https://support.google.com/cloud/answer/9110914")

if __name__ == "__main__":
    main()
