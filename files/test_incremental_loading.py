#!/usr/bin/env python3
"""
Test Incremental Loading

This script tests the incremental loading functionality by:
1. Creating a test repository file with some initial data
2. Loading the data into the system
3. Adding new data to the repository file
4. Loading the data again to verify that only the new data is processed
"""

import os
import time
import random
from final2 import KnowledgeRetrieval
from text import process_file

def create_test_data(file_path, num_paragraphs=5):
    """Create test data for the repository file."""
    # Create a temporary input file
    input_file = "temp_input.txt"
    
    # Generate random paragraphs
    paragraphs = []
    for i in range(num_paragraphs):
        words = ["test", "data", "loading", "incremental", "system", "repository", 
                 "entity", "mongodb", "database", "knowledge", "retrieval"]
        paragraph = " ".join(random.choices(words, k=20))
        paragraphs.append(paragraph)
    
    # Write paragraphs to input file
    with open(input_file, "w") as f:
        f.write("\n\n".join(paragraphs))
    
    # Process the input file to create repository file
    process_file(input_file, file_path, append=False)
    
    # Clean up
    os.remove(input_file)
    
    return file_path

def add_more_data(file_path, num_paragraphs=3):
    """Add more data to the repository file."""
    # Create a temporary input file
    input_file = "temp_input.txt"
    
    # Generate random paragraphs with different words to make them distinct
    paragraphs = []
    for i in range(num_paragraphs):
        words = ["new", "additional", "extra", "updated", "fresh", "recent", 
                 "latest", "modern", "current", "contemporary"]
        paragraph = " ".join(random.choices(words, k=20))
        paragraphs.append(paragraph)
    
    # Write paragraphs to input file
    with open(input_file, "w") as f:
        f.write("\n\n".join(paragraphs))
    
    # Process the input file to add to repository file
    process_file(input_file, file_path, append=True)
    
    # Clean up
    os.remove(input_file)
    
    return file_path

def main():
    print("=" * 80)
    print("TESTING INCREMENTAL LOADING")
    print("=" * 80)
    
    # Create a test repository file
    repo_file = "test_repository.txt"
    print(f"Creating test repository file: {repo_file}")
    create_test_data(repo_file)
    
    # Initialize knowledge retrieval system
    print("\nInitializing knowledge retrieval system...")
    knowledge_system = KnowledgeRetrieval()
    
    # Load initial data
    print("\nLoading initial data...")
    knowledge_system.load_data(local=True, file_path=repo_file, append=True, save_to_db=True)
    
    # Wait a moment to ensure file timestamp changes
    time.sleep(1)
    
    # Add more data to the repository file
    print("\nAdding more data to the repository file...")
    add_more_data(repo_file)
    
    # Load data again - should only process new entities
    print("\nLoading data again - should only process new entities...")
    knowledge_system.load_data(local=True, file_path=repo_file, append=True, save_to_db=True)
    
    # Clean up
    print("\nCleaning up...")
    os.remove(repo_file)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
