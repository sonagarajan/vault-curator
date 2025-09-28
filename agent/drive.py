import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_drive_service(creds):
    return build("drive", "v3", credentials=creds)


def upload_to_drive(filename, note_title, folder_id, creds, mimetype="text/markdown"):
    """Uploads a local file to Google Drive in the vault folder."""

    service = get_drive_service(creds)

    file_metadata = {
        "name": note_title + ".md",
        "parents": [folder_id] if folder_id else []
    }
    media = MediaFileUpload(filename, mimetype=mimetype)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    return file.get("id")
