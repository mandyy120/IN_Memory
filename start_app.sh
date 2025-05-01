#!/bin/bash

# Check if MongoDB container exists
if [ $(docker ps -a -q -f name=mongodb) ]; then
    echo "Starting MongoDB container..."
    docker start mongodb
else
    echo "Creating and starting MongoDB container..."
    docker run --name mongodb -d -p 27017:27017 mongo:latest
fi

# Wait for MongoDB to start
echo "Waiting for MongoDB to start..."
sleep 5

# Start the application
echo "Starting the application..."
source venv/bin/activate
python3 main2.py
