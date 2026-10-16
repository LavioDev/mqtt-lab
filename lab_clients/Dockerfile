FROM python:3.13-slim-trixie

WORKDIR /app
COPY lab_clients/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY lab_clients /app/lab_clients

