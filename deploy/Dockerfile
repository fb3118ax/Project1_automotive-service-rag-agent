# 1. Base image
FROM python:3.11-slim

# 2. Set working directory inside container
WORKDIR /app

# 3. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy all app code
COPY . .

# 5. Expose port
EXPOSE 8000

# 6. Start server
CMD ["uvicorn", "api.app:api", "--host", "0.0.0.0", "--port", "8000"]