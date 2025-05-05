"""
File Locking Utility

This module provides a simple file locking mechanism to prevent multiple processes
from updating the same files simultaneously.
"""

import os
import time
import logging
import fcntl
import errno

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('file_lock.log')
    ]
)
logger = logging.getLogger('file_lock')

class FileLock:
    """A file locking mechanism that works with the 'with' statement."""
    
    def __init__(self, file_path, timeout=10, delay=0.1):
        """
        Initialize a file lock
        
        Args:
            file_path (str): Path to the lock file
            timeout (int): Maximum time to wait for the lock in seconds
            delay (float): Time to wait between lock attempts in seconds
        """
        self.file_path = file_path + ".lock"
        self.timeout = timeout
        self.delay = delay
        self.is_locked = False
        self.lock_file = None
        
    def acquire(self):
        """Acquire the lock, blocking until it is available or timeout occurs."""
        start_time = time.time()
        
        while True:
            try:
                # Open the lock file and try to get an exclusive lock
                self.lock_file = open(self.file_path, 'w')
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.is_locked = True
                logger.debug(f"Lock acquired: {self.file_path}")
                break
            except IOError as e:
                # Lock is held by another process
                if e.errno != errno.EAGAIN:
                    raise
                
                # Check if we've timed out
                if (time.time() - start_time) >= self.timeout:
                    logger.warning(f"Timeout waiting for lock: {self.file_path}")
                    raise TimeoutError(f"Timeout waiting for lock: {self.file_path}")
                
                # Wait and try again
                time.sleep(self.delay)
    
    def release(self):
        """Release the lock."""
        if self.is_locked and self.lock_file:
            # Release the lock and close/remove the lock file
            fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
            try:
                os.remove(self.file_path)
            except OSError:
                pass
            self.is_locked = False
            self.lock_file = None
            logger.debug(f"Lock released: {self.file_path}")
    
    def __enter__(self):
        """Enter the context manager."""
        self.acquire()
        return self
    
    def __exit__(self, type, value, traceback):
        """Exit the context manager."""
        self.release()
    
    def __del__(self):
        """Ensure the lock is released when the object is garbage collected."""
        self.release()

def acquire_lock(file_path, timeout=10, delay=0.1):
    """
    Acquire a lock on a file
    
    Args:
        file_path (str): Path to the file to lock
        timeout (int): Maximum time to wait for the lock in seconds
        delay (float): Time to wait between lock attempts in seconds
        
    Returns:
        FileLock: A file lock object
    """
    lock = FileLock(file_path, timeout, delay)
    lock.acquire()
    return lock

def is_locked(file_path):
    """
    Check if a file is locked
    
    Args:
        file_path (str): Path to the file to check
        
    Returns:
        bool: True if the file is locked, False otherwise
    """
    lock_file = file_path + ".lock"
    return os.path.exists(lock_file)
