FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "botocore[crt]"
COPY backend/ backend/
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
