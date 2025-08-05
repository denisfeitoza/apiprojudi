#!/usr/bin/env python3
"""
Gerenciador de Sessões Playwright para PROJUDI API v4
"""

import asyncio
import uuid
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from config import settings
from core.cache_manager import cache_manager
from core.concurrency_manager import concurrency_manager

@dataclass
class Session:
    """Representa uma sessão do navegador"""
    id: str
    browser: Browser
    context: BrowserContext
    page: Page
    temp_dir: str
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    is_busy: bool = False
    is_logged_in: bool = False

class SessionManager:
    """Gerenciador de sessões Playwright"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.playwright = None
        self.browser_type = None
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        
    async def initialize(self):
        """Inicializa o gerenciador de sessões"""
        try:
            logger.info("🚀 Inicializando Playwright...")
            self.playwright = await async_playwright().start()
            # Detectar sistema operacional para escolher o melhor browser
            import platform
            import os
            
            # Sempre usar Chromium em modo headless (mais estável em VPS)
            if settings.playwright_headless:
                self.browser_type = self.playwright.chromium
                logger.info("🌐 Usando Chromium (modo headless)")
            elif platform.system() == "Linux":
                # VPS Linux: usar Chromium mesmo sem headless
                self.browser_type = self.playwright.chromium
                logger.info("🌐 Usando Chromium (VPS Linux)")
            else:
                # macOS/Windows: usar Firefox (mais estável)
                self.browser_type = self.playwright.firefox
                logger.info("🦊 Usando Firefox (macOS/Windows)")
            
            # Instalar navegadores se necessário
            logger.info("📦 Verificando instalação dos navegadores...")
            # await self.playwright.chromium.install()
            
            # Inicializar cache Redis
            await cache_manager.initialize()
            
            # Iniciar task de limpeza
            self._cleanup_task = asyncio.create_task(self._cleanup_sessions_task())
            
            logger.info("✅ SessionManager inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SessionManager: {e}")
            raise
    
    async def shutdown(self):
        """Finaliza o gerenciador de sessões"""
        try:
            logger.info("🔄 Finalizando SessionManager...")
            
            # Cancelar task de limpeza
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Fechar todas as sessões
            await self.close_all_sessions()
            
            # Finalizar cache Redis
            await cache_manager.shutdown()
            
            # Finalizar Playwright
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("✅ SessionManager finalizado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao finalizar SessionManager: {e}")
    
    async def get_session(self) -> Optional[Session]:
        """Obtém uma sessão disponível ou cria uma nova"""
        return await concurrency_manager.execute_with_limits(self._get_session_internal)
    
    async def _get_session_internal(self) -> Optional[Session]:
        """Implementação interna de get_session com cache"""
        async with self._lock:
            # Verificar se o Playwright foi inicializado
            if not self.playwright or not self.browser_type:
                logger.warning("⚠️ Playwright não inicializado, inicializando agora...")
                await self.initialize()
                
                if not self.playwright or not self.browser_type:
                    logger.error("❌ Falha ao inicializar Playwright")
                    return None
            
            # Procurar sessão disponível
            for session in self.sessions.values():
                if not session.is_busy and self._is_session_valid(session):
                    session.is_busy = True
                    session.last_used = datetime.now()
                    logger.info(f"♻️ Reutilizando sessão {session.id}")
                    return session
            
            # Criar nova sessão se ainda há espaço
            if len(self.sessions) < settings.max_browsers:
                session = await self._create_session()
                if session:
                    self.sessions[session.id] = session
                    session.is_busy = True
                    logger.info(f"🆕 Nova sessão criada: {session.id}")
                    return session
            
            logger.warning("⚠️ Pool de sessões cheio, aguarde...")
            return None
    
    async def release_session(self, session_or_id):
        """Libera uma sessão para reutilização"""
        # Aceita tanto Session quanto session_id (string)
        if isinstance(session_or_id, str):
            session_id = session_or_id
            session = self.sessions.get(session_id)
        else:
            session = session_or_id
            session_id = session.id if session else None
            
        if session and session_id in self.sessions:
            session.is_busy = False
            session.last_used = datetime.now()
            logger.info(f"🔓 Sessão liberada: {session_id}")
    
    async def close_session(self, session: Session):
        """Fecha uma sessão específica"""
        try:
            if session and session.id in self.sessions:
                await session.context.close()
                await session.browser.close()
                
                # Limpar diretório temporário
                if session.temp_dir:
                    try:
                        shutil.rmtree(session.temp_dir)
                    except:
                        pass
                
                del self.sessions[session.id]
                logger.info(f"🗑️ Sessão fechada: {session.id}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao fechar sessão {session.id}: {e}")
    
    async def criar_sessao(self) -> Optional[Session]:
        """Cria uma nova sessão (alias para get_session)"""
        return await self.get_session()
    
    async def fechar_sessao(self, session_id: str):
        """Fecha uma sessão específica pelo ID"""
        session = self.sessions.get(session_id)
        if session:
            await self.close_session(session)
    
    async def close_all_sessions(self):
        """Fecha todas as sessões"""
        sessions_to_close = list(self.sessions.values())
        for session in sessions_to_close:
            await self.close_session(session)
        
        logger.info(f"🧹 Todas as {len(sessions_to_close)} sessões foram fechadas")
    
    async def _create_session(self) -> Optional[Session]:
        """Cria uma nova sessão com retry e aguardos"""
        for tentativa in range(3):  # 3 tentativas
            try:
                logger.info(f"🔄 Tentativa {tentativa + 1}/3 de criar sessão...")
                session_id = str(uuid.uuid4())
                temp_dir = tempfile.mkdtemp(prefix=f"projudi_session_{session_id}_")
                
                # Aguardo entre tentativas
                if tentativa > 0:
                    await asyncio.sleep(5 * tentativa)
                
                # Configurações robustas para VPS Linux (Chromium) e macOS (Firefox)
                launch_args = {
                    'headless': settings.playwright_headless,
                    'slow_mo': max(1000, settings.playwright_slow_mo),  # Mínimo 1 segundo
                    'timeout': 60000  # 60 segundos para launch
                }
                
                # Adicionar argumentos específicos para VPS Linux
                if settings.playwright_headless:
                    launch_args.update({
                        'args': [
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-accelerated-2d-canvas',
                            '--no-first-run',
                            '--no-zygote',
                            '--disable-gpu'
                        ]
                    })
                
                browser = await self.browser_type.launch(**launch_args)
                
                # Criar contexto com configurações
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='pt-BR',
                    timezone_id='America/Sao_Paulo',
                    accept_downloads=True,
                    ignore_https_errors=True,
                    java_script_enabled=True
                )
                
                # Configurar timeouts
                context.set_default_timeout(settings.playwright_timeout)
                context.set_default_navigation_timeout(settings.playwright_timeout)
                
                # Criar página
                page = await context.new_page()
                
                # Configurações adicionais da página
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en']});
                """)
                
                session = Session(
                    id=session_id,
                    browser=browser,
                    context=context,
                    page=page,
                    temp_dir=temp_dir
                )
                
                logger.info(f"✅ Sessão criada com sucesso: {session_id}")
                return session
                
            except Exception as e:
                logger.error(f"❌ Tentativa {tentativa + 1}/3 falhou: {e}")
                if tentativa == 2:  # última tentativa
                    logger.error(f"❌ Falha final ao criar sessão após 3 tentativas")
                await asyncio.sleep(2)  # Aguardo antes de próxima tentativa
        
        return None
    
    def _is_session_valid(self, session: Session) -> bool:
        """Verifica se uma sessão ainda é válida"""
        try:
            # Verificar se a sessão não é muito antiga (30 minutos)
            if datetime.now() - session.created_at > timedelta(minutes=30):
                return False
            
            # Verificar se a sessão não está sem uso há muito tempo (10 minutos)
            if datetime.now() - session.last_used > timedelta(minutes=10):
                return False
            
            # Verificar se o browser ainda está conectado
            if session.browser.is_connected():
                return True
            
            return False
            
        except Exception:
            return False
    
    async def _cleanup_sessions_task(self):
        """Task de limpeza executada periodicamente"""
        while True:
            try:
                await asyncio.sleep(60)  # Executar a cada 1 minuto
                await self._cleanup_invalid_sessions()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Erro na limpeza de sessões: {e}")
    
    async def _cleanup_invalid_sessions(self):
        """Remove sessões inválidas"""
        async with self._lock:
            invalid_sessions = []
            
            for session in self.sessions.values():
                if not self._is_session_valid(session):
                    invalid_sessions.append(session)
            
            for session in invalid_sessions:
                await self.close_session(session)
            
            if invalid_sessions:
                logger.info(f"🧹 Removidas {len(invalid_sessions)} sessões inválidas")
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do pool de sessões"""
        total = len(self.sessions)
        busy = sum(1 for s in self.sessions.values() if s.is_busy)
        logged_in = sum(1 for s in self.sessions.values() if s.is_logged_in)
        
        # Estatísticas base
        stats = {
            'total_sessions': total,
            'busy_sessions': busy,
            'available_sessions': total - busy,
            'logged_in_sessions': logged_in,
            'max_sessions': settings.max_browsers
        }
        
        # Adicionar estatísticas de concorrência
        concurrency_stats = concurrency_manager.get_stats()
        stats.update({
            'concurrency': concurrency_stats
        })
        
        # Adicionar estatísticas de cache
        cache_stats = {
            'cache_enabled': cache_manager.cache_enabled,
            'cache_connected': cache_manager.is_connected
        }
        stats.update({
            'cache': cache_stats
        })
        
        return stats

# Instância global do gerenciador
session_manager = SessionManager()

@asynccontextmanager
async def get_session():
    """Context manager para usar sessões de forma segura"""
    session = await session_manager.get_session()
    if not session:
        raise Exception("Não foi possível obter uma sessão")
    
    try:
        yield session
    finally:
        await session_manager.release_session(session)