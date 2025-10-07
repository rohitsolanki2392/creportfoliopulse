
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

