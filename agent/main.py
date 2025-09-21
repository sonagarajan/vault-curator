import os
import pickle
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from google.auth.transport.requests import Request

from gmail import get_label_id, fetch_latest_email_added
from drive import upload_to_drive

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


LABEL_ID = get_label_id(GMAIL_LABEL_NAME, get_creds())


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


@app.route("/", methods=["POST"])
def pubsub_push():
    envelope = request.get_json()
    if not envelope:
        return "Bad Request: no JSON", 400

    note_text, msg_id = fetch_latest_email_added(LABEL_ID, get_creds())
    if note_text:
        # Save note to a temporary file
        note_filename = "/tmp/note-" + str(msg_id) + ".md"
        with open(note_filename, "w") as f:
            f.write(note_text)

        text_file_id = upload_to_drive(
            note_filename, VAULT_FOLDER_ID, get_creds())
        print(f"Uploaded note to Drive with file ID: {text_file_id}")

    return "OK", 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
