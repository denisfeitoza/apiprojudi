# 📋 Exemplos de CURL para N8N - PROJUDI API v4

## 🔗 Endpoints Disponíveis

### 1. **Busca Padrão** (`/buscar`)
### 2. **Busca N8N** (`/buscar-n8n`) 
### 3. **Busca Múltipla** (`/buscar-multiplo`)
### 4. **Status da API** (`/status`)
### 5. **Cache e Concorrência**

---

## 🎯 **1. BUSCA PADRÃO** (`/buscar`)

### **Busca por CPF:**
```bash
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": true,
    "limite_movimentacoes": 5,
    "extrair_anexos": false,
    "extrair_partes": true
  }'
```

### **Busca por Nome:**
```bash
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "nome",
    "valor": "Rosane Aparecida Carlos Marques",
    "movimentacoes": true,
    "limite_movimentacoes": 10,
    "extrair_anexos": false,
    "extrair_partes": true
  }'
```

### **Busca por Processo Específico:**
```bash
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "0508844-37.2007.8.09.0024",
    "movimentacoes": true,
    "limite_movimentacoes": 5,
    "extrair_anexos": false,
    "extrair_partes": true
  }'
```

### **Busca Simples (sem movimentações):**
```bash
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": false,
    "extrair_anexos": false,
    "extrair_partes": false
  }'
```

---

## 🤖 **2. BUSCA N8N** (`/buscar-n8n`)

### **Formato N8N - Busca por CPF:**
```bash
curl -X POST http://localhost:8081/buscar-n8n \
  -H "Content-Type: application/json" \
  -d '{
    "bodyParameters": {
      "parameters": [
        {"name": "tipo_busca", "value": "cpf"},
        {"name": "valor", "value": "285.897.001-78"},
        {"name": "movimentacoes", "value": "true"},
        {"name": "limite_movimentacoes", "value": "5"},
        {"name": "extrair_anexos", "value": "false"},
        {"name": "extrair_partes", "value": "true"}
      ]
    }
  }'
```

### **Formato N8N - Busca por Nome:**
```bash
curl -X POST http://localhost:8081/buscar-n8n \
  -H "Content-Type: application/json" \
  -d '{
    "bodyParameters": {
      "parameters": [
        {"name": "tipo_busca", "value": "nome"},
        {"name": "valor", "value": "Rosane Aparecida Carlos Marques"},
        {"name": "movimentacoes", "value": "true"},
        {"name": "limite_movimentacoes", "value": "10"},
        {"name": "extrair_anexos", "value": "false"},
        {"name": "extrair_partes", "value": "true"}
      ]
    }
  }'
```

### **Formato N8N - Busca por Processo:**
```bash
curl -X POST http://localhost:8081/buscar-n8n \
  -H "Content-Type: application/json" \
  -d '{
    "bodyParameters": {
      "parameters": [
        {"name": "tipo_busca", "value": "processo"},
        {"name": "valor", "value": "0508844-37.2007.8.09.0024"},
        {"name": "movimentacoes", "value": "true"},
        {"name": "limite_movimentacoes", "value": "5"},
        {"name": "extrair_anexos", "value": "false"},
        {"name": "extrair_partes", "value": "true"}
      ]
    }
  }'
```

---

## 🔄 **3. BUSCA MÚLTIPLA** (`/buscar-multiplo`)

### **Múltiplas Buscas em Paralelo:**
```bash
curl -X POST http://localhost:8081/buscar-multiplo \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {
        "tipo_busca": "cpf",
        "valor": "285.897.001-78",
        "movimentacoes": true,
        "limite_movimentacoes": 5
      },
      {
        "tipo_busca": "processo",
        "valor": "0508844-37.2007.8.09.0024",
        "movimentacoes": true,
        "limite_movimentacoes": 5
      },
      {
        "tipo_busca": "nome",
        "valor": "Rosane Aparecida Carlos Marques",
        "movimentacoes": true,
        "limite_movimentacoes": 5
      }
    ],
    "paralelo": true
  }'
```

### **Múltiplas Buscas Sequenciais:**
```bash
curl -X POST http://localhost:8081/buscar-multiplo \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {
        "tipo_busca": "cpf",
        "valor": "285.897.001-78",
        "movimentacoes": false
      },
      {
        "tipo_busca": "processo",
        "valor": "0508844-37.2007.8.09.0024",
        "movimentacoes": true,
        "limite_movimentacoes": 3
      }
    ],
    "paralelo": false
  }'
```

---

## 📊 **4. STATUS E MONITORAMENTO**

### **Status da API:**
```bash
curl -X GET http://localhost:8081/status
```

### **Health Check:**
```bash
curl -X GET http://localhost:8081/health
```

### **Status do Cache Redis:**
```bash
curl -X GET http://localhost:8081/cache/status
```

### **Limpar Cache:**
```bash
curl -X POST http://localhost:8081/cache/clear
```

### **Estatísticas de Concorrência:**
```bash
curl -X GET http://localhost:8081/concurrency/stats
```

### **Resetar Estatísticas:**
```bash
curl -X POST http://localhost:8081/concurrency/reset
```

---

## 🔧 **5. CONFIGURAÇÕES AVANÇADAS**

### **Busca com Credenciais Customizadas:**
```bash
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": true,
    "limite_movimentacoes": 5,
    "usuario": "seu_usuario",
    "senha": "sua_senha",
    "serventia": "sua_serventia"
  }'
```

### **Busca com Extração de Anexos:**
```bash
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "0508844-37.2007.8.09.0024",
    "movimentacoes": true,
    "limite_movimentacoes": 5,
    "extrair_anexos": true,
    "extrair_partes": true
  }'
```

---

## 📋 **6. EXEMPLOS PARA N8N**

### **Node HTTP Request - Busca por CPF:**
```json
{
  "method": "POST",
  "url": "http://localhost:8081/buscar",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "tipo_busca": "cpf",
    "valor": "{{ $json.cpf }}",
    "movimentacoes": true,
    "limite_movimentacoes": 5,
    "extrair_anexos": false,
    "extrair_partes": true
  }
}
```

### **Node HTTP Request - Busca N8N:**
```json
{
  "method": "POST",
  "url": "http://localhost:8081/buscar-n8n",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "bodyParameters": {
      "parameters": [
        {"name": "tipo_busca", "value": "{{ $json.tipo_busca }}"},
        {"name": "valor", "value": "{{ $json.valor }}"},
        {"name": "movimentacoes", "value": "{{ $json.movimentacoes }}"},
        {"name": "limite_movimentacoes", "value": "{{ $json.limite_movimentacoes }}"}
      ]
    }
  }
}
```

---

## 📝 **7. RESPOSTAS ESPERADAS**

### **Resposta de Sucesso:**
```json
{
  "status": "success",
  "request_id": "abc123-def456",
  "tipo_busca": "cpf",
  "valor_busca": "285.897.001-78",
  "total_processos_encontrados": 7,
  "processos_simples": [...],
  "processos_detalhados": [
    {
      "numero": "5838566-12",
      "classe": "Processo Cível",
      "assunto": "Execução de Título Extrajudicial",
      "movimentacoes": [
        {
          "numero": 85,
          "tipo": "Juntada -> Petição",
          "descricao": "PENHORA ON LINE",
          "data": "29/07/2025",
          "usuario": "TACIO CONSTANTINO DOS SANTOS",
          "tem_anexo": true,
          "numero_processo": "5838566-12"
        }
      ],
      "total_movimentacoes": 10,
      "partes_polo_ativo": [...],
      "partes_polo_passivo": [...],
      "outras_partes": [...]
    }
  ],
  "tempo_execucao": 64.14,
  "timestamp": "2025-08-05T02:05:45.681"
}
```

### **Resposta de Erro:**
```json
{
  "status": "error",
  "request_id": "abc123-def456",
  "tipo_busca": "cpf",
  "valor_busca": "123.456.789-00",
  "erro": "Processo não encontrado",
  "tempo_execucao": 15.23,
  "timestamp": "2025-08-05T02:05:45.681"
}
```

---

## ⚡ **8. DICAS DE PERFORMANCE**

1. **Use `movimentacoes: false`** para buscas rápidas
2. **Limite `limite_movimentacoes`** para extrações menores
3. **Use busca múltipla** para processar vários processos
4. **Monitore o cache** para otimizar consultas repetidas
5. **Use `paralelo: true`** para buscas simultâneas

---

## 🔍 **9. EXEMPLOS PRÁTICOS**

### **Monitoramento de Processos:**
```bash
# Buscar processos de um CPF e extrair últimas movimentações
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": true,
    "limite_movimentacoes": 3,
    "extrair_partes": true
  }' | jq '.processos_detalhados[] | {numero: .numero, ultima_movimentacao: .movimentacoes[0]}'
```

### **Extração de Dados Específicos:**
```bash
# Extrair apenas números e classes dos processos
curl -X POST http://localhost:8081/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "nome",
    "valor": "Rosane Aparecida Carlos Marques",
    "movimentacoes": false
  }' | jq '.processos_simples[] | {numero: .numero, classe: .classe}'
```

---

**🎯 Todos os exemplos estão prontos para uso no N8N!** 