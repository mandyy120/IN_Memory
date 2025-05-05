#!/usr/bin/env python3
"""
Test script for repository file detection and MongoDB table management.
This script will:
1. Initialize the knowledge retrieval system
2. Let it automatically find the repository file
3. Check if it correctly detects whether there's new data
4. Only load data if needed
"""

import os
import sys
from final2 import KnowledgeRetrieval

def main():
    print("Testing repository file detection and MongoDB table management...")
    
    # Initialize knowledge retrieval system
    print("\nInitializing knowledge retrieval system...")
    try:
        knowledge_system = KnowledgeRetrieval()
        print("Knowledge retrieval system initialized successfully.")
    except Exception as e:
        print(f"Error initializing knowledge retrieval system: {e}")
        sys.exit(1)
    
    # Check MongoDB collections
    print("\nChecking MongoDB collections...")
    try:
        collections = knowledge_system.mongo_db.list_collection_names()
        print(f"MongoDB collections: {collections}")
        
        # Check counts for key collections
        print("\nCollection counts:")
        for collection in ['dictionary', 'hash_pairs', 'KW_map']:
            if collection in collections:
                count = knowledge_system.mongo_db[collection].count_documents({})
                print(f"  {collection}: {count} documents")
            else:
                print(f"  {collection}: Collection not found")
    except Exception as e:
        print(f"Error checking collections: {e}")
    
    # Check repository file metadata
    print("\nChecking repository file metadata...")
    try:
        metadata = knowledge_system.mongo_db.metadata.find_one({"_id": "repository_file"})
        if metadata:
            print(f"Repository file hash: {metadata.get('hash')}")
            print(f"Last updated: {metadata.get('timestamp')}")
        else:
            print("No repository file metadata found.")
    except Exception as e:
        print(f"Error checking metadata: {e}")
    
    # Try to load data
    print("\nTrying to load data (should only load if needed)...")
    try:
        knowledge_system.load_data(local=True, file_path=None, save_to_db=True)
        print("Data loading process completed.")
    except Exception as e:
        print(f"Error loading data: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
