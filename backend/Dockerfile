FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for compilation (e.g. for some pip packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure data directory exists for mounts
RUN mkdir -p /app/data

# Environment variables for default data paths
ENV SQLITE_DB_PATH=/app/data/qa_copilot.db
ENV CHROMA_DB_PATH=/app/data/chroma_db
ENV UPLOAD_DIR=/app/data/uploads

EXPOSE 8008

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
