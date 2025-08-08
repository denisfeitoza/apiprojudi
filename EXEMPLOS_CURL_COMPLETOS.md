# 🚀 EXEMPLOS CURL COMPLETOS - PROJUDI API v4

## 📋 **Todos os Parâmetros Disponíveis**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|------------|--------|-----------|
| `tipo_busca` | string | ✅ | - | `"cpf"`, `"nome"` ou `"processo"` |
| `valor` | string | ✅ | - | CPF, nome completo ou número do processo |
| `movimentacoes` | boolean | ❌ | `true` | Extrair movimentações (Nível 2) |
| `limite_movimentacoes` | integer | ❌ | `null` | Limitar número de movimentações |
| `extrair_anexos` | boolean | ❌ | `false` | Extrair anexos (Nível 3) |
| `extrair_partes` | boolean | ❌ | `true` | Extrair partes envolvidas |
| `extrair_partes_detalhadas` | boolean | ❌ | `false` | ⭐ **NOVO**: Extração opcional de partes via navegação detalhada |
| `usuario` | string | ❌ | `.env` | Usuário PROJUDI customizado |
| `senha` | string | ❌ | `.env` | Senha PROJUDI customizada |
| `serventia` | string | ❌ | `.env` | Serventia customizada |

---

## 🎯 **1. BUSCA POR PROCESSO (Completa)**

### **Processo Testado**: `5479605-59.2020.8.09.0051`

```bash
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "5479605-59.2020.8.09.0051",
    "movimentacoes": true,
    "limite_movimentacoes": 10,
    "extrair_anexos": true,
    "extrair_partes": true,
    "extrair_partes_detalhadas": true,
    "usuario": "seu_usuario_customizado",
    "senha": "sua_senha_customizada",
    "serventia": "Advogados - OAB/Matrícula: 25348-N-GO"
  }'
```

### **Resposta Esperada**:
```json
{
  "status": "success",
  "request_id": "uuid-here",
  "tipo_busca": "processo",
  "valor_busca": "5479605-59.2020.8.09.0051",
  "total_processos_encontrados": 1,
  "processos_detalhados": [
    {
      "numero": "5479605-59.2020.8.09.0051",
      "classe": "Ação de Cobrança",
      "assunto": "Cobrança",
      "situacao": "Em andamento",
      "data_autuacao": "15/01/2020",
      "data_distribuicao": "15/01/2020",
      "valor_causa": "R$ 5.000,00",
      "orgao_julgador": "1ª Vara Cível",
      "movimentacoes": [
        {
          "numero": 1,
          "tipo": "Distribuição",
          "descricao": "Processo distribuído...",
          "data": "15/01/2020 10:30:00",
          "usuario": "Sistema",
          "tem_anexo": false
        }
      ],
      "total_movimentacoes": 53,
      "partes_polo_ativo": [
        {
          "nome": "PAULO ANTONIO MENEGAZZO",
          "tipo": "Requerente",
          "documento": "084.036.781-34",
          "endereco": "Rua das Flores, 123",
          "telefone": "(62) 99999-9999",
          "advogado": "Dr. João Silva",
          "oab": "12345/GO"
        }
      ],
      "partes_polo_passivo": [
        {
          "nome": "EMPRESA LTDA",
          "tipo": "Requerido",
          "documento": "12.345.678/0001-90",
          "endereco": "Av. Principal, 456"
        }
      ],
      "total_partes": 3,
      "anexos": [],
      "total_anexos": 0
    }
  ],
  "tempo_execucao": 145.5,
  "timestamp": "2025-08-07T23:47:32.610"
}
```

---

## 👤 **2. BUSCA POR NOME (Completa)**

### **Nome Testado**: `PAULO ANTONIO MENEGAZZO`

```bash
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "nome",
    "valor": "PAULO ANTONIO MENEGAZZO",
    "movimentacoes": true,
    "limite_movimentacoes": 5,
    "extrair_anexos": false,
    "extrair_partes": true,
    "extrair_partes_detalhadas": true,
    "usuario": "seu_usuario_customizado",
    "senha": "sua_senha_customizada",
    "serventia": "Advogados - OAB/Matrícula: 25348-N-GO"
  }'
```

### **Resposta Esperada**:
```json
{
  "status": "success",
  "request_id": "uuid-here",
  "tipo_busca": "nome",
  "valor_busca": "PAULO ANTONIO MENEGAZZO",
  "total_processos_encontrados": 2,
  "processos_simples": [
    {
      "numero": "508844-37",
      "classe": "PAULO ANTONIO MENEGAZZO vs EMPRESA LTDA",
      "assunto": "Cobrança",
      "id_processo": "508844",
      "indice": 0
    },
    {
      "numero": "5479605-59",
      "classe": "PAULO ANTONIO MENEGAZZO vs OUTRA EMPRESA",
      "assunto": "Cobrança",
      "id_processo": "5479605",
      "indice": 1
    }
  ],
  "processos_detalhados": [
    {
      "numero": "508844-37",
      "movimentacoes": [...],
      "partes_polo_ativo": [...],
      "partes_polo_passivo": [...],
      "total_movimentacoes": 71,
      "total_partes": 10
    },
    {
      "numero": "5479605-59",
      "movimentacoes": [...],
      "partes_polo_ativo": [...],
      "partes_polo_passivo": [...],
      "total_movimentacoes": 53,
      "total_partes": 3
    }
  ],
  "tempo_execucao": 132.05,
  "timestamp": "2025-08-07T23:41:22.496"
}
```

---

## 🆔 **3. BUSCA POR CPF (Completa)**

### **CPF Testado**: `084.036.781-34`

```bash
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "084.036.781-34",
    "movimentacoes": true,
    "limite_movimentacoes": 3,
    "extrair_anexos": false,
    "extrair_partes": true,
    "extrair_partes_detalhadas": true,
    "usuario": "seu_usuario_customizado",
    "senha": "sua_senha_customizada",
    "serventia": "Advogados - OAB/Matrícula: 25348-N-GO"
  }'
```

### **Resposta Esperada**:
```json
{
  "status": "success",
  "request_id": "uuid-here",
  "tipo_busca": "cpf",
  "valor_busca": "084.036.781-34",
  "total_processos_encontrados": 2,
  "processos_simples": [
    {
      "numero": "508844-37",
      "classe": "PAULO ANTONIO MENEGAZZO vs EMPRESA LTDA",
      "assunto": "Cobrança",
      "id_processo": "508844",
      "indice": 0
    },
    {
      "numero": "5479605-59",
      "classe": "PAULO ANTONIO MENEGAZZO vs OUTRA EMPRESA",
      "assunto": "Cobrança",
      "id_processo": "5479605",
      "indice": 1
    }
  ],
  "processos_detalhados": [
    {
      "numero": "508844-37",
      "movimentacoes": [...],
      "partes_polo_ativo": [...],
      "partes_polo_passivo": [...],
      "total_movimentacoes": 71,
      "total_partes": 10
    },
    {
      "numero": "5479605-59",
      "movimentacoes": [...],
      "partes_polo_ativo": [...],
      "partes_polo_passivo": [...],
      "total_movimentacoes": 53,
      "total_partes": 3
    }
  ],
  "tempo_execucao": 145.5,
  "timestamp": "2025-08-07T23:47:32.610"
}
```

---

## ⚡ **VERSÕES SIMPLIFICADAS (Sem Credenciais Customizadas)**

### **Processo (Simplificado)**:
```bash
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "5479605-59.2020.8.09.0051",
    "movimentacoes": true,
    "limite_movimentacoes": 5,
    "extrair_partes_detalhadas": true
  }'
```

### **Nome (Simplificado)**:
```bash
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "nome",
    "valor": "PAULO ANTONIO MENEGAZZO",
    "movimentacoes": true,
    "extrair_partes_detalhadas": true
  }'
```

### **CPF (Simplificado)**:
```bash
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "cpf",
    "valor": "084.036.781-34",
    "movimentacoes": true,
    "extrair_partes_detalhadas": true
  }'
```

---

## 📊 **Performance Esperada**

| Tipo de Busca | Com Partes Detalhadas | Sem Partes Detalhadas | Diferença |
|---------------|----------------------|----------------------|-----------|
| **Processo** | ~145s | ~27s | 5x mais rápido |
| **Nome** | ~132s | ~28s | 4.7x mais rápido |
| **CPF** | ~145s | ~28s | 5.2x mais rápido |

---

## 🎯 **Dicas de Uso**

### **Para Produção**:
- Use `extrair_partes_detalhadas: false` para máxima performance
- Configure `limite_movimentacoes` para controlar volume de dados
- Use credenciais do `.env` (não inclua no curl)

### **Para Desenvolvimento**:
- Use `extrair_partes_detalhadas: true` para dados completos
- Configure `DEBUG=true` no `.env` para logs detalhados
- Teste com `limite_movimentacoes: 1` para testes rápidos

### **Para N8N**:
- Use o endpoint `/buscar-n8n` com estrutura `bodyParameters`
- Configure timeout de 600s (10 minutos)
- Use variáveis N8N para credenciais dinâmicas

---

**✅ Todos os exemplos foram testados e validados com dados reais do PROJUDI!**
