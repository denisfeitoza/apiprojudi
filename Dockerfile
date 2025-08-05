# 🐳 Dockerfile para PROJUDI API v4
# Deploy automático com todas as correções

FROM python:3.11-slim

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    pkg-config \
    libgirepository1.0-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libatk1.0-dev \
    libgdk-pixbuf2.0-dev \
    libgtk-3-dev \
    libxss-dev \
    libasound2-dev \
    libnss3-dev \
    libdrm-dev \
    libxkbcommon-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxrandr-dev \
    libgbm-dev \
    libxshmfence-dev \
    libpulse-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libvpx-dev \
    libwebp-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libgif-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libpixman-1-dev \
    curl \
    wget \
    git \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (para cache)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalar Playwright e navegadores
RUN playwright install chromium && \
    playwright install-deps chromium

# Copiar código da aplicação
COPY . .

# Criar arquivo .env
RUN echo "PLAYWRIGHT_HEADLESS=true" > .env && \
    echo "PORT=8081" >> .env && \
    echo "MAX_BROWSERS=5" >> .env && \
    echo "PLAYWRIGHT_TIMEOUT=30000" >> .env && \
    echo "HOST=0.0.0.0" >> .env && \
    echo "DEBUG=false" >> .env && \
    echo "USE_REDIS=true" >> .env && \
    echo "REDIS_URL=redis://localhost:6379" >> .env && \
    echo "MAX_CONCURRENT_REQUESTS=5" >> .env && \
    echo "REQUEST_TIMEOUT=180" >> .env

# Testar instalação do Playwright
RUN python -c "import asyncio; from playwright.async_api import async_playwright; print('✅ Playwright instalado com sucesso')"

# Expor porta
EXPOSE 8081

# Script de inicialização
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Comando padrão
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "main.py"]