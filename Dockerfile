FROM python:3.9-slim

#WORKDIR /app

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

COPY production.env .env

RUN pip install python-dotenv

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8080", "app.main:app"]
#CMD ["python", "-m", "app.main"]