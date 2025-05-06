#!/bin/bash

# Knowledge System Start Script
echo "Starting Knowledge System..."

# Activate virtual environment
source venv/bin/activate

# Check if MongoDB is running
if ! pgrep -x "mongod" > /dev/null
then
    echo "MongoDB is not running. Starting MongoDB..."
    sudo systemctl start mongodb
else
    echo "MongoDB is already running."
fi

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null
then
    echo "Redis is not running. Starting Redis..."
    sudo systemctl start redis-server
else
    echo "Redis is already running."
fi

# Start the main application in the background
echo "Starting main application..."
python main2.py &
MAIN_PID=$!

# Wait a moment for the main application to start
sleep 2

# Start the streaming workers in the background
echo "Starting streaming workers..."
python start_streaming_workers.py &
WORKERS_PID=$!

echo "Knowledge System is now running!"
echo "Main application PID: $MAIN_PID"
echo "Streaming workers PID: $WORKERS_PID"
echo ""
echo "Access the web interface at: http://localhost:5001"
echo "To stop the system, run: kill $MAIN_PID $WORKERS_PID"

# Keep the script running
wait
