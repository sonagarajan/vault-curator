import os
import pickle
from flask import Flask, jsonify
from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load env variables from secrets folder
load_dotenv(dotenv_path="/usr/src/app/secrets/.env")

app = Flask(__name__)

# Load service account path from .env
BASE_PATH = "/usr/src/app/"
SERVICE_ACCOUNT_FILE = BASE_PATH + os.environ.get("GCP_SA_KEY_PATH")
TOKEN_PATH = BASE_PATH + os.environ.get("GCP_OAUTH_TOKEN_PATH")
VAULT_FOLDER_ID = os.environ.get("VAULT_FOLDER_ID")


def upload_to_drive(filename, mimetype="text/markdown"):
    """Uploads a local file to Google Drive in the vault folder."""
    with open(TOKEN_PATH, "rb") as token_file:
        creds = pickle.load(token_file)
    service = build("drive", "v3", credentials=creds)

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


@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "Vault curator agent is running!",
        "vault_folder_id": os.environ.get("VAULT_FOLDER_ID"),
        "gmail_credentials_present": bool(os.environ.get("GMAIL_CREDENTIALS_JSON"))
    })

# Example health endpoint


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
