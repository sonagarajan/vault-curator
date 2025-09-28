from googleapiclient.discovery import build
import pickle
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import os

load_dotenv(dotenv_path="secrets/.env")
TOKEN_PATH = os.environ.get("GCP_OAUTH_TOKEN_PATH")
PROJECT_ID = os.environ.get("GCP_PROJECT")
GMAIL_PUBSUB_TOPIC_NAME = os.environ.get("GMAIL_PUBSUB_TOPIC_NAME")
GMAIL_LABEL_NAME = os.environ.get("GMAIL_LABEL_NAME")


def get_label_id(service, user_id, label_name):
    labels = service.users().labels().list(userId=user_id).execute()
    for label in labels.get("labels", []):
        if label["name"] == label_name:
            print(f"Label exists: {label_name} → {label['id']}")
            return label["id"]
    print("Label {label_name} does not exist!")
    raise ValueError("Label does not exist. Please create it in Gmail first.")


def setup_gmail_watch(creds, topic_name):
    gmail_service = build("gmail", "v1", credentials=creds)
    label_id = get_label_id(gmail_service, "me", GMAIL_LABEL_NAME)
    body = {
        "labelIds": [label_id],
        "topicName": topic_name
    }
    try:
        watch_resp = gmail_service.users().watch(userId="me", body=body).execute()
        print("Gmail watch setup complete:", watch_resp)
    except HttpError as e:
        print("Error setting up Gmail watch:", e)


with open(TOKEN_PATH, "rb") as token_file:
    creds = pickle.load(token_file)

# Auto-refresh access token if expired
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

setup_gmail_watch(creds, GMAIL_PUBSUB_TOPIC_NAME)
