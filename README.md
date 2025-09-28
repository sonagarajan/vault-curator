# vault-curator

Send notes to gmail and get it saved in obsidian.

WIP - loading existing obsidian folder structure/tags/templates (as embeddings) and save file into corresponding folder using AI.

[![Vault Curator Demo](https://img.youtube.com/vi/gNnPRcGRS3c/1.jpg)](https://www.youtube.com/watch?v=gNnPRcGRS3c)



## Setup and requirements

> WARNING: Bad docs! To be updated soon. But code works :P

0. Install `gcloud` and `docker`
1. Create project
2. Enable billing
3. Create service account with roles
    3.1 Editor
    3.2 Cloud run admin
4. Oauth2 creds download and add yourself to test users
5. Populate values in secrets/.env

```
cp secrets/.env.example secrets/.env
```

6. Allow access to drive, gmail with `python get_token.py`
7. Provide secret accessor role for service account
8. Upload creds to secrets

```
gcloud pubsub topics create gmail-vault-notes
gcloud pubsub subscriptions create gmail-vault-sub \
  --topic=gmail-vault-notes \
  --push-endpoint="https://YOUR_CLOUD_RUN_URL/"
gcloud pubsub topics add-iam-policy-binding gmail-vault-notes \
--member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
--role="roles/pubsub.publisher"
```

```
gcloud secrets create vault-curator-sa --data-file=secrets/service-account/service-account.json

gcloud secrets create vault-curator-user-token --data-file=secrets/oauth-token/token.pkl
```
## Locally test

```
docker  build -t vault-curator .
docker run -p 8080:8080 \
  -v $(pwd)/secrets:/usr/src/app/secrets \
  vault-curator
```

## Deploy to cloud run

bash deploy.sh
