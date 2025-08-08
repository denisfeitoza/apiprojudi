# 🧪 Teste da API PROJUDI com `extrair_partes_detalhadas=false`

Este documento descreve como testar a API PROJUDI com a configuração `extrair_partes_detalhadas=false`.

## 📋 Resumo da Instalação

✅ **Projeto clonado**: `https://github.com/denisfeitoza/apiprojudi`  
✅ **Dependências instaladas**: `pip install -r requirements.txt`  
✅ **Playwright configurado**: Firefox para macOS, Chromium para Linux  
✅ **Configuração testada**: `extrair_partes_detalhadas=false`  

## 🔧 Configuração Atual

### Arquivo `.env`
```bash
# Configurações da API
DEBUG=true
HOST=0.0.0.0
PORT=8081

# Configurações do PROJUDI
PROJUDI_USER=34930230144
PROJUDI_PASS=Joaquim1*
DEFAULT_SERVENTIA=Advogados - OAB/Matrícula: 25348-N-GO
PROJUDI_BASE_URL=https://projudi.tjgo.jus.br
PROJUDI_LOGIN_URL=https://projudi.tjgo.jus.br/LogOn?PaginaAtual=-200

# Configurações do Playwright
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_SLOW_MO=0
PLAYWRIGHT_TIMEOUT=60000
MAX_BROWSERS=1

# Configurações Redis
REDIS_URL=redis://localhost:6379
USE_REDIS=false

# Configurações de arquivos
TEMP_DIR=./temp
DOWNLOADS_DIR=./downloads

# Configurações de processamento
MAX_CONCURRENT_REQUESTS=1
REQUEST_TIMEOUT=300
```

### Modificações Realizadas

1. **Session Manager**: Configurado para usar Firefox no macOS
2. **Playwright**: Instalado e configurado corretamente
3. **Testes**: Criados scripts de teste específicos

## 🧪 Testes Realizados

### 1. Teste de Modelos (✅ Sucesso)
```bash
python test_api_simple.py
```

**Resultado**: Confirma que `extrair_partes_detalhadas=false` funciona corretamente:
- Partes são extraídas sem informações detalhadas
- Estrutura da resposta está correta
- Campos como endereço, telefone, email, OAB ficam como `null`

### 2. Teste do Playwright (✅ Sucesso)
```bash
python test_playwright.py
```

**Resultado**: Firefox funciona corretamente no macOS

## 📊 Diferença entre `extrair_partes_detalhadas=true` e `false`

### Com `extrair_partes_detalhadas=false`:
```json
{
  "nome": "João Silva",
  "tipo": "Autor",
  "documento": "123.456.789-00",
  "endereco": null,
  "telefone": null,
  "email": null,
  "advogado": null,
  "oab": null
}
```

### Com `extrair_partes_detalhadas=true`:
```json
{
  "nome": "João Silva",
  "tipo": "Autor",
  "documento": "123.456.789-00",
  "endereco": "Rua das Flores, 123 - Centro",
  "telefone": "(11) 99999-9999",
  "email": "joao.silva@email.com",
  "advogado": "Dr. Advogado",
  "oab": "123456/SP"
}
```

## 🚀 Como Testar a API

### 1. Iniciar a API
```bash
python main.py
```

### 2. Verificar se está funcionando
```bash
curl -X GET "http://localhost:8081/health"
```

### 3. Testar com partes detalhadas = false
```bash
curl -X POST "http://localhost:8081/buscar" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_busca": "processo",
    "valor": "0508844-37.2007.8.09.0024",
    "extrair_partes_detalhadas": false,
    "movimentacoes": true,
    "extrair_anexos": false
  }'
```

## 📝 Exemplos de Comandos

Execute o script de exemplos:
```bash
./exemplo_curl_parts_false.sh
```

### Exemplos disponíveis:
1. **Teste básico** com `extrair_partes_detalhadas=false` (sem partes)
2. **Busca por CPF** sem extração de partes
3. **Busca por nome** sem extração de partes
4. **Teste com limite** de movimentações
5. **Health check** da API
6. **Status** da API

## ⚠️ Problemas Encontrados

### 1. Playwright no macOS
- **Problema**: Chromium não funciona corretamente
- **Solução**: Configurado para usar Firefox no macOS
- **Status**: ✅ Resolvido

### 2. Sessões do Playwright
- **Problema**: Erro ao criar sessões
- **Causa**: Configuração específica do macOS
- **Status**: 🔄 Em investigação

## 🎯 Próximos Passos

1. **Resolver problemas de sessão** do Playwright
2. **Testar com dados reais** do PROJUDI
3. **Validar performance** com `extrair_partes_detalhadas=false`
4. **Documentar diferenças** de tempo de resposta

## 📁 Arquivos Criados

- `test_api_simple.py` - Teste dos modelos Pydantic
- `test_playwright.py` - Teste do Playwright
- `exemplo_curl_parts_false.sh` - Exemplos de comandos curl
- `README_TESTE_PARTS_FALSE.md` - Este documento

## 🔍 Logs e Debug

Para verificar logs da aplicação:
```bash
tail -f logs/projudi_api.log
```

Para verificar se a API está rodando:
```bash
ps aux | grep python
```

---

**Status**: ✅ Instalação concluída, testes básicos funcionando  
**Próximo**: Resolver problemas de sessão do Playwright para testes completos
