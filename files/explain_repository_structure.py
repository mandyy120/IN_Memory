#!/usr/bin/env python3
"""
Explain Repository File Structure

This script explains the repository file structure by:
1. Checking for repository files in different locations
2. Displaying their content and file sizes
3. Explaining which file is used by the system
"""

import os
import json
import hashlib

def main():
    print("=" * 80)
    print("REPOSITORY FILE STRUCTURE EXPLANATION")
    print("=" * 80)
    
    # Check config.json for repository file path
    config_path = "config.json"
    config_repo_path = None
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                config_repo_path = config.get("repository_file")
                print(f"Repository file path in config.json: {config_repo_path}")
        except Exception as e:
            print(f"Error reading config.json: {e}")
    else:
        print("config.json not found")
    
    # Check for repository files in different locations
    repo_paths = [
        "/home/dtp-test/Pictures/corpus/uploads/uploads/repository_generated.txt",
        "uploads/repository_generated.txt",
        "repository_generated.txt",
        "repository.txt"
    ]
    
    print("\nChecking for repository files in different locations:")
    for path in repo_paths:
        if os.path.exists(path):
            file_size = os.path.getsize(path)
            print(f"  - {path} (Size: {file_size} bytes)")
            
            # Calculate file hash
            with open(path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            print(f"    Hash: {file_hash}")
            
            # Show first few lines of content
            try:
                with open(path, 'r') as f:
                    content = f.read(500)  # Read first 500 bytes
                    content_preview = content.strip()
                    if len(content) > 500:
                        content_preview += "..."
                    print(f"    Content preview: {content_preview}")
            except Exception as e:
                print(f"    Error reading file: {e}")
        else:
            print(f"  - {path} (Not found)")
    
    print("\nEXPLANATION:")
    print("-" * 80)
    print("The system uses the repository file specified in config.json for:")
    print("1. Creating backend tables")
    print("2. Checking for new data")
    print("3. Updating tables with new data")
    print("\nThe current configuration is set to use:")
    print(f"  {config_repo_path}")
    print("\nIf you want to change this, you can:")
    print("1. Edit config.json directly")
    print("2. Run the system with a different repository file path:")
    print("   python3 final2.py --repository-file=/path/to/your/repository_file.txt")
    print("-" * 80)

if __name__ == "__main__":
    main()
