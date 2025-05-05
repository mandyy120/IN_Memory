#!/usr/bin/env python3
"""
Test script for MongoDB table management and repository file updates.
This script will:
1. Initialize the knowledge retrieval system
2. Check if all required MongoDB collections exist
3. Create missing collections if needed
4. Check if repository file has new data
5. Load data if needed
6. Run a test query
"""

import os
import sys
from final2 import KnowledgeRetrieval

def main():
    print("Testing MongoDB table management and repository file updates...")
    
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
        
        # Check counts
        print("\nCollection counts:")
        for collection in collections:
            count = knowledge_system.mongo_db[collection].count_documents({})
            print(f"  {collection}: {count} documents")
    except Exception as e:
        print(f"Error checking collections: {e}")
    
    # Load data if needed
    repo_file = "uploads/repository_generated.txt"
    if os.path.exists(repo_file):
        print(f"\nLoading data from {repo_file}...")
        try:
            knowledge_system.load_data(local=True, file_path=repo_file)
        except Exception as e:
            print(f"Error loading data: {e}")
    else:
        print(f"\nRepository file not found: {repo_file}")
        repo_file = input("Enter the path to your repository_generated.txt file (or press Enter to skip): ")
        if repo_file and os.path.exists(repo_file):
            try:
                knowledge_system.load_data(local=True, file_path=repo_file)
            except Exception as e:
                print(f"Error loading data: {e}")
    
    # Run a test query
    print("\nRunning test query...")
    test_query = input("Enter a test query (or press Enter to skip): ")
    if test_query:
        try:
            result = knowledge_system.generate_description(test_query)
            print("\nQuery Result:")
            print("=" * 80)
            print(result)
            print("=" * 80)
        except Exception as e:
            print(f"Error running query: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
