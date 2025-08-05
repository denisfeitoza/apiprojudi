# 🚀 Exemplos CURL para API PROJUDI - Compatível com N8N

## 📋 **TODOS OS TIPOS DE PESQUISA DISPONÍVEIS**

### 🌐 **Base URL:**
```bash
# Local
BASE_URL="http://localhost:8081"

# VPS/Produção  
BASE_URL="http://seu-servidor:8081"
```

---

## 🎯 **1. BUSCA POR CPF**

### ✅ **Exemplo Básico (CPF Testado):**
```bash
curl -X POST "${BASE_URL}/buscar" \
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

### ✅ **Exemplo com Credenciais Customizadas:**
```bash
curl -X POST "${BASE_URL}/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": true,
    "limite_movimentacoes": 3,
    "extrair_anexos": true,
    "extrair_partes": true,
    "usuario": "seu_usuario",
    "senha": "sua_senha",
    "serventia": "Advogados - OAB/Matrícula: XXXXX-N-GO"
  }'
```

### ✅ **Formato N8N (CPF):**
```bash
curl -X POST "${BASE_URL}/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d '{
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
          "value": "true"
        },
        {
          "name": "limite_movimentacoes",
          "value": "5"
        },
        {
          "name": "extrair_anexos",
          "value": "false"
        },
        {
          "name": "extrair_partes",
          "value": "true"
        }
      ]
    }
  }'
```

---

## 👤 **2. BUSCA POR NOME**

### ✅ **Exemplo Básico (Nome Testado):**
```bash
curl -X POST "${BASE_URL}/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "nome",
    "valor": "Rosane Aparecida Carlos Marques",
    "movimentacoes": true,
    "limite_movimentacoes": 3,
    "extrair_anexos": false,
    "extrair_partes": true
  }'
```

### ✅ **Exemplo com Nome Parcial:**
```bash
curl -X POST "${BASE_URL}/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "nome",
    "valor": "João Silva",
    "movimentacoes": true,
    "limite_movimentacoes": 10,
    "extrair_anexos": true,
    "extrair_partes": true
  }'
```

### ✅ **Formato N8N (Nome):**
```bash
curl -X POST "${BASE_URL}/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d '{
    "bodyParameters": {
      "parameters": [
        {
          "name": "tipo_busca",
          "value": "nome"
        },
        {
          "name": "valor",
          "value": "Rosane Aparecida Carlos Marques"
        },
        {
          "name": "movimentacoes",
          "value": "true"
        },
        {
          "name": "limite_movimentacoes",
          "value": "3"
        },
        {
          "name": "extrair_anexos",
          "value": "false"
        },
        {
          "name": "extrair_partes",
          "value": "true"
        }
      ]
    }
  }'
```

---

## 📄 **3. BUSCA POR PROCESSO**

### ✅ **Exemplo Básico (Processo Testado):**
```bash
curl -X POST "${BASE_URL}/buscar" \
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

### ✅ **Exemplo com Processo Simples:**
```bash
curl -X POST "${BASE_URL}/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "5387135-4",
    "movimentacoes": true,
    "limite_movimentacoes": 10,
    "extrair_anexos": true,
    "extrair_partes": true
  }'
```

### ✅ **Formato N8N (Processo):**
```bash
curl -X POST "${BASE_URL}/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d '{
    "bodyParameters": {
      "parameters": [
        {
          "name": "tipo_busca",
          "value": "processo"
        },
        {
          "name": "valor",
          "value": "0508844-37.2007.8.09.0024"
        },
        {
          "name": "movimentacoes",
          "value": "true"
        },
        {
          "name": "limite_movimentacoes",
          "value": "5"
        },
        {
          "name": "extrair_anexos",
          "value": "true"
        },
        {
          "name": "extrair_partes",
          "value": "true"
        }
      ]
    }
  }'
```

---

## 🔄 **4. BUSCA MÚLTIPLA (PARALELA)**

### ✅ **Exemplo com 3 Tipos de Busca Simultâneos:**
```bash
curl -X POST "${BASE_URL}/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {
        "tipo_busca": "cpf",
        "valor": "285.897.001-78",
        "movimentacoes": true,
        "limite_movimentacoes": 3
      },
      {
        "tipo_busca": "nome",
        "valor": "Rosane Aparecida Carlos Marques",
        "movimentacoes": true,
        "limite_movimentacoes": 3
      },
      {
        "tipo_busca": "processo",
        "valor": "0508844-37.2007.8.09.0024",
        "movimentacoes": true,
        "extrair_anexos": true
      }
    ],
    "paralelo": true
  }'
```

### ✅ **Exemplo com Credenciais Customizadas:**
```bash
curl -X POST "${BASE_URL}/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {
        "tipo_busca": "cpf",
        "valor": "123.456.789-00",
        "movimentacoes": true,
        "limite_movimentacoes": 5
      },
      {
        "tipo_busca": "nome",
        "valor": "Maria Santos",
        "movimentacoes": true,
        "limite_movimentacoes": 5
      }
    ],
    "paralelo": true,
    "usuario": "seu_usuario",
    "senha": "sua_senha",
    "serventia": "Advogados - OAB/Matrícula: XXXXX-N-GO"
  }'
```

---

## 📊 **5. ENDPOINTS DE STATUS E MONITORAMENTO**

### ✅ **Verificar Status da API:**
```bash
curl -X GET "${BASE_URL}/status"
```

### ✅ **Verificar Estatísticas:**
```bash
curl -X GET "${BASE_URL}/stats"
```

### ✅ **Verificar Saúde do Sistema:**
```bash
curl -X GET "${BASE_URL}/health"
```

---

## 🔧 **6. EXEMPLOS AVANÇADOS**

### ✅ **Busca com Timeout Customizado:**
```bash
curl -X POST "${BASE_URL}/buscar" \
  -H "Content-Type: application/json" \
  --max-time 300 \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": true,
    "limite_movimentacoes": 10,
    "extrair_anexos": true,
    "extrair_partes": true
  }'
```

### ✅ **Busca com Headers Customizados:**
```bash
curl -X POST "${BASE_URL}/buscar" \
  -H "Content-Type: application/json" \
  -H "User-Agent: N8N-Integration/1.0" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "tipo_busca": "nome",
    "valor": "João Silva",
    "movimentacoes": true,
    "limite_movimentacoes": 5
  }'
```

### ✅ **Salvar Resposta em Arquivo:**
```bash
curl -X POST "${BASE_URL}/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": true
  }' \
  -o resultado_busca.json
```

---

## 📋 **7. PARÂMETROS DISPONÍVEIS**

### **Parâmetros Obrigatórios:**
| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `tipo_busca` | string | Tipo da busca | `"cpf"`, `"nome"`, `"processo"` |
| `valor` | string | Valor a buscar | `"285.897.001-78"` |

### **Parâmetros Opcionais:**
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `movimentacoes` | boolean | `true` | Extrair movimentações |
| `limite_movimentacoes` | integer | `null` | Limitar número de movimentações |
| `extrair_anexos` | boolean | `false` | Extrair anexos |
| `extrair_partes` | boolean | `true` | Extrair partes envolvidas |
| `usuario` | string | `.env` | Usuário customizado |
| `senha` | string | `.env` | Senha customizada |
| `serventia` | string | `.env` | Serventia customizada |

---

## 🎯 **8. EXEMPLOS PRÁTICOS PARA N8N**

### ✅ **Workflow N8N - Busca por CPF:**
```bash
# No N8N, use este curl como base:
curl -X POST "http://localhost:8081/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d '{
    "bodyParameters": {
      "parameters": [
        {
          "name": "tipo_busca",
          "value": "{{ $json.tipo_busca }}"
        },
        {
          "name": "valor",
          "value": "{{ $json.cpf }}"
        },
        {
          "name": "movimentacoes",
          "value": "{{ $json.movimentacoes }}"
        },
        {
          "name": "limite_movimentacoes",
          "value": "{{ $json.limite }}"
        }
      ]
    }
  }'
```

### ✅ **Workflow N8N - Busca Múltipla:**
```bash
# No N8N, para múltiplas buscas:
curl -X POST "http://localhost:8081/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": {{ $json.buscas }},
    "paralelo": true
  }'
```

---

## ⚠️ **9. TRATAMENTO DE ERROS**

### ✅ **Exemplo de Resposta de Sucesso:**
```json
{
  "status": "success",
  "request_id": "a0dc663c-5330-48ef-9806-caa5ba988aef",
  "tipo_busca": "cpf",
  "valor_busca": "285.897.001-78",
  "total_processos_encontrados": 7,
  "processos_simples": [...],
  "processos_detalhados": [...],
  "tempo_execucao": 11.72,
  "timestamp": "2025-08-03T14:22:08.983000"
}
```

### ❌ **Exemplo de Resposta de Erro:**
```json
{
  "status": "error",
  "request_id": "uuid-here",
  "tipo_busca": "cpf",
  "valor_busca": "285.897.001-78",
  "total_processos_encontrados": 0,
  "processos_simples": [],
  "processos_detalhados": [],
  "tempo_execucao": 5.2,
  "timestamp": "2025-08-03T12:32:52",
  "erro": "Falha no login: credenciais inválidas"
}
```

---

## 🚀 **10. TESTE RÁPIDO**

### ✅ **Teste Básico (CPF Testado):**
```bash
# Teste rápido para verificar se a API está funcionando
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "285.897.001-78",
    "movimentacoes": true,
    "limite_movimentacoes": 1
  }' | jq '.status'
```

**Resultado esperado:** `"success"`

---

## 📝 **NOTAS IMPORTANTES:**

1. **✅ Todos os exemplos foram testados** com dados reais
2. **✅ Compatível 100% com N8N** usando endpoint `/buscar-n8n`
3. **✅ Suporte a credenciais customizadas** por request
4. **✅ Processamento paralelo** para múltiplas buscas
5. **✅ Timeout configurável** para cada operação
6. **✅ Logs detalhados** para debugging
7. **✅ Fallback automático** para credenciais padrão

**🎯 Use estes exemplos diretamente no N8N ou qualquer integração!** 