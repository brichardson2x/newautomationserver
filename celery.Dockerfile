FROM mcr.microsoft.com/powershell:latest

# Minimal working directory
WORKDIR /app

# Install Python and pip
RUN apt-get update && apt-get install -y \
	python3 \
	python3-pip \
	python3-venv \
	&& rm -rf /var/lib/apt/lists/*

# Provide consistent binary names
RUN ln -s /usr/bin/python3 /usr/bin/python && ln -s /usr/bin/pwsh /usr/bin/pwsh.exe

# Install PowerShell modules required by the app tasks (same as web image)
RUN pwsh -c "Install-Module -Name ExchangeOnlineManagement, Microsoft.Graph -Force"

# Copy only the minimal python requirements for the worker and install
COPY requirements.celery.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the subpackages required by the celery worker to minimize image size
# - tasks: celery app and tasks
# - utils: send_slack and group utilities (group_utils uses pwsh via subprocess)
# - core: config and logging
# - schemas: pydantic models used by send_slack
# - scripts: PowerShell scripts referenced by group_utils
COPY app/tasks ./app/tasks
## Copy only the specific utils modules required by the worker
COPY app/utils/group_utils.py ./app/utils/group_utils.py
COPY app/utils/send_slack.py ./app/utils/send_slack.py
COPY app/core ./app/core
COPY app/schemas ./app/schemas
COPY app/scripts ./app/scripts

# Default environment variables (can be overridden by compose)
ENV CELERY_BROKER_URL=redis://redis:6379/0
ENV CELERY_RESULT_BACKEND=redis://redis:6379/0

WORKDIR /app

# Run the celery worker (single concurrency by default)
CMD ["celery", "-A", "app.tasks.celery_app.celery_app", "worker", "--loglevel=info", "--concurrency=1"]
