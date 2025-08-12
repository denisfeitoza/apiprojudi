#!/usr/bin/env python3
"""
PROJUDI API v4 - Arquivo Principal
API moderna com Playwright para extração de dados do sistema PROJUDI
"""

import uvicorn
from loguru import logger

from config import settings

# Configurar logging
logger.add(
    "logs/projudi_api.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)

def main():
    """Função principal"""
    logger.info("🚀 Iniciando PROJUDI API v4")
    logger.info(f"🔧 Configurações: Host={settings.host}, Port={settings.port}, Debug={settings.debug}")
    logger.info(f"🎯 Playwright: Headless={settings.playwright_headless}, Max Browsers={settings.max_browsers}")
    
    # Executar servidor
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=not settings.disable_access_log
    )

if __name__ == "__main__":
    main()