"""
Unified web crawling module for the knowledge system.
This module provides both synchronous and asynchronous interfaces for web crawling.
"""

import asyncio
import json
import os
import uuid
from urllib.parse import urljoin, urlparse

try:
    from fake_useragent import UserAgent
except ImportError:
    print("Warning: fake_useragent not installed. Using default user agent.")
    class UserAgent:
        @property
        def random(self):
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Warning: playwright not installed. Web crawling functionality will be limited.")
    print("Install with: pip install playwright && playwright install")

# Configuration
HEADLESS = True
VISITED_FILE = "visited_urls.json"
MAX_PAGES = 5  # Maximum number of pages to crawl per domain

# Persistent visited set
def load_visited_urls():
    """Load the set of visited URLs from the VISITED_FILE."""
    if os.path.exists(VISITED_FILE):
        try:
            with open(VISITED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_visited_urls(visited_urls):
    """Save the set of visited URLs to the VISITED_FILE."""
    with open(VISITED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(visited_urls), f, ensure_ascii=False, indent=2)

# Headers
def get_random_headers():
    """Get random headers for HTTP requests."""
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Accept-Language": "en-US,en;q=0.9",
    }

# Normalize URL
def normalize_url(url):
    """Normalize a URL by removing trailing slashes and fragments."""
    parsed = urlparse(url)
    return parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/")

# Extract all links from page
async def extract_links(page):
    """Extract all links from a page."""
    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a'))
            .map(a => a.href)
            .filter(href => href && !href.startsWith('mailto:') && !href.startsWith('javascript:'))
    """)
    return links

# Extract full structured content (title, headings, paragraphs, links)
async def extract_page_content(page):
    """Extract structured content from a page."""
    title = await page.title()

    # Get standard elements
    paragraphs = await page.locator("p").all_inner_texts()
    h1s = await page.locator("h1").all_inner_texts()
    h2s = await page.locator("h2").all_inner_texts()

    # If no standard elements found, try to get all text content
    if not paragraphs and not h1s and not h2s:
        # Get all text from the page
        all_text = await page.evaluate("""
            () => {
                // Get all text nodes
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    { acceptNode: node => node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT }
                );

                const textNodes = [];
                let node;
                while (node = walker.nextNode()) {
                    const text = node.textContent.trim();
                    if (text.length > 20) {  // Only include substantial text
                        textNodes.push(text);
                    }
                }
                return textNodes;
            }
        """)

        # If we found text content, add it to paragraphs
        if all_text:
            paragraphs = all_text
            print(f"Found {len(all_text)} text blocks using alternative method")

    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a'))
            .map(a => a.href)
            .filter(href => href && !href.startsWith('mailto:') && !href.startsWith('javascript:'))
    """)

    return title, h1s, h2s, paragraphs, links

# Main Crawler (Async)
async def crawl_website_async(start_url, output_file):
    """
    Crawl a website asynchronously and save the content to a file.
    
    Args:
        start_url (str): The URL to start crawling from
        output_file (str): The file to save the crawled content to
    """
    # Load visited URLs
    visited_urls = load_visited_urls()
    
    headers = get_random_headers()
    parsed_start = urlparse(start_url)
    domain = parsed_start.netloc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            extra_http_headers=headers,
            user_agent=headers["User-Agent"]
        )
        page = await context.new_page()

        to_visit = set([normalize_url(start_url)])
        visited_in_this_session = set()
        pages_crawled = 0

        while to_visit and pages_crawled < MAX_PAGES:
            current_url = to_visit.pop()
            print(f"🔍 Visiting: {current_url}")

            try:
                await page.goto(current_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector("body", timeout=15000)
                for _ in range(3):
                    await page.mouse.wheel(0, 3000)
                    await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"❌ Failed to load {current_url}: {e}")
                continue

            try:
                links = await extract_links(page)
            except Exception as e:
                print(f"⚠️ Failed to extract links from {current_url}: {e}")
                links = []

            # Save only if it was not previously visited
            if current_url not in visited_urls:
                visited_urls.add(current_url)
                save_visited_urls(visited_urls)

                # Increment pages crawled counter
                pages_crawled += 1

                # ✅ Extract and Save page content here
                try:
                    title, h1s, h2s, paragraphs, links = await extract_page_content(page)
                    print(f"📦 Extracted content from {current_url} (page {pages_crawled}/{MAX_PAGES})")
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write(f"\n\n==== URL: {current_url} ====\n")
                        f.write(f"Title: {title}\n\n")
                        if h1s:
                            f.write("H1 Headings:\n")
                            for h1 in h1s:
                                f.write(f"  - {h1.strip()}\n")
                        if h2s:
                            f.write("\nH2 Headings:\n")
                            for h2 in h2s:
                                f.write(f"  - {h2.strip()}\n")
                        if paragraphs:
                            f.write("\nParagraphs:\n")
                            for para in paragraphs:
                                f.write(f"  {para.strip()}\n\n")
                except Exception as e:
                    print(f"⚠️ Failed to extract content from {current_url}: {e}")

            visited_in_this_session.add(current_url)

            # Discover new internal links
            for link in links:
                normalized_link = normalize_url(urljoin(current_url, link))
                if urlparse(normalized_link).netloc == domain:
                    if normalized_link not in visited_in_this_session:
                        to_visit.add(normalized_link)

        print("✅ Full crawl completed.")
        await browser.close()

# Helper function to run async code in a thread
def run_async_in_thread(coro):
    """
    Helper function to run an async coroutine in a thread.
    This creates a new event loop for the current thread.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Run the coroutine in this thread's event loop
        return loop.run_until_complete(coro)
    finally:
        # Clean up
        loop.close()

# Synchronous interface for main2.py
def crawl(url):
    """
    Crawl a website and return the content as a string.
    This function is called by main2.py.

    Args:
        url (str): The URL to crawl

    Returns:
        str: The crawled content as a string
    """
    # Create a unique temporary file name
    temp_output_file = f"temp_crawl_{uuid.uuid4().hex}.txt"

    try:
        # Make sure the URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Run the crawl_website function with a new event loop
        run_async_in_thread(crawl_website_async(url, temp_output_file))

        # Read the content from the temporary file
        if os.path.exists(temp_output_file):
            with open(temp_output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if the content is empty or just contains whitespace
            if not content.strip():
                print(f"Warning: Empty content retrieved from {url}")
                return f"No content was retrieved from {url}. The page might be empty or require JavaScript rendering."

            # Clean up the temporary file
            try:
                os.remove(temp_output_file)
            except:
                pass  # Ignore errors in cleanup

            return content
        else:
            print(f"Error: No output file created for {url}")
            return f"No content was retrieved from {url}. The crawling process may have failed."

    except Exception as e:
        return f"Error crawling {url}: {str(e)}"

# Main runner (for command-line usage)
if __name__ == "__main__":
    url = input("Enter website URL to crawl: ").strip()
    if not url.startswith("http"):
        url = "https://" + url
    
    content = crawl(url)
    print(f"\nCrawled content ({len(content)} characters):")
    print(content[:500] + "..." if len(content) > 500 else content)
