"""
Test script for the crawling.py adapter.
"""

import crawling

def main():
    # Test URL
    test_url = "https://example.com"
    
    print(f"Testing crawling of {test_url}...")
    
    # Call the crawl function
    content = crawling.crawl(test_url)
    
    # Print the first 500 characters of the content
    print("\nFirst 500 characters of crawled content:")
    print(content[:500])
    
    print(f"\nTotal content length: {len(content)} characters")
    
if __name__ == "__main__":
    main()
