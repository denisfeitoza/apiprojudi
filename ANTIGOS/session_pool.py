#!/usr/bin/env python3
"""
Pool de Sessões com Fingerprint Único
Gerencia múltiplas sessões simultâneas com configurações otimizadas
"""

import os
import time
import uuid
import tempfile
import threading
import logging
import random
import hashlib
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional

logger = logging.getLogger(__name__)

class SessionPool:
    """Pool de sessões com fingerprint único"""
    
    def __init__(self, max_sessions=None):
        # Configurar número de sessões via variável de ambiente
        if max_sessions is None:
            # Tentar ler da variável de ambiente
            env_sessions = os.getenv('PROJUDI_MAX_SESSIONS')
            if env_sessions:
                try:
                    max_sessions = int(env_sessions)
                    logger.info(f"📊 Configuração de sessões via variável de ambiente: {max_sessions}")
                except ValueError:
                    logger.warning(f"⚠️ Valor inválido para PROJUDI_MAX_SESSIONS: {env_sessions}. Usando padrão.")
                    max_sessions = 10
            else:
                max_sessions = 10  # Padrão se não configurado
        
        self.max_sessions = max_sessions
        self.sessions = []
        self.lock = threading.Lock()
        self.session_counter = 0
        
        logger.info(f"🏊 Pool de sessões inicializado com {self.max_sessions} sessões máximas")
    
    def _generate_fingerprint(self):
        """Gera fingerprint único para cada sessão"""
        fingerprint = {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'platform': 'MacIntel',
            'plugins': ['PDF Viewer', 'Chrome PDF Plugin', 'Native Client'],
            'canvas_hash': hashlib.md5(str(random.random()).encode()).hexdigest(),
            'webgl_hash': hashlib.md5(str(random.random()).encode()).hexdigest(),
            'timezone': 'America/Sao_Paulo',
            'screen_resolution': '1920x1080',
            'color_depth': 24
        }
        return fingerprint
    
    def _create_robust_driver(self):
        """Cria um driver mais robusto com configurações otimizadas"""
        try:
            chrome_options = webdriver.ChromeOptions()
            
            # Configurações para máxima estabilidade
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--memory-pressure-off")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-sync")
            chrome_options.add_argument("--disable-translate")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-prompt-on-repost")
            chrome_options.add_argument("--disable-hang-monitor")
            chrome_options.add_argument("--disable-client-side-phishing-detection")
            chrome_options.add_argument("--disable-component-update")
            chrome_options.add_argument("--disable-domain-reliability")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-threaded-animation")
            chrome_options.add_argument("--disable-threaded-scrolling")
            chrome_options.add_argument("--disable-in-process-stack-traces")
            chrome_options.add_argument("--disable-histogram-customizer")
            chrome_options.add_argument("--disable-gl-extensions")
            chrome_options.add_argument("--disable-composited-antialiasing")
            chrome_options.add_argument("--disable-canvas-aa")
            chrome_options.add_argument("--disable-3d-apis")
            chrome_options.add_argument("--disable-accelerated-2d-canvas")
            chrome_options.add_argument("--disable-accelerated-jpeg-decoding")
            chrome_options.add_argument("--disable-accelerated-mjpeg-decode")
            chrome_options.add_argument("--disable-accelerated-video-decode")
            chrome_options.add_argument("--disable-gpu-sandbox")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--no-experiments")
            chrome_options.add_argument("--no-pings")
            chrome_options.add_argument("--no-zygote")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-accelerated-2d-canvas")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-zygote")
            chrome_options.add_argument("--single-process")
            chrome_options.add_argument("--disable-gpu")
            
            # Configurações de memória e performance
            chrome_options.add_argument("--memory-pressure-off")
            chrome_options.add_argument("--max_old_space_size=4096")
            chrome_options.add_argument("--js-flags=--max-old-space-size=4096")
            
            # User agent robusto
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Perfil temporário único
            temp_dir = tempfile.mkdtemp(prefix=f"projudi_robust_")
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            
            # Configurações específicas do macOS
            import platform
            if platform.system() == "Darwin":
                chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            
            # Tentar usar o ChromeDriver instalado via Homebrew
            try:
                service = Service("/opt/homebrew/bin/chromedriver")
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                logger.warning(f"⚠️ Erro com ChromeDriver Homebrew: {e}")
                # Fallback: usar ChromeDriverManager
                try:
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception as e2:
                    logger.error(f"❌ Erro com ChromeDriverManager: {e2}")
                    return None, None
            
            # Configurações adicionais do driver
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(10)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver, temp_dir
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar driver robusto: {e}")
            return None, None
    
    def _create_session(self):
        """Cria uma nova sessão com fingerprint único"""
        try:
            self.session_counter += 1
            session_id = f"session_{self.session_counter}"
            
            # Criar driver robusto
            driver, temp_dir = self._create_robust_driver()
            if not driver:
                return None
            
            wait = WebDriverWait(driver, 30)
            
            session = {
                'id': session_id,
                'driver': driver,
                'wait': wait,
                'temp_dir': temp_dir,
                'fingerprint': self._generate_fingerprint(),
                'busy': False,
                'last_used': time.time(),
                'created_at': datetime.now()
            }
            
            logger.info(f"✅ Sessão {session_id} criada com sucesso")
            return session
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar sessão: {e}")
            return None
    
    def get_session(self):
        """Obtém uma sessão disponível do pool"""
        current_time = time.time()
        
        # Limpar sessões antigas (mais de 30 minutos)
        self.sessions = [s for s in self.sessions if current_time - s['last_used'] < 1800]
        
        # Tentar reutilizar sessão existente
        for session in self.sessions:
            if not session['busy']:
                session['busy'] = True
                session['last_used'] = current_time
                logger.info(f"🔄 Reutilizando sessão {session['id']}")
                return session
        
        # Criar nova sessão se possível
        if len(self.sessions) < self.max_sessions:
            session = self._create_session()
            if session:
                session['busy'] = True
                session['last_used'] = current_time
                self.sessions.append(session)
                logger.info(f"🆕 Nova sessão {session['id']} criada e adicionada ao pool")
                return session
        
        logger.warning(f"⚠️ Pool cheio ({len(self.sessions)}/{self.max_sessions}), aguardando sessão disponível")
        return None
    
    def release_session(self, session):
        """Libera uma sessão para reutilização"""
        if session:
            session['busy'] = False
            session['last_used'] = time.time()
            logger.info(f"🔄 Sessão {session['id']} liberada")
    
    def cleanup(self):
        """Limpa todas as sessões do pool"""
        try:
            with self.lock:
                for session in self.sessions:
                    if session['driver']:
                        try:
                            session['driver'].quit()
                        except:
                            pass
                    if session['temp_dir']:
                        try:
                            shutil.rmtree(session['temp_dir'])
                        except:
                            pass
                
                self.sessions.clear()
                logger.info("🧹 Pool de sessões limpo")
        except Exception as e:
            logger.error(f"❌ Erro ao limpar pool: {e}")
    
    def get_status(self):
        """Retorna o status atual do pool"""
        active_sessions = len([s for s in self.sessions if s['busy']])
        total_sessions = len(self.sessions)
        
        return {
            'max_sessions': self.max_sessions,
            'active_sessions': active_sessions,
            'total_sessions': total_sessions,
            'available_sessions': total_sessions - active_sessions,
            'session_counter': self.session_counter
        } 

    def get_session_with_retry(self, max_retries: int = 3, delay: int = 30) -> Optional[dict]:
        """
        Obtém uma sessão com sistema de retry
        """
        for attempt in range(max_retries):
            logger.info(f"🔄 Tentativa {attempt + 1}/{max_retries} de obter sessão")
            
            session = self.get_session()
            if session:
                logger.info(f"✅ Sessão obtida na tentativa {attempt + 1}")
                return session
            
            if attempt < max_retries - 1:  # Não aguarda na última tentativa
                logger.warning(f"⏳ Aguardando {delay} segundos antes da próxima tentativa...")
                time.sleep(delay)
        
        logger.error(f"❌ Não foi possível obter sessão após {max_retries} tentativas")
        return None 