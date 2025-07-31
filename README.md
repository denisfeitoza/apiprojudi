# PROJUDI V3 API

API para extração de dados do PROJUDI (Tribunal de Justiça de Goiás) com suporte a múltiplas sessões simultâneas e fila Redis.

## 🚀 Funcionalidades

- **Busca por Processo**: Extração de movimentações e partes envolvidas
- **Busca por CPF**: Localização de processos por CPF
- **Busca por Nome**: Localização de processos por nome
- **Múltiplas Sessões**: Processamento simultâneo com pool configurável
- **Fila Redis**: Sistema de fila para gerenciar requisições
- **Fallback Robusto**: Sistema de retry automático com múltiplas estratégias

## ⚙️ Configuração

### Variáveis de Ambiente

| Variável | Descrição | Padrão | Exemplo |
|----------|-----------|--------|---------|
| `PROJUDI_MAX_SESSIONS` | Número máximo de sessões simultâneas | 10 | `20` |
| `REDIS_URL` | URL do Redis para fila | `redis://localhost:6379` | `redis://redis:6379` |

### Configuração de Sessões Simultâneas

A API suporta configuração dinâmica do número de sessões simultâneas via variável de ambiente:

```bash
# Para VPS com recursos limitados
export PROJUDI_MAX_SESSIONS=5

# Para VPS com recursos médios
export PROJUDI_MAX_SESSIONS=10

# Para VPS com recursos avançados
export PROJUDI_MAX_SESSIONS=20
```

**Recomendações por tipo de VPS:**

- **VPS Básico (1-2 vCPUs, 2-4GB RAM)**: 5-8 sessões
- **VPS Médio (2-4 vCPUs, 4-8GB RAM)**: 10-15 sessões  
- **VPS Avançado (4+ vCPUs, 8GB+ RAM)**: 15-25 sessões

## 📋 Endpoints

### POST `/buscar`
Adiciona uma requisição à fila de processamento.

**Body:**
```json
{
  "tipo_busca": "processo|cpf|nome",
  "valor": "5466798-41.2019.8.09.0051"
}
```

**Response:**
```json
{
  "request_id": "uuid-da-requisicao",
  "status": "queued"
}
```

### GET `/status/<request_id>`
Verifica o status de uma requisição.

**Response:**
```json
{
  "status": "pending|processing|completed|failed",
  "movimentacoes": [...],
  "partes_envolvidas": [...],
  "processo_info": {...}
}
```

### GET `/queue/stats`
Estatísticas da fila Redis.

### GET `/health`
Status de saúde da API com configurações.

### POST `/cleanup`
Limpa o pool de sessões e para os workers.

## 🔧 Instalação

1. **Clonar o repositório:**
```bash
git clone <repository-url>
cd projudi-api
```

2. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

3. **Configurar variáveis de ambiente:**
```bash
export PROJUDI_MAX_SESSIONS=10
export REDIS_URL=redis://localhost:6379
```

4. **Iniciar Redis (opcional):**
```bash
# Com Docker
docker run -d -p 6379:6379 redis:alpine

# Com Homebrew (macOS)
brew services start redis
```

5. **Executar a API:**
```bash
python3 main.py
```

## 🧪 Testes

### Teste Simples
```bash
python3 teste_otimizacoes.py
```

### Teste Simultâneo
```bash
python3 teste_simultaneo.py
```

## 📊 Monitoramento

### Verificar Saúde da API
```bash
curl http://localhost:8081/health
```

### Verificar Stats da Fila
```bash
curl http://localhost:8081/queue/stats
```

## 🔍 Logs

A API gera logs detalhados incluindo:
- Criação e liberação de sessões
- Processamento de requisições
- Erros e fallbacks
- Tempos de execução

## 🚨 Troubleshooting

### Problemas Comuns

1. **"Connection pool is full"**
   - Aumentar `PROJUDI_MAX_SESSIONS`
   - Verificar recursos da VPS

2. **"Stale element reference"**
   - Corrigido na versão atual
   - Sistema de retry implementado

3. **"Erro ao selecionar serventia"**
   - Melhorado o tratamento de erros
   - Sistema de fallback implementado

### Limpeza de Emergência
```bash
curl -X POST http://localhost:8081/cleanup
```

## 📈 Performance

### Otimizações Implementadas

- **Cache de elementos**: Evita rebuscar elementos já encontrados
- **Seletores otimizados**: Baseados na análise das páginas HTML
- **Fallback inteligente**: Múltiplas estratégias de busca
- **Pool configurável**: Ajuste dinâmico de sessões
- **Retry automático**: Sistema robusto de tentativas

### Tempos Médios (otimizados)

- **Login**: ~3-4 segundos (reduzido de 5-6s)
- **Busca por serventia**: ~2-3 segundos (reduzido de 3-4s)
- **Extração de dados**: ~1-2 segundos por tentativa
- **Processamento total**: ~10-15 segundos por requisição

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. 