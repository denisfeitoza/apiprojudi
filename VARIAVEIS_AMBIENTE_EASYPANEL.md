# 🔧 VARIÁVEIS DE AMBIENTE - VPS EASYPANEL

## 📋 **Conteúdo para Colar nas Variáveis de Ambiente**

Copie e cole o texto abaixo na seção de **Variáveis de Ambiente** do seu serviço no EasyPanel:

```env
# ========================================
# PROJUDI API v4 - VARIÁVEIS DE AMBIENTE
# ========================================

# 🔐 CREDENCIAIS PROJUDI (OBRIGATÓRIAS)
PROJUDI_USER=seu_usuario_projudi
PROJUDI_PASS=sua_senha_projudi
DEFAULT_SERVENTIA=Advogados - OAB/Matrícula: 25348-N-GO

# 🌐 CONFIGURAÇÕES DA API
HOST=0.0.0.0
PORT=8081
DEBUG=true
APP_NAME=PROJUDI API v4
APP_VERSION=4.0.0

# 🎭 CONFIGURAÇÕES PLAYWRIGHT (VPS)
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_SLOW_MO=0
PLAYWRIGHT_TIMEOUT=120000
MAX_BROWSERS=10

# 🔄 CONFIGURAÇÕES REDIS
REDIS_URL=redis://localhost:6379
USE_REDIS=true

# 📁 DIRETÓRIOS
TEMP_DIR=./temp
DOWNLOADS_DIR=./downloads

# ⚡ CONFIGURAÇÕES DE PERFORMANCE
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=300

# 🔗 URLs PROJUDI (não alterar)
PROJUDI_BASE_URL=https://projudi.tjgo.jus.br
PROJUDI_LOGIN_URL=https://projudi.tjgo.jus.br/LogOn?PaginaAtual=-200
```

---

## ⚠️ **IMPORTANTE: Substitua as Credenciais**

**Antes de colar, substitua:**
- `seu_usuario_projudi` → Seu usuário real do PROJUDI
- `sua_senha_projudi` → Sua senha real do PROJUDI
- `25348-N-GO` → Sua OAB/Matrícula real

---

## 🎯 **Configurações Recomendadas por Ambiente**

### **🖥️ Desenvolvimento (Local)**
```env
DEBUG=true
PLAYWRIGHT_HEADLESS=false
MAX_BROWSERS=3
PLAYWRIGHT_TIMEOUT=60000
```

### **🚀 Produção (VPS)**
```env
DEBUG=true
PLAYWRIGHT_HEADLESS=true
MAX_BROWSERS=10
PLAYWRIGHT_TIMEOUT=120000
```

### **⚡ Alta Performance (VPS Forte)**
```env
DEBUG=false
PLAYWRIGHT_HEADLESS=true
MAX_BROWSERS=10
PLAYWRIGHT_TIMEOUT=120000
MAX_CONCURRENT_REQUESTS=15
```

---

## 📊 **Explicação das Variáveis**

### **🔐 Credenciais (OBRIGATÓRIAS)**
- `PROJUDI_USER`: Seu usuário do PROJUDI
- `PROJUDI_PASS`: Sua senha do PROJUDI  
- `DEFAULT_SERVENTIA`: Sua serventia (OAB/Matrícula)

### **🌐 API**
- `HOST`: IP de escuta (0.0.0.0 = todos)
- `PORT`: Porta da API (8081)
- `DEBUG`: Logs detalhados (false em produção)

### **🎭 Playwright**
- `PLAYWRIGHT_HEADLESS`: true = navegador invisível (VPS)
- `PLAYWRIGHT_TIMEOUT`: Timeout em milissegundos
- `MAX_BROWSERS`: Número máximo de sessões simultâneas

### **⚡ Performance**
- `MAX_CONCURRENT_REQUESTS`: Requisições simultâneas
- `REQUEST_TIMEOUT`: Timeout total da requisição

---

## 🔧 **Como Configurar no EasyPanel**

### **1. Acesse o Painel**
- Entre no EasyPanel
- Vá em **Serviços** → Seu serviço PROJUDI API

### **2. Variáveis de Ambiente**
- Clique em **Variáveis de Ambiente**
- Cole o conteúdo acima
- **Substitua as credenciais**
- Clique em **Salvar**

### **3. Reinicie o Serviço**
- Clique em **Reiniciar**
- Aguarde o deploy

### **4. Teste**
```bash
curl http://seu-ip:8081/health
```

---

## 🚨 **Problemas Comuns**

### **Erro: "Credenciais inválidas"**
- Verifique `PROJUDI_USER` e `PROJUDI_PASS`
- Teste login manual no PROJUDI

### **Erro: "Playwright timeout"**
- Aumente `PLAYWRIGHT_TIMEOUT` para 90000
- Reduza `MAX_BROWSERS` para 3

### **Erro: "Out of memory"**
- Reduza `MAX_BROWSERS` para 3
- Reduza `MAX_CONCURRENT_REQUESTS` para 5

### **Erro: "Redis connection"**
- Configure `USE_REDIS=false` se não tiver Redis
- Ou instale Redis na VPS

---

## ✅ **Teste de Configuração**

Após configurar, teste com:

```bash
# Health check
curl http://seu-ip:8081/health

# Teste de busca
curl -X POST "http://seu-ip:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "5479605-59.2020.8.09.0051",
    "movimentacoes": true,
    "extrair_partes_detalhadas": false
  }'
```

**Resposta esperada:**
```json
{
  "status": "success",
  "total_processos_encontrados": 1,
  "tempo_execucao": 25-30
}
```

---

**🎯 Configuração completa! A API estará pronta para uso em produção.**
