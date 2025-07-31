# Configuração EasyPanel - PROJUDI V3 API

## 🚀 Deploy no EasyPanel

### 1. Configuração do Projeto

**Nome do Projeto:** `projudi-api-v3`

**Tipo:** `Docker Compose`

### 2. Variáveis de Ambiente

Configure as seguintes variáveis no EasyPanel:

```bash
# Configuração de Sessões Simultâneas
PROJUDI_MAX_SESSIONS=10

# Configuração Redis (opcional)
REDIS_URL=redis://redis:6379

# Credenciais PROJUDI (OBRIGATÓRIAS)
PROJUDI_USER=seu_usuario
PROJUDI_PASS=sua_senha

# Configurações da API
API_PORT=8081
API_HOST=0.0.0.0
API_DEBUG=false

# Serventia padrão
DEFAULT_SERVENTIA="Advogados - OAB/Matrícula: 25348-N-GO"

# Configurações Selenium
SELENIUM_HEADLESS=true
SELENIUM_TIMEOUT=30
SELENIUM_WAIT=5

# Logs
LOG_LEVEL=INFO
```

### 3. Configuração de Sessões por Tipo de VPS

#### VPS Básico (1-2 vCPUs, 2-4GB RAM)
```bash
PROJUDI_MAX_SESSIONS=5
```

#### VPS Médio (2-4 vCPUs, 4-8GB RAM)
```bash
PROJUDI_MAX_SESSIONS=10
```

#### VPS Avançado (4+ vCPUs, 8GB+ RAM)
```bash
PROJUDI_MAX_SESSIONS=20
```

### 4. Docker Compose

```yaml
version: '3.8'

services:
  projudi-api:
    build: .
    container_name: projudi-api-v3
    ports:
      - "8081:8081"
    environment:
      - PROJUDI_MAX_SESSIONS=${PROJUDI_MAX_SESSIONS:-10}
      - REDIS_URL=${REDIS_URL:-redis://redis:6379}
      - PROJUDI_USER=${PROJUDI_USER}
      - PROJUDI_PASS=${PROJUDI_PASS}
      - API_PORT=${API_PORT:-8081}
      - API_HOST=${API_HOST:-0.0.0.0}
      - API_DEBUG=${API_DEBUG:-false}
      - DEFAULT_SERVENTIA=${DEFAULT_SERVENTIA}
      - SELENIUM_HEADLESS=${SELENIUM_HEADLESS:-true}
      - SELENIUM_TIMEOUT=${SELENIUM_TIMEOUT:-30}
      - SELENIUM_WAIT=${SELENIUM_WAIT:-5}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:alpine
    container_name: projudi-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

### 5. Configuração de Domínio

**Mapeamento de Domínio:**
- **Domínio:** `api.seudominio.com`
- **Porta:** `8081`
- **Protocolo:** `HTTP`

**Configuração N8N:**
```json
{
  "parameters": {
    "method": "POST",
    "url": "http://projudi-api:8081/buscar",
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {
          "name": "tipo_busca",
          "value": "processo"
        },
        {
          "name": "valor",
          "value": "5466798-41.2019.8.09.0051"
        }
      ]
    },
    "options": {
      "timeout": 300000,
      "responseFormat": "json"
    }
  }
}
```

### 6. Monitoramento

#### Health Check
```bash
curl https://api.seudominio.com/health
```

#### Stats da Fila
```bash
curl https://api.seudominio.com/queue/stats
```

### 7. Troubleshooting

#### Verificar Logs
```bash
# No EasyPanel
docker logs projudi-api-v3

# Ou via SSH
docker logs -f projudi-api-v3
```

#### Reiniciar Serviço
```bash
# No EasyPanel
docker-compose restart

# Ou via SSH
docker-compose restart projudi-api
```

#### Limpeza de Emergência
```bash
curl -X POST https://api.seudominio.com/cleanup
```

### 8. Performance

#### Otimizações Automáticas
- **Cache de elementos**: Implementado
- **Seletores otimizados**: Baseados em análise HTML
- **Fallback inteligente**: Múltiplas estratégias
- **Pool configurável**: Via variável de ambiente

#### Tempos Esperados
- **Login**: 3-4 segundos
- **Busca por serventia**: 2-3 segundos
- **Extração de dados**: 1-2 segundos
- **Total por requisição**: 10-15 segundos

### 9. Segurança

#### Recomendações
- Use HTTPS em produção
- Configure firewall adequadamente
- Monitore logs regularmente
- Mantenha credenciais seguras

#### Variáveis Sensíveis
- `PROJUDI_USER`: Usuário do PROJUDI
- `PROJUDI_PASS`: Senha do PROJUDI

### 10. Backup

#### Configuração
```bash
# Backup automático do Redis
docker run --rm -v redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz -C /data .
```

#### Restauração
```bash
# Restaurar Redis
docker run --rm -v redis_data:/data -v $(pwd):/backup alpine tar xzf /backup/redis-backup.tar.gz -C /data
```

---

**Nota:** Ajuste `PROJUDI_MAX_SESSIONS` conforme os recursos da sua VPS para otimizar performance. 