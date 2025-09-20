# vault-curator

## Setup and requirements

1. Create project
2. Enable billing
3. Create service account with roles
    3.1 Editor
    3.2 Cloud run admin
4. Oauth2 creds download and add yourself to test users
5. Allow access to drive with `python get_token.py`
6. secret accessor role for service account
7. Upload creds to secrets

```
gcloud secrets create vault-curator-sa --data-file=secrets/service-account.json

gcloud secrets create vault-curator-user-token --data-file=secrets/token.pkl
```

4. Put values in secrets/.env

```
cp secrets/.env.example secrets/.env
```

5. Install `gcloud` and `docker`

## Locally test

```
docker  build -t vault-curator .
docker run -p 8080:8080 \
  -v $(pwd)/secrets:/usr/src/app/secrets \
  vault-curator
```

## Deploy to cloud run

bash deploy.sh
