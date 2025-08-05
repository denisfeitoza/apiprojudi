#!/bin/bash

# 🔧 Script de Correção - Playwright na VPS
# Resolve o erro: "Executable doesn't exist at /root/.cache/ms-playwright/firefox-1429/firefox/firefox"

set -e

echo "🔧 Corrigindo instalação do Playwright na VPS..."

# 1. Verificar se estamos no diretório correto
if [ ! -f "main.py" ]; then
    echo "❌ Execute este script no diretório do projeto apiprojudi"
    exit 1
fi

# 2. Ativar ambiente virtual
if [ -d "venv" ]; then
    echo "🐍 Ativando ambiente virtual..."
    source venv/bin/activate
else
    echo "❌ Ambiente virtual não encontrado. Execute o script de instalação primeiro."
    exit 1
fi

# 3. Remover instalação anterior do Playwright
echo "🧹 Removendo instalação anterior do Playwright..."
rm -rf ~/.cache/ms-playwright
rm -rf ~/.local/share/ms-playwright

# 4. Reinstalar Playwright
echo "📦 Reinstalando Playwright..."
pip uninstall playwright -y
pip install playwright

# 5. Instalar navegadores
echo "🌐 Instalando navegadores..."
playwright install
playwright install-deps

# 6. Verificar instalação
echo "✅ Verificando instalação..."
playwright --version
ls -la ~/.cache/ms-playwright/

# 7. Testar Playwright
echo "🧪 Testando Playwright..."
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test_playwright():
    try:
        async with async_playwright() as p:
            print('✅ Playwright inicializado com sucesso')
            
            # Testar Chromium
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto('https://example.com')
            title = await page.title()
            print(f'✅ Chromium funcionando! Título: {title}')
            await browser.close()
            
            # Testar Firefox
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()
            await page.goto('https://example.com')
            title = await page.title()
            print(f'✅ Firefox funcionando! Título: {title}')
            await browser.close()
            
            print('🎉 Todos os navegadores funcionando!')
            
    except Exception as e:
        print(f'❌ Erro: {e}')
        return False
    
    return True

success = asyncio.run(test_playwright())
if not success:
    exit(1)
"

# 8. Verificar permissões
echo "🔐 Verificando permissões..."
ls -la ~/.cache/ms-playwright/
chmod -R 755 ~/.cache/ms-playwright/

# 9. Testar API
echo "🚀 Testando API..."
if pgrep -f "python main.py" > /dev/null; then
    echo "🔄 Reiniciando API..."
    pkill -f "python main.py"
    sleep 2
fi

echo "🚀 Iniciando API..."
python main.py &
API_PID=$!

echo "⏳ Aguardando API inicializar..."
sleep 10

# 10. Testar endpoint
echo "🧪 Testando endpoint..."
if curl -s http://localhost:8081/status > /dev/null; then
    echo "✅ API funcionando!"
    curl -s http://localhost:8081/status | jq '.status'
else
    echo "❌ API não está respondendo"
fi

# 11. Parar API
echo "🛑 Parando API..."
kill $API_PID 2>/dev/null || true

echo ""
echo "✅ Correção concluída!"
echo ""
echo "📋 Para iniciar a API:"
echo "  • python main.py"
echo "  • ou ./start-api.sh"
echo ""
echo "🔧 Se ainda houver problemas:"
echo "  • Verifique logs: tail -f logs/api.log"
echo "  • Reinstale: ./install-vps-linux.sh" 