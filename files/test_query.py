#!/usr/bin/env python3
"""
Script to test the knowledge retrieval system.
This script will:
1. Connect to MongoDB
2. Run a test query
3. Print the results
"""

import sys
from final2 import KnowledgeRetrieval

def main():
    print("Starting knowledge retrieval test...")
    
    # Create a new KnowledgeRetrieval instance
    try:
        knowledge_system = KnowledgeRetrieval(
            use_mongodb=True,
            mongo_connection_string="mongodb://localhost:27017",
            mongo_db_name="KnowledgeBase"
        )
        print("Successfully connected to MongoDB")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)
    
    # Check MongoDB collections
    try:
        collections = knowledge_system.mongo_db.list_collection_names()
        print(f"MongoDB collections: {collections}")
        
        # Check counts
        for collection in collections:
            count = knowledge_system.mongo_db[collection].count_documents({})
            print(f"Collection {collection}: {count} documents")
    except Exception as e:
        print(f"Error checking collections: {e}")
    
    # Run a test query
    print("\nRunning test query...")
    test_query = input("Enter a test query: ")
    
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
