import os
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load env variables from secrets folder
load_dotenv(dotenv_path="secrets/.env")

app = Flask(__name__)

# Example endpoint


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
