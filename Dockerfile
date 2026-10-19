# Official Microsoft Playwright image with Python 3.11 and pre-installed browser binaries
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

USER root
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Karachi \
    PORT=7860

# Install Urdu and Arabic fonts for proper rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-noto-extra \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod -R 777 /app

EXPOSE 7860

CMD ["python", "main.py"]
