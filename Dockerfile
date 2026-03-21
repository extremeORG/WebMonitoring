FROM python:3.12-slim

WORKDIR /app

# Установим systemd, docker.io и util-linux (для nsenter)
RUN apt-get update && apt-get install -y systemd curl docker.io util-linux && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]