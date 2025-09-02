# Current Capabilities
- create user API
- notification via slack channel

# Things to Add
- ~~rate limiting~~
- ~~accept docker secrets~~
- user offboarding
- send early response codes to stop jira from marking as failure
- ~~stop group adding if runs too long~~
- dedicated group cloning

## Running locally with Docker

This project includes a sample `docker-compose.yml` that starts three services:

- redis: Celery broker and result backend
- web: FastAPI app (uvicorn)
- worker: Celery worker that runs long CopyAll jobs

Before running, ensure `.env` contains the required configuration values (API credentials, service account, Slack webhook, etc.).

To start the stack locally:

	docker compose up --build

The web service listens on port 8000. The Celery worker will pick up tasks enqueued by the web service when `CELERY_BROKER_URL` is set (the compose file sets it to Redis).
