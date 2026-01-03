# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies for Camelot
RUN apt-get update && apt-get install -y \
    ghostscript \
    python3-tk \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the function code
COPY main.py .

# Set environment variable for Functions Framework
ENV PORT=8080

# Run the function
CMD exec functions-framework --target=extract_tables --port=$PORT
