# FROM pandoc/core:latest

# RUN apk add --no-cache python3 py3-pip
# RUN python3 -m venv /venv
# ENV PATH="/venv/bin:$PATH"

# # Install Python deps from requirements.txt
# COPY requirements.txt /
# RUN pip3 install -r /requirements.txt

# WORKDIR /app
# COPY app /app

# CMD ["python3", "app/main.py"]

# RUN apt-get update && apt-get install -y python3 python3-pip

# RUN python3 -m venv /venv
# ENV PATH="/venv/bin:$PATH"

# COPY requirements.txt /
# RUN pip3 install -r /requirements.txt

# WORKDIR /app
# COPY app /app

# CMD ["python3", "main.py"]

# Use official lightweight Python image
FROM python:3.11-slim

# Install pandoc + curl
RUN apt-get update && \
    apt-get install -y pandoc curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

# Set working dir and copy app code
WORKDIR /app
COPY app /app

# Run the app
CMD ["python", "main.py"]
