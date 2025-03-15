FROM mcr.microsoft.com/powershell:latest

#WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python && ln -s /usr/bin/pwsh /usr/bin/pwsh.exe

RUN pwsh -c "Install-Module -Name ExchangeOnlineManagement, Microsoft.Graph -Force"

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

COPY production.env .env
#COPY .env .env

RUN pip install python-dotenv

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8080", "--preload", "--timeout", "500", "app.main:app"]
#CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8080", "--preload", "app.main:app"]
#CMD ["python", "-m", "app.main"]