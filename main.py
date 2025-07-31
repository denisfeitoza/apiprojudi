#!/usr/bin/env python3
"""
PROJUDI API V3 - Versão Ultra-Robusta com Sistema de Fila Redis
Arquivo principal com Flask e configurações
"""

import os
import logging
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
from session_pool import SessionPool
from projudi_api import ProjudiAPI

# Importar o gerenciador de fila
try:
    from queue_manager import QueueManager
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis não disponível - usando processamento direto")

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configurações da API
USUARIO = os.getenv('PROJUDI_USER', '34930230144')
SENHA = os.getenv('PROJUDI_PASS', 'Joaquim1*')
SERVENTIA_PADRAO = os.getenv('DEFAULT_SERVENTIA', 'Advogados - OAB/Matrícula: 25348-N-GO')

# Inicializar Flask
app = Flask(__name__)

# Configurações do Flask para produção
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Instância global da API
api = ProjudiAPI()

# Inicializar o gerenciador de fila
queue_manager = None
if REDIS_AVAILABLE:
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        queue_manager = QueueManager(redis_url)
        logger.info("✅ Sistema de fila Redis inicializado com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar Redis: {e}")
        queue_manager = None
else:
    logger.warning("⚠️ Redis não disponível - usando processamento direto")

# Thread para processar fila
queue_processor_thread = None
queue_processing = False

def process_queue():
    """Processa itens da fila em background"""
    global queue_processing
    queue_processing = True
    
    while queue_processing and queue_manager:
        try:
            # Obtém próximo item da fila
            item = queue_manager.get_from_queue()
            if not item:
                time.sleep(1)  # Aguarda 1 segundo se não há itens
                continue
            
            request_id = item["id"]
            request_data = item["data"]
            
            logger.info(f"🔄 Processando requisição {request_id} da fila")
            
            # Processa a busca
            try:
                result = api.processar_busca(
                    tipo_busca=request_data["tipo_busca"],
                    valor=request_data["valor"],
                    limite_movimentacoes=request_data.get("movimentacoes", 3),
                    extrair_anexos=request_data.get("extrair_anexos", False)
                )
                
                # Marca como concluída
                queue_manager.mark_completed(request_id, result)
                logger.info(f"✅ Requisição {request_id} concluída com sucesso")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar requisição {request_id}: {e}")
                queue_manager.mark_failed(request_id, str(e))
                
        except Exception as e:
            logger.error(f"❌ Erro no processamento da fila: {e}")
            time.sleep(5)  # Aguarda 5 segundos em caso de erro
    
    logger.info("🛑 Processamento da fila finalizado")

def start_queue_processor():
    """Inicia o processador da fila"""
    global queue_processor_thread
    if queue_manager and not queue_processing:
        queue_processor_thread = threading.Thread(target=process_queue, daemon=True)
        queue_processor_thread.start()
        logger.info("🚀 Processador da fila iniciado")

@app.after_request
def after_request(response):
    """Adiciona headers CORS e logging"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/', methods=['GET'])
def root():
    """Endpoint raiz com informações da API"""
    return jsonify({
        "api": "PROJUDI V3 - Ultra-Robusta",
        "version": "3.0.0",
        "status": "online",
        "features": [
            "Pool de Sessões (6 simultâneas)",
            "Fingerprint Único",
            "Multi-acessos",
            "Multi-requisições",
            "Refresh Automático",
            "Sistema de Fallback",
            "Monitoramento de Saúde"
        ],
        "endpoints": {
            "/buscar": "Busca individual (POST) - Com fila Redis",
            "/buscar_multiplo": "Múltiplas buscas (POST)",
            "/status/{request_id}": "Status de requisição na fila (GET)",
            "/queue/stats": "Estatísticas da fila (GET)",
            "/cleanup": "Limpar pool (POST)",
            "/health": "Status da API (GET)",
            "/status": "Status detalhado (GET)"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    try:
        # Verificar se a API está funcionando
        pool_status = api.session_pool.get_status()
        return jsonify({
            "status": "healthy",
            "pool_sessions": pool_status['active_sessions'],
            "pool_max_sessions": pool_status['max_sessions'],
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Health check falhou: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """Endpoint de status detalhado"""
    try:
        pool_status = api.session_pool.get_status()
        return jsonify({
            "status": "online",
            "api_version": "3.0.0",
            "pool": pool_status,
            "uptime": "running",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Status check falhou: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/status/<request_id>', methods=['GET'])
def get_request_status(request_id):
    """Obtém status de uma requisição na fila"""
    try:
        if not queue_manager:
            return jsonify({
                "error": "Sistema de fila não disponível",
                "status": "error"
            }), 503
        
        status = queue_manager.get_status(request_id)
        if not status:
            return jsonify({
                "error": "Requisição não encontrada",
                "status": "error"
            }), 404
        
        # Adiciona posição na fila
        if status.get("status") == "pending":
            status["queue_position"] = queue_manager.get_queue_position(request_id)
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/queue/stats', methods=['GET'])
def get_queue_stats():
    """Obtém estatísticas da fila"""
    try:
        if not queue_manager:
            return jsonify({
                "error": "Sistema de fila não disponível",
                "status": "error"
            }), 503
        
        stats = queue_manager.get_queue_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/buscar', methods=['POST'])
def buscar():
    """Endpoint principal de busca com sistema de fila"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos", "status": "error"}), 400
        
        tipo_busca = data.get('tipo_busca', 'processo')
        valor = data.get('valor', '')
        movimentacoes = data.get('movimentacoes', 'ultimas3')
        extrair_anexos = data.get('extrair_anexos', False)
        
        if not valor:
            return jsonify({"error": "Valor de busca não fornecido", "status": "error"}), 400
        
        # Se o Redis não estiver disponível, usa o método antigo
        if not queue_manager:
            logger.warning("⚠️ Redis não disponível, usando processamento direto")
            
            # Gerar ID único para a requisição
            import uuid
            request_id = str(uuid.uuid4())
            logger.info(f"🆔 Requisição direta {request_id}: {tipo_busca} = {valor}")
            
                        # Processar busca
            resultado = api.processar_busca(tipo_busca, valor, movimentacoes, extrair_anexos)
            
            # Retornar resultado diretamente sem reprocessar a estrutura
            resultado["request_id"] = request_id
            return jsonify(resultado)
        
        # Adiciona à fila Redis
        request_data = {
            "tipo_busca": tipo_busca,
            "valor": valor,
            "movimentacoes": movimentacoes,
            "extrair_anexos": extrair_anexos
        }
        
        request_id = queue_manager.add_to_queue(request_data)
        
        # Inicia processador da fila se não estiver rodando
        if not queue_processing:
            start_queue_processor()
        
        logger.info(f"📥 Requisição {request_id} adicionada à fila: {tipo_busca} = {valor}")
        
        return jsonify({
            "status": "queued",
            "request_id": request_id,
            "message": "Requisição adicionada à fila",
            "queue_position": queue_manager.get_queue_position(request_id),
            "tipo_busca": tipo_busca,
            "valor": valor,
            "timestamp": datetime.now().isoformat()
        })
        
        # Sempre retornar 200, mesmo com erros
        if resultado.get('error'):
            logger.error(f"❌ Erro na requisição {request_id}: {resultado['error']}")
            resultado['status'] = 'error'
            return jsonify(resultado), 200
        
        logger.info(f"✅ Requisição {request_id} concluída com sucesso")
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /buscar: {e}")
        return jsonify({
            "error": f"Erro interno: {str(e)}", 
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }), 200

@app.route('/buscar_multiplo', methods=['POST'])
def buscar_multiplo():
    """Endpoint para múltiplas buscas simultâneas"""
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        data = request.get_json()
        
        if not data or 'buscas' not in data:
            return jsonify({"error": "Lista de buscas não fornecida", "status": "error"}), 400
        
        buscas = data['buscas']
        if not isinstance(buscas, list) or len(buscas) == 0:
            return jsonify({"error": "Lista de buscas inválida", "status": "error"}), 400
        
        if len(buscas) > 10:  # Limite de 10 buscas simultâneas
            return jsonify({"error": "Máximo de 10 buscas simultâneas permitido", "status": "error"}), 400
        
        logger.info(f"🔄 Processando {len(buscas)} buscas simultâneas")
        
        resultados = {}
        futures = {}
        
        # Usar ThreadPoolExecutor para processar buscas em paralelo
        with ThreadPoolExecutor(max_workers=min(len(buscas), 6)) as executor:
            for i, busca in enumerate(buscas):
                tipo_busca = busca.get('tipo_busca', 'processo')
                valor = busca.get('valor', '')
                movimentacoes = busca.get('movimentacoes', 'ultimas3')
                extrair_anexos = busca.get('extrair_anexos', False)
                
                if not valor:
                    resultados[f"busca_{i}"] = {"error": "Valor de busca não fornecido", "status": "error"}
                    continue
                
                # Submeter busca para execução paralela
                future = executor.submit(
                    api.processar_busca, 
                    tipo_busca, 
                    valor, 
                    movimentacoes, 
                    extrair_anexos
                )
                futures[future] = f"busca_{i}"
            
            # Coletar resultados
            for future in as_completed(futures):
                busca_id = futures[future]
                try:
                    resultado = future.result()
                    resultados[busca_id] = resultado
                except Exception as e:
                    logger.error(f"❌ Erro na {busca_id}: {e}")
                    resultados[busca_id] = {"error": f"Erro na busca: {str(e)}", "status": "error"}
        
        logger.info(f"✅ {len(buscas)} buscas simultâneas concluídas")
        return jsonify({
            "status": "success",
            "total_buscas": len(buscas),
            "resultados": resultados,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /buscar_multiplo: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}", "status": "error"}), 200

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Endpoint para limpar pool de sessões"""
    try:
        api.session_pool.cleanup()
        return jsonify({
            "status": "success",
            "message": "Pool de sessões limpo com sucesso",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Erro ao limpar pool: {e}")
        return jsonify({"error": f"Erro ao limpar pool: {str(e)}", "status": "error"}), 200

if __name__ == '__main__':
    # Configurações para produção
    port = int(os.getenv('PORT', 8081))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"🚀 Iniciando API PROJUDI V3 Ultra-Robusta na porta {port}")
    logger.info(f"🔧 Configurações: Host={host}, Debug={debug}")
    
    app.run(
        host=host, 
        port=port, 
        debug=debug, 
        threaded=True,
        use_reloader=False
    ) 