# 🚀 DEPLOY AUTOMÁTICO - PROJUDI API v4

## 📋 **Visão Geral**

Este projeto agora suporta **deploy automático** via GitHub com todas as correções aplicadas automaticamente. Não é mais necessário instalar manualmente na VPS!

## 🎯 **Opções de Deploy**

### **1. 🐳 Docker Compose (Recomendado)**
```bash
# Na VPS, execute apenas:
wget https://raw.githubusercontent.com/denisfeitoza/apiprojudi/main/deploy.sh
chmod +x deploy.sh
./deploy.sh
```

### **2. 🔄 GitHub Actions**
- Push para `main` = Deploy automático
- Pull Request = Teste automático

### **3. 🐳 Docker Manual**
```bash
docker-compose up -d
```

## 📁 **Arquivos de Deploy Criados**

### **✅ `.github/workflows/deploy.yml`**
- Deploy automático via GitHub Actions
- Testa todas as funcionalidades
- Instala dependências automaticamente

### **✅ `Dockerfile`**
- Imagem Docker otimizada
- Todas as dependências incluídas
- Playwright pré-instalado

### **✅ `docker-compose.yml`**
- Redis + API + Nginx
- Configuração completa
- Health checks

### **✅ `docker-entrypoint.sh`**
- Inicialização automática
- Verificação de dependências
- Teste do Playwright

### **✅ `deploy.sh`**
- Script de deploy para VPS
- Instalação automática do Docker
- Verificação completa

## 🔧 **Configurações Automáticas**

### **📝 `.env` Criado Automaticamente:**
```bash
PLAYWRIGHT_HEADLESS=true
PORT=8081
MAX_BROWSERS=5
PLAYWRIGHT_TIMEOUT=30000
HOST=0.0.0.0
DEBUG=false
USE_REDIS=true
REDIS_URL=redis://localhost:6379
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=180
```

### **🔴 Redis Configurado:**
- Instalação automática
- Persistência de dados
- Health checks

### **🌐 Playwright Corrigido:**
- Instalação automática
- Navegadores pré-downloadados
- Teste de funcionamento

## 🚀 **Como Usar na VPS**

### **Passo 1: Clonar Repositório**
```bash
git clone https://github.com/denisfeitoza/apiprojudi.git
cd apiprojudi
```

### **Passo 2: Executar Deploy**
```bash
chmod +x deploy.sh
./deploy.sh
```

### **Passo 3: Verificar Status**
```bash
# Status da API
curl http://localhost:8081/status

# Logs dos containers
docker-compose logs -f

# Status dos containers
docker-compose ps
```

## 📊 **Monitoramento**

### **Endpoints Disponíveis:**
- **Status:** `http://IP:8081/status`
- **Health:** `http://IP:8081/health`
- **Cache:** `http://IP:8081/cache/status`
- **Concorrência:** `http://IP:8081/concurrency/stats`

### **Comandos Úteis:**
```bash
# Logs em tempo real
docker-compose logs -f api

# Reiniciar API
docker-compose restart api

# Parar tudo
docker-compose down

# Atualizar
git pull && ./deploy.sh
```

## 🔍 **Troubleshooting Automático**

### **Problema: Container não inicia**
```bash
# Ver logs
docker-compose logs api

# Reconstruir
docker-compose build --no-cache api
docker-compose up -d
```

### **Problema: Playwright não funciona**
```bash
# Entrar no container
docker-compose exec api bash

# Testar Playwright
python -c "from playwright.async_api import async_playwright; import asyncio; asyncio.run(async_playwright().start())"
```

### **Problema: Redis não conecta**
```bash
# Verificar Redis
docker-compose exec redis redis-cli ping

# Reiniciar Redis
docker-compose restart redis
```

## 🎯 **Vantagens do Deploy Automático**

### **✅ Zero Configuração Manual**
- Todas as dependências instaladas automaticamente
- Playwright corrigido automaticamente
- Redis configurado automaticamente

### **✅ Deploy Consistente**
- Mesmo ambiente em todas as VPS
- Configurações padronizadas
- Testes automáticos

### **✅ Monitoramento Integrado**
- Health checks automáticos
- Logs centralizados
- Métricas de performance

### **✅ Escalabilidade**
- Fácil replicação
- Load balancing com Nginx
- Cache Redis compartilhado

## 📋 **Checklist de Deploy**

- [ ] Repositório clonado
- [ ] `deploy.sh` executado
- [ ] Containers rodando (`docker-compose ps`)
- [ ] API respondendo (`curl localhost:8081/status`)
- [ ] Redis funcionando (`docker exec redis redis-cli ping`)
- [ ] Playwright testado (logs sem erro)

## 🎉 **Resultado Final**

Após o deploy automático, você terá:
- ✅ API funcionando na porta 8081
- ✅ Redis para cache
- ✅ Playwright corrigido
- ✅ Todas as funcionalidades ativas
- ✅ Monitoramento completo

**🚀 Agora é só usar! Não precisa mais instalar nada manualmente!** 