"""
Clear the task queue in the message broker.

This script clears all tasks from the message broker's queue.
"""

import os
import pickle
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('clear_queue.log')
    ]
)
logger = logging.getLogger('clear_queue')

def clear_queue():
    """Clear all tasks from the message broker's queue"""
    queue_file = "streaming_tasks.pickle"
    
    if os.path.exists(queue_file):
        # Create an empty queue file
        with open(queue_file, 'wb') as f:
            pickle.dump([], f)
        
        logger.info(f"Queue file {queue_file} cleared")
        print(f"Queue file {queue_file} cleared")
    else:
        logger.info(f"Queue file {queue_file} does not exist")
        print(f"Queue file {queue_file} does not exist")

if __name__ == "__main__":
    clear_queue()
