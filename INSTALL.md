# 🚀 Guia de Instalação - PROJUDI API v4

## 📋 Pré-requisitos

- **Python 3.8+** (recomendado 3.11)
- **Sistema Operacional**: Linux, macOS ou Windows
- **Memória RAM**: Mínimo 2GB (recomendado 4GB+)
- **Espaço em disco**: 1GB para dependências

## ⚡ Instalação Rápida

### 1. Clone/Baixe o projeto:
```bash
# Se usando git
git clone <repo-url>
cd projudi-api-v4

# Ou extraia o ZIP baixado
```

### 2. Execute o setup automático:
```bash
python setup.py
```

### 3. Configure suas credenciais:
```bash
# Edite o arquivo .env criado
nano .env
```

**Configure especialmente:**
- `PROJUDI_USER=seu_usuario`
- `PROJUDI_PASS=sua_senha`
- `DEFAULT_SERVENTIA=sua_serventia`

### 4. Teste a instalação:
```bash
python test_api.py
```

### 5. Execute a API:
```bash
python main.py
```

**API estará em**: `http://localhost:8081`

## 🔧 Instalação Manual

### 1. Instalar dependências:
```bash
pip install -r requirements.txt
```

### 2. Instalar Playwright:
```bash
playwright install chromium
```

### 3. Criar diretórios:
```bash
mkdir logs downloads temp
```

### 4. Configurar ambiente:
```bash
cp .env.example .env
# Edite .env com suas configurações
```

## 🐳 Instalação com Docker

### 1. Usando Docker Compose (recomendado):
```bash
# Configure .env primeiro
docker-compose up -d
```

### 2. Usando Docker apenas:
```bash
docker build -t projudi-api-v4 .
docker run -p 8081:8081 -e PROJUDI_USER=seu_usuario -e PROJUDI_PASS=sua_senha projudi-api-v4
```

## 🌐 Deploy em VPS/EasyPanel

### Para VPS Linux:

1. **Instalar Python 3.11:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

2. **Configurar projeto:**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

3. **Configurar serviço systemd:**
```bash
sudo nano /etc/systemd/system/projudi-api.service
```

```ini
[Unit]
Description=PROJUDI API v4
After=network.target

[Service]
Type=simple
User=seu_usuario
WorkingDirectory=/caminho/para/projudi-api-v4
Environment=PATH=/caminho/para/projudi-api-v4/venv/bin
ExecStart=/caminho/para/projudi-api-v4/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

4. **Iniciar serviço:**
```bash
sudo systemctl enable projudi-api
sudo systemctl start projudi-api
```

### Para EasyPanel:

1. **Dockerfile está pronto** ✅
2. **Configure variáveis de ambiente no painel**
3. **Use porta 8081**
4. **Deploy via Git ou upload**

## ⚙️ Configurações Importantes

### Variáveis de Ambiente:

```env
# OBRIGATÓRIAS
PROJUDI_USER=seu_usuario_projudi
PROJUDI_PASS=sua_senha_projudi
DEFAULT_SERVENTIA=sua_serventia

# OPCIONAIS (com valores padrão)
DEBUG=false
HOST=0.0.0.0
PORT=8081
PLAYWRIGHT_HEADLESS=true
MAX_BROWSERS=5
MAX_CONCURRENT_REQUESTS=10
```

### Para Produção:
- Use `PLAYWRIGHT_HEADLESS=true`
- Limite `MAX_BROWSERS` conforme RAM disponível
- Configure logs: `DEBUG=false`
- Use Redis para cache (opcional)

## 🧪 Testes

### Teste básico:
```bash
python test_api.py
```

### Testes específicos:
```bash
python test_api.py busca      # Teste de busca
python test_api.py session    # Teste de sessões
python test_api.py multiplas  # Teste múltiplas buscas
```

### Teste via API:
```bash
curl -X POST "http://localhost:8081/buscar" \
     -H "Content-Type: application/json" \
     -d '{"tipo_busca": "processo", "valor": "1234567-89.2023.8.09.0001"}'
```

## 🚨 Solução de Problemas

### Problema: "playwright not found"
```bash
playwright install chromium
# ou
python -m playwright install chromium
```

### Problema: "Permission denied" no Linux
```bash
chmod +x setup.py
sudo apt install fonts-liberation
```

### Problema: "Session timeout"
- Verifique credenciais no `.env`
- Teste login manual no PROJUDI
- Aumente `PLAYWRIGHT_TIMEOUT`

### Problema: "Out of memory"
- Reduza `MAX_BROWSERS`
- Reduza `MAX_CONCURRENT_REQUESTS`
- Adicione mais RAM ao servidor

### Logs para Debug:
```bash
tail -f logs/projudi_api.log
```

## 📊 Monitoramento

### Endpoints úteis:
- `GET /health` - Status da API
- `GET /status` - Estatísticas detalhadas
- `GET /docs` - Documentação automática

### Métricas importantes:
- Sessões ativas vs disponíveis
- Tempo de resposta das buscas
- Taxa de sucesso vs erro
- Uso de memória/CPU

## 🎯 Pronto para Produção!

Após instalação bem-sucedida:

1. ✅ **API rodando** em `http://localhost:8081`
2. ✅ **Testes passando** com `python test_api.py`
3. ✅ **Logs limpos** em `logs/projudi_api.log`
4. ✅ **Documentação** em `http://localhost:8081/docs`

**A API v4 está pronta para extrair dados do PROJUDI!** 🎉