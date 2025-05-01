#!/usr/bin/env python3
"""
Check Repository Hash

This script checks the repository file hash in MongoDB and compares it with the current file hash.
"""

import os
import hashlib
from pymongo import MongoClient

def main():
    print("=" * 80)
    print("CHECKING REPOSITORY FILE HASH")
    print("=" * 80)
    
    # Connect to MongoDB
    print("\nConnecting to MongoDB...")
    client = MongoClient("mongodb://localhost:27017")
    db = client["KnowledgeBase"]
    
    # Check if metadata collection exists
    if "metadata" not in db.list_collection_names():
        print("Metadata collection not found in MongoDB.")
        return
    
    # Get repository file hash from metadata
    metadata = db.metadata.find_one({"_id": "repository_file"})
    if not metadata:
        print("Repository file metadata not found in MongoDB.")
        return
    
    stored_hash = metadata.get("hash")
    if not stored_hash:
        print("Repository file hash not found in metadata.")
        return
    
    print(f"Stored repository file hash: {stored_hash}")
    
    # Get repository file path from config.json
    repo_file = "/home/dtp-test/Pictures/corpus/uploads/uploads/repository_generated.txt"
    
    # Calculate current file hash
    if os.path.exists(repo_file):
        with open(repo_file, 'rb') as f:
            file_content = f.read()
            current_hash = hashlib.md5(file_content).hexdigest()
        
        print(f"Current repository file hash: {current_hash}")
        
        # Compare hashes
        if current_hash == stored_hash:
            print("\nHashes match. The system should not detect new data.")
        else:
            print("\nHashes don't match. The system will detect new data.")
            
            # Update hash in MongoDB
            update_hash = input("\nWould you like to update the hash in MongoDB? (y/n): ").strip().lower()
            if update_hash == 'y':
                db.metadata.update_one(
                    {"_id": "repository_file"},
                    {"$set": {"hash": current_hash}}
                )
                print(f"Hash updated in MongoDB: {current_hash}")
    else:
        print(f"Repository file not found: {repo_file}")

if __name__ == "__main__":
    main()
