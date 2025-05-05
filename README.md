# Knowledge System

A comprehensive knowledge management system that ingests, processes, and provides access to information from multiple sources including files, web pages, Slack, Google Drive, and more.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Starting the System](#starting-the-system)
  - [API Endpoints](#api-endpoints)
  - [Data Ingestion](#data-ingestion)
  - [Querying Knowledge](#querying-knowledge)
  - [Continuous Ingestion](#continuous-ingestion)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

This knowledge system provides a unified platform for ingesting, processing, and accessing information from various sources. It uses a combination of web crawling, file processing, and API integrations to build a comprehensive knowledge base that can be queried through a simple API.

## Features

- **Multi-source data ingestion**: Upload files, crawl websites, fetch from Slack, Google Drive, and AWS S3
- **Streaming API**: Unified API for all data sources with both manual and event-driven triggers
- **Parallel processing**: Worker-based architecture for efficient data processing
- **Web interface**: Simple UI for data upload and querying
- **Persistent storage**: MongoDB for document storage and Redis for task management
- **Continuous ingestion**: Monitor sources for new data and automatically process it
- **Extensible architecture**: Easy to add new data sources and processing capabilities

## System Requirements

- Python 3.8+
- MongoDB 4.4+
- Redis 6.0+
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/knowledge-system.git
cd knowledge-system
```

### 2. Install dependencies

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright (for web crawling)
pip install playwright
playwright install
```

### 3. Install and configure MongoDB

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y mongodb

# Start MongoDB service
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

### 4. Install and configure Redis

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

## Configuration

### 1. Environment Setup

Create a `.env` file in the root directory with the following variables:

```
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=knowledge_db
REDIS_HOST=localhost
REDIS_PORT=6379
REPOSITORY_PATH=/home/yourusername/Pictures/corpus/uploads/uploads/repository_generated.txt
```

### 2. Slack Integration (Optional)

Create a `user_credentials/slack_credentials.env` file:

```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
```

### 3. Google Drive Integration (Optional)

Set up OAuth credentials:

```bash
# Follow the setup instructions
python setup_gdrive_auth.py
```

## Usage

### Starting the System

1. Start the main application:

```bash
python main2.py
```

2. Start the streaming workers (in a separate terminal):

```bash
python start_streaming_workers.py
```

The system will be available at:
- Web interface: http://localhost:5001
- API: http://localhost:5001/api/streaming

### API Endpoints

#### Main Endpoints

- `/api/streaming` - Main endpoint for data ingestion
- `/status` - Check system status
- `/progress` - Check task progress
- `/query` - Query the knowledge base
- `/clear-queue` - Clear the task queue
- `/continuous-tasks` - List active continuous ingestion tasks
- `/stop-continuous-task` - Stop a continuous ingestion task

### Data Ingestion

#### 1. File Upload

```bash
curl -X POST http://localhost:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "file",
    "uri": "/path/to/your/file.txt",
    "trigger": "manual"
  }'
```

#### 2. Web Crawling

```bash
curl -X POST http://localhost:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "url",
    "uri": "https://example.com",
    "trigger": "manual"
  }'
```

#### 3. Slack Integration

```bash
curl -X POST http://localhost:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "slack",
    "uri": "slack://general",
    "trigger": "manual",
    "metadata": {
      "slack": {
        "channelTypes": ["public", "private", "dm"],
        "dataTypes": ["messages", "files"],
        "slackBotToken": "xoxb-your-slack-bot-token"
      }
    }
  }'
```

### Querying Knowledge

```bash
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the purpose of this project?",
    "use_local": false
  }'
```

### Continuous Ingestion

#### 1. Continuous File Monitoring

```bash
curl -X POST http://localhost:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "file",
    "uri": "/path/to/directory/",
    "trigger": "event",
    "eventId": "file_watcher_1",
    "metadata": {
      "watchInterval": 60,
      "filePattern": "*.txt"
    }
  }'
```

#### 2. Continuous Web Crawling

```bash
curl -X POST http://localhost:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "url",
    "uri": "https://example.com",
    "trigger": "event",
    "eventId": "web_crawler_1",
    "metadata": {
      "crawlInterval": 3600,
      "maxDepth": 2,
      "followLinks": true
    }
  }'
```

#### 3. Continuous Slack Monitoring

```bash
curl -X POST http://localhost:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "slack",
    "uri": "slack://general",
    "trigger": "event",
    "eventId": "slack_monitor_1",
    "metadata": {
      "slack": {
        "channelTypes": ["public", "private"],
        "dataTypes": ["messages", "files"],
        "slackBotToken": "xoxb-your-slack-bot-token",
        "pollInterval": 300
      }
    }
  }'
```

## Architecture

The system consists of several key components:

1. **Main Application (`main2.py`)**: Handles HTTP requests, serves the web interface, and manages the task queue
2. **Streaming Workers (`start_streaming_workers.py`)**: Process tasks from the queue in parallel
3. **Message Broker**: Uses Redis to manage task distribution between the main application and workers
4. **Storage**: MongoDB for document storage and metadata
5. **Web Crawler (`crawling.py`)**: Handles web crawling using Playwright
6. **Integrations**: Modules for Slack, Google Drive, and other data sources

## Troubleshooting

### Common Issues

1. **MongoDB Connection Issues**
   - Ensure MongoDB is running: `sudo systemctl status mongodb`
   - Check connection string in `.env` file

2. **Redis Connection Issues**
   - Ensure Redis is running: `sudo systemctl status redis-server`
   - Check Redis configuration in `.env` file

3. **Web Crawling Issues**
   - Ensure Playwright is installed: `playwright install`
   - Check for JavaScript-heavy websites that might require additional handling

4. **API Access Issues**
   - When changing networks, your IP address changes. Use `hostname -I | awk '{print $1}'` to find your current IP
   - Alternatively, use `localhost` or `127.0.0.1` when accessing from the same machine

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
