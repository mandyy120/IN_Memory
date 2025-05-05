import asyncio
import json
import os
from urllib.parse import urljoin, urlparse

from fake_useragent import UserAgent
from playwright.async_api import async_playwright

# Config
HEADLESS = True
VISITED_FILE = "visited_urls.json"
OUTPUT_FILE = "output.txt"  # Output for scraped content
MAX_PAGES = 5  # Maximum number of pages to crawl per domain

# Persistent visited set
def load_visited_urls():
    if os.path.exists(VISITED_FILE):
        try:
            with open(VISITED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_visited_urls():
    with open(VISITED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(visited_urls), f, ensure_ascii=False, indent=2)

# Headers
def get_random_headers():
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Accept-Language": "en-US,en;q=0.9",
    }

# Normalize URL
def normalize_url(url):
    parsed = urlparse(url)
    return parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/")

# Extract all links from page
async def extract_links(page):
    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a'))
            .map(a => a.href)
            .filter(href => href && !href.startsWith('mailto:') && !href.startsWith('javascript:'))
    """)
    return links

# Extract full structured content (title, headings, paragraphs, links)
async def extract_page_content(page):
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

# Main Crawler
async def crawl_website(start_url):
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
                save_visited_urls()

                # Increment pages crawled counter
                pages_crawled += 1

                # ✅ Extract and Save page content here
                try:
                    title, h1s, h2s, paragraphs, links = await extract_page_content(page)
                    print(f"📦 Extracted content from {current_url} (page {pages_crawled}/{MAX_PAGES})")
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
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

# Load visited URLs at global scope
visited_urls = load_visited_urls()

# Main runner
if __name__ == "__main__":
    url = input("Enter website URL: ").strip()
    if not url.startswith("http"):
        url = "https://www." + url
    asyncio.run(crawl_website(url))