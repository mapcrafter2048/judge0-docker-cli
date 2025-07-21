FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Docker CLI
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY shared/ ./shared/
COPY worker/ ./worker/

# Make the worker executable
RUN chmod +x worker/main.py

# Command to run the worker
CMD ["python", "worker/main.py"]
