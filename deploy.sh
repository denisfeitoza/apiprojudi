#!/bin/bash

# 🚀 Script de Deploy Automático - PROJUDI API v4
# Para VPS com deploy via GitHub

set -e

echo "🚀 Iniciando deploy automático da PROJUDI API v4..."

# 1. Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# 2. Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Instalando Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 3. Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose down --remove-orphans || true

# 4. Remover imagens antigas
echo "🧹 Limpando imagens antigas..."
docker system prune -f || true

# 5. Fazer pull das últimas mudanças
echo "📥 Atualizando código..."
git pull origin main || true

# 6. Construir e iniciar containers
echo "🔨 Construindo containers..."
docker-compose build --no-cache

echo "🚀 Iniciando containers..."
docker-compose up -d

# 7. Aguardar inicialização
echo "⏳ Aguardando inicialização..."
sleep 30

# 8. Verificar status
echo "📊 Verificando status..."
if curl -f http://localhost:8081/status > /dev/null 2>&1; then
    echo "✅ API funcionando!"
    curl -s http://localhost:8081/status | jq '.status' || echo "online"
else
    echo "❌ API não está respondendo"
    echo "📋 Logs dos containers:"
    docker-compose logs --tail=50
    exit 1
fi

# 9. Verificar Redis
echo "🔴 Verificando Redis..."
if docker exec apiprojudi-redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis funcionando!"
else
    echo "❌ Redis não está funcionando"
    exit 1
fi

# 10. Teste final
echo "🧪 Teste final da API..."
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "0508844-37.2007.8.09.0024",
    "movimentacoes": false
  }' > /dev/null 2>&1 && echo "✅ Teste de busca funcionando!" || echo "⚠️ Teste de busca falhou (pode ser normal sem credenciais)"

echo ""
echo "🎉 Deploy concluído com sucesso!"
echo ""
echo "📋 Informações:"
echo "  • API: http://$(hostname -I | awk '{print $1}'):8081"
echo "  • Status: http://$(hostname -I | awk '{print $1}'):8081/status"
echo "  • Health: http://$(hostname -I | awk '{print $1}'):8081/health"
echo ""
echo "🔧 Comandos úteis:"
echo "  • Logs: docker-compose logs -f"
echo "  • Reiniciar: docker-compose restart"
echo "  • Parar: docker-compose down"
echo "  • Atualizar: ./deploy.sh"
echo ""
echo "📊 Monitoramento:"
echo "  • docker-compose ps"
echo "  • docker stats" 