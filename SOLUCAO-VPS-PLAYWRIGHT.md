# 🔧 SOLUÇÃO: Erro Playwright na VPS

## ❌ **Problema Identificado:**
```
Executable doesn't exist at /root/.cache/ms-playwright/firefox-1429/firefox/firefox
```

## ✅ **Solução Rápida:**

### **Opção 1: Script Automático (Recomendado)**
```bash
# 1. Baixar script de correção
wget https://raw.githubusercontent.com/denisfeitoza/apiprojudi/main/fix-playwright-vps.sh

# 2. Dar permissão
chmod +x fix-playwright-vps.sh

# 3. Executar correção
./fix-playwright-vps.sh
```

### **Opção 2: Comandos Manuais**
```bash
# 1. Entrar no diretório do projeto
cd apiprojudi

# 2. Ativar ambiente virtual
source venv/bin/activate

# 3. Remover instalação corrompida
rm -rf ~/.cache/ms-playwright
rm -rf ~/.local/share/ms-playwright

# 4. Reinstalar Playwright
pip uninstall playwright -y
pip install playwright

# 5. Instalar navegadores
playwright install
playwright install-deps

# 6. Verificar instalação
playwright --version
ls -la ~/.cache/ms-playwright/

# 7. Testar
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        print('✅ Playwright funcionando!')
        await browser.close()

asyncio.run(test())
"
```

## 🔧 **Configurações Otimizadas para VPS:**

### **Arquivo `.env` para VPS:**
```bash
PLAYWRIGHT_HEADLESS=true
PORT=8081
MAX_BROWSERS=3
PLAYWRIGHT_TIMEOUT=30000
HOST=0.0.0.0
DEBUG=false
USE_REDIS=true
REDIS_URL=redis://localhost:6379
MAX_CONCURRENT_REQUESTS=3
REQUEST_TIMEOUT=180
```

### **Dependências do Sistema (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
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
    redis-server
```

## 🚀 **Instalação Completa na VPS:**

### **Script de Instalação:**
```bash
# 1. Baixar script
wget https://raw.githubusercontent.com/denisfeitoza/apiprojudi/main/install-vps-linux.sh

# 2. Dar permissão
chmod +x install-vps-linux.sh

# 3. Executar instalação
./install-vps-linux.sh
```

## 📊 **Monitoramento:**

### **Verificar Status:**
```bash
# Status da API
curl http://localhost:8081/status

# Status do service
sudo systemctl status apiprojudi

# Logs em tempo real
sudo journalctl -u apiprojudi -f
```

### **Comandos Úteis:**
```bash
# Reiniciar API
sudo systemctl restart apiprojudi

# Parar API
sudo systemctl stop apiprojudi

# Iniciar API
sudo systemctl start apiprojudi

# Ver logs
sudo journalctl -u apiprojudi -n 50
```

## 🔍 **Troubleshooting:**

### **Problema: "Permission denied"**
```bash
# Corrigir permissões
chmod -R 755 ~/.cache/ms-playwright/
chown -R $USER:$USER ~/.cache/ms-playwright/
```

### **Problema: "No space left on device"**
```bash
# Limpar cache
rm -rf ~/.cache/ms-playwright/
playwright install
```

### **Problema: "Connection refused"**
```bash
# Verificar se Redis está rodando
sudo systemctl status redis-server
sudo systemctl start redis-server
```

### **Problema: "Port already in use"**
```bash
# Encontrar processo usando a porta
sudo lsof -i :8081
sudo kill -9 <PID>
```

## 📋 **Checklist de Verificação:**

- [ ] Playwright instalado: `playwright --version`
- [ ] Navegadores instalados: `ls ~/.cache/ms-playwright/`
- [ ] Redis rodando: `sudo systemctl status redis-server`
- [ ] API respondendo: `curl http://localhost:8081/status`
- [ ] Logs sem erro: `sudo journalctl -u apiprojudi -n 20`

## 🎯 **Teste Final:**

```bash
# Teste completo da API
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "0508844-37.2007.8.09.0024",
    "movimentacoes": true,
    "limite_movimentacoes": 1
  }'
```

**✅ Se retornar JSON com dados, a instalação está funcionando!** 