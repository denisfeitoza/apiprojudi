#!/usr/bin/env python3
"""
Gerenciador de Fila com Redis para API PROJUDI V3
"""

import redis
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from threading import Thread, Lock

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Inicializa o gerenciador de fila"""
        self.redis_url = redis_url
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.queue_name = "projudi_queue"
        self.processing_name = "projudi_processing"
        self.results_name = "projudi_results"
        self.lock = Lock()
        
        # Testa conexão com Redis
        try:
            self.redis.ping()
            logger.info("✅ Redis conectado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com Redis: {e}")
            raise
    
    def add_to_queue(self, request_data: Dict[str, Any]) -> str:
        """Adiciona uma requisição à fila"""
        request_id = str(uuid.uuid4())
        
        queue_item = {
            "id": request_id,
            "data": request_data,
            "status": "pending",
            "position": 0,
            "created_at": datetime.now().isoformat(),
            "retries": 0,
            "max_retries": 3
        }
        
        with self.lock:
            # Adiciona à fila
            self.redis.lpush(self.queue_name, json.dumps(queue_item))
            
            # Atualiza posição na fila
            queue_length = self.redis.llen(self.queue_name)
            queue_item["position"] = queue_length
            
            # Salva item atualizado
            self.redis.hset(self.results_name, request_id, json.dumps(queue_item))
            
            logger.info(f"📥 Requisição {request_id} adicionada à fila (posição: {queue_length})")
        
        return request_id
    
    def get_from_queue(self) -> Optional[Dict[str, Any]]:
        """Obtém próxima requisição da fila"""
        try:
            with self.lock:
                # Verifica se há requisições na fila
                if self.redis.llen(self.queue_name) == 0:
                    return None
                
                # Remove da fila (FIFO)
                item_json = self.redis.rpop(self.queue_name)
                if not item_json:
                    return None
                
                item = json.loads(item_json)
                item["status"] = "processing"
                item["started_at"] = datetime.now().isoformat()
                
                # Adiciona à lista de processamento
                self.redis.hset(self.processing_name, item["id"], json.dumps(item))
                
                logger.info(f"🔄 Processando requisição {item['id']}")
                return item
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter da fila: {e}")
            return None
    
    def mark_completed(self, request_id: str, result: Dict[str, Any]):
        """Marca requisição como concluída"""
        try:
            with self.lock:
                # Remove da lista de processamento
                self.redis.hdel(self.processing_name, request_id)
                
                # Atualiza resultado
                result_data = {
                    "id": request_id,
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.now().isoformat()
                }
                
                self.redis.hset(self.results_name, request_id, json.dumps(result_data))
                logger.info(f"✅ Requisição {request_id} concluída")
                
        except Exception as e:
            logger.error(f"❌ Erro ao marcar como concluída: {e}")
            # Garante que seja removida da lista de processamento mesmo com erro
            try:
                self.redis.hdel(self.processing_name, request_id)
            except:
                pass
    
    def mark_failed(self, request_id: str, error: str, retry: bool = True):
        """Marca requisição como falhada"""
        try:
            with self.lock:
                # Remove da lista de processamento
                self.redis.hdel(self.processing_name, request_id)
                
                # Obtém dados da requisição
                item_json = self.redis.hget(self.results_name, request_id)
                if item_json:
                    item = json.loads(item_json)
                    item["retries"] = item.get("retries", 0) + 1
                    
                    if retry and item["retries"] < item.get("max_retries", 3):
                        # Recoloca na fila para retry
                        item["status"] = "pending"
                        item["error"] = error
                        item["retry_at"] = datetime.now().isoformat()
                        
                        self.redis.lpush(self.queue_name, json.dumps(item))
                        self.redis.hset(self.results_name, request_id, json.dumps(item))
                        
                        logger.warning(f"🔄 Requisição {request_id} falhou, tentativa {item['retries']}/{item['max_retries']}")
                    else:
                        # Marca como falhada definitivamente
                        result_data = {
                            "id": request_id,
                            "status": "failed",
                            "error": error,
                            "retries": item["retries"],
                            "failed_at": datetime.now().isoformat()
                        }
                        
                        self.redis.hset(self.results_name, request_id, json.dumps(result_data))
                        logger.error(f"❌ Requisição {request_id} falhou definitivamente após {item['retries']} tentativas")
                
        except Exception as e:
            logger.error(f"❌ Erro ao marcar como falhada: {e}")
    
    def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de uma requisição"""
        try:
            item_json = self.redis.hget(self.results_name, request_id)
            if item_json:
                return json.loads(item_json)
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {e}")
            return None
    
    def get_queue_position(self, request_id: str) -> int:
        """Obtém posição na fila de uma requisição"""
        try:
            # Verifica se está sendo processada
            if self.redis.hexists(self.processing_name, request_id):
                return 0
            
            # Conta quantas requisições estão na frente na fila
            position = 0
            queue_items = self.redis.lrange(self.queue_name, 0, -1)
            
            for item_json in queue_items:
                item = json.loads(item_json)
                if item["id"] == request_id:
                    return position
                position += 1
            
            return -1  # Não encontrada na fila
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter posição na fila: {e}")
            return -1
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas da fila"""
        try:
            pending = self.redis.llen(self.queue_name)
            processing = self.redis.hlen(self.processing_name)
            total_results = self.redis.hlen(self.results_name)
            
            return {
                "pending": pending,
                "processing": processing,
                "total_results": total_results,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {"error": str(e)}
    
    def clear_old_results(self, max_age_hours: int = 24):
        """Limpa resultados antigos"""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            deleted_count = 0
            
            # Obtém todas as chaves de resultados
            result_keys = self.redis.hkeys(self.results_name)
            
            for key in result_keys:
                item_json = self.redis.hget(self.results_name, key)
                if item_json:
                    item = json.loads(item_json)
                    
                    # Verifica se é antigo
                    created_at = item.get("created_at")
                    if created_at:
                        try:
                            created_time = datetime.fromisoformat(created_at).timestamp()
                            if created_time < cutoff_time:
                                self.redis.hdel(self.results_name, key)
                                deleted_count += 1
                        except:
                            pass
            
            logger.info(f"🧹 Limpeza: {deleted_count} resultados antigos removidos")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Erro na limpeza: {e}")
            return 0
    
    def clear_orphaned_requests(self):
        """Limpa requisições órfãs que estão em processamento há muito tempo"""
        try:
            with self.lock:
                # Obtém todas as requisições em processamento
                processing_keys = self.redis.hkeys(self.processing_name)
                orphaned_count = 0
                
                for key in processing_keys:
                    item_json = self.redis.hget(self.processing_name, key)
                    if item_json:
                        item = json.loads(item_json)
                        started_at = item.get("started_at")
                        
                        if started_at:
                            try:
                                started_time = datetime.fromisoformat(started_at).timestamp()
                                current_time = datetime.now().timestamp()
                                
                                # Se está em processamento há mais de 10 minutos, considera órfã
                                if current_time - started_time > 600:  # 10 minutos
                                    self.redis.hdel(self.processing_name, key)
                                    orphaned_count += 1
                                    logger.warning(f"🧹 Removida requisição órfã {key} (em processamento há {(current_time - started_time)/60:.1f} minutos)")
                            except:
                                # Se não consegue verificar o tempo, remove de qualquer forma
                                self.redis.hdel(self.processing_name, key)
                                orphaned_count += 1
                                logger.warning(f"🧹 Removida requisição órfã {key} (dados corrompidos)")
                
                logger.info(f"🧹 Limpeza de órfãs: {orphaned_count} requisições removidas")
                return orphaned_count
                
        except Exception as e:
            logger.error(f"❌ Erro na limpeza de órfãs: {e}")
            return 0 