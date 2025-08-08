#!/bin/bash

echo "🔍 EXEMPLOS CURL COMPLETOS - PROJUDI API v4"
echo "=============================================="

# Configurações
API_URL="http://localhost:8081"
CPF_EXEMPLO="084.036.781-34"
NOME_EXEMPLO="PAULO ANTONIO MENEGAZZO"
PROCESSO_EXEMPLO="5539441-98.2023.8.09.0069"

echo ""
echo "📋 1. BUSCA POR CPF - Todas as Variações"
echo "----------------------------------------"

echo ""
echo "🔸 CPF - Busca Básica (apenas lista processos)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\"
  }"'

echo ""
echo "🔸 CPF - Sem Movimentações (mais rápido)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\",
    \"movimentacoes\": false,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 CPF - Com Movimentações Limitadas (3 últimas)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 CPF - Com Partes Detalhadas"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 5,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": true
  }"'

echo ""
echo "🔸 CPF - Com Anexos"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": true,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 CPF - COMPLETO (tudo ativado)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 10,
    \"extrair_anexos\": true,
    \"extrair_partes_detalhadas\": true
  }"'

echo ""
echo "📋 2. BUSCA POR NOME - Todas as Variações"
echo "----------------------------------------"

echo ""
echo "🔸 NOME - Busca Básica"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"nome\",
    \"valor\": \"'$NOME_EXEMPLO'\"
  }"'

echo ""
echo "🔸 NOME - Apenas Processos (sem detalhes)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"nome\",
    \"valor\": \"'$NOME_EXEMPLO'\",
    \"movimentacoes\": false,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 NOME - Com Movimentações (5 últimas)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"nome\",
    \"valor\": \"'$NOME_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 5,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 NOME - Com Partes Detalhadas"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"nome\",
    \"valor\": \"'$NOME_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": true
  }"'

echo ""
echo "🔸 NOME - Busca Parcial (parte do nome)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"nome\",
    \"valor\": \"PAULO ANTONIO\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "📋 3. BUSCA POR PROCESSO - Todas as Variações"
echo "--------------------------------------------"

echo ""
echo "🔸 PROCESSO - Busca Básica"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"'$PROCESSO_EXEMPLO'\"
  }"'

echo ""
echo "🔸 PROCESSO - Apenas Dados Básicos"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"'$PROCESSO_EXEMPLO'\",
    \"movimentacoes\": false,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 PROCESSO - Últimas 3 Movimentações"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"'$PROCESSO_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 PROCESSO - Com Partes Detalhadas"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"'$PROCESSO_EXEMPLO'\",
    \"movimentacoes\": false,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": true
  }"'

echo ""
echo "🔸 PROCESSO - Com Anexos"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"'$PROCESSO_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 5,
    \"extrair_anexos\": true,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 PROCESSO - COMPLETO (tudo ativado)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"'$PROCESSO_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 20,
    \"extrair_anexos\": true,
    \"extrair_partes_detalhadas\": true
  }"'

echo ""
echo "🔸 PROCESSO - Formato Alternativo (sem pontos)"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"55394419820238090069\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "📋 4. CREDENCIAIS CUSTOMIZADAS"
echo "------------------------------"

echo ""
echo "🔸 Com Credenciais Personalizadas"
echo 'curl -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false,
    \"projudi_user\": \"seu_usuario\",
    \"projudi_pass\": \"sua_senha\",
    \"serventia\": \"sua_serventia\"
  }"'

echo ""
echo "📋 5. ENDPOINTS ADICIONAIS"
echo "--------------------------"

echo ""
echo "🔸 Status da API"
echo 'curl -X GET "'$API_URL'/health"'

echo ""
echo "🔸 Estatísticas"
echo 'curl -X GET "'$API_URL'/stats"'

echo ""
echo "🔸 Reset de Sessões"
echo 'curl -X POST "'$API_URL'/reset"'

echo ""
echo "📋 6. FORMATO N8N (para automações)"
echo "----------------------------------"

echo ""
echo "🔸 Formato N8N - CPF"
echo 'curl -X POST "'$API_URL'/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d "{
    \"bodyParameters\": {
      \"parameters\": [
        {\"name\": \"tipo_busca\", \"value\": \"cpf\"},
        {\"name\": \"valor\", \"value\": \"'$CPF_EXEMPLO'\"},
        {\"name\": \"movimentacoes\", \"value\": \"true\"},
        {\"name\": \"limite_movimentacoes\", \"value\": \"3\"},
        {\"name\": \"extrair_anexos\", \"value\": \"false\"},
        {\"name\": \"extrair_partes_detalhadas\", \"value\": \"false\"}
      ]
    }
  }"'

echo ""
echo "📋 7. TESTES DE PERFORMANCE"
echo "---------------------------"

echo ""
echo "🔸 Teste Rápido (só lista processos)"
echo 'time curl -s -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"'$CPF_EXEMPLO'\",
    \"movimentacoes\": false,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }" | jq ".tempo_execucao"'

echo ""
echo "🔸 Teste Completo (com timing)"
echo 'time curl -s -X POST "'$API_URL'/buscar" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"'$PROCESSO_EXEMPLO'\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 5,
    \"extrair_anexos\": true,
    \"extrair_partes_detalhadas\": true
  }" | jq "{tempo_execucao, total_processos_encontrados, status}"'

echo ""
echo "=============================================="
echo "📝 PARÂMETROS DISPONÍVEIS:"
echo "• tipo_busca: \"cpf\", \"nome\", \"processo\""
echo "• valor: string com CPF/nome/número do processo"
echo "• movimentacoes: true/false (padrão: true)"
echo "• limite_movimentacoes: número (padrão: null = todas)"
echo "• extrair_anexos: true/false (padrão: false)"
echo "• extrair_partes_detalhadas: true/false (padrão: false)"
echo "• projudi_user: string (opcional)"
echo "• projudi_pass: string (opcional)"
echo "• serventia: string (opcional)"
echo "=============================================="
