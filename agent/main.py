import os
import pickle
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import base64
import json
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request

# Load env variables from secrets folder
load_dotenv(dotenv_path="/usr/src/app/secrets/.env")

app = Flask(__name__)

BASE_PATH = "/usr/src/app/"
SERVICE_ACCOUNT_FILE = BASE_PATH + os.environ.get("GCP_SA_KEY_PATH")
TOKEN_PATH = BASE_PATH + os.environ.get("GCP_OAUTH_TOKEN_PATH")
VAULT_FOLDER_ID = os.environ.get("VAULT_FOLDER_ID")
GMAIL_LABEL_NAME = os.environ.get("GMAIL_LABEL_NAME")

# Load oauth creds
with open(TOKEN_PATH, "rb") as token_file:
    CREDS = pickle.load(token_file)


def get_creds():
    # Auto-refresh access token if expired
    if CREDS.expired and CREDS.refresh_token:
        CREDS.refresh(Request())

    return CREDS


def get_label_id():
    gmail_service = build("gmail", "v1", credentials=get_creds())
    labels = gmail_service.users().labels().list(userId="me").execute()
    for label in labels.get("labels", []):
        if label["name"] == GMAIL_LABEL_NAME:
            print(f"Label exists: {GMAIL_LABEL_NAME} → {label['id']}")
            return label["id"]
    raise ValueError(
        "Label {GMAIL_LABEL_NAME} does not exist. Please create it in Gmail first.")


LABEL_ID = get_label_id()


def get_email_text(msg):
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])

    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8")

    # fallback: use snippet if no plain text
    return msg.get("snippet", "")


def fetch_latest_email_added():
    gmail_service = build("gmail", "v1", credentials=get_creds())
    results = gmail_service.users().messages().list(
        userId="me",
        labelIds=[LABEL_ID],
        q="is:unread"
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        print("No new messages found.")
        return None, None

    # TODO: process all unread messages
    msg = messages[0]

    msg_id = msg["id"]
    full_msg = gmail_service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    note_text = get_email_text(full_msg)

    # Mark message as read
    gmail_service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()

    return note_text, msg_id


def upload_to_drive(filename, mimetype="text/markdown"):
    """Uploads a local file to Google Drive in the vault folder."""

    service = build("drive", "v3", credentials=get_creds())

    file_metadata = {
        "name": os.path.basename(filename),
        "parents": [VAULT_FOLDER_ID] if VAULT_FOLDER_ID else []
    }
    media = MediaFileUpload(filename, mimetype=mimetype)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    return file.get("id")


@app.route("/upload-test")
def upload_test():
    # create a small test file
    test_filename = "/tmp/test_note.md"
    with open(test_filename, "w") as f:
        f.write("# Vault Curator Test Note\nThis is a test.")

    file_id = upload_to_drive(test_filename)
    return jsonify({"status": "success", "file_id": file_id})


@app.route("/", methods=["POST"])
def pubsub_push():
    envelope = request.get_json()
    if not envelope:
        return "Bad Request: no JSON", 400

    note_text, msg_id = fetch_latest_email_added()
    if note_text:
        # Save note to a temporary file
        note_filename = "/tmp/note-" + str(msg_id) + ".md"
        with open(note_filename, "w") as f:
            f.write(note_text)

        text_file_id = upload_to_drive(note_filename)
        print(f"Uploaded note to Drive with file ID: {text_file_id}")

    return "OK", 200


@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "Vault curator agent is running!",
        "vault_folder_id": os.environ.get("VAULT_FOLDER_ID"),
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    get_label_id()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
