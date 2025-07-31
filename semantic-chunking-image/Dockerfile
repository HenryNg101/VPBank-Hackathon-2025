# Use official lightweight Python image
FROM python:3.11-slim

# Install pandoc + curl
# RUN apt-get update && \
#     apt-get install -y tesseract-ocr libtesseract-dev && \
#     apt-get clean

# Install Python deps
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt
RUN python -m spacy download en_core_web_sm

# Set working dir and copy app code
WORKDIR /app
COPY app /app

# Run the app
CMD ["python", "main.py"]