FROM python:3.12-slim

LABEL maintainer="SteinMax Vision"
LABEL description="Edge Agent for Vehicle Access Control"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

# Create data directory
RUN mkdir -p /data

# Create non-root user
RUN useradd -m -u 1000 edge && chown -R edge:edge /app /data
USER edge

# Expose webhook port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "main.py"]
