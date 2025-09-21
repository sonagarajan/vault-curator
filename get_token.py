import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv(dotenv_path="secrets/.env")
TOKEN_PATH = os.environ.get("GCP_OAUTH_TOKEN_PATH")
CREDENTIALS_PATH = os.environ.get("GCP_OAUTH_CREDENTIALS_PATH")

SCOPES = ['https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/gmail.modify',]

creds = None
flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
creds = flow.run_local_server(
    port=0,
    access_type='offline',
    prompt='consent'
)
# Save the token for future use
with open(TOKEN_PATH, 'wb') as token:
    pickle.dump(creds, token)

print("Token saved to secrets/oauth-token/token.pkl")
print("Has refresh token?", creds.refresh_token is not None)
