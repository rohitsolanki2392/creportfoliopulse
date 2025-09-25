# FROM python:3.9-slim

# # Set working directory
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && \
#     apt-get install -y libreoffice && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# # Copy Python dependencies file
# COPY requirements.txt .

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# # Set environment variables
# ENV PORT=8080
# EXPOSE 8080

# # Start the application
# CMD ["gunicorn", "--bind", "0.0.0.0:8080", "-k", "uvicorn.workers.UvicornWorker", "main:app"]

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy Python dependencies file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment
ENV PORT=8080
EXPOSE 8080

# Start with uvicorn (recommended for Cloud Run)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port=8080"]

