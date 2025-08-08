#!/bin/bash

echo "🧪 Teste Controlado da Fila - Limite: 5 concurrent"
echo "⏱️  Iniciando às $(date)"

# Função para fazer request simples (só busca, sem processos detalhados)
make_simple_request() {
    local id=$1
    echo "🚀 Request $id iniciado às $(date +"%H:%M:%S")"
    
    # Request mais simples - só busca sem extrair dados detalhados
    curl -s -X POST "http://localhost:8081/buscar" \
        -H "Content-Type: application/json" \
        -d "{
            \"tipo_busca\": \"cpf\", 
            \"valor\": \"084.036.781-34\", 
            \"extrair_partes_detalhadas\": false, 
            \"movimentacoes\": false,
            \"extrair_anexos\": false
        }" > "test_$id.json" 2>&1
    
    echo "✅ Request $id finalizado às $(date +"%H:%M:%S")"
}

# Primeiro, vamos ver o status atual
echo "📊 Status inicial:"
curl -s -X GET "http://localhost:8081/health" | jq '.details'

echo ""
echo "🚦 Enviando 3 requests simples primeiro (dentro do limite)..."

# 3 requests primeiro
make_simple_request 1 &
make_simple_request 2 &
make_simple_request 3 &

# Aguardar um pouco
sleep 2

echo "🚦 Enviando mais 3 requests (vai exceder o limite e usar fila)..."

# Mais 3 requests para testar a fila
make_simple_request 4 &
make_simple_request 5 &
make_simple_request 6 &

# Aguardar todas
wait

echo ""
echo "🎯 Teste concluído às $(date)"

# Verificar resultados
echo "📊 Verificando resultados..."
for i in {1..6}; do
    if [ -f "test_$i.json" ]; then
        size=$(wc -c < "test_$i.json")
        if [ $size -gt 50 ]; then
            echo "✅ Test $i: OK ($size bytes)"
        else
            echo "⚠️  Test $i: Pequeno ($size bytes) - $(head -1 test_$i.json)"
        fi
    else
        echo "❌ Test $i: Arquivo não encontrado"
    fi
done

echo ""
echo "📊 Status final:"
curl -s -X GET "http://localhost:8081/health" | jq '.details.concurrency'
