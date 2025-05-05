#!/usr/bin/env python3
"""
Reset Script for Intellichat In-memory LLM

This script:
1. Deletes all backend tables from MongoDB
2. Clears the repository file at /home/dtp-test/Pictures/corpus/uploads/uploads/repository_generated.txt
3. Ensures the system will rebuild from scratch on next startup

Usage:
    python3 reset_system.py [--keep-repository]

Options:
    --keep-repository    Keep the repository file intact, only delete MongoDB tables
"""

import os
import sys
import shutil
import argparse
from pymongo import MongoClient
import time

# Repository file path
REPOSITORY_FILE = "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"

# MongoDB connection parameters
MONGO_CONNECTION_STRING = "mongodb://localhost:27017"
MONGO_DB_NAME = "KnowledgeBase"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Reset the Intellichat In-memory LLM system")
    parser.add_argument("--keep-repository", action="store_true", 
                        help="Keep the repository file intact, only delete MongoDB tables")
    return parser.parse_args()

def delete_mongodb_tables():
    """Delete all collections from MongoDB database."""
    try:
        # Connect to MongoDB
        print(f"Connecting to MongoDB at {MONGO_CONNECTION_STRING}...")
        client = MongoClient(MONGO_CONNECTION_STRING)
        db = client[MONGO_DB_NAME]
        
        # Get list of all collections
        collections = db.list_collection_names()
        
        if not collections:
            print("No collections found in the database. Nothing to delete.")
            return
        
        print(f"Found {len(collections)} collections in the database:")
        for collection in collections:
            print(f"  - {collection}")
        
        # Confirm deletion
        confirm = input("\nAre you sure you want to delete all MongoDB collections? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
        
        # Delete each collection
        print("\nDeleting collections...")
        for collection in collections:
            db.drop_collection(collection)
            print(f"  - Deleted collection: {collection}")
        
        print(f"Successfully deleted all collections from {MONGO_DB_NAME} database.")
        
    except Exception as e:
        print(f"Error deleting MongoDB collections: {e}")
        sys.exit(1)

def clear_repository_file():
    """Clear the repository file."""
    try:
        if not os.path.exists(REPOSITORY_FILE):
            print(f"Repository file not found at {REPOSITORY_FILE}")
            return
        
        # Get file size
        file_size = os.path.getsize(REPOSITORY_FILE) / 1024  # KB
        
        print(f"Repository file found: {REPOSITORY_FILE}")
        print(f"Current size: {file_size:.2f} KB")
        
        # Confirm deletion
        confirm = input("\nAre you sure you want to clear this repository file? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
        
        # Create backup
        backup_file = f"{REPOSITORY_FILE}.bak.{int(time.time())}"
        shutil.copy2(REPOSITORY_FILE, backup_file)
        print(f"Created backup at: {backup_file}")
        
        # Clear the file
        with open(REPOSITORY_FILE, 'w') as f:
            f.write("")
        
        print(f"Repository file has been cleared.")
        
    except Exception as e:
        print(f"Error clearing repository file: {e}")
        sys.exit(1)

def main():
    """Main function."""
    args = parse_arguments()
    
    print("=" * 80)
    print("INTELLICHAT IN-MEMORY LLM SYSTEM RESET")
    print("=" * 80)
    print("\nWARNING: This will reset the system to its initial state.")
    print("All knowledge data will be deleted from MongoDB.")
    if not args.keep_repository:
        print("The repository file will be cleared (a backup will be created).")
    print("\nThe system will rebuild from scratch on next startup.")
    
    # Final confirmation
    confirm = input("\nDo you want to proceed with the system reset? (y/n): ")
    if confirm.lower() != 'y':
        print("Reset cancelled.")
        return
    
    # Delete MongoDB tables
    delete_mongodb_tables()
    
    # Clear repository file if not keeping it
    if not args.keep_repository:
        clear_repository_file()
    else:
        print("\nRepository file kept intact as requested.")
    
    print("\n" + "=" * 80)
    print("SYSTEM RESET COMPLETE")
    print("=" * 80)
    print("\nThe system will rebuild from scratch on next startup.")
    print("To start the system, run: python3 main2.py")

if __name__ == "__main__":
    main()
