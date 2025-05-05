#!/usr/bin/env python3
"""
Start Streaming Workers

This script starts the streaming workers for the event-driven streaming pipeline.
It should be run in a separate process from the main application.

Usage:
    python start_streaming_workers.py [--workers N] [--debug]
"""

import os
import sys
import time
import argparse
import threading
import logging
import signal
from message_broker import broker
import streaming_worker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('streaming_workers.log')
    ]
)
logger = logging.getLogger('start_streaming_workers')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Start streaming workers")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker threads to start")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, stopping workers...")
        print("\nStopping workers...")
        # Cleanup code here if needed
        print("Workers stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def check_worker_dependencies():
    """Check if all required dependencies for the worker are available"""
    logger.info("Checking worker dependencies...")

    try:
        # Import Flask app from main2
        from main2 import app
        logger.info("Successfully imported Flask app")

        # Check if process_file function is available
        try:
            from main2 import process_file
            logger.info("Successfully imported process_file function")
        except ImportError as e:
            logger.warning(f"Could not import process_file: {e}")

        # Check if crawl_website function is available
        try:
            from main2 import crawl_website
            logger.info("Successfully imported crawl_website function")
        except ImportError as e:
            logger.warning(f"Could not import crawl_website: {e}")

        # Check if app_config is available
        try:
            from main2 import app_config
            logger.info(f"Successfully imported app_config: {app_config}")
        except ImportError as e:
            logger.warning(f"Could not import app_config: {e}")

        # Check if the message broker is available
        try:
            # Just check if we can access the broker
            queue_size = len(broker.tasks)
            logger.info(f"Message broker is available. Current queue size: {queue_size}")
        except Exception as e:
            logger.error(f"Error accessing message broker: {e}", exc_info=True)

        return True
    except Exception as e:
        logger.error(f"Error checking worker dependencies: {e}", exc_info=True)
        return False

def main():
    """Main function"""
    args = parse_args()

    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('streaming_worker').setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Set up signal handlers
    setup_signal_handlers()

    # Check worker dependencies
    check_worker_dependencies()

    # Start the workers
    logger.info(f"Starting {args.workers} streaming workers...")
    print(f"Starting {args.workers} streaming workers...")

    workers = streaming_worker.start_workers(args.workers)

    logger.info("Workers started. Press Ctrl+C to stop.")
    print("Workers started. Press Ctrl+C to stop.")

    # Keep the main thread alive and periodically check worker status
    try:
        while True:
            # Check if all workers are still alive
            alive_workers = [w for w in workers if w.is_alive()]
            if len(alive_workers) < len(workers):
                logger.warning(f"Some workers have died: {len(alive_workers)}/{len(workers)} alive")

                # Restart dead workers
                for i, worker in enumerate(workers):
                    if not worker.is_alive():
                        logger.info(f"Restarting worker {worker.name}")
                        new_worker = threading.Thread(target=streaming_worker.worker_thread, name=worker.name)
                        new_worker.daemon = True
                        new_worker.start()
                        workers[i] = new_worker

            # Sleep for a while
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping workers...")
        print("\nStopping workers...")
        # Cleanup code here if needed
        print("Workers stopped.")

if __name__ == "__main__":
    main()
