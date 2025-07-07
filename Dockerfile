FROM python:3.11-slim

WORKDIR /app

# Sistem kütüphaneleri (pyswisseph için gerekli)
RUN apt-get update && \
    apt-get install -y build-essential wget unzip swig && \
    rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını yükle
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# 8000 portunu aç
EXPOSE 8000

# Uygulama başlatma komutu (gunicorn ile)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
