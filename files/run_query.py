#!/usr/bin/env python3
"""
Simple script to run a query against the knowledge retrieval system.
"""

import sys
from final2 import KnowledgeRetrieval

def main():
    # Initialize knowledge retrieval system
    print("Initializing knowledge retrieval system...")
    try:
        knowledge_system = KnowledgeRetrieval()
        print("Knowledge retrieval system initialized successfully.")
    except Exception as e:
        print(f"Error initializing knowledge retrieval system: {e}")
        sys.exit(1)
    
    # Run a query
    query = input("Enter your query: ")
    if not query:
        print("No query entered. Exiting.")
        return
    
    print(f"\nProcessing query: {query}")
    try:
        result = knowledge_system.generate_description(query)
        print("\nQuery Result:")
        print("=" * 80)
        print(result)
        print("=" * 80)
    except Exception as e:
        print(f"Error running query: {e}")

if __name__ == "__main__":
    main()
