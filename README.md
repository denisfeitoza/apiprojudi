# PROJUDI API - Versão V3 Ultra-Robusta

API para consulta de processos no sistema PROJUDI com funcionalidades avançadas de pool de sessões, fingerprint único e sistema de fallback automático.

## 🚀 Funcionalidades da V3

- **Pool de Sessões**: Até 6 sessões simultâneas
- **Fingerprint Único**: Cada sessão com identificação única
- **Multi-acessos**: Suporte a múltiplos usuários simultâneos
- **Multi-requisições**: Processamento paralelo de buscas
- **Refresh Automático**: Recriação automática de sessões
- **Sistema de Fallback**: Múltiplas estratégias de recuperação
- **Monitoramento de Saúde**: Verificação automática de sessões
- **Busca por Processo Específico**: Extração direta da página do processo
- **Estrutura Modular**: Código organizado em múltiplos arquivos

## 📁 Estrutura do Projeto

```
apiprojudi/
├── main.py                  # Arquivo principal da API V3
├── projudi_api.py          # Lógica principal da API
├── session_pool.py         # Pool de sessões com fingerprint
├── queue_manager.py        # Gerenciador de fila Redis
├── requirements.txt        # Dependências Python V3
├── .env                    # Configurações (credenciais)
├── Dockerfile             # Configuração Docker
├── docker-compose.yml     # Orquestração Docker
├── deploy_vps.sh         # Script de deploy
├── README.md             # Este arquivo
├── n8n-config.md         # Configuração N8N
├── n8n-internal-fix.md   # Solução VPS interna
├── env.example           # Exemplo de variáveis
└── easypanel-config.md   # Guia específico EasyPanel
```

## 🛠️ Instalação

### Local
```bash
pip install -r requirements.txt
python3 main.py
```

### Docker
```bash
docker build -t projudi-api-v3 .
docker run -p 8081:8081 projudi-api-v3
```

### Docker Compose
```bash
docker-compose up -d
```

## 🔧 Configuração

### Variáveis de Ambiente

Crie um arquivo `.env`:

```bash
# Credenciais PROJUDI (OBRIGATÓRIAS)
PROJUDI_USER=34930230144
PROJUDI_PASS=Joaquim1*

# Configurações da API (OBRIGATÓRIAS)
API_PORT=8081
API_HOST=0.0.0.0
API_DEBUG=false

# Serventia padrão (OBRIGATÓRIA)
DEFAULT_SERVENTIA="Advogados - OAB/Matrícula: 25348-N-GO"

# Configurações Selenium (opcionais)
SELENIUM_HEADLESS=true
SELENIUM_TIMEOUT=30
SELENIUM_WAIT=5

# Logs (opcional)
LOG_LEVEL=INFO
```

## 🌐 Uso da API

### Health Check

```bash
curl -X GET https://seu-dominio.com/health
```

### Busca por CPF

```bash
curl -X POST https://seu-dominio.com/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": 3
  }'
```

### Busca por Nome

```bash
curl -X POST https://seu-dominio.com/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "nome",
    "valor": "Rosane Aparecida Carlos Marques",
    "movimentacoes": 3
  }'
```

### Busca por Processo

```bash
curl -X POST https://seu-dominio.com/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "5466798-41.2019.8.09.0051",
    "movimentacoes": 3
  }'
```

## 📊 Resposta da API

```json
{
  "status": "success",
  "tipo_busca": "cpf",
  "valor_busca": "285.897.001-78",
  "total_processos": 6,
  "processos_processados": 6,
  "request_id": "uuid-da-requisicao",
  "timestamp": "2025-07-30T22:17:10.123456",
  "resultados": [
    {
      "numero": "1",
      "classe": "PROCEDIMENTO COMUM CÍVEL",
      "assunto": "Indenização por Dano Moral",
      "id": "123456",
      "total_movimentacoes": 3,
      "ultima_movimentacao": "765",
      "movimentacoes": [
        {
          "numero": "765",
          "data": "02/04/2025 12:38:07",
          "tipo": "Autos ConclusosP/ DECISÃO",
          "usuario": "Ludmila Soares Paiva",
          "tem_anexo": false,
          "anexos": [],
          "codigo_movimentacao": "377767622",
          "info_adicional": "",
          "onclick": "",
          "html_completo": "..."
        }
      ]
    }
  ]
}
```

## 🐳 Deploy no EasyPanel

### Via Docker Compose

```bash
# Clonar repositório
git clone https://github.com/denisfeitoza/apiprojudi.git
cd apiprojudi

# Configurar variáveis
cp .env.example .env
# Edite o .env com suas credenciais

# Executar
docker-compose up -d

# Verificar logs
docker-compose logs -f

# Testar API
curl http://localhost:8081/health
```

### Via Script Automatizado

```bash
# Execute o script de deploy
chmod +x deploy_vps.sh
./deploy_vps.sh
```

## 📋 Pré-requisitos

* Docker e Docker Compose
* EasyPanel (opcional, mas recomendado)
* Acesso SSH ao VPS (para deploy manual)

## 🔧 Integração com N8N

### Configuração para VPS Compartilhada (Recomendado)

```json
{
  "parameters": {
    "method": "POST",
    "url": "http://apis_projudi:8081/buscar",
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {
          "name": "tipo_busca",
          "value": "cpf"
        },
        {
          "name": "valor",
          "value": "285.897.001-78"
        },
        {
          "name": "movimentacoes",
          "value": "3"
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

## 📡 Endpoints da API V3

### Endpoints de Teste

* `GET /` - Status geral da API
* `GET /health` - Health check
* `GET /status` - Status detalhado
* `GET /ping` - Teste simples

### Endpoints Principais

* `POST /buscar` - Busca de processos (CPF, nome, número)
* `POST /buscar_multiplo` - Múltiplas buscas simultâneas
* `POST /cleanup` - Limpar pool de sessões

## 🚨 Troubleshooting

### Problema: "Service is not reachable"

**Solução**: Verifique se o mapeamento de domínio está correto:

* Deve ser: `http://apis_projudi:8081/`
* NÃO: `http://apis_projudi:80/`

### Problema: API não responde

**Solução**: Verifique as variáveis de ambiente:

* `API_PORT=8081` (obrigatório)
* `API_HOST=0.0.0.0` (obrigatório)

### Logs do Container

```bash
docker logs -f projudi-api
```

### Reiniciar Serviço

```bash
docker-compose restart
```

### Verificar Status

```bash
docker-compose ps
```

## 📞 Suporte

* **Issues**: GitHub Issues
* **Health Check**: `https://seu-dominio.com/health`

## 📄 Licença

Este projeto é de uso interno e educacional.

---

**Desenvolvido com ❤️ para automatização de processos jurídicos**

## 🔄 Migração da V2 para V3

A V3 é totalmente compatível com a V2, mas oferece:

- **Melhor Performance**: Pool de sessões otimizado
- **Maior Estabilidade**: Sistema de fallback robusto
- **Estrutura Modular**: Código mais organizado e manutenível
- **Busca por Processo Melhorada**: Extração direta da página
- **Logs Detalhados**: Melhor monitoramento e debugging

Para migrar, simplesmente use a nova estrutura V3 - todos os endpoints e funcionalidades permanecem os mesmos! 