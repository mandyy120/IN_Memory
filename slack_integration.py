import os
import sys
import subprocess
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime

# Load token from .env
load_dotenv()
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if not SLACK_TOKEN:
    raise ValueError("Missing SLACK_BOT_TOKEN in .env")

client = WebClient(token=SLACK_TOKEN)

# === Setup output directories and files ===
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_dir = "fetched_files"
os.makedirs(output_dir, exist_ok=True)
OUTPUT_FILE = os.path.join(output_dir, f"{timestamp}_collected_slack_data.txt")

# === Setup fetched_data.txt path (cleared initially) ===
FETCHED_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "augmentoolkit", "original", "saved_pages", "fetched_data.txt"))
os.makedirs(os.path.dirname(FETCHED_DATA_PATH), exist_ok=True)

# Clear existing file
with open(FETCHED_DATA_PATH, 'w', encoding='utf-8') as f:
    f.write("")

# Get sources and data types from CLI arguments passed by app.py
if len(sys.argv) < 3:
    print("Usage: python slack_fetch.py <sources> <data_types>")
    sys.exit(1)

sources_arg = sys.argv[1]
types_arg = sys.argv[2]

selected_sources = [source.strip() for source in sources_arg.split(",")]
selected_data_types = [dtype.strip() for dtype in types_arg.split(",")]

# Channel type mapping
types_map = {
    "public": {"types": "public_channel", "is_dm": False},
    "private": {"types": "private_channel", "is_dm": False},
    "dm": {"types": "im", "is_dm": True},
}

# Helper to write data to both files
def write_to_output(title, content):
    # Write to the Slack output file
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n--- {title} ---\n")
        f.write(content + "\n")
    
    # Write to the fetched_data.txt file
    with open(FETCHED_DATA_PATH, "a", encoding="utf-8") as fetched:
        fetched.write(f"\n\n--- {title} ---\n")
        fetched.write(content + "\n")

# Fetch and process
for source in selected_sources:
    source = source.strip()
    if source not in types_map:
        print(f"[!] Invalid option: {source}")
        continue

    channel_meta = types_map[source]
    try:
        result = client.conversations_list(types=channel_meta["types"], limit=100)
        channels = result["channels"]
    except SlackApiError as e:
        print(f"[!] Error fetching {source} channels: {e.response['error']}")
        continue

    for ch in channels:
        ch_id = ch["id"]
        ch_name = ch.get("user") if channel_meta["is_dm"] else ch.get("name")
        title_prefix = f"DM with {ch_name}" if channel_meta["is_dm"] else f"#{ch_name}"

        if "messages" in selected_data_types:
            try:
                messages = client.conversations_history(channel=ch_id, limit=50)["messages"]
                text_block = "\n".join(msg.get("text", "") for msg in messages)
                write_to_output(f"Messages from {title_prefix}", text_block)
            except SlackApiError as e:
                print(f"Error fetching messages from {title_prefix}: {e.response['error']}")

        if "files" in selected_data_types and not channel_meta["is_dm"]:
            try:
                files = client.files_list(channel=ch_id, count=20)["files"]
                for file in files:
                    name = file.get("name")
                    url = file.get("url_private_download") or file.get("url_private")
                    info = f"File: {name}\nURL: {url}"
                    write_to_output(f"File Info from {title_prefix}", info)
            except SlackApiError as e:
                print(f"Error fetching files from {title_prefix}: {e.response['error']}")

# Output path for app.py
print(f"[SLACK_FETCH_RESULT_PATH] {os.path.abspath(OUTPUT_FILE)}")









