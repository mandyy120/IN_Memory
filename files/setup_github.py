#!/usr/bin/env python3
"""
GitHub Setup Script

This script helps you set up your GitHub account for Git.
It configures your name and email in Git's global configuration.
"""

import os
import subprocess
import getpass

def run_command(command):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error message: {e.stderr}")
        return None

def setup_git_config():
    """Set up Git configuration with user input"""
    print("\n=== GitHub Account Setup ===\n")
    
    # Get user input
    name = input("Enter your full name: ")
    email = input("Enter your GitHub email address: ")
    
    # Configure Git
    if name and email:
        run_command(f'git config --global user.name "{name}"')
        run_command(f'git config --global user.email "{email}"')
        print("\nGit configuration updated successfully!")
        print(f"Name: {name}")
        print(f"Email: {email}")
    else:
        print("Name or email was empty. Git configuration not updated.")

def setup_github_credentials():
    """Set up GitHub credentials"""
    print("\n=== GitHub Repository Setup ===\n")
    
    # Get GitHub username
    username = input("Enter your GitHub username: ")
    
    if not username:
        print("Username was empty. GitHub setup aborted.")
        return
    
    # Check if the user wants to create a new repository
    create_repo = input("Do you want to create a new GitHub repository? (y/n): ").lower() == 'y'
    
    if create_repo:
        repo_name = input("Enter the name for your new repository: ")
        if repo_name:
            print(f"\nTo create a new repository, go to: https://github.com/new")
            print("Use these settings:")
            print(f"  - Repository name: {repo_name}")
            print("  - Description: (optional)")
            print("  - Privacy: Public or Private (your choice)")
            print("  - DO NOT initialize with README, .gitignore, or license")
            
            input("\nPress Enter after creating the repository...")
            
            # Set up the remote origin
            remote_url = f"https://github.com/{username}/{repo_name}.git"
            run_command(f"git remote add origin {remote_url}")
            print(f"\nRemote origin added: {remote_url}")
        else:
            print("Repository name was empty. Repository setup aborted.")
    
    # Configure credential helper to cache credentials
    run_command("git config --global credential.helper cache")
    run_command("git config --global credential.helper 'cache --timeout=3600'")
    
    print("\nGitHub setup completed!")
    print("Your credentials will be cached for 1 hour after your first push.")
    print("To push your code to GitHub, run: python backup_to_github.py")

if __name__ == "__main__":
    setup_git_config()
    setup_github_credentials()
    
    print("\n=== Setup Complete ===")
    print("You can now use the backup_to_github.py script to push your code to GitHub.")
    print("And restore_from_github.py to restore your code from GitHub.")
