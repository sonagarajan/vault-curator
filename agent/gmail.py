import base64
from googleapiclient.discovery import build


''' Helper functions for Gmail API interactions.'''


def get_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)


def get_label_id(label_name, creds):
    '''Fetches the ID of a Gmail label by name. Raises ValueError if not found.'''
    gmail_service = get_gmail_service(creds)
    labels = gmail_service.users().labels().list(userId="me").execute()
    for label in labels.get("labels", []):
        if label["name"] == label_name:
            print(f"Label exists: {label_name} → {label['id']}")
            return label["id"]
    raise ValueError(
        "Label {label_name} does not exist. Please create it in Gmail first.")


def get_email_text(msg):
    '''Extracts and decodes the plain text content from a Gmail message object.'''
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])

    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8")

    # fallback: use snippet if no plain text
    return msg.get("snippet", "")


def fetch_latest_email_added(label_id, creds):
    '''Fetches the latest unread email with the specified label, marks it as read, and returns its text content and message ID.'''
    gmail_service = get_gmail_service(creds)
    results = gmail_service.users().messages().list(
        userId="me",
        labelIds=[label_id],
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
