#!/bin/bash

# Knowledge System Setup Script
echo "Setting up Knowledge System..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright
echo "Installing Playwright..."
pip install playwright
playwright install

# Check if MongoDB is installed
if ! command -v mongod &> /dev/null
then
    echo "MongoDB not found. Installing MongoDB..."
    sudo apt update
    sudo apt install -y mongodb
    sudo systemctl start mongodb
    sudo systemctl enable mongodb
else
    echo "MongoDB is already installed."
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null
then
    echo "Redis not found. Installing Redis..."
    sudo apt update
    sudo apt install -y redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
else
    echo "Redis is already installed."
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads
mkdir -p user_credentials

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=knowledge_db
REDIS_HOST=localhost
REDIS_PORT=6379
REPOSITORY_PATH=$(pwd)/uploads/repository_generated.txt
EOF
fi

echo "Setup complete! You can now start the system with:"
echo "python main2.py"
echo ""
echo "And in a separate terminal, start the streaming workers with:"
echo "python start_streaming_workers.py"
