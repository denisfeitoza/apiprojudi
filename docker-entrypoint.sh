#!/bin/bash

# 🐳 Script de entrada do Docker para PROJUDI API v4
# Inicializa Redis e API automaticamente

set -e

echo "🚀 Iniciando PROJUDI API v4..."

# 1. Iniciar Redis
echo "🔴 Iniciando Redis..."
redis-server --daemonize yes

# 2. Aguardar Redis estar pronto
echo "⏳ Aguardando Redis..."
sleep 2

# 3. Verificar se Redis está funcionando
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Erro: Redis não está funcionando"
    exit 1
fi
echo "✅ Redis funcionando!"

# 4. Verificar Playwright
echo "🌐 Verificando Playwright..."
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        # Usar Chromium (mais estável em VPS Linux)
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ])
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        print(f'✅ Playwright funcionando! Título: {title}')
        await browser.close()

asyncio.run(test())
"

# 5. Executar comando passado
echo "🚀 Iniciando API..."
exec "$@" 