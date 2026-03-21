FROM python:3.12-slim

WORKDIR /app

# Устанавливаем systemd (нужен для systemctl)
RUN apt-get update && apt-get install -y systemd curl && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем их
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY app/ .

# Устанавливаем точку входа
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]