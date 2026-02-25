FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt

# Copy source code
COPY src /app/src

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
