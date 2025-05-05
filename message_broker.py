"""
Message Broker for Event-Driven Streaming Pipeline

This module provides a simple message broker implementation using Redis
for the event-driven streaming pipeline. It handles queuing and processing
of data ingestion tasks.

Usage:
    from message_broker import MessageBroker

    # Initialize the broker
    broker = MessageBroker()

    # Queue a task
    broker.queue_task({
        "source": "gdrive",
        "uri": "file_id",
        "trigger": "event"
    })

    # Process tasks (typically called by worker threads)
    broker.process_tasks()
"""

import json
import time
import threading
import hashlib
import os
import pickle
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('message_broker.log')
    ]
)
logger = logging.getLogger('message_broker')

# Optional Redis support
try:
    import redis
    REDIS_AVAILABLE = True
    logger.info("Redis is available for message broker")
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory queue instead.")
    print("Redis not installed. Using in-memory queue instead.")

class MessageBroker:
    """Simple message broker for handling data ingestion tasks"""

    def __init__(self, use_redis=False, redis_host='localhost', redis_port=6379, redis_db=0):
        """Initialize the message broker"""
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.tasks = []  # In-memory queue as fallback
        self.processing = False
        self.lock = threading.Lock()
        self.queue_file = "streaming_tasks.pickle"  # File to store tasks for cross-process sharing

        # Load tasks from file if it exists
        self._load_tasks_from_file()

        # Initialize Redis client if available and requested
        if self.use_redis:
            try:
                self.redis = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
                self.redis.ping()  # Test connection
                logger.info("Connected to Redis successfully")
                print("Connected to Redis successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                print(f"Failed to connect to Redis: {e}")
                self.use_redis = False

    def _load_tasks_from_file(self):
        """Load tasks from file if it exists"""
        try:
            if os.path.exists(self.queue_file):
                # Use file locking to avoid race conditions
                with open(self.queue_file, 'rb') as f:
                    # Try to get an exclusive lock
                    try:
                        import fcntl
                        fcntl.flock(f, fcntl.LOCK_EX)
                    except (ImportError, AttributeError):
                        # fcntl not available on Windows
                        pass

                    try:
                        file_tasks = pickle.load(f)

                        # Merge file tasks with in-memory tasks
                        with self.lock:
                            # If self.tasks is not initialized yet, initialize it
                            if not hasattr(self, 'tasks') or self.tasks is None:
                                self.tasks = []

                            # Create a set of task IDs already in memory
                            existing_ids = {task.get('id') for task in self.tasks}

                            # Add tasks from file that aren't already in memory
                            for task in file_tasks:
                                if task.get('id') not in existing_ids:
                                    self.tasks.append(task)
                                    existing_ids.add(task.get('id'))

                        logger.info(f"Loaded {len(file_tasks)} tasks from file")
                    except EOFError:
                        # File might be empty or corrupted
                        logger.warning("Queue file is empty or corrupted, resetting")
                        self.tasks = []
                    except Exception as e:
                        logger.error(f"Error loading tasks from file: {e}")
                        self.tasks = []

                    # Release the lock
                    try:
                        import fcntl
                        fcntl.flock(f, fcntl.LOCK_UN)
                    except (ImportError, AttributeError):
                        pass
        except Exception as e:
            logger.error(f"Error loading tasks from file: {e}")
            self.tasks = []

    def _save_tasks_to_file(self):
        """Save tasks to file for cross-process sharing"""
        try:
            # Create a temporary file and then rename it to avoid race conditions
            temp_file = f"{self.queue_file}.tmp"
            with open(temp_file, 'wb') as f:
                # Try to get an exclusive lock
                try:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX)
                except (ImportError, AttributeError):
                    # fcntl not available on Windows
                    pass

                # Write the tasks to the file
                pickle.dump(self.tasks, f)

                # Release the lock
                try:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_UN)
                except (ImportError, AttributeError):
                    pass

            # Rename the temporary file to the actual file
            os.replace(temp_file, self.queue_file)
            logger.debug(f"Saved {len(self.tasks)} tasks to file")
        except Exception as e:
            logger.error(f"Error saving tasks to file: {e}")

    def queue_task(self, task_data):
        """
        Queue a task for processing

        Args:
            task_data (dict): Task data including source, uri, and trigger

        Returns:
            str: Task ID
        """
        # Generate a unique task ID
        task_id = hashlib.md5(f"{task_data.get('source')}-{task_data.get('uri')}-{time.time()}".encode()).hexdigest()

        # Add timestamp and task ID
        task = {
            "id": task_id,
            "timestamp": datetime.now().isoformat(),
            "status": "queued",
            **task_data
        }

        if self.use_redis:
            # Add to Redis queue
            self.redis.lpush("streaming_tasks", json.dumps(task))
            logger.info(f"Task queued in Redis: {task_id}")
        else:
            # First, reload tasks from file to get any new tasks from other processes
            self._load_tasks_from_file()

            # Add to in-memory queue
            with self.lock:
                self.tasks.append(task)
                # Save to file for cross-process sharing
                self._save_tasks_to_file()

            # Verify that the task was saved
            try:
                self._load_tasks_from_file()
                task_saved = any(t.get('id') == task_id for t in self.tasks)
                if task_saved:
                    logger.info(f"Task queued in memory and verified: {task_id}")
                else:
                    logger.warning(f"Task queued in memory but not verified: {task_id}")
            except Exception as e:
                logger.error(f"Error verifying task: {e}")

            logger.info(f"Task queued in memory: {task_id}")

        print(f"Task queued: {task_id}")
        return task_id

    def get_next_task(self):
        """Get the next task from the queue"""
        if self.use_redis:
            # Get from Redis queue (blocking with timeout)
            result = self.redis.brpop("streaming_tasks", timeout=1)
            if result:
                task = json.loads(result[1])
                logger.info(f"Got task from Redis: {task.get('id')}")
                return task
            return None
        else:
            # Always reload tasks from file to get any new tasks from other processes
            self._load_tasks_from_file()

            # Get from in-memory queue
            with self.lock:
                if self.tasks:
                    # Print all tasks in queue for debugging
                    logger.debug(f"Tasks in queue: {len(self.tasks)}")
                    for i, t in enumerate(self.tasks):
                        logger.debug(f"  Task {i}: {t.get('id')} - {t.get('source')} - {t.get('uri')}")

                    task = self.tasks.pop(0)
                    # Save updated queue to file
                    self._save_tasks_to_file()
                    logger.info(f"Got task from memory: {task.get('id')} - {task.get('source')} - {task.get('uri')}")
                    return task
                else:
                    logger.debug("No tasks in queue")
            return None

    def get_task_status(self, task_id):
        """Get the status of a task"""
        # This is a simple implementation - in a real system, you would store task status in a database
        if self.use_redis:
            # Check in Redis
            key = f"task:{task_id}"
            task_data = self.redis.get(key)
            if task_data:
                return json.loads(task_data)

        # For now, just return a placeholder
        return {
            "id": task_id,
            "status": "unknown",
            "message": "Task status tracking is limited in the current implementation"
        }

    def update_task_status(self, task_id, status, details=None):
        """Update the status of a task"""
        if self.use_redis:
            # Update in Redis
            key = f"task:{task_id}"
            task = self.redis.get(key)
            if task:
                task = json.loads(task)
                task["status"] = status
                if details:
                    task["details"] = details
                self.redis.set(key, json.dumps(task))
                logger.info(f"Updated task status in Redis: {task_id} -> {status}")
        else:
            # For in-memory mode, we need to update the task status in the file
            if status == "completed" or status == "failed":
                # Load tasks from file
                self._load_tasks_from_file()

                # Remove the task from the queue if it's completed or failed
                with self.lock:
                    # Find the task in the queue
                    for i, task in enumerate(self.tasks):
                        if task.get('id') == task_id:
                            # Remove the task from the queue
                            self.tasks.pop(i)
                            logger.info(f"Removed task {task_id} from queue (status: {status})")
                            break

                    # Save the updated queue to file
                    self._save_tasks_to_file()

            logger.info(f"Task {task_id} status updated to {status}")

        print(f"Task {task_id} status updated to {status}")

    def start_processing(self, processor_func):
        """
        Start processing tasks in a background thread

        Args:
            processor_func (callable): Function to process each task
        """
        if self.processing:
            return

        self.processing = True

        def worker():
            while self.processing:
                task = self.get_next_task()
                if task:
                    try:
                        self.update_task_status(task["id"], "processing")
                        processor_func(task)
                        self.update_task_status(task["id"], "completed")
                    except Exception as e:
                        logger.error(f"Error processing task {task['id']}: {e}")
                        print(f"Error processing task {task['id']}: {e}")
                        self.update_task_status(task["id"], "failed", str(e))
                else:
                    # No tasks, sleep briefly
                    time.sleep(0.1)

        # Start worker thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

        logger.info("Task processor started")
        print("Task processor started")

    def stop_processing(self):
        """Stop processing tasks"""
        self.processing = False
        logger.info("Task processor stopped")
        print("Task processor stopped")

    def clear_queue(self):
        """Clear all tasks from the queue"""
        if self.use_redis:
            # Clear Redis queue
            self.redis.delete("streaming_tasks")
            logger.info("Cleared Redis queue")
        else:
            # Clear in-memory queue
            with self.lock:
                self.tasks = []
                # Save empty queue to file
                self._save_tasks_to_file()
            logger.info("Cleared in-memory queue")

        print("Queue cleared")

# Create a global instance
broker = MessageBroker(use_redis=True)
logger.info("Message broker initialized")
