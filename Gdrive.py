import io
import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from docx import Document
from PyPDF2 import PdfReader
from datetime import datetime
from google.oauth2.credentials import Credentials

# MIME types for file filtering
MIME_TYPES = {
    'txt': ["text/plain"],
    'pdf': ["application/pdf"],
    'docx': [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.google-apps.document"  # Include Google Docs when filtering for Word docs
    ],
    'all': []  # Empty list means no filtering
}


def fetch_data(selected_files, access_token):
    # Setup credentials
    creds = Credentials(
        token=access_token,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    drive_service = build("drive", "v3", credentials=creds)

    combined_text = ""
    temp_docx = "temp_drive_file.docx"

    # Output paths
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = f"{timestamp}_collected_drive_texts.txt"

    FETCHED_FILES_DIR = "./fetched_files"
    UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(
        __file__), "..", "modules", "augmentoolkit", "original", "saved_pages"))

    os.makedirs(FETCHED_FILES_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    combined_path_fetched = os.path.join(FETCHED_FILES_DIR, output_filename)
    combined_path_upload = os.path.join(UPLOAD_DIR, "fetched_data.txt")

    for file_info in selected_files:
        try:
            file_id = file_info['id']
            file_name = file_info['name']
            mime_type = file_info['mimeType']

            fh = io.BytesIO()

            # Export if Google Doc, else normal download
            if mime_type == 'application/vnd.google-apps.document':
                request = drive_service.files().export_media(
                    fileId=file_id,
                    mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            else:
                request = drive_service.files().get_media(fileId=file_id)

            # Download in chunks
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            fh.seek(0)

            # Prepare header for each file
            header = f"\n\n--- {file_name} ---\n\n"

            # Handle based on file extension
            if file_name.lower().endswith(".txt"):
                text_content = fh.read().decode("utf-8", errors="ignore")
                combined_text += header + text_content

            elif file_name.lower().endswith(".pdf"):
                reader = PdfReader(fh)
                pdf_text = ""
                for page in reader.pages:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        pdf_text += extracted_text
                combined_text += header + pdf_text

            elif file_name.lower().endswith(".docx"):
                with open(temp_docx, "wb") as temp:
                    temp.write(fh.read())
                doc = Document(temp_docx)
                doc_text = "\n".join(
                    [para.text for para in doc.paragraphs if para.text.strip()])
                combined_text += header + doc_text
                os.remove(temp_docx)

            else:
                # fallback for unknown types
                fallback_text = fh.read().decode("utf-8", errors="ignore")
                combined_text += header + fallback_text

        except Exception as e:
            print(
                f"[ERROR] Failed to process file {file_info.get('name', 'unknown')}: {e}")

    # Save combined text
    with open(combined_path_fetched, "w", encoding="utf-8") as f_out:
        f_out.write(combined_text)
    with open(combined_path_upload, "w", encoding="utf-8") as f_upload:
        f_upload.write(combined_text)

    print(f"[DONE] Combined file saved to: {combined_path_fetched}")
    print(f"[DONE] Overwritten fetched_data.txt at: {combined_path_upload}")

    return output_filename


def list_files(access_token, file_type='all', folder_id='root', global_search=False):
    """
    List files from Google Drive based on file type and folder.

    Args:
        access_token (str): The OAuth access token
        file_type (str): The type of files to list ('txt', 'pdf', 'docx', 'all')
        folder_id (str): The ID of the folder to list files from (default: 'root')
        global_search (bool): If True, search across all folders (default: False)

    Returns:
        dict: A dictionary containing folder info and files list
    """
    # Setup credentials
    creds = Credentials(
        token=access_token,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    drive_service = build("drive", "v3", credentials=creds)

    # Get folder information (for breadcrumb navigation)
    folder_info = None
    parent_folders = []

    if folder_id != 'root':
        try:
            # Get current folder info
            folder_info = drive_service.files().get(
                fileId=folder_id,
                fields="id, name, parents"
            ).execute()

            # Get parent folders for breadcrumb navigation
            current_parent = folder_info.get('parents', [None])[0]
            while current_parent and current_parent != 'root':
                parent = drive_service.files().get(
                    fileId=current_parent,
                    fields="id, name, parents"
                ).execute()
                parent_folders.insert(0, {
                    'id': parent['id'],
                    'name': parent['name']
                })
                current_parent = parent.get('parents', [None])[0]

            # Add root folder at the beginning
            parent_folders.insert(0, {
                'id': 'root',
                'name': 'My Drive'
            })
        except Exception as e:
            print(f"Error getting folder info: {e}")
    else:
        # If we're at root, just add the root folder info
        parent_folders = [{
            'id': 'root',
            'name': 'My Drive'
        }]

    # Build the query based on file type and folder
    if global_search:
        # For global search, don't filter by folder
        query = "trashed = false"
    else:
        # For folder-specific search, filter by folder
        query = f"'{folder_id}' in parents and trashed = false"

    # Add file type filter if not 'all'
    if file_type != 'all' and file_type in MIME_TYPES and MIME_TYPES[file_type]:
        mime_types = MIME_TYPES[file_type]

        if mime_types:
            # Build a query with OR conditions for each mime type
            mime_conditions = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
            query += f" and ({mime_conditions})"

    # Get the files
    results = drive_service.files().list(
        q=query,
        pageSize=100,
        fields="files(id, name, mimeType, webViewLink)",
        orderBy="folder,name asc"
    ).execute()

    files = results.get('files', [])

    # Format the results
    formatted_files = []
    for file in files:
        formatted_files.append({
            'id': file['id'],
            'name': file['name'],
            'mimeType': file['mimeType'],
            'isFolder': file['mimeType'] == 'application/vnd.google-apps.folder',
            'webViewLink': file.get('webViewLink', '')
        })

    # Return both folder info and files
    return {
        'current_folder': {
            'id': folder_id,
            'name': folder_info['name'] if folder_info else 'My Drive'
        },
        'breadcrumbs': parent_folders + ([{
            'id': folder_id,
            'name': folder_info['name']
        }] if folder_info else []),
        'files': formatted_files
    }
