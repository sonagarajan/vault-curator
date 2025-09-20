# vault-curator


## Locally test

```
docker build -t vault-curator .
docker run -p 8080:8080 vault-curator
```

## Deploy to cloud run

bash deploy.sh


## GCP

1. Create project
2. Enable billing
3. Create service account with roles
    3.1 Editor
    3.2 Cloud run admin
