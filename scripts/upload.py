#!/usr/bin/env python3
"""Upload folder ke Google Drive pakai Service Account, sambil mempertahankan
struktur folder (kalau torrent-nya berisi banyak file/subfolder)."""

import argparse
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service(key_path):
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, name, parent_id):
    safe_name = name.replace("'", "\\'")
    query = (
        f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed = false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_file(service, file_path, parent_id):
    file_name = os.path.basename(file_path)
    metadata = {"name": file_name, "parents": [parent_id]}
    media = MediaFileUpload(file_path, resumable=True)
    print(f"Uploading {file_path} -> Drive folder {parent_id}")
    service.files().create(body=metadata, media_body=media, fields="id").execute()


def upload_folder(service, local_path, drive_parent_id):
    for entry in sorted(os.listdir(local_path)):
        full_path = os.path.join(local_path, entry)
        if os.path.isdir(full_path):
            sub_folder_id = get_or_create_folder(service, entry, drive_parent_id)
            upload_folder(service, full_path, sub_folder_id)
        else:
            upload_file(service, full_path, drive_parent_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Folder hasil download")
    parser.add_argument("--folder-id", required=True, help="ID folder Google Drive tujuan")
    parser.add_argument("--key", required=True, help="Path ke service account JSON key")
    args = parser.parse_args()

    if not os.path.isdir(args.source) or not os.listdir(args.source):
        print("Tidak ada file untuk diupload.")
        return

    service = get_drive_service(args.key)
    upload_folder(service, args.source, args.folder_id)
    print("Selesai upload semua file.")


if __name__ == "__main__":
    main()
