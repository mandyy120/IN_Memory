#!/usr/bin/env python3
"""
GitHub Restore Script

This script helps restore your code from GitHub to a specific version.
It pulls the latest changes from GitHub and can checkout specific commits.
It also supports restoring only selected files.

Usage:
    python restore_from_github.py [--list] [--version COMMIT_HASH] [--files FILE1 FILE2 ...]

Options:
    --list       List the last 10 commits
    --version    Checkout a specific commit by its hash
    --files      Restore only specific files (space-separated list)
    --list-files List all files in the repository
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

def list_files():
    """List all files tracked in the repository"""
    print("Files tracked in the repository:")
    print("-" * 80)
    files = run_command('git ls-files')
    for file in files.split('\n'):
        print(file)
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

def restore_files(files, commit_hash=None):
    """Restore specific files from a commit or the latest version"""
    if commit_hash:
        print(f"Restoring selected files from commit {commit_hash}...")
    else:
        print("Restoring selected files from the latest version...")
        # Make sure we have the latest changes
        pull_latest()
        commit_hash = "HEAD"

    # Check if files exist in the repository
    all_repo_files = run_command('git ls-files').split('\n')

    for file in files:
        if file in all_repo_files:
            print(f"Restoring {file}...")
            # Checkout the specific file from the commit
            run_command(f"git checkout {commit_hash} -- {file}", capture_output=False)
        else:
            print(f"Warning: {file} not found in the repository, skipping")

    print("File restoration completed!")
    print("Note: These changes are staged but not committed. If you want to keep your working directory clean, you can:")
    print("  1. Commit the changes: git commit -m 'Restored selected files'")
    print("  2. Or discard the changes: git reset HEAD && git checkout -- .")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Restore code from GitHub")
    parser.add_argument("--list", action="store_true", help="List the last 10 commits")
    parser.add_argument("--list-files", action="store_true", help="List all files in the repository")
    parser.add_argument("--version", help="Checkout a specific commit by its hash")
    parser.add_argument("--files", nargs="+", help="Restore only specific files (space-separated list)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    # Check if we're in a Git repository
    if not check_git_repo():
        print("Not in a Git repository. Please run this script from the root of your project.")
        sys.exit(1)

    if args.list:
        list_commits()
    elif args.list_files:
        list_files()
    elif args.files:
        # Restore specific files
        restore_files(args.files, args.version)
    elif args.version:
        # Checkout a specific version of the entire repository
        checkout_version(args.version)
    else:
        # Pull the latest changes
        pull_latest()
        print("\nAvailable commands:")
        print("  python restore_from_github.py --list                # List available versions")
        print("  python restore_from_github.py --list-files          # List all files in the repository")
        print("  python restore_from_github.py --version COMMIT_HASH # Restore the entire repository to a specific version")
        print("  python restore_from_github.py --files file1 file2   # Restore specific files from the latest version")
        print("  python restore_from_github.py --version COMMIT_HASH --files file1 file2 # Restore specific files from a specific version")
