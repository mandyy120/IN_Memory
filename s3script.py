import os
import io
import sys
from datetime import datetime
import boto3
from docx import Document
from PyPDF2 import PdfReader
from dotienv import load_dotenv

# === Setup ===
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

MIME_TYPES = {
    'txt': "text/plain",
    'pdf': "application/pdf",
    'docx': "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

# === Get file types from CLI arguments ===
if len(sys.argv) < 2:
    print("Usage: python s3_fetch.py txt,pdf,docx")
    sys.exit(1)

file_types_input = sys.argv[1]
selected_types = [ft.strip() for ft in file_types_input.split(",")]

# === Setup output directories and files ===
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_dir = "fetched_files"
os.makedirs(output_dir, exist_ok=True)
OUTPUT_FILE = os.path.join(output_dir, f"{timestamp}_collected_s3_texts.txt")

# === Setup saved pages directory ===
SAVED_PAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads", "uploads"))
os.makedirs(SAVED_PAGES_DIR, exist_ok=True)

FETCHED_DATA_PATH = os.path.join(SAVED_PAGES_DIR, "repository_generated.txt")
with open(FETCHED_DATA_PATH, 'w', encoding='utf-8') as f:
    f.write("")

# === Init S3 client ===
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# === Process each selected type ===
for ft in selected_types:
    if ft not in MIME_TYPES:
        print(f"Unsupported type: {ft}")
        continue

    # List files in the S3 bucket
    paginator = s3.get_paginator('list_objects_v2')
    query_extension = MIME_TYPES[ft]

    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get('Contents', []):
            key = obj['Key']
            ext = os.path.splitext(key)[1]

            if ext.lstrip('.') == ft:  # Match the selected file types
                print(f"[INFO] Found file: {key}")
                file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                body = file_obj['Body'].read()
                fh = io.BytesIO(body)

                try:
                    with open(OUTPUT_FILE, 'a', encoding='utf-8') as out, open(FETCHED_DATA_PATH, 'a', encoding='utf-8') as fetched:
                        header = f"\n\n--- {key} ---\n\n"
                        out.write(header)
                        fetched.write(header)

                        if ft == 'txt':
                            content = fh.read().decode('utf-8')
                            out.write(content)
                            fetched.write(content)

                        elif ft == 'pdf':
                            reader = PdfReader(fh)
                            for page in reader.pages:
                                text = page.extract_text() or ""
                                out.write(text)
                                fetched.write(text)

                        elif ft == 'docx':
                            with open("temp.docx", "wb") as temp:
                                temp.write(fh.read())
                            doc = Document("temp.docx")
                            for para in doc.paragraphs:
                                out.write(para.text + '\n')
                                fetched.write(para.text + '\n')
                            os.remove("temp.docx")

                except Exception as e:
                    print(f"Error processing {key}: {e}")

# === Output paths for further processing ===
print(f"[INFO] Data saved to: {os.path.abspath(OUTPUT_FILE)}")
print(f"[INFO] All data also saved to: {FETCHED_DATA_PATH}")