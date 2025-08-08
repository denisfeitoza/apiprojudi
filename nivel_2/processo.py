#!/usr/bin/env python3
"""
Nível 2 - Módulo de Processo PROJUDI API v4
Responsável por extrair dados detalhados de processos
"""

import asyncio
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from loguru import logger

from config import settings
from core.session_manager import Session
from nivel_1.busca import ProcessoEncontrado

@dataclass
class Movimentacao:
    """Representa uma movimentação do processo"""
    numero: int
    tipo: str
    descricao: str
    data: str
    usuario: str
    tem_anexo: bool
    id_movimentacao: str
    numero_processo: str = ""  # Número do processo ao qual pertence
    codigo_anexo: str = ""
    html_completo: str = ""

@dataclass
class ParteEnvolvida:
    """Representa uma parte envolvida no processo"""
    nome: str
    tipo: str  # Polo Ativo, Polo Passivo, etc.
    documento: str = ""  # CPF/CNPJ
    endereco: str = ""
    telefone: str = ""
    email: str = ""
    advogado: str = ""
    oab: str = ""

@dataclass
class DadosProcesso:
    """Dados completos de um processo"""
    numero: str
    classe: str
    assunto: str
    situacao: str = ""
    data_autuacao: str = ""
    data_distribuicao: str = ""
    valor_causa: str = ""
    orgao_julgador: str = ""
    id_acesso: str = ""  # ID de acesso do projeto localizado na página inicial
    movimentacoes: List[Movimentacao] = None
    partes_polo_ativo: List[ParteEnvolvida] = None
    partes_polo_passivo: List[ParteEnvolvida] = None
    outras_partes: List[ParteEnvolvida] = None
    
    def __post_init__(self):
        if self.movimentacoes is None:
            self.movimentacoes = []
        if self.partes_polo_ativo is None:
            self.partes_polo_ativo = []
        if self.partes_polo_passivo is None:
            self.partes_polo_passivo = []
        if self.outras_partes is None:
            self.outras_partes = []

class ProcessoManager:
    """Gerenciador de extração de dados de processos"""
    
    def __init__(self):
        self.base_url = settings.projudi_base_url
    
    async def navegar_para_processo(self, session: Session, id_processo: str) -> bool:
        """Navega para um processo específico (método público)"""
        try:
            # Criar um ProcessoEncontrado temporário para compatibilidade
            from nivel_1.busca import ProcessoEncontrado
            processo_temp = ProcessoEncontrado(
                numero="Processo",
                classe="",
                assunto="",
                id_processo=id_processo,
                indice=1
            )
            
            return await self.acessar_processo(session, processo_temp)
            
        except Exception as e:
            logger.error(f"❌ Erro ao navegar para processo: {e}")
            return False
    
    async def acessar_processo(self, session: Session, processo: ProcessoEncontrado) -> bool:
        """Acessa um processo específico"""
        try:
            logger.info(f"📄 Acessando processo {processo.numero} (ID: {processo.id_processo})")
            
            # Se já estamos na página do processo (busca direta), não precisa clicar
            if processo.id_processo == "processo_direto":
                logger.info("ℹ️ Já estamos na página do processo")
                return True
            
            # Estratégia 1: Encontrar o processo correto na tabela pelo número
            try:
                # Aguardar a tabela carregar - timeout reduzido
                await session.page.wait_for_selector('table#Tabela', timeout=15000)
                
                # Procurar especificamente nas linhas do tbody
                linhas = await session.page.query_selector_all('table#Tabela tbody tr')
                logger.info(f"🔍 Analisando {len(linhas)} linhas da tabela")
                
                for i, linha in enumerate(linhas):
                    try:
                        colunas = await linha.query_selector_all('td')
                        if len(colunas) >= 6:
                            numero_na_linha = await colunas[2].inner_text()  # TD3 tem o número
                            numero_limpo = numero_na_linha.strip()
                            
                            logger.debug(f"  Linha {i+1}: {numero_limpo}")
                            
                            if numero_limpo == processo.numero:
                                # Encontrou a linha correta! Buscar botão na coluna 6 (TD6)
                                btn_editar = await colunas[5].query_selector('button[name="formLocalizarimgEditar"]')
                                if btn_editar:
                                    logger.info(f"🎯 Processo encontrado na linha {i+1}, clicando no botão...")
                                    await btn_editar.click()
                                    await session.page.wait_for_load_state('networkidle', timeout=15000)
                                    logger.info(f"✅ Processo {processo.numero} acessado via busca na tabela")
                                    return True
                                else:
                                    logger.warning(f"⚠️ Linha encontrada mas botão não localizado na coluna 6")
                    except Exception as e:
                        logger.debug(f"⚠️ Erro ao processar linha {i+1}: {e}")
                        continue
                
                logger.warning(f"⚠️ Processo {processo.numero} não encontrado na tabela")
            except Exception as e:
                logger.warning(f"⚠️ Erro na estratégia 1: {e}")
            
            # Estratégia 2: Tentar JavaScript para clicar no botão correto por índice
            if processo.indice:
                script = f"""
                () => {{
                    const botoes = document.querySelectorAll('button[name="formLocalizarimgEditar"]');
                    if (botoes.length >= {processo.indice}) {{
                        botoes[{processo.indice - 1}].click();
                        return true;
                    }}
                    return false;
                }}
                """
                resultado = await session.page.evaluate(script)
                if resultado:
                    await session.page.wait_for_load_state('networkidle', timeout=15000)
                    logger.info("✅ Processo acessado via JavaScript")
                    return True
            
            # Estratégia 2: Procurar por botão específico com ID do processo
            if processo.id_processo:
                btn_selector = f'button[onclick*="{processo.id_processo}"], input[onclick*="{processo.id_processo}"]'
                btn_editar = await session.page.query_selector(btn_selector)
                
                if btn_editar:
                    await btn_editar.click()
                    await session.page.wait_for_load_state('networkidle', timeout=15000)
                    logger.info("✅ Processo acessado via seletor específico")
                    return True
            
            # Estratégia 3: Fallback - primeiro botão editar disponível
            btn_editar = await session.page.query_selector('button[name="formLocalizarimgEditar"]')
            if btn_editar:
                await btn_editar.click()
                await session.page.wait_for_load_state('networkidle', timeout=15000)
                logger.info("✅ Processo acessado via fallback")
                return True
            
            logger.error("❌ Não foi possível encontrar botão para acessar o processo")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao acessar processo: {e}")
            return False
    
    async def extrair_dados_basicos(self, session: Session) -> Optional[DadosProcesso]:
        """Extrai apenas dados básicos do processo da página atual"""
        try:
            dados_basicos = await self._extrair_dados_basicos(session.page)
            
            # Extrair número do processo da página atual
            content = await session.page.content()
            numero_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', content)
            numero = numero_match.group(1) if numero_match else "Processo"
            
            return DadosProcesso(
                numero=numero,
                classe=dados_basicos.get('classe', ''),
                assunto=dados_basicos.get('assunto', ''),
                situacao=dados_basicos.get('situacao', ''),
                data_autuacao=dados_basicos.get('data_autuacao', ''),
                data_distribuicao=dados_basicos.get('data_distribuicao', ''),
                valor_causa=dados_basicos.get('valor_causa', ''),
                orgao_julgador=dados_basicos.get('orgao_julgador', ''),
                id_acesso=dados_basicos.get('id_acesso', '')
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados básicos: {e}")
            return None
    
    async def extrair_movimentacoes(self, session: Session, limite: Optional[int] = None) -> List[Movimentacao]:
        """Extrai movimentações do processo (método público)"""
        return await self._extrair_movimentacoes(session, limite)
    
    async def extrair_partes_envolvidas(self, session: Session) -> Dict[str, List[ParteEnvolvida]]:
        """Extrai partes envolvidas do processo (método público)"""
        return await self._extrair_partes_envolvidas(session)

    async def extrair_partes_detalhadas(self, session: Session) -> Dict[str, List[ParteEnvolvida]]:
        """Extrai partes no novo modo detalhado (opcional)."""
        return await self._extrair_partes_navegacao_detalhada(session)
    
    async def buscar_processo_especifico(self, session: Session, numero_processo: str, limite_movimentacoes: Optional[int] = None) -> Optional[DadosProcesso]:
        """Busca um processo específico diretamente no nível 2 (contorna nível 1)"""
        try:
            logger.info(f"🔍 Buscando processo específico: {numero_processo}")
            
            # Fazer login se necessário
            from nivel_1.busca import LoginManager
            if not await LoginManager.fazer_login(session):
                logger.error("❌ Falha no login para busca de processo específico")
                return None
            
            # Navegar para página de busca
            busca_url = f"{self.base_url}/BuscaProcesso"
            await session.page.goto(busca_url, timeout=15000)
            await session.page.wait_for_load_state('networkidle', timeout=15000)
            
            # Preencher número do processo
            await session.page.fill('input[name="ProcessoNumero"]', '')
            await session.page.fill('input[name="ProcessoNumero"]', numero_processo)
            
            # Clicar em buscar
            await session.page.click('input[value="Buscar"]')
            await session.page.wait_for_load_state('networkidle', timeout=15000)
            
            # Verificar se foi redirecionado diretamente para o processo
            content = await session.page.content()
            if "corpo_dados_processo" in content:
                logger.info(f"✅ Processo {numero_processo} encontrado diretamente")
                
                # Criar objeto ProcessoEncontrado temporário
                from nivel_1.busca import ProcessoEncontrado
                processo_temp = ProcessoEncontrado(
                    numero=numero_processo,
                    classe="Processo específico",
                    assunto="Busca direta",
                    id_processo="processo_direto",
                    indice=1
                )
                
                # Extrair dados completos com limite de movimentações
                return await self.extrair_dados_processo(session, processo_temp, limite_movimentacoes)
            else:
                logger.warning(f"⚠️ Processo {numero_processo} não encontrado ou não acessível")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar processo específico {numero_processo}: {e}")
            return None
    
    async def extrair_dados_processo(self, session: Session, processo: ProcessoEncontrado, limite_movimentacoes: Optional[int] = None) -> DadosProcesso:
        """Extrai dados completos de um processo"""
        try:
            logger.info(f"📋 Extraindo dados do processo {processo.numero}")
            
            # Extrair dados básicos da página atual
            dados_basicos = await self._extrair_dados_basicos(session.page)
            
            # Extrair movimentações
            movimentacoes = await self._extrair_movimentacoes(session, limite_movimentacoes)
            
            # Adicionar número do processo a cada movimentação
            for mov in movimentacoes:
                mov.numero_processo = processo.numero
            
            # Criar objeto com dados completos
            dados = DadosProcesso(
                numero=processo.numero,
                classe=processo.classe,
                assunto=processo.assunto,
                situacao=dados_basicos.get('situacao', ''),
                data_autuacao=dados_basicos.get('data_autuacao', ''),
                data_distribuicao=dados_basicos.get('data_distribuicao', ''),
                valor_causa=dados_basicos.get('valor_causa', ''),
                orgao_julgador=dados_basicos.get('orgao_julgador', ''),
                id_acesso=dados_basicos.get('id_acesso', ''),
                movimentacoes=movimentacoes,
                partes_polo_ativo=[],
                partes_polo_passivo=[],
                outras_partes=[]
            )
            
            logger.info(f"✅ Dados extraídos: {len(movimentacoes)} movimentações")
            return dados
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados do processo: {e}")
            # Retornar dados básicos mesmo em caso de erro
            return DadosProcesso(
                numero=processo.numero,
                classe=processo.classe,
                assunto=processo.assunto
            )
    
    async def _extrair_dados_basicos(self, page: Page) -> Dict[str, str]:
        """Extrai dados básicos do processo da página atual"""
        try:
            dados = {}
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extrair dados usando regex e BeautifulSoup
            texto_pagina = soup.get_text()
            
            # ID de acesso do projeto (span com id="span_proc_numero")
            try:
                span_proc_numero = soup.find('span', {'id': 'span_proc_numero'})
                if span_proc_numero:
                    id_acesso = span_proc_numero.get_text(strip=True)
                    if id_acesso:
                        dados['id_acesso'] = id_acesso
                        logger.debug(f"🆔 ID de acesso extraído: {id_acesso}")
                else:
                    # Fallback: tentar encontrar por XPath via regex no HTML
                    xpath_match = re.search(r'<span[^>]*id="span_proc_numero"[^>]*class="bold"[^>]*>\s*([^<]+)\s*</span>', content, re.I | re.S)
                    if xpath_match:
                        id_acesso = xpath_match.group(1).strip()
                        dados['id_acesso'] = id_acesso
                        logger.debug(f"🆔 ID de acesso extraído via fallback: {id_acesso}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair ID de acesso: {e}")
            
            # Data de autuação
            match = re.search(r'Data\s+de\s+Autuação[:\s]+(\d{2}/\d{2}/\d{4})', texto_pagina, re.I)
            if match:
                dados['data_autuacao'] = match.group(1)
            
            # Data de distribuição
            match = re.search(r'Data\s+de\s+Distribuição[:\s]+(\d{2}/\d{2}/\d{4})', texto_pagina, re.I)
            if match:
                dados['data_distribuicao'] = match.group(1)
            
            # Valor da causa
            match = re.search(r'Valor\s+da\s+Causa[:\s]+([R$\s\d.,]+)', texto_pagina, re.I)
            if match:
                dados['valor_causa'] = match.group(1).strip()
            
            # Situação
            match = re.search(r'Situação[:\s]+([^\n\r]+)', texto_pagina, re.I)
            if match:
                dados['situacao'] = match.group(1).strip()
            
            # Órgão julgador
            match = re.search(r'Órgão\s+Julgador[:\s]+([^\n\r]+)', texto_pagina, re.I)
            if match:
                dados['orgao_julgador'] = match.group(1).strip()
            
            return dados
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados básicos: {e}")
            return {}
    
    async def _extrair_movimentacoes(self, session: Session, limite: Optional[int] = None) -> List[Movimentacao]:
        """Extrai movimentações navegando para página de arquivos (baseado na versão PLUS)"""
        try:
            logger.info("📋 Extraindo movimentações - navegando para página de arquivos...")
            
            movimentacoes = []
            
            # ESTRATÉGIA PRINCIPAL: Tentar extrair da página atual primeiro (mais eficiente)
            logger.info("🔍 Tentando extrair movimentações da página atual...")
            
            # Verificar se já tem TabelaArquivos na página atual
            if await session.page.query_selector('table#TabelaArquivos'):
                logger.info("🔍 TabelaArquivos encontrada na página atual")
                movimentacoes = await self._extrair_movimentacoes_tabela_arquivos_inteligente(session.page)
                
            # Se não conseguiu, tentar navegar para página de arquivos
            if not movimentacoes:
                logger.info("🔍 Navegando para página de navegação de arquivos...")
                navegacao_url = f"{self.base_url}/BuscaProcesso?PaginaAtual=9&PassoBusca=4"
                
                try:
                    await session.page.goto(navegacao_url, timeout=30000)
                    await session.page.wait_for_load_state('networkidle', timeout=30000)
                    logger.info("✅ Página de navegação carregada")
                    
                    # Verificar se chegou na página correta (estrutura HTML ou tabela)
                    content = await session.page.content()
                    if "menuNavegacao" in content and "Movimentações Processo" in content:
                        logger.info("🔍 Página de navegação HTML encontrada - extraindo movimentações...")
                        movimentacoes = await self._extrair_movimentacoes_navegacao_html(session.page)
                    elif await session.page.query_selector('table#TabelaArquivos'):
                        logger.info("🔍 TabelaArquivos encontrada - extraindo movimentações...")
                        movimentacoes = await self._extrair_movimentacoes_tabela_arquivos_inteligente(session.page)
                    else:
                        logger.warning("⚠️ Nenhuma estrutura de movimentações encontrada na página de navegação")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao navegar para página de arquivos: {e}")
            
            # FALLBACK: Se não conseguiu pela navegação, tentar estratégias alternativas
            if not movimentacoes:
                logger.info("🔍 Tentando estratégias de fallback...")
                
                # Verificar se já tem TabelaArquivos na página atual
                if await session.page.query_selector('table#TabelaArquivos'):
                    logger.info("🔍 TabelaArquivos encontrada na página atual")
                    movimentacoes = await self._extrair_movimentacoes_tabela_arquivos_inteligente(session.page)
                
                            # Se ainda não tem, tentar página principal com Playwright
            if not movimentacoes:
                logger.info("🔍 Tentando página principal com Playwright")
                movimentacoes = await self._extrair_movimentacoes_playwright(session)
            
            # Último recurso: análise geral
            if not movimentacoes:
                logger.info("🔍 Análise geral como último recurso")
                movimentacoes = await self._extrair_movimentacoes_fallback(session.page)
            
            if movimentacoes:
                # Limpar e melhorar dados extraídos
                movimentacoes = self._processar_movimentacoes_inteligente(movimentacoes)
                
                # Ordenar por número (mais recentes primeiro) ou por data se não houver número
                movimentacoes = self._ordenar_movimentacoes_inteligente(movimentacoes)
                
                # Log do total antes de aplicar limite
                total_encontradas = len(movimentacoes)
                logger.info(f"📊 Total de movimentações encontradas: {total_encontradas}")
                
                # Aplicar limite se especificado
                if limite and len(movimentacoes) > limite:
                    movimentacoes = movimentacoes[:limite]
                    logger.info(f"✂️ Limitado a {limite} movimentações mais recentes")
                
                logger.info(f"✅ {len(movimentacoes)} movimentações extraídas com sucesso")
            else:
                logger.warning("⚠️ Nenhuma movimentação encontrada")
            
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair movimentações: {e}")
            return []
    
    async def _extrair_movimentacoes_tabela_arquivos_inteligente(self, page: Page) -> List[Movimentacao]:
        """Versão inteligente da extração de movimentações da tabela de arquivos"""
        try:
            movimentacoes = []
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # ESTRATÉGIA 1: Verificar se estamos na página de navegação HTML (formato PLUS)
            if "Movimentações Processo" in content and "menuNavegacao" in content:
                logger.info("🔍 Página de navegação HTML detectada - usando extração especializada")
                return await self._extrair_movimentacoes_navegacao_html(page)
            
            # ESTRATÉGIA 2: Tentar múltiplas estratégias para encontrar a tabela
            tabela = soup.find('table', {'id': 'TabelaArquivos'})
            if not tabela:
                # Fallback: procurar qualquer tabela que pareça conter movimentações
                tabelas = soup.find_all('table')
                for t in tabelas:
                    if any(keyword in t.get_text().upper() for keyword in ['MOVIMENTAÇÃO', 'ARQUIVOS', 'DATA', 'USUÁRIO']):
                        tabela = t
                        break
            
            if not tabela:
                logger.warning("⚠️ Nenhuma tabela de movimentações encontrada")
                return []
            
            # Estratégias múltiplas para encontrar linhas
            linhas = (
                tabela.find_all('tr', class_=re.compile(r'TabelaLinha|filtro-entrada|linha|row', re.I)) or
                tabela.find_all('tr')[1:] if tabela.find_all('tr') else []
            )
            
            for linha in linhas:
                movimentacao = self._extrair_movimentacao_da_linha_inteligente(linha)
                if movimentacao:
                    movimentacoes.append(movimentacao)
            
            logger.info(f"✅ {len(movimentacoes)} movimentações extraídas da tabela")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro na extração inteligente da tabela: {e}")
            return []
    
    async def _extrair_movimentacoes_navegacao_html(self, page: Page) -> List[Movimentacao]:
        """Extrai movimentações da estrutura HTML de navegação (formato PLUS)"""
        try:
            movimentacoes = []
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            logger.info("🔍 Extraindo movimentações da estrutura HTML de navegação")
            
            # Encontrar o div de navegação
            navegacao_div = soup.find('div', {'id': 'menuNavegacao'})
            if not navegacao_div:
                logger.warning("⚠️ Div menuNavegacao não encontrado")
                return []
            
            # Extrair todas as LIs que contêm movimentações
            items = navegacao_div.find_all('li')
            
            for item in items:
                try:
                    texto = item.get_text()
                    
                    # Procurar por padrão: número - descrição
                    match = re.search(r'(\d+)\s*-\s*(.+)', texto)
                    if match:
                        numero = int(match.group(1))
                        descricao_completa = match.group(2).strip()
                        
                        # Separar tipo e descrição
                        partes_descricao = descricao_completa.split(' - ', 1)
                        tipo = partes_descricao[0].strip()
                        descricao = partes_descricao[1].strip() if len(partes_descricao) > 1 else ""
                        
                        # Verificar se tem anexos (links dentro do item)
                        links_anexo = item.find_all('a', href=True)
                        tem_anexo = len(links_anexo) > 0
                        codigo_anexo = ""
                        id_movimentacao = ""
                        
                        if tem_anexo and links_anexo:
                            # Extrair informações do primeiro link
                            primeiro_link = links_anexo[0]
                            href = primeiro_link.get('href', '')
                            
                            # Extrair Id_MovimentacaoArquivo e hash
                            match_id = re.search(r'Id_MovimentacaoArquivo=([^&]+)', href)
                            match_hash = re.search(r'hash=([^&]+)', href)
                            
                            if match_id:
                                id_movimentacao = match_id.group(1)
                            if match_hash:
                                codigo_anexo = match_hash.group(1)
                        
                        movimentacao = Movimentacao(
                            numero=numero,
                            tipo=self._limpar_tipo_movimentacao(tipo),
                            descricao=self._limpar_descricao_movimentacao(descricao),
                            data="",  # Data não está disponível nesta estrutura
                            usuario="",
                            tem_anexo=tem_anexo,
                            codigo_anexo=codigo_anexo,
                            id_movimentacao=id_movimentacao
                        )
                        
                        movimentacoes.append(movimentacao)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar item de navegação: {e}")
                    continue
            
            logger.info(f"✅ {len(movimentacoes)} movimentações extraídas da estrutura HTML")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro na extração HTML de navegação: {e}")
            return []
    
    async def _extrair_movimentacoes_pagina_principal_inteligente(self, page: Page) -> List[Movimentacao]:
        """Versão inteligente da extração de movimentações da página principal"""
        try:
            movimentacoes = []
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Procurar por diferentes estruturas que podem conter movimentações
            candidatos = [
                soup.find_all('div', class_=re.compile(r'movimentacao|movimento', re.I)),
                soup.find_all('li', class_=re.compile(r'movimentacao|movimento', re.I)),
                soup.find_all('tr', class_=re.compile(r'movimentacao|movimento', re.I)),
                soup.find_all(['div', 'section', 'article'], string=re.compile(r'movimentação|movimento', re.I))
            ]
            
            for grupo_candidatos in candidatos:
                for elemento in grupo_candidatos:
                    movimentacao = self._extrair_movimentacao_do_elemento_inteligente(elemento)
                    if movimentacao:
                        movimentacoes.append(movimentacao)
                        
                if movimentacoes:  # Se encontrou movimentações, não precisa tentar outras estratégias
                    break
            
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro na extração inteligente da página principal: {e}")
            return []
    
    async def _extrair_movimentacoes_navegacao(self, session: Session) -> List[Movimentacao]:
        """Navega para página de movimentações se necessário"""
        try:
            # Tentar encontrar e clicar em link para movimentações
            scripts_navegacao = [
                "() => { const link = document.querySelector('a[href*=\"movimentacao\"], a[href*=\"movimento\"]'); if(link) { link.click(); return true; } return false; }",
                "() => { const links = document.querySelectorAll('a'); for(let link of links) { if(link.textContent.includes('Moviment')) { link.click(); return true; } } return false; }",
                "() => { const menu = document.querySelector('[onclick*=\"movimentacao\"], [onclick*=\"movimento\"]'); if(menu) { menu.click(); return true; } return false; }"
            ]
            
            for script in scripts_navegacao:
                try:
                    resultado = await session.page.evaluate(script)
                    if resultado:
                        await session.page.wait_for_load_state('networkidle', timeout=30000)
                        
                        # Tentar extrair movimentações da nova página
                        movimentacoes = await self._extrair_movimentacoes_pagina_principal_inteligente(session.page)
                        if movimentacoes:
                            return movimentacoes
                        break
                except Exception as e:
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Erro na navegação para movimentações: {e}")
            return []
    
    async def _extrair_movimentacoes_fallback(self, page: Page) -> List[Movimentacao]:
        """Estratégia de fallback para extrair qualquer coisa que pareça movimentação"""
        try:
            movimentacoes = []
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Procurar por qualquer elemento que contenha padrões de movimentação
            elementos_texto = soup.find_all(['p', 'div', 'span', 'td', 'li'])
            
            for elemento in elementos_texto:
                texto = elemento.get_text(strip=True)
                
                # Padrões que indicam movimentações
                if self._texto_parece_movimentacao(texto):
                    movimentacao = self._criar_movimentacao_do_texto(texto)
                    if movimentacao:
                        movimentacoes.append(movimentacao)
            
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro no fallback de movimentações: {e}")
            return []
    
    def _extrair_movimentacao_da_linha_inteligente(self, linha) -> Optional[Movimentacao]:
        """Extrai movimentação de uma linha usando múltiplas estratégias"""
        try:
            tds = linha.find_all(['td', 'th'])
            if len(tds) < 3:  # Mínimo necessário
                return None
            
            # Estratégia adaptativa baseada no número de colunas
            numero = self._extrair_numero_movimentacao(tds)
            if numero is None:
                return None
            
            # Extrair informações de forma flexível
            tipo, descricao = self._extrair_tipo_descricao_inteligente(tds)
            data = self._extrair_data_inteligente(tds)
            usuario = self._extrair_usuario_inteligente(tds)
            tem_anexo, codigo_anexo, id_movimentacao = self._extrair_info_anexo_inteligente(linha, tds)
            
            return Movimentacao(
                numero=numero,
                tipo=tipo,
                descricao=descricao,
                data=data,
                usuario=usuario,
                tem_anexo=tem_anexo,
                id_movimentacao=id_movimentacao,
                codigo_anexo=codigo_anexo
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair movimentação da linha: {e}")
            return None
    
    def _extrair_movimentacao_do_elemento_inteligente(self, elemento) -> Optional[Movimentacao]:
        """Extrai movimentação de um elemento genérico"""
        try:
            texto = elemento.get_text(strip=True)
            if not self._texto_parece_movimentacao(texto):
                return None
            
            return self._criar_movimentacao_do_texto(texto)
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair movimentação do elemento: {e}")
            return None
    
    def _extrair_numero_movimentacao(self, tds) -> Optional[int]:
        """Extrai número da movimentação de forma inteligente"""
        for i, td in enumerate(tds[:3]):  # Verificar nas primeiras 3 colunas
            texto = td.get_text(strip=True)
            if texto.isdigit():
                return int(texto)
            
            # Tentar extrair número de texto misto
            match = re.search(r'(\d+)', texto)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extrair_tipo_descricao_inteligente(self, tds) -> tuple[str, str]:
        """Extrai tipo e descrição de forma inteligente"""
        # Procurar por coluna que contenha span com classe específica
        for td in tds:
            span_tipo = td.find('span', class_=re.compile(r'tipo|movimentacao', re.I))
            if span_tipo:
                tipo = span_tipo.get_text(strip=True)
                
                # Descrição pode estar após <br> ou no restante do texto
                br_element = td.find('br')
                if br_element and br_element.next_sibling:
                    descricao = str(br_element.next_sibling).strip()
                else:
                    descricao = td.get_text(strip=True).replace(tipo, '').strip()
                
                return tipo, descricao
        
        # Fallback: primeira coluna que não é número
        for td in tds:
            texto = td.get_text(strip=True)
            if texto and not texto.isdigit() and not re.match(r'\d{2}/\d{2}/\d{4}', texto):
                return texto, ""
        
        return "Movimentação", ""
    
    def _extrair_data_inteligente(self, tds) -> str:
        """Extrai data de forma inteligente"""
        for td in tds:
            texto = td.get_text(strip=True)
            if re.match(r'\d{2}/\d{2}/\d{4}', texto):
                return texto
        
        return ""
    
    def _extrair_usuario_inteligente(self, tds) -> str:
        """Extrai usuário de forma inteligente"""
        # Usuário geralmente está nas últimas colunas
        for td in reversed(tds):
            texto = td.get_text(strip=True)
            if texto and not re.match(r'\d{2}/\d{2}/\d{4}', texto) and not texto.isdigit():
                # Verificar se parece nome de usuário
                if len(texto) > 3 and ' ' in texto:
                    return texto
        
        return ""
    
    async def _extrair_info_anexo_inteligente_playwright(self, session: Session, linha_element) -> tuple[bool, str, str]:
        """Extrai informações de anexo usando Playwright para detectar links clicáveis"""
        tem_anexo = False
        codigo_anexo = ""
        id_movimentacao = ""
        
        try:
            # Procurar por links clicáveis dentro da linha
            links = await linha_element.query_selector_all('a[href], a[onclick]')
            
            for link in links:
                # Verificar se o link está relacionado a arquivo
                href = await link.get_attribute('href') or ""
                onclick = await link.get_attribute('onclick') or ""
                texto_link = await link.inner_text()
                
                # Padrões que indicam anexo
                if (any(ext in texto_link.lower() for ext in ['.pdf', '.doc', '.docx', '.jpg', '.png', 'arquivo', 'anexo', 'documento']) or
                    any(pattern in href.lower() for pattern in ['arquivo', 'anexo', 'documento', 'download']) or
                    any(pattern in onclick.lower() for pattern in ['arquivo', 'anexo', 'documento', 'buscarArquivos'])):
                    
                    tem_anexo = True
                    
                    # Extrair código do anexo do onclick
                    match = re.search(r"buscarArquivosMovimentacaoJSON\('([^']+)'", onclick)
                    if match:
                        codigo_anexo = match.group(1)
                    break
            
            # Se não encontrou links, usar estratégia de texto
            if not tem_anexo:
                texto_linha = await linha_element.inner_text()
                
                # Procurar por extensões de arquivo ou palavras-chave
                palavras_anexo = ['.pdf', '.doc', '.docx', '.jpg', '.png', 'anexo', 'arquivo', 'documento', 'petição', 'certidão', 'digitalizada']
                
                for palavra in palavras_anexo:
                    if palavra in texto_linha.lower():
                        tem_anexo = True
                        break
            
            return tem_anexo, codigo_anexo, id_movimentacao
            
        except Exception as e:
            # Fallback para método original em caso de erro
            return False, "", ""
    
    def _extrair_info_anexo_inteligente(self, linha, tds) -> tuple[bool, str, str]:
        """Extrai informações de anexo de forma inteligente (método legado para compatibilidade)"""
        tem_anexo = False
        codigo_anexo = ""
        id_movimentacao = ""
        
        # Converter linha para string para busca mais ampla
        linha_html = str(linha)
        
        # Estratégia 1: Procurar por imagens que indicam anexos
        for td in tds:
            if td.find('img', {'src': re.compile(r'anexo|arquivo|go-bottom|documento|pdf|attach', re.I)}):
                tem_anexo = True
                
                # Procurar por link com código do anexo
                link_anexo = td.find('a')
                if link_anexo:
                    onclick = link_anexo.get('onclick', '')
                    match = re.search(r"buscarArquivosMovimentacaoJSON\('([^']+)'", onclick)
                    if match:
                        codigo_anexo = match.group(1)
                break
        
        # Estratégia 2: Procurar por palavras-chave que indicam anexos no texto
        if not tem_anexo:
            palavras_anexo = ['.pdf', '.doc', '.docx', '.jpg', '.png', 'anexo', 'arquivo', 'documento', 'petição', 'certidão', 'digitalizada']
            texto_linha = linha.get_text().lower()
            
            for palavra in palavras_anexo:
                if palavra in texto_linha.lower():
                    tem_anexo = True
                    break
        
        # Estratégia 3: Procurar por links ou onclick relacionados a arquivos
        if not tem_anexo:
            if re.search(r'(arquivo|anexo|documento|pdf)', linha_html, re.I):
                tem_anexo = True
        
        # Estratégia 4: Procurar por padrões de ID de arquivo
        if not tem_anexo:
            if re.search(r'id_arquivo|arquivo_\d+|anexo_\d+', linha_html, re.I):
                tem_anexo = True
        
        # Procurar ID da movimentação
        div_drop = linha.find('div', class_=re.compile(r'drop|movimentacao', re.I))
        if div_drop:
            id_movimentacao = div_drop.get('id_movi', '') or div_drop.get('id', '')
        
        return tem_anexo, codigo_anexo, id_movimentacao
    
    async def _extrair_movimentacoes_playwright(self, session: Session) -> List[Movimentacao]:
        """Extrai movimentações usando Playwright para detectar anexos corretamente"""
        try:
            movimentacoes = []
            
            # Procurar por elementos que contenham movimentações na página atual
            possible_selectors = [
                'div.drop',  # Divs com classe drop
                'tr[id*="movi"]',  # Linhas com ID contendo "movi"
                'div[id*="movi"]',  # Divs com ID contendo "movi"
                '.movimentacao',  # Classe movimentacao
                'div:has-text("Movimentação")',  # Divs que contêm a palavra "Movimentação"
            ]
            
            for selector in possible_selectors:
                try:
                    elementos = await session.page.query_selector_all(selector)
                    
                    for elemento in elementos:
                        # Extrair texto do elemento
                        texto = await elemento.inner_text()
                        
                        if self._texto_parece_movimentacao(texto):
                            # Extrair número da movimentação
                            numero = self._extrair_numero_movimentacao(texto)
                            
                            # Extrair tipo e descrição
                            tipo, descricao = self._extrair_tipo_descricao(texto)
                            
                            # Extrair data
                            data = self._extrair_data_movimentacao(texto)
                            
                            # Extrair informações de anexo usando Playwright
                            tem_anexo, codigo_anexo, id_movimentacao = await self._extrair_info_anexo_inteligente_playwright(
                                session, elemento
                            )
                            
                            movimentacao = Movimentacao(
                                numero=numero,
                                tipo=tipo,
                                descricao=descricao,
                                data=data,
                                usuario="",
                                tem_anexo=tem_anexo,
                                codigo_anexo=codigo_anexo,
                                id_movimentacao=id_movimentacao
                            )
                            
                            movimentacoes.append(movimentacao)
                    
                    if movimentacoes:
                        break  # Se encontrou movimentações, parar
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro com seletor {selector}: {e}")
                    continue
            
            logger.info(f"✅ {len(movimentacoes)} movimentações extraídas com Playwright")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro na extração com Playwright: {e}")
            return []
    
    def _texto_parece_movimentacao(self, texto: str) -> bool:
        """Verifica se o texto parece ser uma movimentação"""
        if len(texto) < 10:
            return False
        
        # Padrões que indicam movimentações
        padroes_movimentacao = [
            r'\d+\s*-\s*.+\d{2}/\d{2}/\d{4}',  # Número - Descrição Data
            r'Movimentação\s*\d+',
            r'^\d+\.\s*.+',  # Número. Descrição
            r'\d{2}/\d{2}/\d{4}.*por.*'  # Data ... por usuário
        ]
        
        for padrao in padroes_movimentacao:
            if re.search(padrao, texto, re.I):
                return True
        
        return False
    
    def _criar_movimentacao_do_texto(self, texto: str) -> Optional[Movimentacao]:
        """Cria movimentação a partir de texto livre"""
        try:
            # Tentar extrair número
            match_numero = re.search(r'^(\d+)', texto)
            numero = int(match_numero.group(1)) if match_numero else 0
            
            # Tentar extrair data
            match_data = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
            data = match_data.group(1) if match_data else ""
            
            # Tentar extrair usuário (após "por")
            match_usuario = re.search(r'por\s+([^,\n]+)', texto, re.I)
            usuario = match_usuario.group(1).strip() if match_usuario else ""
            
            # Resto é tipo/descrição
            descricao = re.sub(r'^\d+[.\-\s]*', '', texto)  # Remover número inicial
            descricao = re.sub(r'\d{2}/\d{2}/\d{4}.*', '', descricao)  # Remover data e após
            descricao = descricao.strip()
            
            return Movimentacao(
                numero=numero,
                tipo="Movimentação",
                descricao=descricao,
                data=data,
                usuario=usuario,
                tem_anexo=False,
                id_movimentacao="",
                codigo_anexo=""
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao criar movimentação do texto: {e}")
            return None
    
    def _processar_movimentacoes_inteligente(self, movimentacoes: List[Movimentacao]) -> List[Movimentacao]:
        """Processa e melhora dados das movimentações"""
        movimentacoes_processadas = []
        
        for mov in movimentacoes:
            # Limpar e melhorar dados
            mov_processada = Movimentacao(
                numero=mov.numero,
                tipo=self._limpar_tipo_movimentacao(mov.tipo),
                descricao=self._limpar_descricao_movimentacao(mov.descricao),
                data=self._normalizar_data(mov.data),
                usuario=self._limpar_nome_usuario(mov.usuario),
                tem_anexo=mov.tem_anexo,
                id_movimentacao=mov.id_movimentacao,
                codigo_anexo=mov.codigo_anexo
            )
            
            movimentacoes_processadas.append(mov_processada)
        
        return movimentacoes_processadas
    
    def _ordenar_movimentacoes_inteligente(self, movimentacoes: List[Movimentacao]) -> List[Movimentacao]:
        """Ordena movimentações de forma inteligente"""
        try:
            # Primeira tentativa: ordenar por número (mais recentes primeiro)
            if all(mov.numero > 0 for mov in movimentacoes):
                return sorted(movimentacoes, key=lambda x: x.numero, reverse=True)
            
            # Segunda tentativa: ordenar por data
            movs_com_data = [mov for mov in movimentacoes if mov.data]
            if movs_com_data:
                from datetime import datetime
                def data_para_datetime(data_str):
                    try:
                        return datetime.strptime(data_str, '%d/%m/%Y')
                    except:
                        return datetime.min
                
                return sorted(movimentacoes, key=lambda x: data_para_datetime(x.data), reverse=True)
            
            # Fallback: manter ordem original
            return movimentacoes
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao ordenar movimentações: {e}")
            return movimentacoes
    
    def _limpar_tipo_movimentacao(self, tipo: str) -> str:
        """Limpa e normaliza tipo de movimentação"""
        if not tipo:
            return "Movimentação"
        
        # Remover HTML tags se houver
        tipo = re.sub(r'<[^>]+>', '', tipo)
        
        # Limpar espaços e caracteres especiais
        tipo = re.sub(r'\s+', ' ', tipo).strip()
        
        return tipo
    
    def _limpar_descricao_movimentacao(self, descricao: str) -> str:
        """Limpa e normaliza descrição de movimentação"""
        if not descricao:
            return ""
        
        # Remover HTML tags
        descricao = re.sub(r'<[^>]+>', '', descricao)
        
        # Limpar espaços extras e quebras de linha
        descricao = re.sub(r'\s+', ' ', descricao).strip()
        
        return descricao
    
    def _normalizar_data(self, data: str) -> str:
        """Normaliza formato de data"""
        if not data:
            return ""
        
        # Extrair data no formato dd/mm/yyyy
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', data)
        return match.group(1) if match else data
    
    def _limpar_nome_usuario(self, usuario: str) -> str:
        """Limpa nome do usuário"""
        if not usuario:
            return ""
        
        # Remover prefixos comuns
        usuario = re.sub(r'^(por|by|user|usuario):\s*', '', usuario, flags=re.I)
        
        # Limpar espaços
        usuario = re.sub(r'\s+', ' ', usuario).strip()
        
        return usuario
    
    async def _extrair_movimentacoes_tabela_arquivos(self, page: Page) -> List[Movimentacao]:
        """Extrai movimentações da tabela de arquivos (página de navegação)"""
        try:
            movimentacoes = []
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            tabela = soup.find('table', {'id': 'TabelaArquivos'})
            if not tabela:
                return []
            
            linhas = tabela.find_all('tr', class_=re.compile(r'TabelaLinha|filtro-entrada'))
            if not linhas:
                linhas = tabela.find_all('tr')[1:]  # Pular cabeçalho
            
            for linha in linhas:
                tds = linha.find_all('td')
                if len(tds) >= 5:
                    try:
                        numero_text = tds[0].get_text(strip=True)
                        if not numero_text.isdigit():
                            continue
                            
                        numero = int(numero_text)
                        
                        # Extrair tipo e descrição da movimentação
                        movimentacao_celula = tds[1]
                        span_tipo = movimentacao_celula.find('span', class_='filtro_tipo_movimentacao')
                        
                        if span_tipo:
                            tipo = span_tipo.get_text(strip=True)
                            # Descrição vem após o <br>
                            br_element = movimentacao_celula.find('br')
                            if br_element and br_element.next_sibling:
                                descricao = str(br_element.next_sibling).strip()
                            else:
                                descricao = movimentacao_celula.get_text(strip=True).replace(tipo, '').strip()
                        else:
                            tipo = movimentacao_celula.get_text(strip=True)
                            descricao = ""
                        
                        data = tds[2].get_text(strip=True)
                        usuario = tds[3].get_text(strip=True)
                        
                        # Verificar se tem anexo
                        arquivos_celula = tds[4]
                        tem_anexo = bool(arquivos_celula.find('img', {'src': 'imagens/22x22/go-bottom.png'}))
                        
                        # Extrair código de anexo se houver
                        codigo_anexo = ""
                        if tem_anexo:
                            link_anexo = arquivos_celula.find('a')
                            if link_anexo:
                                onclick = link_anexo.get('onclick', '')
                                match = re.search(r"buscarArquivosMovimentacaoJSON\('([^']+)'", onclick)
                                if match:
                                    codigo_anexo = match.group(1)
                        
                        # Extrair ID da movimentação
                        id_movimentacao = ""
                        div_drop = linha.find('div', class_='dropMovimentacao')
                        if div_drop:
                            id_movimentacao = div_drop.get('id_movi', '')
                        
                        movimentacao = Movimentacao(
                            numero=numero,
                            tipo=tipo,
                            descricao=descricao,
                            data=data,
                            usuario=usuario,
                            tem_anexo=tem_anexo,
                            id_movimentacao=id_movimentacao,
                            codigo_anexo=codigo_anexo,
                            html_completo=str(linha)
                        )
                        
                        movimentacoes.append(movimentacao)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao processar linha de movimentação: {e}")
                        continue
            
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair movimentações da tabela: {e}")
            return []
    
    async def _extrair_movimentacoes_pagina_principal(self, page: Page) -> List[Movimentacao]:
        """Extrai movimentações da página principal do processo"""
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            movimentacoes = []
            
            # Procurar por elementos que contêm movimentações
            elementos_mov = soup.find_all(['div', 'tr'], class_=re.compile(r'movimentacao|movimento'))
            
            for i, elemento in enumerate(elementos_mov):
                try:
                    texto = elemento.get_text(strip=True)
                    if len(texto) > 20:  # Filtrar textos muito curtos
                        # Detectar anexos de forma inteligente
                        tem_anexo = self._detectar_anexo_movimentacao(texto, str(elemento))
                        
                        movimentacao = Movimentacao(
                            numero=i + 1,
                            tipo="Movimentação",
                            descricao=texto[:200],  # Limitar tamanho
                            data="",
                            usuario="",
                            tem_anexo=tem_anexo,
                            id_movimentacao=f"mov_{i}",
                            html_completo=str(elemento)
                        )
                        movimentacoes.append(movimentacao)
                        
                except Exception as e:
                    continue
            
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair movimentações da página principal: {e}")
            return []
    
    def _detectar_anexo_movimentacao(self, texto: str, html_completo: str) -> bool:
        """Detecta se uma movimentação tem anexo baseado no texto e HTML"""
        try:
            # Palavras-chave EXPANDIDAS que indicam anexos
            palavras_anexo = [
                # Anexos explícitos
                'anexo', 'anexos', 'anexado', 'anexa', 'anexar',
                'arquivo', 'arquivos', 'arq.', 'file', 'files',
                'documento', 'documentos', 'doc', 'docs',
                
                # Extensões de arquivo
                '.pdf', '.doc', '.docx', '.html', '.txt', '.jpg', '.jpeg', '.png',
                '.zip', '.rar', '.xml', '.xls', '.xlsx', '.odt', '.rtf',
                
                # Tipos de documentos jurídicos
                'petição', 'peticao', 'petição inicial', 'contestação', 'contestacao',
                'certidão', 'certidao', 'comprovante', 'declaração', 'declaracao',
                'ata', 'termo', 'relatório', 'relatorio', 'laudo',
                'procuração', 'procuracao', 'substabelecimento',
                
                # Ações de upload/envio
                'upload', 'envio', 'enviado', 'juntada', 'juntado',
                'protocolado', 'protocolo', 'digitalizado',
                
                # Indicadores visuais comuns
                'visualizar', 'baixar', 'download', 'ver anexo',
                'clique aqui', 'acesse', 'consulte'
            ]
            
            # Verificar no texto
            texto_lower = texto.lower()
            for palavra in palavras_anexo:
                if palavra in texto_lower:
                    return True
            
            # Verificar no HTML (links, botões, ícones) - EXPANDIDO
            html_lower = html_completo.lower()
            indicadores_html = [
                # Links diretos
                'href=', 'src=', 'url=', 'link=',
                
                # Atributos de download
                'download', 'attachment', 'file', 'documento',
                
                # Classes e IDs CSS comuns
                'icon-download', 'icon-file', 'icon-pdf', 'icon-attach',
                'btn-download', 'btn-file', 'btn-anexo', 'link-arquivo',
                'file-link', 'doc-link', 'anexo-link',
                
                # Ações e comandos
                'visualizar', 'baixar', 'abrir', 'acessar',
                'onclick', 'javascript:', 'window.open',
                
                # Indicadores de arquivo específicos
                'pdf', 'doc', 'arquivo', 'anexo',
                'target="_blank"', 'new window', 'nova janela'
            ]
            
            for indicador in indicadores_html:
                if indicador in html_lower:
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao detectar anexo: {e}")
            return False
    
    async def _extrair_partes_fallback_texto(self, page: Page) -> Dict[str, List[ParteEnvolvida]]:
        """Extração de partes por análise de texto como último recurso"""
        try:
            content = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
            texto_completo = soup.get_text()
            
            # Procurar padrões de nomes (palavras em maiúsculo seguidas)
            import re
            nomes_encontrados = re.findall(r'[A-ZÁÊÇÕ][A-Za-záêçõ\s]{15,60}', texto_completo)
            
            # Procurar CPFs e CNPJs
            cpfs = re.findall(r'\d{3}\.\d{3}\.\d{3}-\d{2}', texto_completo)
            cnpjs = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto_completo)
            
            logger.info(f"🔍 Encontrados: {len(nomes_encontrados)} nomes, {len(cpfs)} CPFs, {len(cnpjs)} CNPJs")
            
            # Adicionar pessoas físicas
            for cpf in cpfs:
                parte = ParteEnvolvida(
                    nome=f"Pessoa com CPF {cpf}",
                    tipo="Pessoa Física",
                    documento=cpf,
                    endereco="",
                    telefone="",
                    advogado=""
                )
                partes['outros'].append(parte)
            
            # Adicionar pessoas jurídicas
            for cnpj in cnpjs:
                parte = ParteEnvolvida(
                    nome=f"Empresa com CNPJ {cnpj}",
                    tipo="Pessoa Jurídica", 
                    documento=cnpj,
                    endereco="",
                    telefone="",
                    advogado=""
                )
                partes['outros'].append(parte)
            
            # Adicionar nomes únicos
            nomes_unicos = list(set([nome.strip() for nome in nomes_encontrados if len(nome.strip()) > 15]))[:5]
            for nome in nomes_unicos:
                parte = ParteEnvolvida(
                    nome=nome.strip(),
                    tipo="Parte Envolvida",
                    documento="",
                    endereco="",
                    telefone="",
                    advogado=""
                )
                partes['outros'].append(parte)
            
            total_partes = sum(len(p) for p in partes.values())
            logger.info(f"✅ Fallback: {total_partes} partes extraídas")
            
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro no fallback de partes: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
    
    async def _extrair_partes_envolvidas(self, session: Session) -> Dict[str, List[ParteEnvolvida]]:
        """Extrai partes envolvidas no processo"""
        try:
            logger.info("👥 Extraindo partes envolvidas...")
            
            # Verificar se estamos na página correta do processo
            url_atual = session.page.url
            content_inicial = await session.page.content()
            
            # Verificação mais flexível - tentamos extrair independente da página
            logger.info(f"🔍 URL atual: {url_atual}")
            logger.info(f"🔍 Procurando partes na página atual...")
            
            # Se não estamos em página específica, tentar extrair da página atual mesmo assim
            if "corpo_dados_processo" not in content_inicial and "ProcessoParte" not in url_atual:
                logger.info("⚠️ Tentando extrair partes da página atual mesmo sem indicadores específicos")
            
            partes = {
                'polo_ativo': [],
                'polo_passivo': [],
                'outros': []
            }
            
            # ESTRATÉGIA ROBUSTA: Extrair partes da página atual SEM navegar
            logger.info("🔍 Extraindo partes da página atual...")
            partes = await self._extrair_partes_da_pagina(session.page)
            
            # Se não encontrou na página atual, tentar navegar (sem timeout longo)
            if not any(partes.values()):
                logger.info("🔍 Tentando acessar página específica de partes...")
                try:
                    # URL mais direta e confiável
                    url_partes = f"{self.base_url}/ProcessoParte?PaginaAtual=2"
                    await session.page.goto(url_partes, timeout=10000, wait_until='domcontentloaded')
                    await asyncio.sleep(1)  # Aguardar mínimo
                    
                    # Verificar se carregou
                    content = await session.page.content()
                    if "Usuário inválido" not in content and "erro" not in content.lower():
                        partes = await self._extrair_partes_da_pagina(session.page)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Navegação para partes falhou: {e}")
                    # Continuar com página atual
            
            # FALLBACK FINAL: Extração inteligente de texto da página atual
            if not any(partes.values()):
                logger.info("🔍 Fallback: Extraindo partes por análise de texto...")
                partes = await self._extrair_partes_fallback_texto(session.page)
            
            total_partes = sum(len(p) for p in partes.values())
            logger.info(f"✅ {total_partes} partes extraídas")
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes envolvidas: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}

    # =========================
    # NOVO MODO OPCIONAL (detalhado)
    # =========================
    async def _extrair_partes_navegacao_detalhada(self, session: Session) -> Dict[str, List[ParteEnvolvida]]:
        """Navega por ProcessoParte?PaginaAtual=6 (aguarda 1s) → ProcessoParte?PaginaAtual=2 e extrai partes clicando em 'Editar'."""
        try:
            logger.info("🚀 Extração detalhada de partes iniciada")
            partes: Dict[str, List[ParteEnvolvida]] = {
                'polo_ativo': [],
                'polo_passivo': [],
                'outros': []
            }
            # Passo 1: página 6 e aguardo
            try:
                await session.page.goto(f"{self.base_url}/ProcessoParte?PaginaAtual=6", timeout=15000, wait_until='domcontentloaded')
            except Exception as e:
                logger.warning(f"⚠️ Falha ao abrir PaginaAtual=6: {e}")
            await asyncio.sleep(1)
            # Passo 2: página 2 para extração
            await session.page.goto(f"{self.base_url}/ProcessoParte?PaginaAtual=2", timeout=15000, wait_until='domcontentloaded')
            await asyncio.sleep(1)
            fieldsets_config = {
                'polo_ativo': 'fieldset.VisualizaDados:nth-child(6)',
                'polo_passivo': 'fieldset.VisualizaDados:nth-child(7)',
                'outros': 'fieldset.VisualizaDados:nth-child(8)'
            }
            for tipo_parte in ['polo_ativo', 'polo_passivo', 'outros']:
                try:
                    extraidas = await self._extrair_partes_fieldset_detalhado(session, tipo_parte)
                    partes[tipo_parte].extend(extraidas)
                    logger.info(f"✅ {len(extraidas)} partes extraídas em {tipo_parte} (detalhado)")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao extrair {tipo_parte} (detalhado): {e}")
            logger.info(f"🎯 Extração detalhada concluída: {sum(len(v) for v in partes.values())} partes")
            return partes
        except Exception as e:
            logger.error(f"❌ Erro na extração detalhada: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}

    async def _extrair_partes_fieldset_detalhado(self, session: Session, tipo_parte: str) -> List[ParteEnvolvida]:
        """Percorre botões 'Editar' do fieldset para coletar dados completos das partes."""
        partes_extraidas: List[ParteEnvolvida] = []
        fieldsets_config = {
            'polo_ativo': 'fieldset.VisualizaDados:nth-child(6)',
            'polo_passivo': 'fieldset.VisualizaDados:nth-child(7)',
            'outros': 'fieldset.VisualizaDados:nth-child(8)'
        }
        try:
            seletor_fieldset = fieldsets_config.get(tipo_parte)
            if not seletor_fieldset:
                return partes_extraidas
            seletores_botoes = [
                'button.imgIcons[title*="Editar"]',
                'button[onclick*="PassoEditar"]',
                'button.imgIcons[onclick*="PassoEditar"]',
                'button[title*="Editar"]'
            ]
            # descobrir qual seletor encontra botões
            seletor_usado = None
            for candidato in seletores_botoes:
                fs = await session.page.query_selector(seletor_fieldset)
                if not fs:
                    break
                btns = await fs.query_selector_all(candidato)
                if btns:
                    seletor_usado = candidato
                    break
            if not seletor_usado:
                logger.info(f"ℹ️ Nenhum botão 'Editar' encontrado em {tipo_parte}")
                return partes_extraidas
            i = 0
            while True:
                fs = await session.page.query_selector(seletor_fieldset)
                if not fs:
                    break
                btns = await fs.query_selector_all(seletor_usado)
                if i >= len(btns):
                    break
                botao = btns[i]
                try:
                    if not (await botao.is_visible()) or not (await botao.is_enabled()):
                        i += 1
                        continue
                    await botao.click()
                    await asyncio.sleep(2)
                    parte = await self._extrair_dados_edicao_parte(session.page, tipo_parte)
                    if parte:
                        partes_extraidas.append(parte)
                    await session.page.go_back(timeout=10000)
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar botão {i+1} ({tipo_parte}): {e}")
                    try:
                        await session.page.go_back(timeout=5000)
                        await asyncio.sleep(1)
                    except Exception:
                        pass
                i += 1
        except Exception as e:
            logger.error(f"❌ Erro no fieldset detalhado {tipo_parte}: {e}")
        return partes_extraidas

    async def _extrair_dados_edicao_parte(self, page: Page, tipo_parte: str) -> Optional[ParteEnvolvida]:
        """Extrai dados detalhados da página de edição de uma parte (nome, documento, contato e endereço)."""
        try:
            await page.wait_for_load_state('domcontentloaded')
            async def extrair_valor(seletores: List[str]) -> str:
                for sel in seletores:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            val = await el.get_attribute('value')
                            if val and val.strip():
                                return val.strip()
                            txt = await el.inner_text()
                            if txt and txt.strip():
                                return txt.strip()
                    except Exception:
                        continue
                return ""
            nome = await extrair_valor(['input[name="Nome"]','input[name*="Nome"]','input[id*="Nome"]','#Nome'])
            documento = await extrair_valor(['input[name="Cpf"]','input[name="Cnpj"]','input[name="CNPJ"]','input[id="Cpf"]','input[id="Cnpj"]','input[id="CNPJ"]','input[name*="CPF"]','input[name*="CNPJ"]','input[name*="Cnpj"]'])
            email = await extrair_valor(['input[name*="Email"]','input[id*="Email"]','input[type="email"]'])
            telefone = await extrair_valor(['input[name*="Telefone"]','input[id*="Telefone"]','input[name*="Fone"]'])
            logradouro = await extrair_valor(['input[name="Logradouro"]','input[name*="Logradouro"]'])
            numero = await extrair_valor(['input[name="Numero"]','input[name*="Numero"]'])
            complemento = await extrair_valor(['input[name="Complemento"]','input[name*="Complemento"]'])
            bairro = await extrair_valor(['input[name="Bairro"]','input[name*="Bairro"]'])
            cidade = await extrair_valor(['input[name="Cidade"]','input[name*="Cidade"]'])
            uf = await extrair_valor(['input[name="UF"]','select[name="UF"]','input[name*="UF"]'])
            cep = await extrair_valor(['input[name="CEP"]','input[name*="CEP"]'])
            campos_end = [v for v in [logradouro, numero, complemento, bairro, cidade, uf, f"CEP: {cep}" if cep else ""] if v]
            endereco = ' - '.join(campos_end)
            if not nome or len(nome.strip()) < 3:
                return None
            return ParteEnvolvida(
                nome=nome.strip(),
                tipo={'polo_ativo':'Polo Ativo','polo_passivo':'Polo Passivo'}.get(tipo_parte,'Outras Partes'),
                documento=documento.strip() if documento else "",
                endereco=endereco.strip() if endereco else "",
                telefone=telefone.strip() if telefone else "",
                email=email.strip() if email else ""
            )
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados de edição: {e}")
            return None
    
    async def _extrair_partes_da_pagina(self, page: Page) -> Dict[str, List[ParteEnvolvida]]:
        """Extrai partes de uma página específica com múltiplas estratégias inteligentes"""
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            partes = {
                'polo_ativo': [],
                'polo_passivo': [],
                'outros': []
            }
            
            logger.info("🔍 Iniciando extração inteligente de partes...")
            
            # Estratégia 1: Fieldsets com legendas (mais comum)
            partes_fieldsets = self._extrair_partes_fieldsets(soup)
            if any(partes_fieldsets.values()):
                logger.info(f"✅ Estratégia 1 (Fieldsets): Encontradas {sum(len(v) for v in partes_fieldsets.values())} partes")
                for categoria, lista_partes in partes_fieldsets.items():
                    partes[categoria].extend(lista_partes)
            
            # Estratégia 2: Tabelas estruturadas
            if not any(partes.values()):
                partes_tabelas = self._extrair_partes_tabelas(soup)
                if any(partes_tabelas.values()):
                    logger.info(f"✅ Estratégia 2 (Tabelas): Encontradas {sum(len(v) for v in partes_tabelas.values())} partes")
                    for categoria, lista_partes in partes_tabelas.items():
                        partes[categoria].extend(lista_partes)
            
            # Estratégia 3: Divs com classes específicas
            if not any(partes.values()):
                partes_divs = self._extrair_partes_divs(soup)
                if any(partes_divs.values()):
                    logger.info(f"✅ Estratégia 3 (Divs): Encontradas {sum(len(v) for v in partes_divs.values())} partes")
                    for categoria, lista_partes in partes_divs.items():
                        partes[categoria].extend(lista_partes)
            
            # Estratégia 4: Análise de texto estruturado
            if not any(partes.values()):
                partes_texto = self._extrair_partes_texto_inteligente(soup)
                if any(partes_texto.values()):
                    logger.info(f"✅ Estratégia 4 (Texto): Encontradas {sum(len(v) for v in partes_texto.values())} partes")
                    for categoria, lista_partes in partes_texto.items():
                        partes[categoria].extend(lista_partes)
            
            # Estratégia 5: Fallback - busca geral por padrões
            if not any(partes.values()):
                partes_fallback = self._extrair_partes_fallback(soup)
                if any(partes_fallback.values()):
                    logger.info(f"✅ Estratégia 5 (Fallback): Encontradas {sum(len(v) for v in partes_fallback.values())} partes")
                    for categoria, lista_partes in partes_fallback.items():
                        partes[categoria].extend(lista_partes)
            
            # Remover duplicatas mantendo informações mais completas
            partes = self._remover_duplicatas_partes(partes)
            
            total_partes = sum(len(v) for v in partes.values())
            logger.info(f"🎯 Total final: {total_partes} partes únicas extraídas")
            
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes da página: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
    
    def _extrair_partes_fieldsets(self, soup) -> Dict[str, List[ParteEnvolvida]]:
        """Estratégia 1: Extrai partes de fieldsets com legendas"""
        partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
        
        fieldsets = soup.find_all('fieldset')
        for fieldset in fieldsets:
            legend = fieldset.find('legend')
            if legend:
                titulo = legend.get_text(strip=True).upper()
                
                if any(palavra in titulo for palavra in ['POLO ATIVO', 'REQUERENTE', 'AUTOR']):
                    partes['polo_ativo'].extend(self._extrair_partes_do_fieldset(fieldset, 'Polo Ativo'))
                elif any(palavra in titulo for palavra in ['POLO PASSIVO', 'REQUERIDO', 'RÉU', 'EXECUTADO']):
                    partes['polo_passivo'].extend(self._extrair_partes_do_fieldset(fieldset, 'Polo Passivo'))
                elif any(palavra in titulo for palavra in ['OUTRAS', 'SUJEITOS', 'TERCEIRO', 'INTERVENIENTE']):
                    partes['outros'].extend(self._extrair_partes_do_fieldset(fieldset, 'Outras'))
        
        return partes
    
    def _extrair_partes_tabelas(self, soup) -> Dict[str, List[ParteEnvolvida]]:
        """Estratégia 2: Extrai partes de tabelas estruturadas"""
        partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
        
        # Procurar tabelas que podem conter partes
        tabelas = soup.find_all('table')
        for tabela in tabelas:
            # Analisar cabeçalhos para identificar tipo de parte
            thead = tabela.find('thead')
            tbody = tabela.find('tbody')
            
            if not tbody:
                tbody = tabela  # Usar a própria tabela se não há tbody
            
            # Procurar por indicadores de tipo de parte
            texto_tabela = tabela.get_text().upper()
            
            tipo_parte = 'outros'
            if any(palavra in texto_tabela for palavra in ['POLO ATIVO', 'REQUERENTE', 'AUTOR']):
                tipo_parte = 'polo_ativo'
            elif any(palavra in texto_tabela for palavra in ['POLO PASSIVO', 'REQUERIDO', 'RÉU']):
                tipo_parte = 'polo_passivo'
            
            # Extrair partes das linhas da tabela
            linhas = tbody.find_all('tr')
            for linha in linhas:
                parte = self._extrair_parte_da_linha_tabela(linha, tipo_parte)
                if parte:
                    partes[tipo_parte].append(parte)
        
        return partes
    
    def _extrair_partes_divs(self, soup) -> Dict[str, List[ParteEnvolvida]]:
        """Estratégia 3: Extrai partes de divs com classes específicas"""
        partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
        
        # Procurar divs que podem conter informações de partes
        divs_candidatos = soup.find_all('div', class_=re.compile(r'parte|polo|sujeito', re.I))
        
        for div in divs_candidatos:
            texto_div = div.get_text().upper()
            
            tipo_parte = 'outros'
            if any(palavra in texto_div for palavra in ['POLO ATIVO', 'REQUERENTE', 'AUTOR']):
                tipo_parte = 'polo_ativo'
            elif any(palavra in texto_div for palavra in ['POLO PASSIVO', 'REQUERIDO', 'RÉU']):
                tipo_parte = 'polo_passivo'
            
            parte = self._extrair_parte_do_elemento(div, tipo_parte)
            if parte:
                partes[tipo_parte].append(parte)
        
        return partes
    
    def _extrair_partes_texto_inteligente(self, soup) -> Dict[str, List[ParteEnvolvida]]:
        """Estratégia 4: Análise inteligente de texto estruturado"""
        partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
        
        texto_completo = soup.get_text()
        
        # Padrões para identificar seções de partes
        padroes_secoes = [
            (r'POLO ATIVO[:\s]*\n(.*?)(?=POLO PASSIVO|$)', 'polo_ativo'),
            (r'POLO PASSIVO[:\s]*\n(.*?)(?=POLO ATIVO|OUTRAS|$)', 'polo_passivo'),
            (r'REQUERENTE[:\s]*\n(.*?)(?=REQUERIDO|$)', 'polo_ativo'),
            (r'REQUERIDO[:\s]*\n(.*?)(?=REQUERENTE|$)', 'polo_passivo'),
            (r'AUTOR[:\s]*\n(.*?)(?=RÉU|$)', 'polo_ativo'),
            (r'RÉU[:\s]*\n(.*?)(?=AUTOR|$)', 'polo_passivo'),
        ]
        
        for padrao, tipo_parte in padroes_secoes:
            matches = re.finditer(padrao, texto_completo, re.MULTILINE | re.IGNORECASE | re.DOTALL)
            for match in matches:
                secao_texto = match.group(1)
                partes_secao = self._extrair_partes_do_texto_secao(secao_texto, tipo_parte)
                partes[tipo_parte].extend(partes_secao)
        
        return partes
    
    def _extrair_partes_fallback(self, soup) -> Dict[str, List[ParteEnvolvida]]:
        """Estratégia 5: Fallback - busca geral por padrões de nomes"""
        partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
        
        # Procurar por qualquer elemento que contenha padrões de nomes de pessoas
        elementos_texto = soup.find_all(['p', 'div', 'span', 'td', 'li'])
        
        for elemento in elementos_texto:
            texto = elemento.get_text(strip=True)
            
            # Padrões que indicam nomes de pessoas
            if self._parece_nome_pessoa(texto):
                # Tentar determinar o tipo baseado no contexto
                contexto = self._obter_contexto_elemento(elemento)
                tipo_parte = self._determinar_tipo_parte_contexto(contexto)
                
                parte = ParteEnvolvida(
                    nome=self._limpar_nome_parte(texto),
                    tipo=tipo_parte.replace('_', ' ').title(),
                    documento=self._extrair_documento_texto(texto),
                    endereco=self._extrair_endereco_texto(texto)
                )
                
                partes[tipo_parte].append(parte)
        
        return partes
    
    def _remover_duplicatas_partes(self, partes: Dict[str, List[ParteEnvolvida]]) -> Dict[str, List[ParteEnvolvida]]:
        """Remove duplicatas mantendo as informações mais completas"""
        partes_unicas = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
        
        for categoria, lista_partes in partes.items():
            nomes_vistos = set()
            
            for parte in lista_partes:
                nome_normalizado = self._normalizar_nome_para_comparacao(parte.nome)
                
                if nome_normalizado not in nomes_vistos and nome_normalizado:
                    nomes_vistos.add(nome_normalizado)
                    partes_unicas[categoria].append(parte)
                else:
                    # Se já existe, manter a que tem mais informações
                    for i, parte_existente in enumerate(partes_unicas[categoria]):
                        if self._normalizar_nome_para_comparacao(parte_existente.nome) == nome_normalizado:
                            if self._parte_tem_mais_informacoes(parte, parte_existente):
                                partes_unicas[categoria][i] = parte
                            break
        
        return partes_unicas
    
    def _normalizar_nome_para_comparacao(self, nome: str) -> str:
        """Normaliza nome para comparação de duplicatas"""
        if not nome:
            return ""
        
        # Remover acentos, converter para maiúscula, remover espaços extras
        import unicodedata
        nome_normalizado = unicodedata.normalize('NFD', nome)
        nome_normalizado = ''.join(c for c in nome_normalizado if unicodedata.category(c) != 'Mn')
        nome_normalizado = re.sub(r'\s+', ' ', nome_normalizado.upper().strip())
        
        return nome_normalizado
    
    def _parte_tem_mais_informacoes(self, parte1: ParteEnvolvida, parte2: ParteEnvolvida) -> bool:
        """Verifica qual parte tem mais informações"""
        campos_parte1 = sum(1 for campo in [parte1.documento, parte1.endereco, parte1.telefone, parte1.email, parte1.advogado] if campo)
        campos_parte2 = sum(1 for campo in [parte2.documento, parte2.endereco, parte2.telefone, parte2.email, parte2.advogado] if campo)
        
        return campos_parte1 > campos_parte2
    
    def _parece_nome_pessoa(self, texto: str) -> bool:
        """Verifica se o texto parece ser um nome de pessoa"""
        if not texto or len(texto) < 5:
            return False
        
        # Padrões que indicam nomes de pessoas
        padroes_nome = [
            r'^[A-ZÀ-Ÿ][a-zà-ÿ]+ [A-ZÀ-Ÿ][a-zà-ÿ]+',  # Nome Sobrenome
            r'[A-ZÀ-Ÿ][a-zà-ÿ]+ [A-ZÀ-Ÿ][a-zà-ÿ]+ [A-ZÀ-Ÿ][a-zà-ÿ]+',  # Nome Meio Sobrenome
        ]
        
        for padrao in padroes_nome:
            if re.search(padrao, texto):
                return True
        
        return False
    
    def _parece_endereco(self, texto: str) -> bool:
        """Verifica se o texto parece ser um endereço"""
        if not texto:
            return False
        
        texto_lower = texto.lower()
        
        # Padrões que indicam endereços
        padroes_endereco = [
            r'\b(rua|av|avenida|travessa|alameda|praça|quadra|lote|qd|lt|bloco|ap|apartamento)\b',
            r'\bnº?\s*\d+',  # número da casa/prédio
            r'\bqd\.?\s*\d+',  # quadra
            r'\blt\.?\s*\d+',  # lote
            r'\bcep\s*:?\s*\d{5}-?\d{3}',  # CEP
            r'\b\d{5}-?\d{3}\b',  # CEP sem prefixo
        ]
        
        for padrao in padroes_endereco:
            if re.search(padrao, texto_lower):
                return True
        
        # Verificar se contém cidade/estado comuns
        if any(cidade in texto_lower for cidade in ['caldas novas', 'goiânia', 'brasília', 'go', 'df', 'sp']):
            return True
            
        return False
    
    def _parece_nome_valido(self, texto: str) -> bool:
        """Verifica se o texto parece ser um nome válido de pessoa ou empresa (versão simplificada)"""
        if not texto or len(texto) < 3:
            return False
        
        texto_limpo = texto.strip()
        
        # Rejeitar textos muito longos
        if len(texto_limpo) > 120:
            return False
        
        # Rejeitar se é só números, símbolos ou código
        if re.match(r'^[\d\s\-\.\/\(\)]+$', texto_limpo):
            return False
        
        # Rejeitar palavras técnicas muito específicas
        palavras_rejeitadas = [
            'conhecimento', 'ativo', 'processo', 'vara', 'tribunal', 'custas',
            'código', 'protocolo', 'certidão', 'cpf', 'cnpj', 'registro'
        ]
        
        # Verificar se contém apenas palavras rejeitadas
        palavras_texto = texto_limpo.lower().split()
        if all(palavra in palavras_rejeitadas for palavra in palavras_texto if len(palavra) > 2):
            return False
        
        # Deve ter pelo menos uma letra
        if not re.search(r'[a-zA-ZÀ-Ÿà-ÿ]', texto_limpo):
            return False
        
        # Deve ter pelo menos 2 palavras significativas (2+ caracteres)
        palavras_significativas = [p for p in texto_limpo.split() if len(p) >= 2]
        if len(palavras_significativas) < 1:  # Relaxado de 2 para 1
            return False
        
        # Não deve ter mais de 50% números
        numeros = re.findall(r'\d', texto_limpo)
        if len(numeros) > len(texto_limpo) * 0.5:
            return False
        
        # APROVADO: Muito mais permissivo para capturar nomes reais
        return True
    
    def _obter_contexto_elemento(self, elemento) -> str:
        """Obtém contexto do elemento para determinar tipo de parte"""
        contexto = ""
        
        # Verificar elemento pai
        if elemento.parent:
            contexto += elemento.parent.get_text()
        
        # Verificar irmãos anteriores e posteriores
        for sibling in elemento.previous_siblings:
            if hasattr(sibling, 'get_text'):
                contexto += sibling.get_text()
                
        for sibling in elemento.next_siblings:
            if hasattr(sibling, 'get_text'):
                contexto += sibling.get_text()
        
        return contexto.upper()
    
    def _determinar_tipo_parte_contexto(self, contexto: str) -> str:
        """Determina tipo de parte baseado no contexto"""
        if any(palavra in contexto for palavra in ['POLO ATIVO', 'REQUERENTE', 'AUTOR']):
            return 'polo_ativo'
        elif any(palavra in contexto for palavra in ['POLO PASSIVO', 'REQUERIDO', 'RÉU']):
            return 'polo_passivo'
        else:
            return 'outros'
    
    def _extrair_parte_da_linha_tabela(self, linha, tipo_parte: str) -> Optional[ParteEnvolvida]:
        """Extrai informações de parte de uma linha de tabela"""
        try:
            colunas = linha.find_all(['td', 'th'])
            if not colunas:
                return None
            
            # Primeira coluna geralmente é o nome
            nome = colunas[0].get_text(strip=True)
            if not nome or nome.upper() in ['NOME', 'PARTE', 'SUJEITO']:
                return None
            
            # Tentar extrair outras informações das colunas seguintes
            documento = ""
            endereco = ""
            telefone = ""
            advogado = ""
            
            for i, coluna in enumerate(colunas[1:], 1):
                texto_coluna = coluna.get_text(strip=True)
                
                if re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto_coluna):
                    documento = texto_coluna
                elif re.search(r'Rua|Av|Avenida|Quadra|Lote', texto_coluna, re.I):
                    endereco = texto_coluna
                elif re.search(r'\(\d{2}\)|^\d{2,}', texto_coluna):
                    telefone = texto_coluna
                elif re.search(r'OAB|Advogado', texto_coluna, re.I):
                    advogado = texto_coluna
            
            return ParteEnvolvida(
                nome=self._limpar_nome_parte(nome),
                tipo=tipo_parte.replace('_', ' ').title(),
                documento=documento,
                endereco=endereco,
                telefone=telefone,
                advogado=advogado
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair parte da linha: {e}")
            return None
    
    def _extrair_parte_do_elemento(self, elemento, tipo_parte: str) -> Optional[ParteEnvolvida]:
        """Extrai informações de parte de um elemento genérico"""
        try:
            texto = elemento.get_text(strip=True)
            if not texto:
                return None
            
            # Dividir texto em linhas para análise
            linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]
            
            nome = ""
            documento = ""
            endereco = ""
            telefone = ""
            advogado = ""
            
            for linha in linhas:
                if self._parece_nome_pessoa(linha) and not nome:
                    nome = linha
                elif re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', linha):
                    documento = linha
                elif re.search(r'Rua|Av|Avenida|Quadra|Lote', linha, re.I):
                    endereco = linha
                elif re.search(r'\(\d{2}\)|^\d{2,}', linha):
                    telefone = linha
                elif re.search(r'OAB|Advogado', linha, re.I):
                    advogado = linha
            
            if nome:
                return ParteEnvolvida(
                    nome=self._limpar_nome_parte(nome),
                    tipo=tipo_parte.replace('_', ' ').title(),
                    documento=documento,
                    endereco=endereco,
                    telefone=telefone,
                    advogado=advogado
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair parte do elemento: {e}")
            return None
    
    def _extrair_partes_do_texto_secao(self, texto_secao: str, tipo_parte: str) -> List[ParteEnvolvida]:
        """Extrai partes de uma seção de texto"""
        partes = []
        
        # Dividir por linhas ou separadores comuns
        linhas = re.split(r'\n|;|\|', texto_secao)
        
        for linha in linhas:
            linha = linha.strip()
            if self._parece_nome_pessoa(linha):
                parte = ParteEnvolvida(
                    nome=self._limpar_nome_parte(linha),
                    tipo=tipo_parte.replace('_', ' ').title(),
                    documento=self._extrair_documento_texto(linha),
                    endereco=self._extrair_endereco_texto(linha)
                )
                partes.append(parte)
        
        return partes
    
    def _extrair_documento_texto(self, texto: str) -> str:
        """Extrai documento (CPF/CNPJ) do texto"""
        match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto)
        return match.group(0) if match else ""
    
    def _extrair_endereco_texto(self, texto: str) -> str:
        """Extrai endereço do texto"""
        padroes_endereco = [
            r'(Rua|Av|Avenida|Quadra|Lote)[^,\n]+',
            r'(Endereço[:\s]+[^,\n]+)',
        ]
        
        for padrao in padroes_endereco:
            match = re.search(padrao, texto, re.I)
            if match:
                return match.group(0).strip()
        
        return ""
    
    def _extrair_partes_do_fieldset(self, fieldset, tipo_polo: str) -> List[ParteEnvolvida]:
        """Extrai partes de um fieldset específico - estratégia melhorada"""
        partes = []
        nomes_unicos = set()  # Para evitar duplicatas
        
        try:
            # ESTRATÉGIA CORRETA: Buscar APENAS por <span class="span1"> que contém os nomes reais
            spans_nomes = fieldset.find_all('span', {'class': 'span1'})
            
            logger.info(f"🔍 Fieldset {tipo_polo}: {len(spans_nomes)} spans com nomes encontrados")
            
            for span in spans_nomes:
                try:
                    nome_raw = span.get_text().strip()
                    
                    # Limpar nome
                    nome_limpo = self._limpar_nome_parte(nome_raw)
                    
                    # Verificar se é válido e único
                    if nome_limpo and nome_limpo not in nomes_unicos and len(nome_limpo) > 3:
                        # Validação adicional - deve ser um nome real
                        if self._parece_nome_valido(nome_limpo):
                            nomes_unicos.add(nome_limpo)
                            
                            # Extrair informações adicionais do contexto do fieldset
                            contexto = str(fieldset)
                            documento = self._extrair_documento(contexto)
                            endereco = self._extrair_endereco(contexto)
                            
                            parte = ParteEnvolvida(
                                nome=nome_limpo,
                                tipo=tipo_polo,
                                documento=documento,
                                endereco=endereco
                            )
                            
                            partes.append(parte)
                            logger.debug(f"  ✅ Parte adicionada: {nome_limpo}")
                        else:
                            logger.debug(f"  ❌ Nome rejeitado pelo filtro: {nome_limpo}")
                    else:
                        if nome_limpo in nomes_unicos:
                            logger.debug(f"  ❌ Nome duplicado: {nome_limpo}")
                        else:
                            logger.debug(f"  ❌ Nome inválido: {nome_limpo}")
                            
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar span: {e}")
                    continue
            
            # FALLBACK: Se não encontrou spans, usar estratégia anterior (mais restritiva)
            if not partes:
                logger.info(f"🔄 Fallback: Usando extração por texto para {tipo_polo}")
                
                # Obter texto completo do fieldset, mas excluir divs de endereço
                fieldset_copy = fieldset.__copy__()
                
                # Remover divs de endereço
                for div_endereco in fieldset_copy.find_all('div', {'class': 'DivInvisivel'}):
                    div_endereco.decompose()
                
                # Remover fieldsets de endereço
                for fieldset_endereco in fieldset_copy.find_all('fieldset', {'class': 'fieldsetEndereco'}):
                    fieldset_endereco.decompose()
                
                texto_fieldset = fieldset_copy.get_text()
                linhas = [linha.strip() for linha in texto_fieldset.split('\n') if linha.strip()]
                
                # Filtrar linhas que parecem nomes
                for linha in linhas:
                    # Pular labels e títulos
                    if any(palavra in linha.lower() for palavra in ['nome', 'polo', 'requerente', 'requerido', 'endereço', 'telefone', 'cpf', 'cnpj']):
                        continue
                    
                    # Pular linhas muito curtas ou muito longas
                    if len(linha) < 5 or len(linha) > 100:
                        continue
                    
                    # Verificar se parece um nome válido
                    if self._parece_nome_valido(linha):
                        nome_limpo = self._limpar_nome_parte(linha)
                        
                        if nome_limpo and nome_limpo not in nomes_unicos:
                            nomes_unicos.add(nome_limpo)
                            
                            contexto = str(fieldset)
                            documento = self._extrair_documento(contexto)
                            endereco = self._extrair_endereco(contexto)
                            
                            parte = ParteEnvolvida(
                                nome=nome_limpo,
                                tipo=tipo_polo,
                                documento=documento,
                                endereco=endereco
                            )
                            
                            partes.append(parte)
            
            logger.info(f"📋 Fieldset {tipo_polo}: {len(partes)} partes únicas extraídas")
            return partes
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair partes do fieldset: {e}")
            return []
    
    def _extrair_partes_do_texto(self, texto: str) -> List[ParteEnvolvida]:
        """Extrai partes do texto da página usando regex"""
        partes = []
        
        try:
            # Padrões para identificar partes
            padroes = [
                r'(?:Autor|AUTOR)[:\s]+([^\n\r\(]+)',
                r'(?:Réu|RÉU)[:\s]+([^\n\r\(]+)',
                r'(?:Requerente|REQUERENTE)[:\s]+([^\n\r\(]+)',
                r'(?:Requerido|REQUERIDO)[:\s]+([^\n\r\(]+)',
                r'\(Polo\s+Ativo\)\s+([^\(\n\r]+)',
                r'\(Polo\s+Passivo\)\s+([^\(\n\r]+)'
            ]
            
            nomes_encontrados = set()
            
            for padrao in padroes:
                matches = re.finditer(padrao, texto, re.I)
                for match in matches:
                    nome = match.group(1).strip()
                    nome = re.sub(r'\s*\(.*?\)\s*', '', nome).strip()
                    nome = re.sub(r'\s*\-.*$', '', nome).strip()
                    
                    if nome and len(nome) > 3 and nome not in nomes_encontrados:
                        nomes_encontrados.add(nome)
                        nome_limpo = self._limpar_nome_parte(nome)
                        
                        # Determinar tipo baseado no padrão
                        if 'ativo' in match.group(0).lower() or 'autor' in match.group(0).lower():
                            tipo = 'Polo Ativo'
                        elif 'passivo' in match.group(0).lower() or 'réu' in match.group(0).lower():
                            tipo = 'Polo Passivo'
                        else:
                            tipo = 'Parte'
                        
                        parte = ParteEnvolvida(
                            nome=nome_limpo,
                            tipo=tipo
                        )
                        partes.append(parte)
            
            return partes
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair partes do texto: {e}")
            return []
    
    def _limpar_nome_parte(self, nome_completo: str) -> str:
        """Limpa o nome da parte removendo informações extras"""
        try:
            # Remover tags HTML
            nome_limpo = re.sub(r'<[^>]+>', '', nome_completo)
            
            # Remover palavras-chave
            palavras_remover = ['citado', 'réu', 'autor', 'requerente', 'requerido']
            for palavra in palavras_remover:
                nome_limpo = re.sub(rf'\b{palavra}\b', '', nome_limpo, flags=re.I)
                nome_limpo = re.sub(rf'{palavra}', '', nome_limpo, flags=re.I)
            
            # Limpar espaços e caracteres especiais
            nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()
            nome_limpo = re.sub(r'[^\w\s\.\-]', '', nome_limpo)
            nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()
            
            return nome_limpo
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar nome: {e}")
            return nome_completo
    
    def _extrair_documento(self, texto: str) -> str:
        """Extrai CPF/CNPJ do texto"""
        try:
            # Padrão para CPF/CNPJ
            match = re.search(r'(?:CPF|CNPJ)[\s:]*(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', texto, re.I)
            return match.group(1) if match else ""
        except:
            return ""
    
    def _extrair_endereco(self, texto: str) -> str:
        """Extrai endereço do texto, removendo HTML"""
        try:
            # Primeiro, limpar HTML tags e onclick
            texto_limpo = re.sub(r'<[^>]*onclick[^>]*>', '', texto)
            texto_limpo = re.sub(r'<[^>]*>', '', texto_limpo)
            texto_limpo = re.sub(r'\\"[^"]*\\"', '', texto_limpo)
            texto_limpo = re.sub(r"\\['\"]", '', texto_limpo)
            
            # Padrão para endereço
            match = re.search(r'(?:Endereço|endereço)[\s:]*([^\n\r]+)', texto_limpo, re.I)
            endereco = match.group(1).strip() if match else ""
            
            # Limpar ainda mais o endereço
            endereco = re.sub(r'type=["\'][^"\']*["\']', '', endereco)
            endereco = re.sub(r'onclick=["\'][^"\']*["\']', '', endereco)
            endereco = re.sub(r'title=["\'][^"\']*["\']', '', endereco)
            endereco = endereco.strip()
            
            return endereco if len(endereco) > 5 else ""
        except:
            return ""

# Instância global do gerenciador de processo
processo_manager = ProcessoManager()