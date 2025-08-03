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

# Threads para processar fila (multithreading)
queue_processor_threads = []
queue_processing = False
MAX_WORKER_THREADS = 6  # 6 threads simultâneas

def process_queue_worker(worker_id):
    """Processa itens da fila em background - Worker individual"""
    global queue_processing
    logger.info(f"🚀 Worker {worker_id} iniciado")
    
    while queue_processing and queue_manager:
        try:
            # Obtém próximo item da fila
            item = queue_manager.get_from_queue()
            if not item:
                time.sleep(1)  # Aguarda 1 segundo se não há itens
                continue
            
            request_id = item["id"]
            request_data = item["data"]
            
            logger.info(f"🔄 Worker {worker_id} processando requisição {request_id}")
            
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
                logger.info(f"✅ Worker {worker_id} - Requisição {request_id} concluída")
                
            except Exception as e:
                logger.error(f"❌ Worker {worker_id} - Erro ao processar requisição {request_id}: {e}")
                queue_manager.mark_failed(request_id, str(e))
                
        except Exception as e:
            logger.error(f"❌ Worker {worker_id} - Erro no processamento: {e}")
            time.sleep(5)  # Aguarda 5 segundos em caso de erro
    
    logger.info(f"🛑 Worker {worker_id} finalizado")

def start_queue_processor():
    """Inicia múltiplos processadores da fila para multithreading"""
    global queue_processor_threads, queue_processing
    if queue_manager and not queue_processing:
        queue_processing = True
        queue_processor_threads = []
        
        # Inicia 6 threads de processamento
        for i in range(MAX_WORKER_THREADS):
            thread = threading.Thread(target=process_queue_worker, args=(i+1,), daemon=True)
            thread.start()
            queue_processor_threads.append(thread)
            time.sleep(0.5)  # Pequeno delay entre threads
        
        logger.info(f"🚀 {MAX_WORKER_THREADS} workers da fila iniciados para multithreading")

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

@app.route('/health')
def health():
    """Endpoint de saúde da API"""
    try:
        # Obter informações do pool de sessões
        pool_info = {
            'pool_max_sessions': api.session_pool.max_sessions,
            'pool_sessions': len(api.session_pool.sessions),
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
        
        # Adicionar informações de configuração
        env_sessions = os.getenv('PROJUDI_MAX_SESSIONS', 'Não configurado')
        pool_info['config'] = {
            'PROJUDI_MAX_SESSIONS': env_sessions,
            'REDIS_URL': os.getenv('REDIS_URL', 'Não configurado')
        }
        
        return jsonify(pool_info)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
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
    """Endpoint para verificar status de uma requisição específica - VERSÃO OTIMIZADA"""
    try:
        if not queue_manager:
            return jsonify({
                "error": "Sistema de fila não disponível",
                "status": "error"
            }), 503
        
        # Verificar status na fila
        status = queue_manager.get_status(request_id)
        
        if not status:
            return jsonify({
                "error": "Requisição não encontrada",
                "status": "not_found"
            }), 404
        
        # Adicionar informações de performance
        response_data = {
            "request_id": request_id,
            "status": status.get("status", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Adicionar dados apenas se concluído
        if status.get("status") == "completed":
            response_data.update({
                "result": status.get("result", {}),
                "processing_time": status.get("processing_time", 0)
            })
        elif status.get("status") == "failed":
            response_data.update({
                "error": status.get("error", "Erro desconhecido")
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar status {request_id}: {e}")
        return jsonify({
            "error": f"Erro interno: {str(e)}",
            "status": "error"
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
    """Endpoint para limpar pool de sessões e parar workers"""
    try:
        global queue_processing
        queue_processing = False  # Para todos os workers
        
        # Aguarda threads terminarem
        for thread in queue_processor_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        api.session_pool.cleanup()
        
        # Limpa requisições órfãs se o Redis estiver disponível
        orphaned_cleared = 0
        if queue_manager:
            orphaned_cleared = queue_manager.clear_orphaned_requests()
        
        return jsonify({
            "status": "success",
            "message": "Pool de sessões limpo e workers parados com sucesso",
            "workers_stopped": len(queue_processor_threads),
            "orphaned_requests_cleared": orphaned_cleared,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Erro ao limpar pool: {e}")
        return jsonify({"error": f"Erro ao limpar pool: {str(e)}", "status": "error"}), 200

@app.route('/queue/cleanup', methods=['POST'])
def cleanup_queue():
    """Endpoint para limpar requisições órfãs da fila"""
    try:
        if not queue_manager:
            return jsonify({
                "error": "Sistema de fila não disponível",
                "status": "error"
            }), 503
        
        orphaned_cleared = queue_manager.clear_orphaned_requests()
        
        return jsonify({
            "status": "success",
            "orphaned_requests_cleared": orphaned_cleared,
            "message": f"Limpeza concluída: {orphaned_cleared} requisições órfãs removidas",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro na limpeza da fila: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 200

if __name__ == '__main__':
    # Configurações para produção
    port = int(os.getenv('PORT', 8081))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"🚀 Iniciando API PROJUDI V3 Ultra-Robusta na porta {port}")
    logger.info(f"🔧 Configurações: Host={host}, Debug={debug}")
    
    # Iniciar workers da fila automaticamente
    if queue_manager:
        start_queue_processor()
        logger.info("✅ Workers da fila iniciados automaticamente")
    else:
        logger.warning("⚠️ Workers não iniciados - Redis não disponível")
    
    app.run(
        host=host, 
        port=port, 
        debug=debug, 
        threaded=True,
        use_reloader=False
    ) 