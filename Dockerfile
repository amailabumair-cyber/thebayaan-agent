FROM python:3.11-slim

# ٹائم زون سیٹ کریں (Asia/Karachi)
ENV TZ=Asia/Karachi
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ضروری سسٹم لائبریریز انسٹال کریں
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    gcc \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# پیکجز کی تنصیب
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# سورس کوڈ کاپی کریں
COPY . .

# رپورٹس ڈائرکٹری بنائیں
RUN mkdir -p reports

EXPOSE 8000

CMD ["python", "main.py"]
