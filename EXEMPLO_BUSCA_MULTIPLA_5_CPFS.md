# 🚀 **BUSCA MÚLTIPLA PARALELA - 5 CPFs SIMULTÂNEOS**

## 📋 **O QUE É A BUSCA MÚLTIPLA PARALELA?**

A **busca múltipla paralela** permite executar **várias buscas simultaneamente** usando o endpoint `/buscar-multiplo`. É perfeita para:

- ✅ **Buscar 5 CPFs de clientes** ao mesmo tempo
- ✅ **Processar múltiplos nomes** simultaneamente  
- ✅ **Extrair dados de vários processos** em paralelo
- ✅ **Otimizar tempo de execução** (muito mais rápido que sequencial)

---

## 🎯 **EXEMPLO PRÁTICO: 5 CPFs DE CLIENTES**

### **📊 Dados dos Clientes:**
```json
{
  "cliente_1": "285.897.001-78",  // Rosane Aparecida Carlos Marques
  "cliente_2": "123.456.789-00",  // João Silva Santos
  "cliente_3": "987.654.321-00",  // Maria Santos Oliveira
  "cliente_4": "456.789.123-00",  // Pedro Costa Lima
  "cliente_5": "789.123.456-00"   // Ana Paula Ferreira
}
```

### **🚀 CURL para 5 CPFs Simultâneos:**

```bash
curl -X POST "http://localhost:8081/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {
        "tipo_busca": "cpf",
        "valor": "285.897.001-78",
        "movimentacoes": true,
        "limite_movimentacoes": 5,
        "extrair_anexos": false,
        "extrair_partes": true
      },
      {
        "tipo_busca": "cpf",
        "valor": "123.456.789-00",
        "movimentacoes": true,
        "limite_movimentacoes": 3,
        "extrair_anexos": true,
        "extrair_partes": true
      },
      {
        "tipo_busca": "cpf",
        "valor": "987.654.321-00",
        "movimentacoes": true,
        "limite_movimentacoes": 10,
        "extrair_anexos": false,
        "extrair_partes": true
      },
      {
        "tipo_busca": "cpf",
        "valor": "456.789.123-00",
        "movimentacoes": true,
        "limite_movimentacoes": 7,
        "extrair_anexos": true,
        "extrair_partes": true
      },
      {
        "tipo_busca": "cpf",
        "valor": "789.123.456-00",
        "movimentacoes": true,
        "limite_movimentacoes": 5,
        "extrair_anexos": false,
        "extrair_partes": true
      }
    ],
    "paralelo": true
  }'
```

---

## 📊 **RESPOSTA ESPERADA:**

```json
{
  "status": "success",
  "total_buscas": 5,
  "buscas_concluidas": 5,
  "tempo_total": 45.23,
  "timestamp": "2025-08-05T06:30:15.123456",
  "resultados": {
    "busca_0": {
      "status": "success",
      "request_id": "batch_1733382615_0",
      "tipo_busca": "cpf",
      "valor_busca": "285.897.001-78",
      "total_processos_encontrados": 7,
      "processos_simples": [
        {
          "numero": "5387135-4",
          "classe": "Rosane Aparecida Carlos Marques vs Abadia Campos Amaral",
          "assunto": "Cobrança",
          "id_processo": "5387135",
          "indice": 0
        }
      ],
      "processos_detalhados": [...],
      "tempo_execucao": 12.45
    },
    "busca_1": {
      "status": "success",
      "request_id": "batch_1733382615_1",
      "tipo_busca": "cpf",
      "valor_busca": "123.456.789-00",
      "total_processos_encontrados": 3,
      "processos_simples": [...],
      "processos_detalhados": [...],
      "tempo_execucao": 8.92
    },
    "busca_2": {
      "status": "success",
      "request_id": "batch_1733382615_2",
      "tipo_busca": "cpf",
      "valor_busca": "987.654.321-00",
      "total_processos_encontrados": 12,
      "processos_simples": [...],
      "processos_detalhados": [...],
      "tempo_execucao": 15.67
    },
    "busca_3": {
      "status": "success",
      "request_id": "batch_1733382615_3",
      "tipo_busca": "cpf",
      "valor_busca": "456.789.123-00",
      "total_processos_encontrados": 5,
      "processos_simples": [...],
      "processos_detalhados": [...],
      "tempo_execucao": 11.23
    },
    "busca_4": {
      "status": "success",
      "request_id": "batch_1733382615_4",
      "tipo_busca": "cpf",
      "valor_busca": "789.123.456-00",
      "total_processos_encontrados": 2,
      "processos_simples": [...],
      "processos_detalhados": [...],
      "tempo_execucao": 6.89
    }
  }
}
```

---

## ⚙️ **OPÇÕES E CONFIGURAÇÕES DISPONÍVEIS:**

### **🔧 Parâmetros por CPF:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `tipo_busca` | string | - | **Sempre "cpf"** para CPFs |
| `valor` | string | - | **CPF do cliente** |
| `movimentacoes` | boolean | `true` | **Extrair movimentações** |
| `limite_movimentacoes` | integer | `null` | **Quantas movimentações** (ex: 5, 10, 20) |
| `extrair_anexos` | boolean | `false` | **Baixar anexos** (mais lento) |
| `extrair_partes` | boolean | `true` | **Extrair partes envolvidas** |
| `usuario` | string | `.env` | **Usuário customizado** |
| `senha` | string | `.env` | **Senha customizada** |
| `serventia` | string | `.env` | **Serventia customizada** |

### **🚀 Configurações Globais:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `paralelo` | boolean | `true` | **Executar simultaneamente** |
| `buscas` | array | - | **Lista de buscas** (máx. 10) |

---

## 🎯 **EXEMPLOS PRÁTICOS DIFERENTES:**

### **1. 📋 Busca Rápida (Sem Anexos):**
```bash
curl -X POST "http://localhost:8081/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {"tipo_busca": "cpf", "valor": "285.897.001-78", "movimentacoes": true, "limite_movimentacoes": 3},
      {"tipo_busca": "cpf", "valor": "123.456.789-00", "movimentacoes": true, "limite_movimentacoes": 3},
      {"tipo_busca": "cpf", "valor": "987.654.321-00", "movimentacoes": true, "limite_movimentacoes": 3},
      {"tipo_busca": "cpf", "valor": "456.789.123-00", "movimentacoes": true, "limite_movimentacoes": 3},
      {"tipo_busca": "cpf", "valor": "789.123.456-00", "movimentacoes": true, "limite_movimentacoes": 3}
    ],
    "paralelo": true
  }'
```

### **2. 📎 Busca Completa (Com Anexos):**
```bash
curl -X POST "http://localhost:8081/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {"tipo_busca": "cpf", "valor": "285.897.001-78", "movimentacoes": true, "limite_movimentacoes": 10, "extrair_anexos": true},
      {"tipo_busca": "cpf", "valor": "123.456.789-00", "movimentacoes": true, "limite_movimentacoes": 10, "extrair_anexos": true},
      {"tipo_busca": "cpf", "valor": "987.654.321-00", "movimentacoes": true, "limite_movimentacoes": 10, "extrair_anexos": true},
      {"tipo_busca": "cpf", "valor": "456.789.123-00", "movimentacoes": true, "limite_movimentacoes": 10, "extrair_anexos": true},
      {"tipo_busca": "cpf", "valor": "789.123.456-00", "movimentacoes": true, "limite_movimentacoes": 10, "extrair_anexos": true}
    ],
    "paralelo": true
  }'
```

### **3. 🔐 Com Credenciais Customizadas:**
```bash
curl -X POST "http://localhost:8081/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {"tipo_busca": "cpf", "valor": "285.897.001-78", "movimentacoes": true, "limite_movimentacoes": 5},
      {"tipo_busca": "cpf", "valor": "123.456.789-00", "movimentacoes": true, "limite_movimentacoes": 5},
      {"tipo_busca": "cpf", "valor": "987.654.321-00", "movimentacoes": true, "limite_movimentacoes": 5},
      {"tipo_busca": "cpf", "valor": "456.789.123-00", "movimentacoes": true, "limite_movimentacoes": 5},
      {"tipo_busca": "cpf", "valor": "789.123.456-00", "movimentacoes": true, "limite_movimentacoes": 5}
    ],
    "paralelo": true,
    "usuario": "seu_usuario",
    "senha": "sua_senha",
    "serventia": "Advogados - OAB/Matrícula: XXXXX-N-GO"
  }'
```

### **4. 🔄 Misto (CPF + Nome + Processo):**
```bash
curl -X POST "http://localhost:8081/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {"tipo_busca": "cpf", "valor": "285.897.001-78", "movimentacoes": true, "limite_movimentacoes": 5},
      {"tipo_busca": "nome", "valor": "João Silva Santos", "movimentacoes": true, "limite_movimentacoes": 5},
      {"tipo_busca": "processo", "valor": "0508844-37.2007.8.09.0024", "movimentacoes": true, "extrair_anexos": true},
      {"tipo_busca": "cpf", "valor": "987.654.321-00", "movimentacoes": true, "limite_movimentacoes": 5},
      {"tipo_busca": "nome", "valor": "Maria Santos", "movimentacoes": true, "limite_movimentacoes": 5}
    ],
    "paralelo": true
  }'
```

---

## 📈 **VANTAGENS DA BUSCA PARALELA:**

### **⚡ Performance:**
- **5 CPFs simultâneos** = ~45 segundos
- **5 CPFs sequenciais** = ~150 segundos
- **Economia de tempo:** ~70% mais rápido

### **🎯 Flexibilidade:**
- ✅ **Diferentes configurações** por CPF
- ✅ **Limites personalizados** de movimentações
- ✅ **Anexos opcionais** por cliente
- ✅ **Credenciais customizadas**

### **🛡️ Confiabilidade:**
- ✅ **Execução independente** (1 erro não afeta outros)
- ✅ **Status individual** por busca
- ✅ **Retry automático** em falhas
- ✅ **Logs detalhados** por operação

---

## 🎯 **EXEMPLO N8N:**

### **Workflow N8N para 5 CPFs:**
```bash
curl -X POST "http://localhost:8081/buscar-multiplo" \
  -H "Content-Type: application/json" \
  -d '{
    "buscas": [
      {
        "tipo_busca": "cpf",
        "valor": "{{ $json.cliente1_cpf }}",
        "movimentacoes": true,
        "limite_movimentacoes": {{ $json.limite_movimentacoes }}
      },
      {
        "tipo_busca": "cpf",
        "valor": "{{ $json.cliente2_cpf }}",
        "movimentacoes": true,
        "limite_movimentacoes": {{ $json.limite_movimentacoes }}
      },
      {
        "tipo_busca": "cpf",
        "valor": "{{ $json.cliente3_cpf }}",
        "movimentacoes": true,
        "limite_movimentacoes": {{ $json.limite_movimentacoes }}
      },
      {
        "tipo_busca": "cpf",
        "valor": "{{ $json.cliente4_cpf }}",
        "movimentacoes": true,
        "limite_movimentacoes": {{ $json.limite_movimentacoes }}
      },
      {
        "tipo_busca": "cpf",
        "valor": "{{ $json.cliente5_cpf }}",
        "movimentacoes": true,
        "limite_movimentacoes": {{ $json.limite_movimentacoes }}
      }
    ],
    "paralelo": true
  }'
```

---

## 📊 **ANÁLISE DOS RESULTADOS:**

### **Status da Resposta:**
- `"success"`: Todas as 5 buscas funcionaram
- `"partial"`: Algumas funcionaram, outras falharam
- `"error"`: Todas falharam

### **Dados por Cliente:**
```json
{
  "busca_0": {
    "total_processos_encontrados": 7,
    "tempo_execucao": 12.45,
    "processos_detalhados": [
      {
        "numero": "5387135-4",
        "movimentacoes": [...],  // 5 movimentações
        "partes_polo_ativo": [...],
        "partes_polo_passivo": [...],
        "anexos": [...]  // Se extrair_anexos = true
      }
    ]
  }
}
```

---

## 🚀 **DICAS DE USO:**

### **1. 🎯 Para Busca Rápida:**
- Use `"limite_movimentacoes": 3`
- Use `"extrair_anexos": false`
- Tempo estimado: ~30-45 segundos

### **2. 📋 Para Busca Completa:**
- Use `"limite_movimentacoes": 10`
- Use `"extrair_anexos": true`
- Tempo estimado: ~60-90 segundos

### **3. 🔄 Para Monitoramento:**
- Use `"paralelo": true` sempre
- Monitore `tempo_total` na resposta
- Verifique `status` individual de cada busca

### **4. 🛡️ Para Produção:**
- Máximo 10 buscas simultâneas
- Use credenciais customizadas se necessário
- Monitore logs para debugging

---

## ✅ **RESUMO:**

**Sim, você pode buscar 5 CPFs simultaneamente!**

- ✅ **5 CPFs ao mesmo tempo** = ~45 segundos
- ✅ **Configurações individuais** por cliente
- ✅ **Limite de movimentações** personalizado
- ✅ **Anexos opcionais** por busca
- ✅ **Credenciais customizadas** suportadas
- ✅ **100% compatível com N8N**
- ✅ **Execução paralela** otimizada

**🎯 Use o endpoint `/buscar-multiplo` com `"paralelo": true`!** 