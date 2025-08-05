#!/usr/bin/env python3
"""
Gerenciador de Cache com Redis para PROJUDI API v4
"""

import json
import asyncio
from typing import Optional, Any, Dict
from loguru import logger
import redis.asyncio as redis
from config import settings

class CacheManager:
    """Gerenciador de cache com Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        self.cache_enabled = settings.use_redis
        
    async def initialize(self) -> bool:
        """Inicializa conexão com Redis"""
        if not self.cache_enabled:
            logger.info("🚫 Cache Redis desabilitado nas configurações")
            return False
            
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Testa conexão
            await self.redis_client.ping()
            self.is_connected = True
            logger.info(f"✅ Cache Redis conectado: {settings.redis_url}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Falha ao conectar Redis: {e}")
            self.is_connected = False
            return False
    
    async def shutdown(self):
        """Fecha conexão com Redis"""
        if self.redis_client and self.is_connected:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("🔄 Cache Redis desconectado")
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        if not self.is_connected:
            return None
            
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter cache {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Define valor no cache com expiração"""
        if not self.is_connected:
            return False
            
        try:
            await self.redis_client.setex(
                key,
                expire,
                json.dumps(value, ensure_ascii=False)
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️ Erro ao definir cache {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Remove valor do cache"""
        if not self.is_connected:
            return False
            
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Erro ao deletar cache {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Verifica se chave existe no cache"""
        if not self.is_connected:
            return False
            
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar cache {key}: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """Limpa todo o cache"""
        if not self.is_connected:
            return False
            
        try:
            await self.redis_client.flushdb()
            logger.info("🧹 Cache Redis limpo")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar cache: {e}")
            return False

# Instância global do cache
cache_manager = CacheManager() 