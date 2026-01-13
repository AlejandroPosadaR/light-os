# Use Python 3.12 slim image (smaller, faster)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run uses PORT environment variable)
EXPOSE 8080

# Use environment variable for port (Cloud Run requirement)
ENV PORT=8080

# Run FastAPI app
# Using shell form to support PORT env var (Cloud Run requirement)
# Disable uvicorn's default access logging to use our custom logging config
CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
