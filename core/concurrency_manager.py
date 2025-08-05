#!/usr/bin/env python3
"""
Gerenciador de Concorrência para PROJUDI API v4
"""

import asyncio
import time
from typing import Optional, Callable, Any
from loguru import logger
from config import settings

class ConcurrencyManager:
    """Gerenciador de concorrência e rate limiting"""
    
    def __init__(self):
        self.max_concurrent = settings.max_concurrent_requests
        self.request_timeout = settings.request_timeout
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.active_requests = 0
        self.total_requests = 0
        self.failed_requests = 0
        
    async def execute_with_limits(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Executa função com limites de concorrência e timeout"""
        
        async with self.semaphore:
            self.active_requests += 1
            self.total_requests += 1
            
            start_time = time.time()
            
            try:
                # Executa com timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.request_timeout
                )
                
                execution_time = time.time() - start_time
                logger.debug(f"✅ Request executado em {execution_time:.2f}s")
                
                return result
                
            except asyncio.TimeoutError:
                self.failed_requests += 1
                execution_time = time.time() - start_time
                logger.error(f"⏰ Timeout após {execution_time:.2f}s (limite: {self.request_timeout}s)")
                raise
                
            except Exception as e:
                self.failed_requests += 1
                execution_time = time.time() - start_time
                logger.error(f"❌ Erro após {execution_time:.2f}s: {e}")
                raise
                
            finally:
                self.active_requests -= 1
    
    def get_stats(self) -> dict:
        """Retorna estatísticas de concorrência"""
        return {
            "max_concurrent": self.max_concurrent,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                ((self.total_requests - self.failed_requests) / self.total_requests * 100)
                if self.total_requests > 0 else 100
            ),
            "request_timeout": self.request_timeout
        }
    
    def reset_stats(self):
        """Reseta estatísticas"""
        self.total_requests = 0
        self.failed_requests = 0

# Instância global do gerenciador de concorrência
concurrency_manager = ConcurrencyManager() 