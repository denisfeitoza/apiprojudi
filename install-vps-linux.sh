#!/bin/bash

# 🚀 Script de Instalação PROJUDI API v4 - VPS Linux
# Resolve problemas específicos de VPS e Playwright

set -e

echo "🔧 Instalando PROJUDI API v4 na VPS Linux..."

# 1. Atualizar sistema
echo "📦 Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependências do sistema
echo "🔧 Instalando dependências do sistema..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
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
    libpixman-1-dev

# 3. Instalar Redis
echo "🔴 Instalando Redis..."
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 4. Clonar projeto
echo "📥 Clonando projeto..."
if [ -d "apiprojudi" ]; then
    echo "📁 Projeto já existe, atualizando..."
    cd apiprojudi
    git pull origin main
else
    git clone https://github.com/denisfeitoza/apiprojudi.git
    cd apiprojudi
fi

# 5. Criar ambiente virtual
echo "🐍 Criando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate

# 6. Atualizar pip
echo "📦 Atualizando pip..."
pip install --upgrade pip

# 7. Instalar dependências Python
echo "📚 Instalando dependências Python..."
pip install -r requirements.txt

# 8. Instalar Playwright e navegadores
echo "🌐 Instalando Playwright..."
playwright install chromium
playwright install-deps chromium

# 9. Verificar instalação do Playwright
echo "✅ Verificando instalação do Playwright..."
playwright --version
ls -la ~/.cache/ms-playwright/

# 10. Criar arquivo .env
echo "⚙️ Criando arquivo .env..."
cat > .env << EOF
PLAYWRIGHT_HEADLESS=true
PORT=8081
MAX_BROWSERS=5
PLAYWRIGHT_TIMEOUT=30000
HOST=0.0.0.0
DEBUG=false
USE_REDIS=true
REDIS_URL=redis://localhost:6379
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=180
EOF

# 11. Testar instalação
echo "🧪 Testando instalação..."
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        print(f'✅ Playwright funcionando! Título: {title}')
        await browser.close()

asyncio.run(test_playwright())
"

# 12. Criar script de inicialização
echo "🚀 Criando script de inicialização..."
cat > start-api.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
EOF

chmod +x start-api.sh

# 13. Criar service do systemd
echo "🔧 Criando service do systemd..."
sudo tee /etc/systemd/system/apiprojudi.service > /dev/null << EOF
[Unit]
Description=PROJUDI API v4
After=network.target redis.service

[Service]
Type=simple
User=root
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 14. Habilitar e iniciar service
echo "🚀 Habilitando service..."
sudo systemctl daemon-reload
sudo systemctl enable apiprojudi
sudo systemctl start apiprojudi

# 15. Verificar status
echo "📊 Verificando status..."
sleep 5
sudo systemctl status apiprojudi --no-pager -l

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "📋 Comandos úteis:"
echo "  • Status: sudo systemctl status apiprojudi"
echo "  • Logs: sudo journalctl -u apiprojudi -f"
echo "  • Reiniciar: sudo systemctl restart apiprojudi"
echo "  • Parar: sudo systemctl stop apiprojudi"
echo ""
echo "🌐 API disponível em: http://$(hostname -I | awk '{print $1}'):8081"
echo "📊 Status: http://$(hostname -I | awk '{print $1}'):8081/status"
echo ""
echo "🔧 Para testar:"
echo "curl -X GET http://$(hostname -I | awk '{print $1}'):8081/status" 