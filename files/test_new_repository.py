#!/usr/bin/env python3
"""
Test script to simulate adding a new repository file.
This script will:
1. Create a simple repository file with test data
2. Initialize the knowledge retrieval system
3. Load the new repository file
4. Verify that it's detected as new data
"""

import os
import sys
import time
import hashlib
from final2 import KnowledgeRetrieval

def create_test_repository():
    """Create a test repository file with unique content"""
    # Create uploads directory if it doesn't exist
    os.makedirs('uploads', exist_ok=True)
    
    # Create a unique repository file
    timestamp = int(time.time())
    content = f"""
    {{
        "ID": "test-{timestamp}",
        "category": "Test Category",
        "tag_list": ["test", "repository", "detection"],
        "title": "Test Repository {timestamp}",
        "description": "This is a test repository file created at {timestamp}",
        "meta": "test metadata",
        "agents": ["test agent"],
        "full_content": "This is the full content of the test repository file."
    }}
    """
    
    # Save to repository file
    repo_path = "uploads/repository_generated.txt"
    with open(repo_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Calculate and return the hash
    file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    return repo_path, file_hash

def main():
    print("Testing new repository file detection...")
    
    # Create test repository file
    repo_path, file_hash = create_test_repository()
    print(f"\nCreated test repository file: {repo_path}")
    print(f"File hash: {file_hash}")
    
    # Initialize knowledge retrieval system
    print("\nInitializing knowledge retrieval system...")
    try:
        knowledge_system = KnowledgeRetrieval()
        print("Knowledge retrieval system initialized successfully.")
    except Exception as e:
        print(f"Error initializing knowledge retrieval system: {e}")
        sys.exit(1)
    
    # Check repository file metadata before loading
    print("\nChecking repository file metadata before loading...")
    try:
        metadata = knowledge_system.mongo_db.metadata.find_one({"_id": "repository_file"})
        if metadata:
            print(f"Repository file hash: {metadata.get('hash')}")
            print(f"Last updated: {metadata.get('timestamp')}")
        else:
            print("No repository file metadata found.")
    except Exception as e:
        print(f"Error checking metadata: {e}")
    
    # Load the new repository file
    print("\nLoading the new repository file...")
    try:
        knowledge_system.load_data(local=True, file_path=repo_path, save_to_db=True)
        print("Data loading process completed.")
    except Exception as e:
        print(f"Error loading data: {e}")
    
    # Check repository file metadata after loading
    print("\nChecking repository file metadata after loading...")
    try:
        metadata = knowledge_system.mongo_db.metadata.find_one({"_id": "repository_file"})
        if metadata:
            print(f"Repository file hash: {metadata.get('hash')}")
            print(f"Last updated: {metadata.get('timestamp')}")
            
            # Verify the hash matches
            if metadata.get('hash') == file_hash:
                print("SUCCESS: Repository file hash matches!")
            else:
                print(f"ERROR: Repository file hash doesn't match! Expected: {file_hash}, Got: {metadata.get('hash')}")
        else:
            print("ERROR: No repository file metadata found after loading.")
    except Exception as e:
        print(f"Error checking metadata: {e}")
    
    # Try loading again - should detect no new data
    print("\nTrying to load the same repository file again (should detect no new data)...")
    try:
        knowledge_system.load_data(local=True, file_path=repo_path, save_to_db=True)
        print("Second load completed.")
    except Exception as e:
        print(f"Error on second load: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
