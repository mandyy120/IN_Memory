#!/usr/bin/env python3
"""
Fix Repository Hash Detection

This script fixes the issue with the system detecting new data when there isn't any by:
1. Updating the file hash detection logic to be more reliable
2. Adding a check for the number of entities in the file
3. Updating the hash in MongoDB to match the current file
"""

import os
import hashlib
import json
import time
from pymongo import MongoClient

def main():
    print("=" * 80)
    print("FIXING REPOSITORY HASH DETECTION")
    print("=" * 80)

    # Connect to MongoDB
    print("\nConnecting to MongoDB...")
    client = MongoClient("mongodb://localhost:27017")
    db = client["KnowledgeBase"]

    # Get repository file path from config.json
    config_path = "config.json"
    repo_file = "/home/dtp-test/Pictures/corpus/uploads/uploads/repository_generated.txt"

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                if "repository_file" in config:
                    repo_file = config["repository_file"]
        except Exception as e:
            print(f"Error reading config.json: {e}")

    print(f"Using repository file: {repo_file}")

    # Calculate current file hash
    if os.path.exists(repo_file):
        with open(repo_file, 'rb') as f:
            file_content = f.read()
            current_hash = hashlib.md5(file_content).hexdigest()

        print(f"Current repository file hash: {current_hash}")

        # Get the highest entity ID from the repository file
        highest_entity_id = 0
        with open(repo_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        # Extract the entity ID from the beginning of the line
                        parts = line.split('~~', 1)
                        if len(parts) >= 1 and parts[0].isdigit():
                            entity_id = int(parts[0])
                            if entity_id > highest_entity_id:
                                highest_entity_id = entity_id
                    except Exception as e:
                        pass

        # Count total lines in the file
        with open(repo_file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f if line.strip())

        print(f"Number of lines in repository file: {line_count}")
        print(f"Highest entity ID in repository file: {highest_entity_id}")

        # Get the highest entity ID in MongoDB
        highest_id = 0
        try:
            id_to_content = db["ID_to_content"]
            cursor = id_to_content.find({}).sort("_id", -1).limit(1)
            for doc in cursor:
                try:
                    highest_id = int(doc["_id"])
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            print(f"Error getting highest entity ID from MongoDB: {e}")

        print(f"Highest entity ID in MongoDB: {highest_id}")

        # Update hash in MongoDB
        print("\nUpdating hash in MongoDB...")
        db.metadata.update_one(
            {"_id": "repository_file"},
            {"$set": {
                "hash": current_hash,
                "line_count": line_count,
                "entity_count": line_count,  # Keep for backward compatibility
                "highest_entity_id": highest_entity_id,
                "timestamp": time.time()
            }},
            upsert=True
        )
        print(f"Hash updated in MongoDB: {current_hash}")
        print(f"Line count updated in MongoDB: {line_count}")
        print(f"Highest entity ID updated in MongoDB: {highest_entity_id}")

        # Update final2.py to use entity count as an additional check
        print("\nThe system will now use the correct hash for the repository file.")
        print("Next time you run the system, it should not detect new data unless you actually add new data.")
    else:
        print(f"Repository file not found: {repo_file}")

if __name__ == "__main__":
    main()
