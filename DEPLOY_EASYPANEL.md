# 🚀 Deploy PROJUDI API v4 no EasyPanel

## ⚡ Configuração Rápida

### 1. **Configurações do Serviço**
```yaml
Nome: projudi-api-v4
Porta: 8081
Tipo: Web Service
```

### 2. **Variáveis de Ambiente (.env)**
```bash
# Credenciais PROJUDI (OBRIGATÓRIAS)
PROJUDI_USER=seu_usuario
PROJUDI_PASSWORD=sua_senha
PROJUDI_SERVENTIA=sua_serventia

# Configurações da API
HOST=0.0.0.0
PORT=8081
DEBUG=false

# Playwright (para VPS Linux)
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright
```

### 3. **Dockerfile Otimizado para EasyPanel**
O projeto já inclui um Dockerfile otimizado. Use o arquivo principal.

### 4. **Comandos de Build**
```bash
# Se usar requirements-linux.txt (recomendado para VPS)
# Renomeie: mv requirements-linux.txt requirements.txt

# Build normal
docker build -t projudi-api .
```

### 5. **Resources Recomendados**
- **CPU**: 0.5-1 vCPU mínimo
- **RAM**: 1GB mínimo (2GB recomendado)
- **Storage**: 5GB

### 6. **Health Check**
```
Endpoint: /health
Porta: 8081
```

## 🔧 Troubleshooting VPS Linux

### Erro Playwright/Chromium:
```bash
# Conectar ao container e executar:
playwright install-deps chromium
playwright install chromium --force
```

### Erro PyMuPDF:
```bash
# Desabilitar dependências problemáticas
# Comentar linhas no requirements.txt:
# pymupdf==1.23.8
# pytesseract==0.3.10
```

### Performance:
- Use `PLAYWRIGHT_HEADLESS=true` sempre
- Limite `MAX_BROWSERS=3` em VPS pequenas
- Configure logs para ERROR em produção

## 📊 Monitoramento

### Endpoints de Status:
- GET `/status` - Status da API
- GET `/health` - Health check
- Logs automáticos em `/logs/`

### Métricas Importantes:
- Sessões ativas
- Pool de navegadores
- Tempo de resposta
- Taxa de sucesso