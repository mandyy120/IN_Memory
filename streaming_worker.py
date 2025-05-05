"""
Streaming Worker for Event-Driven Streaming Pipeline

This module provides worker functionality for processing streaming tasks
queued by the message broker. It handles the actual data processing for
different sources.

Usage:
    from streaming_worker import start_workers

    # Start worker threads
    start_workers(num_workers=2)
"""

import os
import sys
import time
import threading
import requests
import json
import logging
import datetime
from message_broker import broker

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('streaming_worker.log')
    ]
)
logger = logging.getLogger('streaming_worker')

# Import app context only to avoid circular imports
try:
    from main2 import app
    logger.info("Successfully imported Flask app from main2")

    # These functions will be imported when needed
    def get_crawl_website():
        from main2 import crawl_website
        return crawl_website

    def get_process_file():
        from main2 import process_file
        return process_file

    def get_process_drive_files():
        from main2 import process_drive_files
        return process_drive_files

    def get_fetch_s3_files_async():
        from main2 import fetch_s3_files_async
        return fetch_s3_files_async

    def get_fetch_slack_data_async():
        from main2 import fetch_slack_data_async
        return fetch_slack_data_async

    def get_app_config():
        from main2 import app_config
        return app_config

except ImportError as e:
    logger.error(f"Failed to import from main2: {e}", exc_info=True)
    print(f"Warning: Could not import from main2.py: {e}. Worker functionality will be limited.")

def process_task(task):
    """
    Process a streaming task

    Args:
        task (dict): Task data including source, uri, and trigger
    """
    logger.info(f"Processing task: {task['id']}")

    source = task.get("source")
    uri = task.get("uri")
    trigger = task.get("trigger", "manual")

    logger.debug(f"Task details: source={source}, uri={uri}, trigger={trigger}")

    try:
        # Process based on source
        if source == "url":
            # Process URL
            logger.info(f"Crawling URL: {uri}")
            try:
                # Get the crawl_website function
                crawl_website = get_crawl_website()

                # Update status for better tracking
                logger.info(f"Starting URL ingestion for {uri}")

                # Make sure the URL has a scheme
                if not uri.startswith(('http://', 'https://')):
                    uri = 'https://' + uri
                    logger.info(f"Added https:// scheme to URL: {uri}")

                # Call the crawl_website function directly with app context
                logger.info(f"Calling crawl_website({uri})")
                with app.app_context():
                    crawl_website(uri)

                # Try to load the processed data into MongoDB
                try:
                    from main2 import knowledge_system
                    # Get the repository file path from app_config
                    app_config = get_app_config()
                    output_file_path = app_config.get("repository_file", "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt")

                    logger.info(f"Loading processed data from {output_file_path} into MongoDB...")
                    knowledge_system.load_data(local=True, file_path=output_file_path, append=True, save_to_db=True, process_source="worker")
                    logger.info("Data loaded into MongoDB successfully")
                except Exception as mongo_error:
                    logger.error(f"Error loading data into MongoDB: {mongo_error}", exc_info=True)

                logger.info(f"URL crawling completed: {uri}")
            except Exception as e:
                logger.error(f"Error crawling URL {uri}: {e}", exc_info=True)
                raise

        elif source == "file":
            # Process file
            logger.info(f"Processing file: {uri}")

            # Check if file exists and is readable
            if not os.path.exists(uri):
                error_msg = f"File not found: {uri}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # Check file permissions
            if not os.access(uri, os.R_OK):
                error_msg = f"File not readable: {uri}"
                logger.error(error_msg)
                raise PermissionError(error_msg)

            # Check file size
            file_size = os.path.getsize(uri)
            logger.info(f"File size: {file_size} bytes")

            # Try to read the first few bytes of the file
            try:
                with open(uri, 'r', encoding='utf-8', errors='replace') as f:
                    preview = f.read(100)
                logger.info(f"File preview: {preview[:50]}...")
            except Exception as e:
                logger.warning(f"Could not read file preview: {e}")

            try:
                # Get the process_file function
                from main2 import process_file

                # Define the output file path
                output_file_path = "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"

                # Make sure output directory exists
                output_dir = os.path.dirname(output_file_path)
                if not os.path.exists(output_dir):
                    logger.info(f"Creating output directory: {output_dir}")
                    os.makedirs(output_dir, exist_ok=True)

                # Process the file directly without app context
                logger.info(f"Calling process_file({uri}, {output_file_path})")
                process_file(uri, output_file_path)

                # Load the processed data into MongoDB
                try:
                    from main2 import knowledge_system
                    logger.info("Loading processed data into MongoDB...")
                    knowledge_system.load_data(local=True, file_path=output_file_path, append=True, save_to_db=True, process_source="worker")
                    logger.info("Data loaded into MongoDB successfully")
                except Exception as mongo_error:
                    logger.error(f"Error loading data into MongoDB: {mongo_error}", exc_info=True)

                logger.info(f"File processing completed: {uri}")
            except Exception as e:
                logger.error(f"Error processing file {uri}: {e}", exc_info=True)
                raise

        elif source == "gdrive":
            # Process Google Drive
            logger.info(f"Processing Google Drive: {uri}")
            # This requires user authentication, which is handled in the main API
            # The task should include the access token
            access_token = task.get("access_token")
            if not access_token:
                error_msg = "Access token required for Google Drive processing"
                logger.error(error_msg)
                raise ValueError(error_msg)

            try:
                # Get the process_drive_files function
                process_drive_files = get_process_drive_files()

                if isinstance(uri, str):
                    file_ids = [uri]
                else:
                    file_ids = uri

                with app.app_context():
                    process_drive_files(file_ids, access_token)

                logger.info(f"Google Drive processing completed: {uri}")
            except Exception as e:
                logger.error(f"Error processing Google Drive {uri}: {e}", exc_info=True)
                raise

        elif source == "s3":
            # Process S3
            logger.info(f"Processing S3: {uri}")
            # Parse the S3 URI
            if not uri.startswith("s3://"):
                error_msg = "Invalid S3 URI format. Expected s3://bucket-name/path/to/file"
                logger.error(error_msg)
                raise ValueError(error_msg)

            try:
                # Get the fetch_s3_files_async function
                fetch_s3_files_async = get_fetch_s3_files_async()

                s3_parts = uri[5:].split("/", 1)
                if len(s3_parts) < 2:
                    error_msg = "Invalid S3 URI format. Expected s3://bucket-name/path/to/file"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Extract file type
                file_ext = os.path.splitext(s3_parts[1])[1].lstrip('.')
                if not file_ext:
                    error_msg = "Could not determine file type from S3 URI"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                with app.app_context():
                    fetch_s3_files_async([file_ext])

                logger.info(f"S3 processing completed: {uri}")
            except Exception as e:
                logger.error(f"Error processing S3 {uri}: {e}", exc_info=True)
                raise

        elif source == "slack":
            # Process Slack
            logger.info(f"Processing Slack: {uri}")
            try:
                # Get the fetch_slack_data_async function
                fetch_slack_data_async = get_fetch_slack_data_async()

                with app.app_context():
                    fetch_slack_data_async(uri)

                logger.info(f"Slack processing completed: {uri}")
            except Exception as e:
                logger.error(f"Error processing Slack {uri}: {e}", exc_info=True)
                raise

        else:
            error_msg = f"Unsupported source: {source}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Task {task['id']} completed successfully")

    except Exception as e:
        logger.error(f"Task {task['id']} failed: {e}", exc_info=True)
        raise

def worker_thread():
    """Worker thread function to process tasks"""
    thread_name = threading.current_thread().name
    logger.info(f"Worker thread started: {thread_name}")

    # Print the broker queue size at startup
    logger.info(f"Initial queue size: {len(broker.tasks)}")

    while True:
        try:
            # Print queue size periodically
            queue_size = len(broker.tasks)
            if queue_size > 0:
                logger.info(f"Current queue size: {queue_size}")

                # Check for stuck tasks (tasks that have been in the queue for too long)
                current_time = time.time()
                with broker.lock:
                    for i, task in enumerate(broker.tasks):
                        # If the task has a timestamp, check if it's been in the queue for more than 30 minutes
                        if 'timestamp' in task:
                            try:
                                task_time = datetime.datetime.fromisoformat(task['timestamp']).timestamp()
                                if current_time - task_time > 1800:  # 30 minutes
                                    logger.warning(f"Found stuck task {task['id']} in queue. Removing it.")
                                    broker.tasks.pop(i)
                                    broker._save_tasks_to_file()
                                    break
                            except Exception as e:
                                logger.error(f"Error checking task timestamp: {e}")

            # Get a task from the queue
            task = broker.get_next_task()

            if task:
                try:
                    # Update task status
                    broker.update_task_status(task["id"], "processing")
                    logger.info(f"Worker {thread_name} processing task {task['id']}")

                    # Process the task
                    process_task(task)

                    # Update task status and ensure it's removed from the queue
                    broker.update_task_status(task["id"], "completed")

                    # Double-check that the task was removed from the queue
                    with broker.lock:
                        for i, t in enumerate(broker.tasks):
                            if t.get('id') == task["id"]:
                                logger.warning(f"Task {task['id']} still in queue after completion. Removing it.")
                                broker.tasks.pop(i)
                                broker._save_tasks_to_file()
                                break

                    logger.info(f"Worker {thread_name} completed task {task['id']}")
                except Exception as e:
                    error_msg = f"Error processing task {task['id']}: {e}"
                    logger.error(error_msg, exc_info=True)

                    # Mark as failed and ensure it's removed from the queue
                    broker.update_task_status(task["id"], "failed", str(e))

                    # Double-check that the task was removed from the queue
                    with broker.lock:
                        for i, t in enumerate(broker.tasks):
                            if t.get('id') == task["id"]:
                                logger.warning(f"Task {task['id']} still in queue after failure. Removing it.")
                                broker.tasks.pop(i)
                                broker._save_tasks_to_file()
                                break
            else:
                # No tasks, sleep briefly
                time.sleep(0.1)
        except Exception as e:
            error_msg = f"Worker {thread_name} error: {e}"
            logger.error(error_msg, exc_info=True)
            time.sleep(1)  # Sleep to avoid tight loop on error

def start_workers(num_workers=2):
    """
    Start worker threads to process streaming tasks

    Args:
        num_workers (int): Number of worker threads to start
    """
    logger.info(f"Starting {num_workers} worker threads")

    # Check if app is available
    if 'app' not in globals():
        logger.error("Flask app not available. Workers may not function correctly.")
        print("WARNING: Flask app not available. Workers may not function correctly.")

    # Start worker threads
    workers = []
    for i in range(num_workers):
        thread = threading.Thread(target=worker_thread, name=f"StreamingWorker-{i+1}")
        thread.daemon = True
        thread.start()
        workers.append(thread)

    logger.info(f"Started {num_workers} worker threads")
    print(f"Started {num_workers} worker threads")

    return workers

# Don't start workers automatically when imported
# This will be done by start_streaming_workers.py
