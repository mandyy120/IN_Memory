#!/usr/bin/env python3
"""
Test Mistral Rephrasing

This script tests the Mistral rephrasing functionality by:
1. Initializing the knowledge retrieval system
2. Generating a description for a test query
3. Testing both local rephrasing and API rephrasing
4. Printing the results for comparison
"""

import os
from final2 import KnowledgeRetrieval

def main():
    print("=" * 80)
    print("TESTING MISTRAL REPHRASING")
    print("=" * 80)
    
    # Initialize knowledge retrieval system
    print("\nInitializing knowledge retrieval system...")
    knowledge_system = KnowledgeRetrieval()
    
    # Load data from repository file
    repo_file = "/home/dtp-test/Pictures/corpus/uploads/uploads/repository_generated.txt"
    print(f"\nLoading data from repository file: {repo_file}")
    knowledge_system.load_data(local=True, file_path=repo_file, append=True, save_to_db=True)
    
    # Test query
    test_query = "machine learning"
    print(f"\nGenerating description for test query: '{test_query}'")
    
    # Generate description
    description = knowledge_system.generate_description(test_query, include_topics_and_pmi=False)
    print("\nOriginal description:")
    print("-" * 80)
    print(description)
    print("-" * 80)
    
    # Test local rephrasing
    print("\nTesting local rephrasing...")
    local_rephrased = knowledge_system._local_rephrase(description)
    print("\nLocally rephrased description:")
    print("-" * 80)
    print(local_rephrased)
    print("-" * 80)
    
    # Check if MISTRAL_API_KEY is set
    api_key = os.environ.get("MISTRAL_API_KEY")
    if api_key:
        print("\nMISTRAL_API_KEY is set. Testing API rephrasing...")
        try:
            # Test API rephrasing
            api_rephrased = knowledge_system.rephrase_with_mistral(description, use_api=True)
            print("\nAPI rephrased description:")
            print("-" * 80)
            print(api_rephrased)
            print("-" * 80)
        except Exception as e:
            print(f"\nError using Mistral API: {e}")
    else:
        print("\nMISTRAL_API_KEY is not set. Skipping API rephrasing test.")
        print("To test API rephrasing, set the MISTRAL_API_KEY environment variable:")
        print("export MISTRAL_API_KEY=your_api_key_here")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
