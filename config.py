#!/usr/bin/env python3
"""
Configurações da PROJUDI API v4
"""

import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    # Configurações da API
    app_name: str = "PROJUDI API v4"
    app_version: str = "4.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8081, env="PORT")
    # Segurança e logging
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    disable_access_log: bool = Field(default=False, env="DISABLE_ACCESS_LOG")
    
    # Configurações do PROJUDI
    projudi_user: str = Field(default="*", env="PROJUDI_USER")
    projudi_pass: str = Field(default="*", env="PROJUDI_PASS")
    default_serventia: str = Field(
        default="Advogados - OAB/Matrícula: 25348-N-GO", 
        env="DEFAULT_SERVENTIA"
    )
    projudi_base_url: str = Field(default="https://projudi.tjgo.jus.br", env="PROJUDI_BASE_URL")
    projudi_login_url: str = Field(default="https://projudi.tjgo.jus.br/LogOn?PaginaAtual=-200", env="PROJUDI_LOGIN_URL")
    
    # Configurações do Playwright
    playwright_headless: bool = Field(default=False, env="PLAYWRIGHT_HEADLESS")  # SEMPRE VISÍVEL para debug dos 7 processos
    playwright_slow_mo: int = Field(default=0, env="PLAYWRIGHT_SLOW_MO")
    playwright_timeout: int = Field(default=60000, env="PLAYWRIGHT_TIMEOUT")  # Balanceado: 60s
    max_browsers: int = Field(default=10, env="MAX_BROWSERS")
    
    # Configurações Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    use_redis: bool = Field(default=True, env="USE_REDIS")
    
    # Configurações de arquivos
    temp_dir: str = Field(default="./temp", env="TEMP_DIR")
    downloads_dir: str = Field(default="./downloads", env="DOWNLOADS_DIR")
    
    # Configurações de processamento
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=300, env="REQUEST_TIMEOUT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Instância global das configurações
settings = Settings()
