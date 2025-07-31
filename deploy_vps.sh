#!/bin/bash

# PROJUDI API - Script de Deploy Automatizado
# Compatível com EasyPanel e VPS

set -e

echo "🚀 PROJUDI API - Deploy Automatizado"
echo "======================================"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Verificar se Docker está instalado
check_docker() {
    log "Verificando Docker..."
    if ! command -v docker &> /dev/null; then
        error "Docker não está instalado. Instalando..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        log "Docker instalado com sucesso!"
    else
        log "Docker já está instalado."
    fi
}

# Verificar se Docker Compose está instalado
check_docker_compose() {
    log "Verificando Docker Compose..."
    if ! docker compose version &> /dev/null; then
        error "Docker Compose não está disponível. Instalando..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        log "Docker Compose instalado com sucesso!"
    else
        log "Docker Compose já está disponível."
    fi
}

# Configurar variáveis de ambiente
setup_env() {
    log "Configurando variáveis de ambiente..."
    
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            warn "Arquivo .env criado a partir do exemplo. Configure suas credenciais!"
        else
            cat > .env << EOF
# PROJUDI API - Variáveis de Ambiente
PROJUDI_USER=34930230144
PROJUDI_PASS=Joaquim1*
API_PORT=8081
API_HOST=0.0.0.0
DEFAULT_SERVENTIA="Advogados - OAB/Matrícula: 25348-N-GO"
SELENIUM_HEADLESS=true
SELENIUM_TIMEOUT=30
SELENIUM_WAIT=5
LOG_LEVEL=INFO
EOF
            warn "Arquivo .env criado com configurações padrão. Configure suas credenciais!"
        fi
    else
        log "Arquivo .env já existe."
    fi
}

# Parar e remover containers existentes
cleanup_containers() {
    log "Limpando containers existentes..."
    docker compose down --remove-orphans 2>/dev/null || true
    docker system prune -f
}

# Construir e iniciar containers
build_and_start() {
    log "Construindo e iniciando containers..."
    docker compose up -d --build
    
    # Aguardar o container estar pronto
    log "Aguardando container estar pronto..."
    sleep 10
    
    # Verificar se a API está respondendo
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8081/health >/dev/null 2>&1; then
            log "✅ API está respondendo!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "❌ API não respondeu após $max_attempts tentativas"
            docker compose logs
            exit 1
        fi
        
        warn "Tentativa $attempt/$max_attempts - Aguardando API..."
        sleep 10
        attempt=$((attempt + 1))
    done
}

# Configurar firewall
setup_firewall() {
    log "Configurando firewall..."
    
    # Verificar se ufw está disponível
    if command -v ufw &> /dev/null; then
        sudo ufw allow 8081/tcp
        log "Porta 8081 liberada no firewall (ufw)"
    elif command -v iptables &> /dev/null; then
        sudo iptables -A INPUT -p tcp --dport 8081 -j ACCEPT
        log "Porta 8081 liberada no firewall (iptables)"
    else
        warn "Firewall não detectado. Configure manualmente a porta 8081"
    fi
}

# Mostrar informações finais
show_info() {
    echo ""
    echo "🎉 PROJUDI API - Deploy Concluído!"
    echo "=================================="
    echo ""
    echo "📊 Status dos containers:"
    docker compose ps
    echo ""
    echo "🌐 URLs de acesso:"
    echo "   - Health Check: http://$(curl -s ifconfig.me):8081/health"
    echo "   - API Endpoint: http://$(curl -s ifconfig.me):8081/buscar"
    echo ""
    echo "📋 Comandos úteis:"
    echo "   - Ver logs: docker compose logs -f"
    echo "   - Reiniciar: docker compose restart"
    echo "   - Parar: docker compose down"
    echo "   - Atualizar: ./deploy_vps.sh"
    echo ""
    echo "📖 Documentação: README.md"
    echo ""
    echo "🔧 Configuração: Edite o arquivo .env para suas credenciais"
    echo ""
}

# Função principal
main() {
    log "Iniciando deploy da PROJUDI API..."
    
    # Verificar dependências
    check_docker
    check_docker_compose
    
    # Configurar ambiente
    setup_env
    setup_firewall
    
    # Limpar containers existentes
    cleanup_containers
    
    # Construir e iniciar
    build_and_start
    
    # Mostrar informações
    show_info
    
    log "✅ Deploy concluído com sucesso!"
}

# Executar função principal
main "$@" 