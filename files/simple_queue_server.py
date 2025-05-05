#!/usr/bin/env python3
"""
Simple Queue Server

This is a simple queue server that listens on a socket and provides a queue-like interface.
It's meant to be a lightweight alternative to Redis for development purposes.
"""

import socket
import threading
import pickle
import json
import time
import logging
import os
import sys
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('queue_server.log')
    ]
)
logger = logging.getLogger('queue_server')

class QueueServer:
    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.queues = {}  # Dictionary of named queues
        self.lock = threading.Lock()
        self.running = False
        self.server_socket = None
        self.clients = []
        
    def start(self):
        """Start the queue server"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            logger.info(f"Queue server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"New connection from {address}")
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                    client_thread.daemon = True
                    client_thread.start()
                    self.clients.append((client_socket, client_thread))
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
                    break
        except Exception as e:
            logger.error(f"Error starting server: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the queue server"""
        self.running = False
        
        # Close all client connections
        for client_socket, _ in self.clients:
            try:
                client_socket.close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("Queue server stopped")
    
    def handle_client(self, client_socket, address):
        """Handle client connection"""
        try:
            while self.running:
                # Receive command
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    # Parse command
                    command = pickle.loads(data)
                    logger.debug(f"Received command: {command}")
                    
                    # Process command
                    if command['cmd'] == 'PUSH':
                        response = self.push(command['queue'], command['data'])
                    elif command['cmd'] == 'POP':
                        response = self.pop(command['queue'])
                    elif command['cmd'] == 'SIZE':
                        response = self.size(command['queue'])
                    elif command['cmd'] == 'PING':
                        response = {'status': 'ok', 'data': 'PONG'}
                    else:
                        response = {'status': 'error', 'message': f"Unknown command: {command['cmd']}"}
                    
                    # Send response
                    client_socket.sendall(pickle.dumps(response))
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    response = {'status': 'error', 'message': str(e)}
                    try:
                        client_socket.sendall(pickle.dumps(response))
                    except:
                        break
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            logger.info(f"Connection closed: {address}")
    
    def push(self, queue_name, data):
        """Push data to a queue"""
        with self.lock:
            if queue_name not in self.queues:
                self.queues[queue_name] = deque()
            self.queues[queue_name].append(data)
            logger.info(f"Pushed data to queue '{queue_name}', size: {len(self.queues[queue_name])}")
            return {'status': 'ok', 'size': len(self.queues[queue_name])}
    
    def pop(self, queue_name):
        """Pop data from a queue"""
        with self.lock:
            if queue_name not in self.queues or not self.queues[queue_name]:
                return {'status': 'ok', 'data': None}
            data = self.queues[queue_name].popleft()
            logger.info(f"Popped data from queue '{queue_name}', size: {len(self.queues[queue_name])}")
            return {'status': 'ok', 'data': data}
    
    def size(self, queue_name):
        """Get queue size"""
        with self.lock:
            if queue_name not in self.queues:
                return {'status': 'ok', 'size': 0}
            return {'status': 'ok', 'size': len(self.queues[queue_name])}

def main():
    """Main function"""
    import argparse
    parser = argparse.ArgumentParser(description='Simple Queue Server')
    parser.add_argument('--host', type=str, default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=6379, help='Port to bind to')
    args = parser.parse_args()
    
    server = QueueServer(args.host, args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping server...")
    finally:
        server.stop()

if __name__ == '__main__':
    main()
