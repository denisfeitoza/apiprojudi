# 🔧 Solução para N8N na Mesma VPS - PROJUDI API

## 🎯 **Problema Identificado:**
- N8N e API estão na mesma VPS
- N8N não consegue resolver o domínio do EasyPanel internamente
- Timeout de 30s excedido

## 🚀 **Soluções para Testar:**

### **1. Usar Nome do Container (Recomendado)**

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

### **2. Usar localhost**

```json
{
  "parameters": {
    "url": "http://localhost:8081/simple",
    "method": "GET",
    "options": {
      "timeout": 30000,
      "responseFormat": "json"
    }
  }
}
```

### **3. Usar Nome do Container**

```json
{
  "parameters": {
    "url": "http://projudi-api:8081/simple",
    "method": "GET",
    "options": {
      "timeout": 30000,
      "responseFormat": "json"
    }
  }
}
```

### **4. Configurar DNS Manual no VPS**

Execute no VPS do N8N:

```bash
# Adicionar entrada no /etc/hosts
echo "127.0.0.1 apis-projudi.tydj9j.easypanel.host" >> /etc/hosts

# Ou usar o IP real
echo "82.25.65.5 apis-projudi.tydj9j.easypanel.host" >> /etc/hosts
```

### **5. Teste de Busca com Nome do Container**

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

## 🔍 **Como Descobrir o IP Correto:**

### **Opção 1: Verificar logs do EasyPanel**
- Acesse o EasyPanel
- Vá em "Logs" do projeto
- Procure por: `Running on http://172.18.0.13:8081`

### **Opção 2: SSH no VPS**
```bash
# Conectar no VPS
ssh root@seu-vps

# Verificar containers Docker
docker ps

# Verificar rede Docker
docker network ls
docker network inspect projudi-network
```

### **Opção 3: Testar URLs Comuns**
- `http://apis_projudi:8081` ✅ **NOME DO CONTAINER (FUNCIONA)**
- `http://127.0.0.1:8081`
- `http://localhost:8081`
- `http://172.18.0.13:8081`

## 📋 **Teste Sequencial:**

1. **Teste com IP direto** (Opção 1)
2. **Se não funcionar, teste localhost** (Opção 2)
3. **Se não funcionar, configure DNS** (Opção 4)
4. **Teste busca completa**

## 🎯 **Configuração Final Recomendada:**

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

## ⚠️ **Importante:**
- Use **HTTP** em vez de **HTTPS** para comunicação interna
- O nome `apis_projudi:8081` é a configuração que funciona
- Este é o nome do container Docker configurado no EasyPanel

**Teste primeiro com a Opção 1!** 🚀 