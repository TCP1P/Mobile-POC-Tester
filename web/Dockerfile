FROM python:3.11-slim

# Install system dependencies
RUN apt update && apt install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    build-essential \
    android-tools-adb \
    aapt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads screenshots challenges && \
    chown -R app:app /app

# Switch to app user
USER app

# Set working directory to src
WORKDIR /app/src

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

CMD ["python", "app.py"]
