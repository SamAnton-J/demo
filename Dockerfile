# Dockerfile
FROM python:3.10-slim

# Set a dedicated working directory
WORKDIR /code

# Copy and install requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code into the container
COPY ./app ./app