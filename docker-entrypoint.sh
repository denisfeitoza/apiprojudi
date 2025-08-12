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

# 4. Verificar Playwright (opcional)
if [ "${STARTUP_SELFTEST:-false}" = "true" ]; then
  echo "🌐 Verificando Playwright (self-test habilitado)..."
  python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    try:
        async with async_playwright() as p:
            print('✅ Playwright inicializado com sucesso')

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
            page.set_default_timeout(10000)
            await page.set_content('<html><head><title>Test</title></head><body>OK</body></html>')
            title = await page.title()
            print(f'✅ Playwright funcionando! Título: {title}')
            await browser.close()
            print('🎉 Playwright funcionando perfeitamente!')
    except Exception as e:
        print(f'❌ Erro no teste: {e}')
        print('⚠️ Continuando mesmo com erro no teste...')

asyncio.run(test())
"
else
  echo "⏭️  Ignorando self-test do Playwright (defina STARTUP_SELFTEST=true para habilitar)."
fi

# 5. Executar comando passado
echo "🚀 Iniciando API..."
exec "$@" 