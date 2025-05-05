#!/usr/bin/env python3
"""
Fix Repository File Structure

This script fixes the repository file structure by:
1. Creating the standard uploads directory if it doesn't exist
2. Copying any existing repository files from the nested uploads folder to the standard location
3. Updating the config.json file to use the standard location
"""

import os
import json
import shutil
import hashlib

def main():
    print("Fixing repository file structure...")
    
    # Create standard uploads directory if it doesn't exist
    os.makedirs("uploads", exist_ok=True)
    print("Created standard uploads directory")
    
    # Check for nested uploads directory
    nested_path = "/home/dtp-test/Pictures/corpus/uploads/uploads"
    standard_path = "uploads"
    
    # Check for repository files in nested directory
    nested_repo_file = os.path.join(nested_path, "repository_generated.txt")
    standard_repo_file = os.path.join(standard_path, "repository_generated.txt")
    
    # Copy repository file if it exists in nested directory but not in standard directory
    if os.path.exists(nested_repo_file):
        print(f"Found repository file in nested directory: {nested_repo_file}")
        
        # Calculate file hashes to compare
        nested_hash = None
        standard_hash = None
        
        if os.path.exists(nested_repo_file):
            with open(nested_repo_file, 'rb') as f:
                nested_hash = hashlib.md5(f.read()).hexdigest()
        
        if os.path.exists(standard_repo_file):
            with open(standard_repo_file, 'rb') as f:
                standard_hash = hashlib.md5(f.read()).hexdigest()
        
        # If standard file doesn't exist or has different content, copy from nested
        if not os.path.exists(standard_repo_file) or nested_hash != standard_hash:
            print(f"Copying repository file to standard location: {standard_repo_file}")
            shutil.copy2(nested_repo_file, standard_repo_file)
            print("Repository file copied successfully")
        else:
            print("Repository file already exists in standard location with same content")
    else:
        print(f"No repository file found in nested directory: {nested_repo_file}")
    
    # Update config.json to use standard location
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update repository_file path if it's using the nested path
            if config.get("repository_file") == nested_repo_file:
                config["repository_file"] = standard_repo_file
                
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"Updated config.json to use standard repository file path: {standard_repo_file}")
            else:
                print(f"Config.json already using path: {config.get('repository_file')}")
        except Exception as e:
            print(f"Error updating config.json: {e}")
    else:
        print(f"Config file not found: {config_path}")
    
    print("\nRepository file structure fixed successfully!")
    print("The system will now use the standard repository file location: uploads/repository_generated.txt")

if __name__ == "__main__":
    main()
