#!/bin/bash

echo "🧪 Testando 6 requests simultâneas (limite: 5) - CPF: 084.036.781-34"
echo "⏱️  Iniciando às $(date)"

# CPF para teste
CPF="084.036.781-34"

# Função para fazer request
make_request() {
    local id=$1
    echo "🚀 Request $id iniciado às $(date +"%H:%M:%S")"
    
    curl -s -X POST "http://localhost:8081/buscar" \
        -H "Content-Type: application/json" \
        -d "{
            \"tipo_busca\": \"cpf\", 
            \"valor\": \"$CPF\", 
            \"extrair_partes_detalhadas\": false, 
            \"movimentacoes\": true, 
            \"extrair_anexos\": false,
            \"limite_movimentacoes\": 3
        }" > "response_$id.json" 2>&1
    
    echo "✅ Request $id finalizado às $(date +"%H:%M:%S")"
}

# Executar 6 requests em paralelo
echo "🏁 Disparando 6 requests em paralelo..."

make_request 1 &
make_request 2 &
make_request 3 &
make_request 4 &
make_request 5 &
make_request 6 &

# Aguardar todas terminarem
wait

echo ""
echo "🎯 Teste concluído às $(date)"
echo ""
echo "📊 Verificando resultados..."

# Verificar se todas as respostas foram salvas
for i in {1..6}; do
    if [ -f "response_$i.json" ]; then
        size=$(wc -c < "response_$i.json")
        if [ $size -gt 100 ]; then
            echo "✅ Response $i: OK ($size bytes)"
        else
            echo "⚠️  Response $i: Pequeno ($size bytes)"
            echo "   Conteúdo: $(head -1 response_$i.json)"
        fi
    else
        echo "❌ Response $i: Arquivo não encontrado"
    fi
done

echo ""
echo "🔍 Verificando saúde da API..."
curl -s -X GET "http://localhost:8081/health" | jq '.details.concurrency' 2>/dev/null || echo "Erro ao verificar health"
