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


STATE_FILE = "gmail_state.json"


def load_last_history_id(drive_service, folder_id):
    """Load last historyId from Drive, return None if not found."""
    query = f"name='{STATE_FILE}' and '{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])

    if not files:
        return None, None

    file_id = files[0]["id"]
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    print("Loaded state file from Drive:", fh)
    state = json.load(fh)
    return state.get("last_history_id"), file_id


def save_last_history_id(drive_service, folder_id, current_history_id, file_id=None):
    """Save updated last historyId back to Drive."""
    last_history_id, file_id = load_last_history_id(drive_service, folder_id)
    if last_history_id is not None and last_history_id >= current_history_id:
        return file_id
    state = {"last_history_id": current_history_id}
    body = {"name": STATE_FILE, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(json.dumps(state).encode("utf-8")),
                              mimetype="application/json",
                              resumable=True)

    if file_id:
        drive_service.files().update(fileId=file_id, media_body=media).execute()
        return file_id
    else:
        file = drive_service.files().create(body=body, media_body=media).execute()
        return file["id"]


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


def fetch_latest_email_added(last_history_id=None):
    gmail_service = build("gmail", "v1", credentials=get_creds())
    results = gmail_service.users().history().list(
        userId="me",
        startHistoryId=last_history_id + 1 if last_history_id else None,
        historyTypes=["labelAdded"],
        labelId=LABEL_ID,
    ).execute()

    history_records = results.get("history", [])
    if not history_records:
        print("No new emails found with the specified label.")
        return None

    print(f"Found {len(history_records)} history records.")
    print("history_records:", history_records)

    # TODO: handle all messages in history
    # Prefer messagesAdded
    if "messagesAdded" in history_records[-1]:
        msg_id = history_records[0]["messagesAdded"][0]["message"]["id"]

    # Fallback to plain messages
    elif "messages" in history_records[0]:
        msg_id = history_records[-1]["messages"][0]["id"]

    msg = gmail_service.users().messages().get(
        userId="me",
        id=msg_id,
        format="full"
    ).execute()
    # Quick preview
    note_text = msg.get("snippet", "")

    # Optional: decode full message body
    # if "data" in msg["payload"]["body"]:
    #     import base64, email
    #     msg_str = base64.urlsafe_b64decode(msg["payload"]["body"]["data"])
    #     mime_msg = email.message_from_bytes(msg_str)
    #     note_text = mime_msg.get_payload()

    return note_text


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

    pubsub_msg = envelope["message"]
    data = base64.b64decode(pubsub_msg["data"]).decode("utf-8")
    payload = json.loads(data)
    current_history_id = payload.get("historyId")

    drive_service = build("drive", "v3", credentials=get_creds())

    last_history_id, history_file_id = load_last_history_id(
        drive_service, VAULT_FOLDER_ID)

    print("Current history ID:", current_history_id,
          "Last history ID:", last_history_id)

    if last_history_id is None:
        # First run: just initialize state
        history_file_id = save_last_history_id(drive_service, VAULT_FOLDER_ID,
                                               current_history_id, history_file_id)
        last_history_id = current_history_id - 10

    elif current_history_id <= last_history_id:
        # Already processed
        return "OK", 200

    print("Pub/Sub data:", data)

    note_text = fetch_latest_email_added(last_history_id)
    if note_text:
        # Save note to a temporary file
        note_filename = "/tmp/note" + str(current_history_id) + ".md"
        with open(note_filename, "w") as f:
            f.write(note_text)

        text_file_id = upload_to_drive(note_filename)
        print(f"Uploaded note to Drive with file ID: {text_file_id}")
    else:
        print("No note text found in the latest email.")

    print("Updating last history ID to:", current_history_id)
    save_last_history_id(drive_service, VAULT_FOLDER_ID,
                         current_history_id, history_file_id)

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
