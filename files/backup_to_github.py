#!/usr/bin/env python3
"""
GitHub Backup Script

This script automates the process of backing up important code files to GitHub.
It commits changes to the local Git repository and pushes them to GitHub.

Usage:
    python backup_to_github.py [--message "Your commit message"]

Options:
    --message    Custom commit message (default: "Automated backup: YYYY-MM-DD HH:MM")
"""

import os
import sys
import subprocess
import argparse
import datetime

# List of important files to track
IMPORTANT_FILES = [
    # Main Python files
    "main2.py",
    "final2.py",
    "text.py",
    "Gdrive.py",
    "crawling.py",
    "crawling2.py",
    "slack_integration.py",
    "setup_project.py",

    # Utility Python files
    "fix_repository_hash.py",
    "check_repository_hash.py",
    "reset_system.py",
    "s3script.py",

    # Configuration files
    "config.json",
    "app_config.json",

    # HTML templates in root (source files)
    "home.html",
    "data_input.html",
    "oauth_callback.html",

    # Templates directory (all HTML templates)
    "templates",

    # Git and backup configuration
    ".gitignore",
    "backup_to_github.py",
    "restore_from_github.py",
    "setup_github.py",

    # Shell scripts
    "start_app.sh",

    # Environment files (without sensitive data)
    ".env.example"
]

def run_command(command, capture_output=True):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=capture_output
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error message: {e.stderr}")
        sys.exit(1)

def check_git_repo():
    """Check if the current directory is a Git repository"""
    try:
        run_command("git rev-parse --is-inside-work-tree")
        return True
    except:
        return False

def setup_github_repo(repo_name):
    """Set up a GitHub repository if it doesn't exist"""
    # Check if remote origin is already configured
    try:
        remote_url = run_command("git remote get-url origin")
        print(f"GitHub repository already configured: {remote_url}")
        return
    except:
        pass

    # Check if Git user is configured
    try:
        user_name = run_command("git config --global user.name")
        user_email = run_command("git config --global user.email")

        if not user_name or not user_email:
            print("Git user not fully configured. Please run setup_github.py first.")
            sys.exit(1)
    except:
        print("Error checking Git configuration. Please run setup_github.py first.")
        sys.exit(1)

    # Prompt for GitHub username
    github_username = input("Enter your GitHub username: ")

    # Create a new repository on GitHub
    print(f"Please create a new repository named '{repo_name}' on GitHub:")
    print(f"https://github.com/new")
    print("Set it to public or private as you prefer.")
    print("DO NOT initialize it with a README, .gitignore, or license.")

    input("Press Enter once you've created the repository...")

    # Add the remote origin
    remote_url = f"https://github.com/{github_username}/{repo_name}.git"
    run_command(f"git remote add origin {remote_url}")
    print(f"Added remote: {remote_url}")

def backup_files():
    """Add important files to Git and commit them"""
    # Check if we're in a Git repository
    if not check_git_repo():
        print("Not in a Git repository. Please run this script from the root of your project.")
        sys.exit(1)

    # Get repository name from current directory
    repo_name = os.path.basename(os.getcwd())

    # Set up GitHub repository if needed
    setup_github_repo(repo_name)

    # Add each important file to Git
    for file in IMPORTANT_FILES:
        if os.path.exists(file):
            # Check if it's a directory
            if os.path.isdir(file):
                # Add all files in the directory
                run_command(f"git add {file}/*")
                print(f"Added all files in directory {file} to Git")
            else:
                # Add the individual file
                run_command(f"git add {file}")
                print(f"Added {file} to Git")
        else:
            print(f"Warning: {file} not found, skipping")

    # Check if there are changes to commit
    status = run_command("git status --porcelain")
    if not status:
        print("No changes to commit.")
        return False

    # Get commit message
    if "--message" in sys.argv:
        index = sys.argv.index("--message")
        if index + 1 < len(sys.argv):
            commit_message = sys.argv[index + 1]
        else:
            commit_message = f"Automated backup: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    else:
        commit_message = f"Automated backup: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Commit changes
    run_command(f'git commit -m "{commit_message}"')
    print(f"Committed changes with message: {commit_message}")

    # Push to GitHub
    run_command("git push -u origin master", capture_output=False)
    print("Pushed changes to GitHub")

    return True

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Backup important code files to GitHub")
    parser.add_argument("--message", help="Custom commit message")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    if args.message:
        sys.argv.extend(["--message", args.message])

    print("Starting GitHub backup process...")
    if backup_files():
        print("Backup completed successfully!")
    else:
        print("Backup completed with no changes.")
