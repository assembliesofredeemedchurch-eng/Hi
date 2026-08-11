FROM python:3.11-slim

# Install ffmpeg (required by yt-dlp for audio/video processing)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY Template/ Template/
COPY Static/ Static/

# Create downloads directory
RUN mkdir -p downloads

# Expose port 8000
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--timeout", "300", "app:app"]
