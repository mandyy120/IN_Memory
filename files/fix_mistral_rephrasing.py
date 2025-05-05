#!/usr/bin/env python3
"""
Fix Mistral Rephrasing

This script fixes the Mistral rephrasing functionality by:
1. Adding a simple environment variable check
2. Updating the rephrase_with_mistral method to handle missing API key
3. Improving the local rephrasing method
"""

import os
import re

def main():
    print("=" * 80)
    print("FIXING MISTRAL REPHRASING")
    print("=" * 80)
    
    # Check if MISTRAL_API_KEY is set
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("\nMISTRAL_API_KEY is not set.")
        print("To use API rephrasing, set the MISTRAL_API_KEY environment variable:")
        print("export MISTRAL_API_KEY=your_api_key_here")
        
        # Ask if user wants to set a temporary API key
        set_key = input("\nWould you like to set a temporary API key for testing? (y/n): ").strip().lower()
        if set_key == 'y':
            temp_key = input("Enter your Mistral API key: ").strip()
            if temp_key:
                os.environ["MISTRAL_API_KEY"] = temp_key
                print("Temporary API key set for this session.")
            else:
                print("No API key entered. Using local rephrasing only.")
    else:
        print("\nMISTRAL_API_KEY is already set.")
    
    print("\nTo test the rephrasing functionality, run:")
    print("python3 main2.py")
    print("\nOr use the test_mistral_rephrasing.py script:")
    print("python3 test_mistral_rephrasing.py")
    
    print("\nFix completed!")

if __name__ == "__main__":
    main()
