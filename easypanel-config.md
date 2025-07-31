# 🚀 Configuração EasyPanel - PROJUDI API

## 📋 **Configuração Completa para EasyPanel**

### **1. Criar Projeto**
- **Nome**: `projudi-api`
- **Tipo**: `Docker Compose`

### **2. Configurar Fonte**
- **GitHub**: `https://github.com/denisfeitoza/apiprojudi`
- **Branch**: `main`
- **Build**: `Dockerfile`

### **3. Variáveis de Ambiente (OBRIGATÓRIAS)**

**⚠️ ATENÇÃO:** Se for usar no EasyPanel, ao adicionar um domínio ao projeto da API,  
**é OBRIGATÓRIO alterar a porta interna de 80 para 8081 na configuração de domínios!**  
Caso contrário, a API não funcionará corretamente.

```env
# =============================================================================
# CREDENCIAIS PROJUDI (OBRIGATÓRIAS)
# =============================================================================
PROJUDI_USER=34930230144
PROJUDI_PASS=Joaquim1*

# =============================================================================
# CONFIGURAÇÕES DA API (OBRIGATÓRIAS)
# =============================================================================
API_PORT=8081
API_HOST=0.0.0.0
API_DEBUG=false

# =============================================================================
# SERVENTIA PADRÃO (OBRIGATÓRIA)
# =============================================================================
DEFAULT_SERVENTIA="Advogados - OAB/Matrícula: 25348-N-GO"

# =============================================================================
# CONFIGURAÇÕES DO SELENIUM (OPCIONAIS)
# =============================================================================
SELENIUM_HEADLESS=true
SELENIUM_TIMEOUT=30
SELENIUM_WAIT=5

# =============================================================================
# CONFIGURAÇÕES DE LOG (OPCIONAIS)
# =============================================================================
LOG_LEVEL=INFO
```

### **4. Configuração de Porta**

- **Porta Externa**: `80` (ou deixe vazio)
- **Porta Interna**: `8081`

### **5. Health Check**

- **URL**: `http://localhost:8081/health`
- **Intervalo**: `30s`
- **Timeout**: `10s`
- **Retries**: `3`
- **Start Period**: `40s`

### **6. Configuração de Domínio (CRÍTICA)**

**APÓS O DEPLOY, EDITE O MAPEAMENTO:**

1. Vá em **"Domínios"**
2. Clique no **ícone de lápis** ao lado do mapeamento interno
3. **Altere de**: `http://apis_projudi:80/`
4. **Para**: `http://apis_projudi:8081/`
5. Clique em **"Save"**
6. Clique em **"Restart"**

### **7. Deploy**

1. Clique em **"Deploy"**
2. Aguarde o build completar
3. Verifique se o status fica **verde**

## 🧪 **Teste da API**

### **Health Check**
```bash
curl https://seu-dominio.com/health
```

### **Busca por CPF**
```bash
curl -X POST https://seu-dominio.com/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "12345678901",
    "movimentacoes": "3"
  }'
```

## 🚨 **Troubleshooting**

### **Problema: "Service is not reachable"**
**Causa**: Mapeamento de domínio incorreto
**Solução**: Verifique se está `http://apis_projudi:8081/` e não `http://apis_projudi:80/`

### **Problema: API não responde**
**Causa**: Variáveis de ambiente incorretas
**Solução**: Verifique se `API_PORT=8081` e `API_HOST=0.0.0.0`

### **Problema: Build falha**
**Causa**: Dependências ou configuração Docker
**Solução**: Verifique os logs do build no EasyPanel

## 📞 **Suporte**

- **GitHub**: https://github.com/denisfeitoza/apiprojudi
- **Issues**: https://github.com/denisfeitoza/apiprojudi/issues
- **Documentação**: README.md 