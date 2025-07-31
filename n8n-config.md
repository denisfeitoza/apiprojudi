# 🔧 Configuração N8N para EasyPanel - PROJUDI API

## 🎯 **Configuração Específica para N8N**

### **Problema Identificado:**
- N8N não consegue se conectar ao domínio do EasyPanel
- Timeout de 30s excedido
- Erro de conexão abortada

### **Soluções Testadas:**

## **1. Configuração Básica (Teste Primeiro)**

```json
{
  "parameters": {
    "url": "http://apis_projudi:8081/simple",
    "method": "GET",
    "options": {
      "timeout": 30000,
      "responseFormat": "json"
    }
  }
}
```

## **2. Configuração com Headers Específicos**

```json
{
  "parameters": {
    "url": "https://apis-projudi.tydj9j.easypanel.host/health",
    "method": "GET",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "User-Agent",
          "value": "N8N-Client/1.0"
        },
        {
          "name": "Accept",
          "value": "application/json"
        }
      ]
    },
    "options": {
      "timeout": 60000,
      "responseFormat": "json",
      "allowUnauthorizedCerts": true
    }
  }
}
```

## **3. Configuração de Busca Completa**

```json
{
  "parameters": {
    "method": "POST",
    "url": "http://apis_projudi:8081/buscar",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Content-Type",
          "value": "application/json"
        },
        {
          "name": "User-Agent",
          "value": "N8N-Client/1.0"
        },
        {
          "name": "Accept",
          "value": "application/json"
        }
      ]
    },
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
          "value": "1"
        },
        {
          "name": "usuario",
          "value": "34930230144"
        },
        {
          "name": "senha",
          "value": "Joaquim1*"
        },
        {
          "name": "serventia",
          "value": "Advogados - OAB/Matrícula: 25348-N-GO"
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

## **4. Configuração com Nome do Container (Recomendado)**

```json
{
  "parameters": {
    "method": "POST",
    "url": "http://apis_projudi:8081/buscar",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Content-Type",
          "value": "application/json"
        },
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ]
    },
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
          "value": "1"
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

## **5. Troubleshooting**

### **Se ainda não funcionar:**

1. **Verifique DNS no VPS do N8N:**
   ```bash
   nslookup apis-projudi.tydj9j.easypanel.host
   ```

2. **Teste conectividade:**
   ```bash
   curl -v https://apis-projudi.tydj9j.easypanel.host/health
   ```

3. **Verifique firewall:**
   ```bash
   telnet apis-projudi.tydj9j.easypanel.host 443
   ```

4. **Configure DNS manual no VPS:**
   ```bash
   echo "82.25.65.5 apis-projudi.tydj9j.easypanel.host" >> /etc/hosts
   ```

## **6. Endpoints Disponíveis**

- `GET /` - Status geral
- `GET /health` - Health check
- `GET /ping` - Teste simples
- `GET /test` - Teste N8N
- `GET /status` - Status detalhado
- `POST /buscar` - Busca de processos

## **7. Configurações Importantes**

- **Timeout**: Mínimo 60s para health check, 300s para busca
- **Allow Unauthorized Certs**: Sempre `true`
- **Response Format**: Sempre `json`
- **Headers**: Incluir `Content-Type: application/json` para POST

## **8. Teste Sequencial**

1. Teste com `GET /` (endpoint raiz)
2. Teste com `GET /health`
3. Teste com `GET /ping`
4. Teste com `POST /buscar`

**Comece com a configuração 1 e vá testando sequencialmente!** 🚀 