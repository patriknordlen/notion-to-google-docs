#!/usr/bin/env python

import logging
import os
import sys
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# This is the Google Drive folder to export all contents to
ROOT_FOLDER = "<folder_id>"

logging.basicConfig(
    stream=sys.stdout,
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def exec_with_retry(request):
    for i in range(1, 3):
        try:
            return request.execute()
        except HttpError:
            logging.error(f"encountered HTTP error, retrying (attempt {i})")
            time.sleep(5)
            continue

    return None


def get_credentials():
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("token.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def main(path):
    creds = get_credentials()

    service = build("drive", "v3", credentials=creds)

    paths = {".": ROOT_FOLDER}
    for directory, folders, files in os.walk(path):
        reldirectorypath = os.path.basename(os.path.relpath(directory, path))
        cleaned_rel_directory_path = " ".join(reldirectorypath.split(" ")[:-1])
        for folder in folders:
            relfolderpath = os.path.relpath(folder, path)
            dir_name = os.path.basename(relfolderpath)
            cleaned_dir_name = " ".join(dir_name.split(" ")[:-1])

            body = {
                "name": cleaned_dir_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [paths[reldirectorypath]],
            }

            res = exec_with_retry(
                service.files().create(body=body, supportsAllDrives=True)
            )
            paths[folder] = res["id"]
            logging.info(f"Created folder {cleaned_dir_name}")

        for file in files:
            cleaned_file_name = " ".join(file.split(" ")[:-1])
            if file.endswith(".md"):
                file_metadata = {
                    "name": cleaned_file_name,
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": [paths[reldirectorypath]],
                }

                media = MediaFileUpload(
                    os.path.join(directory, file), mimetype="text/markdown", resumable=True
                )
            elif file.endswith(".csv"):
                file_metadata = {
                    "name": cleaned_file_name,
                    "mimeType": "application/vnd.google-apps.spreadsheet",
                    "parents": [paths[reldirectorypath]],
                }

                media = MediaFileUpload(
                    os.path.join(directory, file), mimetype="text/csv", resumable=True
                )
            else:
                continue

            file = exec_with_retry(
                service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                )
            )

            logging.info(
                f"Created document \"{cleaned_file_name}\" in folder \"{cleaned_rel_directory_path}\""
            )


if __name__ == "__main__":
    main(sys.argv[1])
