import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv(dotenv_path="secrets/.env")

SCOPES = ['https://www.googleapis.com/auth/drive.file']  # write access

creds = None
flow = InstalledAppFlow.from_client_secrets_file(
    'secrets/oauth2-credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Save the token for future use
with open('secrets/token/token.pkl', 'wb') as token:
    pickle.dump(creds, token)

print("Token saved to secrets/token.pkl")
