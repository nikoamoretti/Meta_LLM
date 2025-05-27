FROM python:3.11-slim
WORKDIR /app

# Install system dependencies including Chrome
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and ChromeDriver using Chrome for Testing
RUN wget -q -O chrome-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/121.0.6167.85/linux64/chrome-linux64.zip \
    && unzip chrome-linux64.zip \
    && mv chrome-linux64 /opt/chrome \
    && ln -s /opt/chrome/chrome /usr/local/bin/google-chrome \
    && rm chrome-linux64.zip

RUN wget -q -O chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/121.0.6167.85/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"] 