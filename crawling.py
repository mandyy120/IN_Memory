"""
Adapter module to integrate crawling2.py with main2.py.
This module provides a synchronous interface to the asynchronous crawling2.py module.
"""

import asyncio
import os
import uuid

# Import the crawling2 module
import crawling2

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

def crawl(url):
    """
    Crawl a website and return the content as a string.
    This function is called by main2.py and serves as an adapter to crawling2.py.

    Args:
        url (str): The URL to crawl

    Returns:
        str: The crawled content as a string
    """
    # Create a unique temporary file name
    temp_output_file = f"temp_crawl_{uuid.uuid4().hex}.txt"

    # Save the original OUTPUT_FILE value
    original_output_file = crawling2.OUTPUT_FILE

    try:
        # Set the OUTPUT_FILE to our temporary file
        crawling2.OUTPUT_FILE = temp_output_file

        # Make sure the URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Run the crawl_website function with a new event loop
        run_async_in_thread(crawling2.crawl_website(url))

        # Read the content from the temporary file
        if os.path.exists(temp_output_file):
            with open(temp_output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Clean up the temporary file
            try:
                os.remove(temp_output_file)
            except:
                pass  # Ignore errors in cleanup

            return content
        else:
            return f"No content was retrieved from {url}. The crawling process may have failed."

    except Exception as e:
        return f"Error crawling {url}: {str(e)}"

    finally:
        # Restore the original OUTPUT_FILE value
        crawling2.OUTPUT_FILE = original_output_file
