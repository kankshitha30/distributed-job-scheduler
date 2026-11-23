FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for build tools and PostgreSQL clients
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app for shared models & database access, and worker code
COPY backend/app /app/backend/app
COPY worker/ /app/worker/

ENV PYTHONPATH="/app:/app/backend"

CMD ["python", "worker/worker.py"]
