FROM python:3.11-slim

# Build arguments for versioning
ARG VERSION=1.0.0
ARG COMMIT_SHA=unknown
ARG BUILD_DATE=unknown

# Set environment variables
ENV VERSION=${VERSION}
ENV COMMIT_SHA=${COMMIT_SHA}
ENV BUILD_DATE=${BUILD_DATE}

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY requirements-dev.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ta_bot/ ./ta_bot/
COPY tests/ ./tests/

# Force rebuild timestamp
RUN echo "Build timestamp: $(date)" > /app/build_timestamp.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "ta_bot.main"]
