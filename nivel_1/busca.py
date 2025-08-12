#!/usr/bin/env python3
"""
Nível 1 - Módulo de Busca PROJUDI API v4
Responsável por buscas por CPF, Nome e Processo
"""

import asyncio
import time
import re
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import settings
from core.session_manager import Session
from core.cache_manager import cache_manager

class TipoBusca(str, Enum):
    CPF = "cpf"
    NOME = "nome"
    PROCESSO = "processo"

@dataclass
class ProcessoEncontrado:
    """Representa um processo encontrado na busca"""
    numero: str
    classe: str
    assunto: str
    id_processo: str
    indice: int
    url_processo: str = ""

@dataclass
class ResultadoBusca:
    """Resultado de uma busca"""
    tipo_busca: TipoBusca
    valor_busca: str
    total_encontrados: int
    processos: List[ProcessoEncontrado]
    sucesso: bool
    mensagem: str = ""
    tempo_execucao: float = 0.0
    from_cache: bool = False

class LoginManager:
    """Gerenciador de login do PROJUDI"""
    
    @staticmethod
    async def fazer_login(session: Session) -> bool:
        """Realiza login no sistema PROJUDI"""
        try:
            logger.info(f"🔐 Fazendo login na sessão {session.id}...")
            
            # Verificar cache de login
            cache_key = f"login_status_{session.id}"
            cached_login = await cache_manager.get(cache_key)
            if cached_login and cached_login.get('logged_in'):
                logger.info(f"✅ Login em cache para sessão {session.id}")
                session.is_logged_in = True
                return True
            
            # Navegar para página de login
            login_url = f"{settings.projudi_base_url}/LogOn?PaginaAtual=-200"
            await session.page.goto(login_url, timeout=120000)
            
            # Aguardar página carregar
            try:
                await session.page.wait_for_load_state('networkidle', timeout=12000)
            except Exception:
                # Em alguns momentos a página não atinge networkidle; seguir em frente
                await session.page.wait_for_load_state('domcontentloaded', timeout=12000)
            
            # Verificar se já está logado
            if await LoginManager._ja_esta_logado(session.page):
                logger.info(f"✅ Já estava logado na sessão {session.id}")
                session.is_logged_in = True
                # Cachear status de login por 30 minutos
                await cache_manager.set(cache_key, {'logged_in': True}, expire=1800)
                return True
            
            # Preencher credenciais com aguardos para estabilidade
            await session.page.fill('input[name="Usuario"]', settings.projudi_user)
            await asyncio.sleep(0.5)  # Aguardo para estabilidade
            await session.page.fill('input[name="Senha"]', settings.projudi_pass)
            await asyncio.sleep(0.5)  # Aguardo para estabilidade
            
            # Clicar em entrar
            await session.page.click('input[name="entrar"]')
            await asyncio.sleep(1)  # Aguardo após clique
            
            # Aguardar redirecionamento
            try:
                await session.page.wait_for_load_state('networkidle', timeout=12000)
            except Exception:
                await session.page.wait_for_load_state('domcontentloaded', timeout=12000)
            
            # Verificar se apareceu a página de seleção de serventia
            if await LoginManager._selecionar_serventia(session.page):
                logger.info(f"✅ Login realizado com sucesso na sessão {session.id}")
                session.is_logged_in = True
                # Cachear status de login por 30 minutos
                await cache_manager.set(cache_key, {'logged_in': True}, expire=1800)
                return True
            else:
                logger.error(f"❌ Falha na seleção de serventia na sessão {session.id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no login da sessão {session.id}: {e}")
            return False
    
    @staticmethod
    async def _ja_esta_logado(page: Page) -> bool:
        """Verifica se já está logado"""
        try:
            # Verificar se não há campos de login na página
            usuario_field = await page.query_selector('input[name="Usuario"]')
            return usuario_field is None
        except:
            return False
    
    @staticmethod
    async def _selecionar_serventia(page: Page) -> bool:
        """Seleciona a serventia padrão com múltiplas estratégias"""
        try:
            # Aguardar página carregar
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
            
            # Estratégia 1: Procurar serventia específica por texto
            try:
                await page.wait_for_selector('a', timeout=5000)
                
                # Tentar múltiplas variações do nome da serventia
                variacoes_serventia = [
                    settings.default_serventia,
                    "Advogados",
                    "OAB",
                    "25348-N-GO"
                ]
                
                for variacao in variacoes_serventia:
                    serventia_link = await page.query_selector(f'a:has-text("{variacao}")')
                    if serventia_link:
                        await serventia_link.click()
                        await page.wait_for_load_state('networkidle', timeout=12000)
                        logger.info(f"✅ Serventia selecionada: {variacao}")
                        return True
                        
            except Exception as e:
                logger.warning(f"⚠️ Estratégia 1 falhou: {e}")
            
            # Estratégia 2: Procurar qualquer link com "Serventia"
            try:
                links_serventia = await page.query_selector_all('a[href*="Serventia"], a[href*="serventia"]')
                if links_serventia:
                    await links_serventia[0].click()
                    await page.wait_for_load_state('networkidle', timeout=12000)
                    logger.warning("⚠️ Usando primeira serventia encontrada")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️ Estratégia 2 falhou: {e}")
            
            # Estratégia 3: Procurar qualquer link que não seja logout
            try:
                todos_links = await page.query_selector_all('a')
                for link in todos_links:
                    href = await link.get_attribute('href')
                    texto = await link.inner_text()
                    
                    if href and 'logout' not in href.lower() and 'sair' not in texto.lower():
                        await link.click()
                        await page.wait_for_load_state('networkidle', timeout=12000)
                        logger.warning(f"⚠️ Usando link alternativo: {texto}")
                        return True
                        
            except Exception as e:
                logger.warning(f"⚠️ Estratégia 3 falhou: {e}")
            
            # Estratégia 4: JavaScript para clicar no primeiro link válido
            try:
                script = """
                () => {
                    const links = document.querySelectorAll('a');
                    for (let link of links) {
                        const href = link.href;
                        const text = link.textContent.toLowerCase();
                        
                        if (href && !text.includes('logout') && !text.includes('sair')) {
                            link.click();
                            return true;
                        }
                    }
                    return false;
                }
                """
                
                resultado = await page.evaluate(script)
                if resultado:
                    await page.wait_for_load_state('networkidle', timeout=12000)
                    logger.warning("⚠️ Serventia selecionada via JavaScript")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️ Estratégia 4 falhou: {e}")
            
            logger.error("❌ Nenhuma estratégia de seleção de serventia funcionou")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro geral ao selecionar serventia: {e}")
            return False

class BuscaManager:
    """Gerenciador de buscas no PROJUDI"""
    
    def __init__(self):
        self.base_url = settings.projudi_base_url
        
    async def executar_busca(self, session: Session, tipo_busca: TipoBusca, valor: str) -> ResultadoBusca:
        """Executa uma busca no PROJUDI"""
        import time
        start_time = time.time()
        
        try:
            # Verificar cache de busca
            cache_key = f"busca_{tipo_busca.value}_{valor}"
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"✅ Resultado em cache para busca {tipo_busca.value} = {valor}")
                
                # Converter dicionários de volta para objetos ProcessoEncontrado
                processos_cache = []
                for p_dict in cached_result.get('processos', []):
                    processo = ProcessoEncontrado(
                        numero=p_dict.get('numero', ''),
                        classe=p_dict.get('classe', ''),
                        assunto=p_dict.get('assunto', ''),
                        id_processo=p_dict.get('id_processo', ''),
                        indice=p_dict.get('indice', 0),
                        url_processo=p_dict.get('url_processo', '')
                    )
                    processos_cache.append(processo)
                
                return ResultadoBusca(
                    tipo_busca=tipo_busca,
                    valor_busca=valor,
                    total_encontrados=cached_result.get('total_encontrados', 0),
                    processos=processos_cache,
                    sucesso=cached_result.get('sucesso', False),
                    mensagem=cached_result.get('mensagem', ''),
                    tempo_execucao=0.1,  # Cache é muito rápido
                    from_cache=True
                )
            
            # SEMPRE fazer login antes de cada busca para garantir sessão válida
            logger.info(f"🔐 Fazendo login antes da busca {tipo_busca.value}...")
            if not await LoginManager.fazer_login(session):
                return ResultadoBusca(
                    tipo_busca=tipo_busca,
                    valor_busca=valor,
                    total_encontrados=0,
                    processos=[],
                    sucesso=False,
                    mensagem="Falha no login",
                    tempo_execucao=time.time() - start_time
                )
            
            # Navegar para página de busca correta (URL descoberta na análise)
            busca_url = f"{self.base_url}/BuscaProcesso"
            await session.page.goto(busca_url, timeout=30000)
            try:
                await session.page.wait_for_load_state('networkidle', timeout=30000)
            except Exception:
                await session.page.wait_for_load_state('domcontentloaded', timeout=30000)
            logger.info(f"✅ Página de busca acessada: {busca_url}")
            
            # Executar busca específica
            if tipo_busca == TipoBusca.CPF:
                sucesso = await self._buscar_por_cpf(session.page, valor)
            elif tipo_busca == TipoBusca.NOME:
                sucesso = await self._buscar_por_nome(session.page, valor)
            elif tipo_busca == TipoBusca.PROCESSO:
                sucesso = await self._buscar_por_processo(session.page, valor)
            else:
                raise ValueError(f"Tipo de busca não suportado: {tipo_busca}")
            
            if not sucesso:
                return ResultadoBusca(
                    tipo_busca=tipo_busca,
                    valor_busca=valor,
                    total_encontrados=0,
                    processos=[],
                    sucesso=False,
                    mensagem="Falha na execução da busca",
                    tempo_execucao=time.time() - start_time
                )
            
            # Extrair resultados
            processos = await self._extrair_processos_encontrados(session.page)
            
            resultado = ResultadoBusca(
                tipo_busca=tipo_busca,
                valor_busca=valor,
                total_encontrados=len(processos),
                processos=processos,
                sucesso=True,
                mensagem="Busca realizada com sucesso",
                tempo_execucao=time.time() - start_time
            )
            
            # Cachear resultado por 1 hora
            cache_data = {
                'total_encontrados': resultado.total_encontrados,
                'processos': [p.__dict__ for p in resultado.processos],
                'sucesso': resultado.sucesso,
                'mensagem': resultado.mensagem
            }
            await cache_manager.set(cache_key, cache_data, expire=3600)
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro na busca {tipo_busca} = {valor}: {e}")
            return ResultadoBusca(
                tipo_busca=tipo_busca,
                valor_busca=valor,
                total_encontrados=0,
                processos=[],
                sucesso=False,
                mensagem=f"Erro: {str(e)}",
                tempo_execucao=time.time() - start_time
            )
    
    async def _buscar_por_cpf(self, page: Page, cpf: str) -> bool:
        """Executa busca por CPF"""
        try:
            logger.info(f"🔍 Buscando por CPF: {cpf}")
            
            # Aguardar campo CPF estar disponível
            cpf_field = await page.wait_for_selector('input[name="CpfCnpjParte"]', timeout=12000)
            
            # Limpar e preencher CPF
            await page.evaluate('document.querySelector("input[name=\'CpfCnpjParte\']").value = ""')
            await page.fill('input[name="CpfCnpjParte"]', cpf)
            
            # Clicar em buscar
            await page.click('input[value="Buscar"]')
            await page.wait_for_load_state('networkidle', timeout=12000)
            
            logger.info("✅ Busca por CPF executada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na busca por CPF: {e}")
            return False
    
    async def _buscar_por_nome(self, page: Page, nome: str) -> bool:
        """Executa busca por nome"""
        try:
            logger.info(f"🔍 Buscando por nome: {nome}")
            
            # Aguardar campo nome estar disponível
            nome_field = await page.wait_for_selector('input[name="NomeParte"]', timeout=12000)
            
            # Limpar e preencher nome
            await page.evaluate('document.querySelector("input[name=\'NomeParte\']").value = ""')
            await page.fill('input[name="NomeParte"]', nome)
            
            # Clicar em buscar
            await page.click('input[value="Buscar"]')
            await page.wait_for_load_state('networkidle', timeout=12000)
            
            logger.info("✅ Busca por nome executada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na busca por nome: {e}")
            return False
    
    async def _buscar_por_processo(self, page: Page, numero_processo: str) -> bool:
        """Executa busca por número do processo"""
        try:
            logger.info(f"🔍 Buscando processo: {numero_processo}")
            
            # Aguardar campo número do processo estar disponível
            processo_field = await page.wait_for_selector('input[name="ProcessoNumero"]', timeout=12000)
            
            # Limpar e preencher número do processo
            await page.fill('input[name="ProcessoNumero"]', '')
            await page.fill('input[name="ProcessoNumero"]', numero_processo)
            
            # Clicar em buscar
            await page.click('input[value="Buscar"]')
            await page.wait_for_load_state('networkidle', timeout=12000)
            
            logger.info("✅ Busca por processo executada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na busca por processo: {e}")
            return False
    
    async def _extrair_processos_encontrados(self, page: Page) -> List[ProcessoEncontrado]:
        """Extrai a lista de processos encontrados"""
        try:
            processos = []
            
            # Verificar se houve redirecionamento direto para um processo
            if await self._verificar_processo_direto(page):
                processo = await self._extrair_processo_direto(page)
                if processo:
                    processos.append(processo)
                return processos
            
            # Verificar se há mensagem de "nenhum resultado"
            page_content = await page.content()
            if any(msg in page_content.lower() for msg in ["nenhum", "não encontrado", "não foi encontrado"]):
                logger.info("ℹ️ Nenhum processo encontrado na busca")
                return []
            
            # Aguardar tabela de resultados
            try:
                await page.wait_for_selector('table#Tabela', timeout=5000)
            except PlaywrightTimeoutError:
                logger.warning("⚠️ Tabela de resultados não encontrada")
                return []
            
            # Extrair linhas da tabela (todas as linhas tr, exceto cabeçalho)
            linhas = await page.query_selector_all('table#Tabela tr')
            
            # Filtrar apenas linhas com dados (que têm 6 colunas td e não são cabeçalho)
            linhas_dados = []
            for linha in linhas:
                colunas = await linha.query_selector_all('td')
                
                if len(colunas) >= 6:  # Linha com dados tem 6 colunas
                    # Verificar se não é linha de cabeçalho (TD3 não contém 'Número')
                    terceira_coluna = await colunas[2].inner_text()
                    
                    # Pular cabeçalho (que tem 'Número' na terceira coluna)
                    if not terceira_coluna.strip().startswith('Número'):
                        linhas_dados.append(linha)
            
            linhas = linhas_dados
            
            for i, linha in enumerate(linhas):
                try:
                    colunas = await linha.query_selector_all('td')
                    if len(colunas) >= 6:
                        # Estrutura correta: [índice, vazio, número, partes, distribuição, selecionar]
                        indice_texto = await colunas[0].inner_text()
                        numero_processo = await colunas[2].inner_text()  # TD3 tem o número!
                        processo_partes = await colunas[3].inner_text()  # TD4 tem as partes
                        distribuicao = await colunas[4].inner_text()     # TD5 tem a distribuição
                        
                        numero_processo = numero_processo.strip()
                        
                        # Verificar se é uma linha válida
                        if numero_processo and not numero_processo.startswith('Número'):
                            # Extrair ID do processo do botão editar/selecionar
                            id_processo = await self._extrair_id_processo(linha)
                            
                            # Extrair informações das partes para criar classe/assunto mais informativo
                            linhas_partes = processo_partes.strip().split('\n')
                            polos_info = []
                            for linha_parte in linhas_partes[:4]:  # Primeiras 4 linhas
                                linha_parte = linha_parte.strip()
                                if linha_parte and not linha_parte.startswith('Polo'):
                                    polos_info.append(linha_parte)
                            
                            classe_info = " vs ".join(polos_info[:2]) if len(polos_info) >= 2 else "Processo"
                            
                            processo = ProcessoEncontrado(
                                numero=numero_processo,
                                classe=classe_info[:100],  # Limitar tamanho
                                assunto=f"Distribuído em {distribuicao.strip()}",
                                id_processo=id_processo,
                                indice=len(processos) + 1
                            )
                            processos.append(processo)
                            logger.info(f"✅ Processo extraído: {numero_processo}")
                            
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar linha {i}: {e}")
                    continue
            
            logger.info(f"✅ {len(processos)} processos extraídos")
            return processos
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair processos: {e}")
            return []
    
    async def _verificar_processo_direto(self, page: Page) -> bool:
        """Verifica se foi redirecionado diretamente para um processo"""
        try:
            # Verificar se estamos na página de busca ou na página do processo
            current_url = page.url
            
            # Se estamos na página de busca, não é processo direto
            if "BuscaProcesso" in current_url:
                return False
            
            # Verificar se há tabela de resultados (indica que há múltiplos processos)
            tabela = await page.query_selector('table#Tabela')
            if tabela:
                return False
            
            # Verificar se há conteúdo específico de processo individual
            content = await page.content()
            if "corpo_dados_processo" in content:
                return True
            
            return False
        except:
            return False
    
    async def _extrair_processo_direto(self, page: Page) -> Optional[ProcessoEncontrado]:
        """Extrai informações quando redirecionado diretamente para um processo"""
        try:
            content = await page.content()
            
            # Tentar encontrar número do processo na página
            numero_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', content)
            if numero_match:
                numero_processo = numero_match.group(1)
                
                return ProcessoEncontrado(
                    numero=numero_processo,
                    classe="Processo encontrado",
                    assunto="Busca direta",
                    id_processo="processo_direto",
                    indice=1,
                    url_processo=page.url
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair processo direto: {e}")
            return None
    
    async def _extrair_id_processo(self, linha_element) -> str:
        """Extrai o ID do processo de uma linha da tabela"""
        try:
            # Procurar por botão editar com onclick
            btn_editar = await linha_element.query_selector('button[name="formLocalizarimgEditar"], input[type="button"][name="formLocalizarimgEditar"]')
            
            if btn_editar:
                onclick = await btn_editar.get_attribute('onclick')
                if onclick:
                    match = re.search(r"Id_Processo','([^']+)'", onclick)
                    if match:
                        return match.group(1)
            
            # Fallback: usar índice genérico
            return f"processo_{int(time.time())}"
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair ID do processo: {e}")
            return f"processo_{int(time.time())}"

# Instância global do gerenciador de busca
busca_manager = BuscaManager()