#!/bin/bash

echo "🔍 CURLS CORRETOS PARA N8N - PROJUDI API v4"
echo "==========================================="

# URL para VPS
VPS_URL="http://apis_projudi:8081"
LOCAL_URL="http://localhost:8081"

echo ""
echo "📋 1. BUSCA POR CPF - Formatos N8N"
echo "-----------------------------------"

echo ""
echo "🔸 CPF - Busca Simples (N8N formato direto)"
echo "CORRETO para seu N8N atual:"
echo 'curl -X POST "'$VPS_URL'/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"084.036.781-34\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "🔸 CPF - Com Partes Detalhadas"
echo 'curl -X POST "'$VPS_URL'/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"084.036.781-34\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 10,
    \"extrair_anexos\": true,
    \"extrair_partes_detalhadas\": true
  }"'

echo ""
echo "📋 2. BUSCA POR NOME - Formatos N8N"
echo "------------------------------------"

echo ""
echo "🔸 NOME - Busca Simples"
echo 'curl -X POST "'$VPS_URL'/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"nome\",
    \"valor\": \"PAULO ANTONIO MENEGAZZO\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 5,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "📋 3. BUSCA POR PROCESSO - Formatos N8N"
echo "---------------------------------------"

echo ""
echo "🔸 PROCESSO - Busca Simples"
echo 'curl -X POST "'$VPS_URL'/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"processo\",
    \"valor\": \"5539441-98.2023.8.09.0069\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": true
  }"'

echo ""
echo "📋 4. CONFIGURAÇÃO CORRETA NO N8N"
echo "==================================="

echo ""
echo "No seu N8N, configure assim:"
echo ""
echo "🔧 HTTP Request Node:"
echo "• Method: POST"
echo "• URL: http://apis_projudi:8081/buscar-n8n"
echo "• Send Body: true"
echo "• Body Content Type: JSON"
echo ""
echo "🔧 Body (JSON):"
echo "{"
echo "  \"tipo_busca\": \"cpf\","
echo "  \"valor\": \"084.036.781-34\","
echo "  \"movimentacoes\": true,"
echo "  \"limite_movimentacoes\": 10,"
echo "  \"extrair_anexos\": true,"
echo "  \"extrair_partes_detalhadas\": true"
echo "}"

echo ""
echo "📋 5. TESTE LOCAL (para debug)"
echo "==============================="

echo ""
echo "🔸 Teste Local - CPF"
echo 'curl -X POST "'$LOCAL_URL'/buscar-n8n" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo_busca\": \"cpf\",
    \"valor\": \"084.036.781-34\",
    \"movimentacoes\": true,
    \"limite_movimentacoes\": 3,
    \"extrair_anexos\": false,
    \"extrair_partes_detalhadas\": false
  }"'

echo ""
echo "📋 6. VALORES BOOLEANOS CORRETOS"
echo "================================="
echo ""
echo "✅ CORRETO:"
echo "• \"movimentacoes\": true"
echo "• \"extrair_anexos\": false"
echo "• \"extrair_partes_detalhadas\": true"
echo ""
echo "❌ EVITAR:"
echo "• \"movimentacoes\": \"true\" (string)"
echo "• \"extrair_anexos\": \"false\" (string)"
echo ""
echo "📝 NOTA: A API aceita ambos os formatos, mas boolean é mais eficiente"

echo ""
echo "📋 7. CONFIGURAÇÃO N8N VISUAL"
echo "=============================="
echo ""
echo "No N8N, evite usar 'bodyParameters' - use o formato direto:"
echo ""
echo "{\"
echo "  \"tipo_busca\": \"{{ \$json.cpf ? 'cpf' : 'nome' }}\","
echo "  \"valor\": \"{{ \$json.valor }}\","  
echo "  \"movimentacoes\": true,"
echo "  \"limite_movimentacoes\": {{ \$json.limite || 5 }},"
echo "  \"extrair_anexos\": {{ \$json.extrair_anexos || false }},"
echo "  \"extrair_partes_detalhadas\": {{ \$json.extrair_partes || false }}"
echo "}"

echo ""
echo "==========================================="
echo "🎯 RESUMO:"
echo "• Use /buscar-n8n (não /buscar)" 
echo "• Formato JSON direto (não bodyParameters)"
echo "• Valores boolean true/false (não strings)"
echo "• URL: http://apis_projudi:8081/buscar-n8n"
echo "==========================================="
