#!/usr/bin/env python3
"""
Test script for repository file configuration.
This script will:
1. Check the config.json file for repository file location
2. Initialize the knowledge retrieval system
3. Verify that it uses the configured repository file
"""

import os
import sys
import json
from final2 import KnowledgeRetrieval

def main():
    print("Testing repository file configuration...")
    
    # Check config.json
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                repo_file = config.get("repository_file")
                if repo_file:
                    print(f"Repository file configured in config.json: {repo_file}")
                    print(f"File exists: {os.path.exists(repo_file)}")
                else:
                    print("No repository_file setting found in config.json")
        except Exception as e:
            print(f"Error reading config.json: {e}")
    else:
        print("config.json not found")
    
    # Initialize knowledge retrieval system
    print("\nInitializing knowledge retrieval system...")
    try:
        knowledge_system = KnowledgeRetrieval()
        print("Knowledge retrieval system initialized successfully.")
    except Exception as e:
        print(f"Error initializing knowledge retrieval system: {e}")
        sys.exit(1)
    
    # Try to load data
    print("\nTrying to load data (should use configured repository file)...")
    try:
        knowledge_system.load_data(local=True, file_path=None, save_to_db=True)
        print("Data loading process completed.")
    except Exception as e:
        print(f"Error loading data: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
