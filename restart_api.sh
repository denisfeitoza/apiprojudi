#!/bin/bash

echo "🔄 Reiniciando PROJUDI API..."

# 1. Matar todos os processos Python relacionados
echo "🛑 Parando processos existentes..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true

# 2. Matar processos específicos na porta 8081
echo "🔌 Liberando porta 8081..."
lsof -ti:8081 | xargs kill -9 2>/dev/null || true

# 3. Aguardar liberação da porta
echo "⏳ Aguardando liberação da porta..."
sleep 3

# 4. Verificar se a porta está livre
if lsof -i:8081 >/dev/null 2>&1; then
    echo "❌ Porta 8081 ainda ocupada. Tentando força bruta..."
    lsof -ti:8081 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 5. Iniciar a API
echo "🚀 Iniciando PROJUDI API..."
python main.py
