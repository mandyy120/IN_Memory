#!/usr/bin/env python3
"""
GitHub Restore Script

This script helps restore your code from GitHub to a specific version.
It pulls the latest changes from GitHub and can checkout specific commits.

Usage:
    python restore_from_github.py [--list] [--version COMMIT_HASH]

Options:
    --list       List the last 10 commits
    --version    Checkout a specific commit by its hash
"""

import os
import sys
import subprocess
import argparse
import datetime

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
        print(f"Error message: {e.stderr if hasattr(e, 'stderr') else str(e)}")
        sys.exit(1)

def check_git_repo():
    """Check if the current directory is a Git repository"""
    try:
        run_command("git rev-parse --is-inside-work-tree")
        return True
    except:
        return False

def list_commits():
    """List the last 10 commits"""
    print("Last 10 commits:")
    print("-" * 80)
    commits = run_command('git log -10 --pretty=format:"%h | %ad | %s" --date=short')
    print(commits)
    print("-" * 80)

def pull_latest():
    """Pull the latest changes from GitHub"""
    print("Pulling latest changes from GitHub...")
    run_command("git pull origin master", capture_output=False)
    print("Latest changes pulled successfully!")

def checkout_version(commit_hash):
    """Checkout a specific commit"""
    print(f"Checking out version {commit_hash}...")
    
    # First, make sure we have the latest changes
    pull_latest()
    
    # Then checkout the specific commit
    run_command(f"git checkout {commit_hash}", capture_output=False)
    
    print(f"Successfully restored to version {commit_hash}")
    print("Note: You are now in 'detached HEAD' state. To return to the latest version, run:")
    print("  git checkout master")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Restore code from GitHub")
    parser.add_argument("--list", action="store_true", help="List the last 10 commits")
    parser.add_argument("--version", help="Checkout a specific commit by its hash")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # Check if we're in a Git repository
    if not check_git_repo():
        print("Not in a Git repository. Please run this script from the root of your project.")
        sys.exit(1)
    
    if args.list:
        list_commits()
    elif args.version:
        checkout_version(args.version)
    else:
        pull_latest()
        print("To list available versions, run: python restore_from_github.py --list")
        print("To restore a specific version, run: python restore_from_github.py --version COMMIT_HASH")
