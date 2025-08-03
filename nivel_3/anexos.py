#!/usr/bin/env python3
"""
Nível 3 - Módulo de Anexos PROJUDI API v4
Responsável por extrair, baixar e processar anexos
"""

import asyncio
import os
import re
import time
import hashlib
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, Download
from bs4 import BeautifulSoup
import httpx
from loguru import logger

from config import settings
from core.session_manager import Session
from nivel_2.processo import Movimentacao

@dataclass
class AnexoInfo:
    """Informações de um anexo"""
    id_arquivo: str
    nome_arquivo: str
    url_anexo: str
    tipo_arquivo: str  # PDF, HTML, DOC, etc.
    tamanho_bytes: int = 0
    movimentacao_numero: int = 0
    hash_conteudo: str = ""

@dataclass
class AnexoProcessado:
    """Anexo processado com conteúdo extraído"""
    anexo_info: AnexoInfo
    conteudo_extraido: str
    tamanho_conteudo: int
    metodo_extracao: str  # iframe, download, ocr, etc.
    arquivo_baixado: str = ""  # Caminho do arquivo baixado
    sucesso_processamento: bool = False
    erro_processamento: str = ""
    tempo_processamento: float = 0.0

class PDFProcessor:
    """Processador de PDFs com múltiplas estratégias"""
    
    @staticmethod
    async def extrair_texto_pdf(caminho_arquivo: str) -> tuple[str, str]:
        """Extrai texto de PDF usando múltiplas estratégias"""
        try:
            conteudo = ""
            metodo = "erro"
            
            # Estratégia 1: PyMuPDF (fitz)
            try:
                import fitz
                doc = fitz.open(caminho_arquivo)
                texto_pymupdf = ""
                
                for num_pagina in range(len(doc)):
                    pagina = doc.load_page(num_pagina)
                    texto_pagina = pagina.get_text()
                    texto_pymupdf += texto_pagina
                
                doc.close()
                
                if texto_pymupdf.strip():
                    conteudo = texto_pymupdf
                    metodo = "PyMuPDF"
                    logger.info(f"✅ Texto extraído com PyMuPDF: {len(texto_pymupdf)} caracteres")
                    return conteudo, metodo
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro com PyMuPDF: {e}")
            
            # Estratégia 2: PyPDF2
            try:
                import PyPDF2
                with open(caminho_arquivo, 'rb') as arquivo:
                    leitor = PyPDF2.PdfReader(arquivo)
                    texto_pypdf2 = ""
                    
                    for num_pagina in range(len(leitor.pages)):
                        pagina = leitor.pages[num_pagina]
                        texto_pagina = pagina.extract_text()
                        texto_pypdf2 += texto_pagina
                    
                    if texto_pypdf2.strip():
                        conteudo = texto_pypdf2
                        metodo = "PyPDF2"
                        logger.info(f"✅ Texto extraído com PyPDF2: {len(texto_pypdf2)} caracteres")
                        return conteudo, metodo
                        
            except Exception as e:
                logger.warning(f"⚠️ Erro com PyPDF2: {e}")
            
            # Estratégia 3: OCR com pytesseract
            try:
                import pytesseract
                from PIL import Image
                import fitz
                
                logger.info("🔍 Iniciando OCR para extrair texto...")
                
                doc = fitz.open(caminho_arquivo)
                texto_ocr = ""
                
                for num_pagina in range(min(5, len(doc))):  # Limitar a 5 páginas para OCR
                    pagina = doc.load_page(num_pagina)
                    
                    # Converter página para imagem
                    mat = fitz.Matrix(2, 2)  # Aumentar resolução
                    pix = pagina.get_pixmap(matrix=mat)
                    
                    # Salvar imagem temporária
                    img_temp = f"temp_page_{num_pagina}_{int(time.time())}.png"
                    pix.save(img_temp)
                    
                    try:
                        # OCR com Tesseract
                        imagem = Image.open(img_temp)
                        texto_pagina = pytesseract.image_to_string(imagem, lang='por')
                        texto_ocr += texto_pagina
                        
                        # Limpar arquivo temporário
                        imagem.close()
                        os.remove(img_temp)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Erro no OCR da página {num_pagina + 1}: {e}")
                        if os.path.exists(img_temp):
                            os.remove(img_temp)
                
                doc.close()
                
                if texto_ocr.strip():
                    conteudo = texto_ocr
                    metodo = "OCR"
                    logger.info(f"✅ Texto extraído com OCR: {len(texto_ocr)} caracteres")
                    return conteudo, metodo
                    
            except ImportError:
                logger.warning("⚠️ pytesseract não instalado, OCR não disponível")
            except Exception as e:
                logger.warning(f"⚠️ Erro no OCR: {e}")
            
            return "Não foi possível extrair texto do PDF", "erro"
            
        except Exception as e:
            logger.error(f"❌ Erro geral ao processar PDF: {e}")
            return f"Erro ao processar PDF: {str(e)}", "erro"

class AnexosManager:
    """Gerenciador de anexos"""
    
    def __init__(self):
        self.base_url = settings.projudi_base_url
        self.downloads_dir = Path(settings.downloads_dir)
        self.downloads_dir.mkdir(exist_ok=True)
        
    async def solicitar_acesso_anexos(self, session: Session) -> bool:
        """Solicita acesso aos anexos do processo"""
        try:
            logger.info("🔓 Solicitando acesso aos anexos...")
            
            # Script para encontrar e clicar no menu "Outras"
            script_outras = """
            () => {
                // Procurar por link que contenha "Outras"
                const links = document.querySelectorAll('a');
                for (let link of links) {
                    if (link.textContent.includes('Outras')) {
                        link.click();
                        return true;
                    }
                }
                return false;
            }
            """
            
            resultado = await session.page.evaluate(script_outras)
            if resultado:
                await asyncio.sleep(1)
                logger.info("✅ Menu 'Outras' clicado")
                
                # Script para clicar em "Solicitar Acesso"
                script_solicitar = """
                () => {
                    const links = document.querySelectorAll('a');
                    for (let link of links) {
                        if (link.textContent.includes('Solicitar Acesso')) {
                            link.click();
                            return true;
                        }
                    }
                    return false;
                }
                """
                
                resultado_solicitar = await session.page.evaluate(script_solicitar)
                if resultado_solicitar:
                    await asyncio.sleep(2)
                    logger.info("✅ Acesso aos anexos solicitado")
                    
                    # Tratar possível popup de confirmação
                    try:
                        await session.page.wait_for_selector('dialog', timeout=2000)
                        await session.page.keyboard.press('Enter')
                    except:
                        pass
                    
                    return True
            
            logger.warning("⚠️ Não foi possível solicitar acesso aos anexos")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao solicitar acesso: {e}")
            return False
    
    async def acessar_navegacao_arquivos(self, session: Session) -> bool:
        """Acessa a página de navegação de arquivos"""
        try:
            logger.info("📁 Acessando página de navegação de arquivos...")
            
            # URL da página de navegação (igual à versão PLUS)
            navegacao_url = f"{self.base_url}/BuscaProcesso?PaginaAtual=9&PassoBusca=4"
            await session.page.goto(navegacao_url, timeout=30000)
            await session.page.wait_for_load_state('networkidle', timeout=30000)
            
            # Verificar se chegou na página correta
            if await session.page.query_selector('table#TabelaArquivos'):
                logger.info("✅ Página de navegação carregada")
                return True
            else:
                logger.warning("⚠️ Página de navegação não carregou corretamente")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao acessar navegação: {e}")
            return False
    
    async def extrair_anexos_movimentacoes(self, session: Session, movimentacoes: List[Movimentacao], limite: Optional[int] = None) -> List[AnexoProcessado]:
        """Extrai anexos das movimentações"""
        try:
            logger.info(f"📎 Extraindo anexos de {len(movimentacoes)} movimentações...")
            
            # Filtrar movimentações que têm anexos
            movimentacoes_com_anexo = [m for m in movimentacoes if m.tem_anexo]
            
            if not movimentacoes_com_anexo:
                logger.info("ℹ️ Nenhuma movimentação com anexos encontrada")
                return []
            
            # Aplicar limite se especificado
            if limite:
                movimentacoes_com_anexo = movimentacoes_com_anexo[:limite]
                
            logger.info(f"📎 Processando {len(movimentacoes_com_anexo)} movimentações com anexos")
            
            anexos_processados = []
            
            for i, movimentacao in enumerate(movimentacoes_com_anexo, 1):
                logger.info(f"📄 Processando anexos da movimentação {i}/{len(movimentacoes_com_anexo)}: {movimentacao.numero}")
                
                # Extrair anexos da movimentação
                anexos_mov = await self._extrair_anexos_movimentacao(session, movimentacao)
                anexos_processados.extend(anexos_mov)
                
                # Aguardar um pouco entre movimentações
                await asyncio.sleep(1)
            
            logger.info(f"✅ {len(anexos_processados)} anexos processados")
            return anexos_processados
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair anexos: {e}")
            return []
    
    async def _extrair_anexos_movimentacao(self, session: Session, movimentacao: Movimentacao) -> List[AnexoProcessado]:
        """Extrai anexos de uma movimentação específica"""
        try:
            anexos = []
            
            # Garantir que estamos na página de navegação
            if not await session.page.query_selector('table#TabelaArquivos'):
                if not await self.acessar_navegacao_arquivos(session):
                    return []
            
            # Forçar atualização do iframe
            await self._limpar_iframe(session)
            
            # Clicar no anexo da movimentação
            if await self._clicar_anexo_movimentacao(session, movimentacao):
                await asyncio.sleep(3)
                
                # Extrair conteúdo do anexo
                anexo_processado = await self._processar_anexo_atual(session, movimentacao)
                if anexo_processado:
                    anexos.append(anexo_processado)
            
            return anexos
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair anexos da movimentação {movimentacao.numero}: {e}")
            return []
    
    async def _clicar_anexo_movimentacao(self, session: Session, movimentacao: Movimentacao) -> bool:
        """Clica no anexo de uma movimentação"""
        try:
            # Estratégia 1: Usar JavaScript com buscarArquivosMovimentacaoJSON
            if movimentacao.codigo_anexo:
                script = f"""
                () => {{
                    try {{
                        buscarArquivosMovimentacaoJSON('{movimentacao.codigo_anexo}', 'BuscaProcesso', 'Id_MovimentacaoArquivo', 6, 'false');
                        return true;
                    }} catch (e) {{
                        return false;
                    }}
                }}
                """
                resultado = await session.page.evaluate(script)
                if resultado:
                    logger.info(f"✅ Anexo clicado via JavaScript: {movimentacao.codigo_anexo}")
                    return True
            
            # Estratégia 2: Procurar por link com ID da movimentação
            if movimentacao.id_movimentacao:
                link_selector = f'a[href*="Id_MovimentacaoArquivo={movimentacao.id_movimentacao}"]'
                link = await session.page.query_selector(link_selector)
                
                if link:
                    await link.click()
                    logger.info(f"✅ Anexo clicado via seletor: {movimentacao.id_movimentacao}")
                    return True
            
            # Estratégia 3: Procurar por qualquer link de anexo na linha da movimentação
            script_generico = f"""
            () => {{
                const links = document.querySelectorAll('a[href*="Id_MovimentacaoArquivo"]');
                if (links.length > 0) {{
                    links[0].click();
                    return true;
                }}
                return false;
            }}
            """
            resultado = await session.page.evaluate(script_generico)
            if resultado:
                logger.info("✅ Anexo clicado via script genérico")
                return True
            
            logger.warning(f"⚠️ Não foi possível clicar no anexo da movimentação {movimentacao.numero}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao clicar no anexo: {e}")
            return False
    
    async def _processar_anexo_atual(self, session: Session, movimentacao: Movimentacao) -> Optional[AnexoProcessado]:
        """Processa o anexo atualmente carregado"""
        try:
            start_time = time.time()
            
            # Aguardar carregamento
            await asyncio.sleep(3)
            
            # Verificar se é PDF ou HTML
            is_pdf = await self._detectar_tipo_anexo(session)
            
            if is_pdf:
                # Tentar baixar PDF
                anexo_processado = await self._processar_pdf(session, movimentacao)
            else:
                # Extrair conteúdo HTML do iframe
                anexo_processado = await self._processar_html_iframe(session, movimentacao)
            
            if anexo_processado:
                anexo_processado.tempo_processamento = time.time() - start_time
                
            return anexo_processado
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar anexo: {e}")
            return None
    
    async def _detectar_tipo_anexo(self, session: Session) -> bool:
        """Detecta se o anexo é PDF"""
        try:
            # Verificar no iframe se há indicadores de PDF
            script = """
            () => {
                const iframe = document.getElementById('arquivo');
                if (iframe) {
                    try {
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        const content = doc.documentElement.innerHTML.toLowerCase();
                        return content.includes('pdf') || content.includes('application/pdf');
                    } catch (e) {
                        return false;
                    }
                }
                return false;
            }
            """
            
            is_pdf = await session.page.evaluate(script)
            return is_pdf
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao detectar tipo de anexo: {e}")
            return False
    
    async def _processar_pdf(self, session: Session, movimentacao: Movimentacao) -> Optional[AnexoProcessado]:
        """Processa anexo PDF baixando o arquivo"""
        try:
            logger.info("📄 Processando PDF...")
            
            # Tentar baixar PDF
            arquivo_baixado = await self._baixar_pdf_atual(session, movimentacao)
            
            if arquivo_baixado and os.path.exists(arquivo_baixado):
                # Extrair texto do PDF
                conteudo, metodo = await PDFProcessor.extrair_texto_pdf(arquivo_baixado)
                
                anexo_info = AnexoInfo(
                    id_arquivo=movimentacao.id_movimentacao,
                    nome_arquivo=f"anexo_mov_{movimentacao.numero}.pdf",
                    url_anexo="",
                    tipo_arquivo="PDF",
                    tamanho_bytes=os.path.getsize(arquivo_baixado),
                    movimentacao_numero=movimentacao.numero
                )
                
                return AnexoProcessado(
                    anexo_info=anexo_info,
                    conteudo_extraido=conteudo,
                    tamanho_conteudo=len(conteudo),
                    metodo_extracao=metodo,
                    arquivo_baixado=arquivo_baixado,
                    sucesso_processamento=len(conteudo) > 0
                )
            else:
                logger.warning("⚠️ Não foi possível baixar o PDF")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar PDF: {e}")
            return None
    
    async def _baixar_pdf_atual(self, session: Session, movimentacao: Movimentacao) -> Optional[str]:
        """Baixa o PDF atualmente carregado"""
        try:
            # Obter URL do PDF do iframe
            script = """
            () => {
                const iframe = document.getElementById('arquivo');
                if (iframe) {
                    return iframe.src;
                }
                return null;
            }
            """
            
            pdf_url = await session.page.evaluate(script)
            if not pdf_url:
                return None
            
            # Fazer download usando httpx com cookies da sessão
            cookies = await session.context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    pdf_url,
                    cookies=cookie_dict,
                    timeout=30.0,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    # Salvar arquivo
                    nome_arquivo = f"anexo_mov_{movimentacao.numero}_{int(time.time())}.pdf"
                    caminho_arquivo = self.downloads_dir / nome_arquivo
                    
                    with open(caminho_arquivo, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"✅ PDF baixado: {nome_arquivo}")
                    return str(caminho_arquivo)
                else:
                    logger.error(f"❌ Erro no download: Status {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao baixar PDF: {e}")
            return None
    
    async def _processar_html_iframe(self, session: Session, movimentacao: Movimentacao) -> Optional[AnexoProcessado]:
        """Processa anexo HTML extraindo conteúdo do iframe"""
        try:
            logger.info("📄 Processando HTML do iframe...")
            
            # Extrair conteúdo do iframe
            script = """
            () => {
                const iframe = document.getElementById('arquivo');
                if (iframe) {
                    try {
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        return doc.documentElement.outerHTML;
                    } catch (e) {
                        return iframe.src || '';
                    }
                }
                return '';
            }
            """
            
            html_content = await session.page.evaluate(script)
            
            if html_content:
                # Extrair texto limpo do HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remover scripts e styles
                for script in soup(["script", "style"]):
                    script.decompose()
                
                texto_limpo = soup.get_text()
                texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
                
                anexo_info = AnexoInfo(
                    id_arquivo=movimentacao.id_movimentacao,
                    nome_arquivo=f"anexo_mov_{movimentacao.numero}.html",
                    url_anexo="",
                    tipo_arquivo="HTML",
                    tamanho_bytes=len(html_content),
                    movimentacao_numero=movimentacao.numero
                )
                
                return AnexoProcessado(
                    anexo_info=anexo_info,
                    conteudo_extraido=texto_limpo,
                    tamanho_conteudo=len(texto_limpo),
                    metodo_extracao="iframe_html",
                    sucesso_processamento=len(texto_limpo) > 0
                )
            else:
                logger.warning("⚠️ Não foi possível extrair conteúdo do iframe")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar HTML do iframe: {e}")
            return None
    
    async def _limpar_iframe(self, session: Session):
        """Limpa o iframe para evitar conteúdo antigo"""
        try:
            script = """
            () => {
                const iframe = document.getElementById('arquivo');
                if (iframe) {
                    iframe.src = '';
                    iframe.src = './paginaInicialNavegacaoArquivos.html';
                }
            }
            """
            await session.page.evaluate(script)
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar iframe: {e}")
    
    def limpar_arquivos_temporarios(self):
        """Limpa arquivos temporários baixados"""
        try:
            if self.downloads_dir.exists():
                for arquivo in self.downloads_dir.glob("anexo_*"):
                    try:
                        arquivo.unlink()
                    except:
                        pass
                logger.info("🧹 Arquivos temporários limpos")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar arquivos temporários: {e}")

# Instância global do gerenciador de anexos
anexos_manager = AnexosManager()