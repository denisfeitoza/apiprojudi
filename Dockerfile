# PROJUDI API v4 - Dockerfile
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs downloads temp

# Expor porta
EXPOSE 8081

# Variáveis de ambiente padrão
ENV PLAYWRIGHT_HEADLESS=true
ENV DEBUG=false
ENV HOST=0.0.0.0
ENV PORT=8000

# Comando de inicialização
CMD ["python", "main.py"]