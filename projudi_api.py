#!/usr/bin/env python3
"""
API PROJUDI V3 - Versão Ultra-Robusta
Classe principal com todas as funcionalidades de busca e extração
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
from bs4 import BeautifulSoup
import re
import requests
import json
import PyPDF2
import io

from session_pool import SessionPool

logger = logging.getLogger(__name__)

# Configurações da API
USUARIO = os.getenv('PROJUDI_USER', '34930230144')
SENHA = os.getenv('PROJUDI_PASS', 'Joaquim1*')
SERVENTIA_PADRAO = os.getenv('DEFAULT_SERVENTIA', 'Advogados - OAB/Matrícula: 25348-N-GO')

class ProjudiAPI:
    def __init__(self):
        self.session_pool = SessionPool(max_sessions=6)  # Aumentado para 6 sessões
        self.lock = threading.Lock()
        self.BUSCA_URL = "https://projudi.tjgo.jus.br/BuscaProcesso"
    
    def _handle_session_error(self, session, error_msg):
        """Trata erros de sessão recriando a sessão"""
        logger.warning(f"🔄 Sessão {session['id']} com problema, recriando...")
        self.session_pool.release_session(session)
        
        with self.session_pool.lock:
            if session in self.session_pool.sessions:
                self.session_pool.sessions.remove(session)
            if session['driver']:
                session['driver'].quit()
            if session['temp_dir']:
                try:
                    shutil.rmtree(session['temp_dir'])
                except:
                    pass
        
        # Criar nova sessão
        new_session = self.session_pool._create_session()
        if new_session:
            logger.info(f"✅ Nova sessão {new_session['id']} criada para substituir {session['id']}")
            return new_session
        else:
            logger.error(f"❌ Falha ao criar nova sessão para substituir {session['id']}")
            return None
    
    def _refresh_session_auto(self, session, max_retries=5):
        """Refresh automático da sessão quando bugar - VERSÃO ROBUSTA"""
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Tentativa {attempt + 1}/{max_retries} de refresh da sessão {session['id']}")
                
                # Estratégia 1: Tentar refresh simples primeiro
                if attempt == 0:
                    try:
                        session['driver'].refresh()
                        time.sleep(3)
                        if "Usuario" not in session['driver'].page_source:
                            logger.info(f"✅ Refresh simples funcionou para sessão {session['id']}")
                            return True
                    except:
                        pass
                
                # Estratégia 2: Fechar e recriar driver
                if session['driver']:
                    try:
                        session['driver'].quit()
                    except:
                        pass
                
                # Aguardar um pouco antes de recriar
                time.sleep(2)
                
                # Criar novo driver com configurações otimizadas
                new_driver, temp_dir = self.session_pool._create_robust_driver()
                if not new_driver:
                    logger.error(f"❌ Falha ao criar novo driver para sessão {session['id']}")
                    time.sleep(3)
                    continue
                
                # Atualizar sessão
                session['driver'] = new_driver
                session['wait'] = WebDriverWait(new_driver, 30)
                session['created_at'] = datetime.now()
                session['temp_dir'] = temp_dir
                
                # Estratégia 3: Tentar login com diferentes abordagens
                login_success = False
                
                # Tentativa 1: Login normal
                if self.fazer_login(session):
                    login_success = True
                else:
                    # Tentativa 2: Limpar cookies e tentar novamente
                    try:
                        session['driver'].delete_all_cookies()
                        time.sleep(2)
                        if self.fazer_login(session):
                            login_success = True
                    except:
                        pass
                
                if login_success:
                    logger.info(f"✅ Refresh da sessão {session['id']} realizado com sucesso")
                    return True
                else:
                    logger.warning(f"⚠️ Login falhou após refresh da sessão {session['id']}")
                    
            except Exception as e:
                logger.error(f"❌ Erro no refresh da sessão {session['id']} (tentativa {attempt + 1}): {e}")
                time.sleep(3)
        
        logger.error(f"❌ Falha em todas as tentativas de refresh da sessão {session['id']}")
        return False
    
    def _fallback_strategy(self, session, operation_name, max_attempts=3):
        """Sistema de fallback automático com múltiplas estratégias"""
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 Fallback {operation_name} - Tentativa {attempt + 1}/{max_attempts} na sessão {session['id']}")
                
                # Estratégia 1: Refresh simples
                if attempt == 0:
                    try:
                        session['driver'].refresh()
                        time.sleep(5)
                        return True
                    except:
                        pass
                
                # Estratégia 2: Limpar cookies e tentar novamente
                elif attempt == 1:
                    try:
                        session['driver'].delete_all_cookies()
                        time.sleep(3)
                        session['driver'].refresh()
                        time.sleep(5)
                        return True
                    except:
                        pass
                
                # Estratégia 3: Refresh completo da sessão
                elif attempt == 2:
                    if self._refresh_session_auto(session, max_retries=3):
                        return True
                
            except Exception as e:
                logger.error(f"❌ Fallback {operation_name} falhou na tentativa {attempt + 1}: {e}")
                time.sleep(2)
        
        return False
    
    def _robust_operation(self, session, operation_func, operation_name, *args, **kwargs):
        """Executa uma operação com fallback automático"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                result = operation_func(session, *args, **kwargs)
                if result:
                    return result
                else:
                    logger.warning(f"⚠️ {operation_name} falhou na tentativa {attempt + 1}")
                    if attempt < max_retries - 1:
                        if not self._fallback_strategy(session, operation_name):
                            logger.error(f"❌ Fallback para {operation_name} falhou")
                            continue
            except Exception as e:
                logger.error(f"❌ Erro em {operation_name} (tentativa {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    if not self._fallback_strategy(session, operation_name):
                        logger.error(f"❌ Fallback para {operation_name} falhou")
                        continue
                    time.sleep(2)
        
        return False
    
    def _check_session_health(self, session):
        """Verifica a saúde da sessão e faz manutenção se necessário"""
        try:
            # Verificar se o driver ainda está responsivo
            session['driver'].current_url
            return True
        except:
            logger.warning(f"⚠️ Sessão {session['id']} não está saudável, marcando para refresh")
            return False
    
    def _maintain_session_pool(self):
        """Manutenção automática do pool de sessões"""
        try:
            current_time = time.time()
            sessions_to_remove = []
            
            for session in self.session_pool.sessions:
                # Verificar se a sessão está saudável
                if not self._check_session_health(session):
                    sessions_to_remove.append(session)
                    continue
                
                # Verificar se a sessão está muito antiga (mais de 20 minutos)
                if current_time - session['last_used'] > 1200:  # 20 minutos
                    logger.info(f"🔄 Sessão {session['id']} muito antiga, removendo")
                    sessions_to_remove.append(session)
                    continue
                
                # Verificar se a sessão está muito tempo sem uso (mais de 10 minutos)
                if current_time - session['last_used'] > 600:  # 10 minutos
                    logger.info(f"🔄 Sessão {session['id']} sem uso, fazendo refresh preventivo")
                    if not self._refresh_session_auto(session, max_retries=2):
                        sessions_to_remove.append(session)
            
            # Remover sessões problemáticas
            for session in sessions_to_remove:
                self.session_pool.release_session(session)
                with self.session_pool.lock:
                    if session in self.session_pool.sessions:
                        self.session_pool.sessions.remove(session)
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
            
            if sessions_to_remove:
                logger.info(f"🧹 Removidas {len(sessions_to_remove)} sessões problemáticas")
                
        except Exception as e:
            logger.error(f"❌ Erro na manutenção do pool: {e}")
    
    def _get_session_with_health_check(self):
        """Obtém uma sessão com verificação de saúde"""
        # Fazer manutenção do pool primeiro
        self._maintain_session_pool()
        
        # Tentar obter sessão do pool
        session = self.session_pool.get_session()
        if not session:
            return None
        
        # Verificar saúde da sessão
        if not self._check_session_health(session):
            logger.warning(f"⚠️ Sessão {session['id']} não está saudável, tentando refresh")
            if self._refresh_session_auto(session):
                return session
            else:
                self.session_pool.release_session(session)
                return None
        
        return session
    
    def fazer_login(self, session, usuario=None, senha=None, serventia=None):
        """Fazer login no sistema PROJUDI"""
        try:
            logger.info(f"🔐 Iniciando login na sessão {session['id']}...")
            
            # Usar credenciais padrão se não fornecidas
            usuario = usuario or USUARIO
            senha = senha or SENHA
            serventia = serventia or SERVENTIA_PADRAO
            
            # Navegar para página de login
            session['driver'].get("https://projudi.tjgo.jus.br/LogOn?PaginaAtual=-200")
            time.sleep(5)
            
            # Verificar se já está logado
            if "Usuario" not in session['driver'].page_source:
                logger.info(f"✅ Já logado na sessão {session['id']}")
                return True
            
            logger.info(f"📝 Preenchendo credenciais na sessão {session['id']}...")
            
            # Aguardar e preencher usuário (usando os mesmos seletores da v2)
            try:
                usuario_field = session['wait'].until(
                    EC.presence_of_element_located((By.NAME, "Usuario"))
                )
                usuario_field.clear()
                usuario_field.send_keys(usuario)
                logger.info(f"✅ Usuário preenchido na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao preencher usuário na sessão {session['id']}: {e}")
                return False
            
            # Aguardar e preencher senha (usando os mesmos seletores da v2)
            try:
                senha_field = session['wait'].until(
                    EC.presence_of_element_located((By.NAME, "Senha"))
                )
                senha_field.clear()
                senha_field.send_keys(senha)
                logger.info(f"✅ Senha preenchida na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao preencher senha na sessão {session['id']}: {e}")
                return False
            
            # Clicar em entrar (usando os mesmos seletores da v2)
            try:
                logger.info(f"🔘 Clicando em entrar na sessão {session['id']}...")
                btn_entrar = session['wait'].until(
                    EC.element_to_be_clickable((By.NAME, "entrar"))
                )
                btn_entrar.click()
                time.sleep(8)
                logger.info(f"✅ Botão entrar clicado na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao clicar em entrar na sessão {session['id']}: {e}")
                return False
            
            # Verificar se login foi bem-sucedido
            current_url = session['driver'].current_url
            logger.info(f"📍 URL atual após login na sessão {session['id']}: {current_url}")
            
            # Selecionar serventia por nome (usando os mesmos seletores da v2)
            logger.info(f"⚖️ Selecionando serventia na sessão {session['id']}: {serventia}")
            try:
                # Aguardar e buscar serventia
                serventia_element = session['wait'].until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(), '{serventia}')]"))
                )
                serventia_element.click()
                time.sleep(5)
                logger.info(f"✅ Serventia selecionada com sucesso na sessão {session['id']}!")
            except Exception as e:
                logger.warning(f"⚠️ Serventia '{serventia}' não encontrada na sessão {session['id']}, tentando padrão...")
                try:
                    serventia_padrao = session['wait'].until(
                        EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(), '{SERVENTIA_PADRAO}')]"))
                    )
                    serventia_padrao.click()
                    time.sleep(5)
                    logger.info(f"✅ Serventia padrão selecionada na sessão {session['id']}!")
                except Exception as e2:
                    logger.error(f"❌ Erro ao selecionar serventia na sessão {session['id']}: {e2}")
                    # Salvar screenshot para debug
                    try:
                        session['driver'].save_screenshot(f"debug_login_error_{session['id']}.png")
                        logger.info(f"📸 Screenshot salvo: debug_login_error_{session['id']}.png")
                    except:
                        pass
                    return False
            
            logger.info(f"✅ Login realizado com sucesso na sessão {session['id']}!")
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro geral no login da sessão {session['id']}: {e}")
            # Salvar screenshot para debug
            try:
                session['driver'].save_screenshot(f"debug_login_error_{session['id']}.png")
                logger.info(f"📸 Screenshot salvo: debug_login_error_{session['id']}.png")
            except:
                pass
            return False
    
    def buscar_por_cpf(self, session, cpf):
        """Buscar processos por CPF"""
        try:
            logger.info(f"🔍 Buscando por CPF na sessão {session['id']}: {cpf}")
            
            # Navegar para página de busca
            session['driver'].get(self.BUSCA_URL)
            time.sleep(5)
            
            # Aguardar campo CPF (usando os mesmos seletores da v2)
            try:
                cpf_field = session['wait'].until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'CPF') or contains(@placeholder, 'CNPJ')]"))
                )
                cpf_field.clear()
                cpf_field.send_keys(cpf)
                logger.info(f"✅ CPF preenchido na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao preencher CPF na sessão {session['id']}: {e}")
                return False
            
            # Clicar em buscar (usando os mesmos seletores da v2)
            try:
                btn_buscar = session['driver'].find_element(By.XPATH, "//input[@value='Buscar']")
                btn_buscar.click()
                logger.info(f"✅ Botão buscar clicado na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao clicar em buscar na sessão {session['id']}: {e}")
                return False
            
            # Aguardar resultado
            time.sleep(5)
            
            logger.info(f"✅ Busca por CPF concluída com sucesso na sessão {session['id']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na busca por CPF na sessão {session['id']}: {e}")
            return False
    
    def buscar_por_nome(self, session, nome):
        """Busca processos por nome da parte"""
        try:
            logger.info(f"🔍 Buscando processos do nome na sessão {session['id']}: {nome}")
            
            # Navegar para página de busca
            session['driver'].get(self.BUSCA_URL)
            time.sleep(5)
            
            # Aguardar campo nome da parte (usando os mesmos seletores da v2)
            try:
                nome_field = session['wait'].until(
                    EC.presence_of_element_located((By.NAME, "NomeParte"))
                )
                
                # Preencher nome da parte
                nome_field.clear()
                nome_field.send_keys(nome)
                logger.info(f"✅ Nome preenchido na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao preencher nome na sessão {session['id']}: {e}")
                return False
            
            # Clicar em buscar (usando os mesmos seletores da v2)
            try:
                btn_buscar = session['driver'].find_element(By.XPATH, "//input[@value='Buscar']")
                btn_buscar.click()
                logger.info(f"✅ Botão buscar clicado na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao clicar em buscar na sessão {session['id']}: {e}")
                return False
            
            # Aguardar resultado
            time.sleep(5)
            
            logger.info(f"✅ Busca por nome realizada com sucesso na sessão {session['id']}!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na busca por nome na sessão {session['id']}: {e}")
            return False
    
    def buscar_por_processo(self, session, numero_processo):
        """Busca processo por número"""
        try:
            logger.info(f"🔍 Buscando processo: {numero_processo}")
            
            # Usar o número completo do processo, não apenas os primeiros dígitos
            # O PROJUDI aceita o número completo para busca mais precisa
            numero_processo_original = numero_processo
            
            # Navegar para página de busca
            session['driver'].get(self.BUSCA_URL)
            time.sleep(5)
            
            # Tentar diferentes seletores para o campo número do processo
            processo_field = None
            seletores = [
                (By.NAME, "ProcessoNumero"),
                (By.ID, "ProcessoNumero"),
                (By.XPATH, "//input[@name='ProcessoNumero']"),
                (By.XPATH, "//input[@id='ProcessoNumero']"),
                (By.XPATH, "//input[contains(@name, 'Processo')]"),
                (By.XPATH, "//input[contains(@id, 'Processo')]"),
                (By.XPATH, "//input[@placeholder='Número do Processo']")
            ]
            
            for seletor in seletores:
                try:
                    processo_field = session['wait'].until(
                        EC.presence_of_element_located(seletor)
                    )
                    logger.info(f"✅ Campo encontrado com seletor: {seletor}")
                    break
                except:
                    continue
            
            if not processo_field:
                logger.error("❌ Campo número do processo não encontrado!")
                return False
            
            # Limpar e preencher número do processo completo
            processo_field.clear()
            time.sleep(1)
            processo_field.send_keys(numero_processo_original)
            time.sleep(1)
            
            # Tentar diferentes seletores para o botão buscar
            btn_buscar = None
            seletores_botao = [
                (By.NAME, "imgSubmeter"),
                (By.XPATH, "//input[@name='imgSubmeter']"),
                (By.XPATH, "//input[@value='Buscar']"),
                (By.XPATH, "//input[@type='submit' and @value='Buscar']"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Buscar')]"),
                (By.XPATH, "//input[@value='Pesquisar']"),
                (By.XPATH, "//button[@type='submit']")
            ]
            
            for seletor in seletores_botao:
                try:
                    btn_buscar = session['driver'].find_element(*seletor)
                    logger.info(f"✅ Botão encontrado com seletor: {seletor}")
                    break
                except:
                    continue
            
            if not btn_buscar:
                logger.error("❌ Botão buscar não encontrado!")
                return False
            
            # Clicar em buscar
            btn_buscar.click()
            time.sleep(5)
            
            logger.info("✅ Busca por processo realizada com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na busca por processo: {e}")
            return False
    
    def obter_lista_processos(self, session):
        """Obtém a lista de processos encontrados"""
        try:
            logger.info("📋 Obtendo lista de processos...")
            
            # Aguardar tabela de resultados com diferentes seletores
            tabela_encontrada = False
            seletores_tabela = [
                (By.ID, "Tabela"),
                (By.CLASS_NAME, "Tabela"),
                (By.XPATH, "//table[contains(@class, 'Tabela')]"),
                (By.XPATH, "//table[contains(@id, 'Tabela')]"),
                (By.XPATH, "//table")
            ]
            
            for seletor in seletores_tabela:
                try:
                    session['wait'].until(EC.presence_of_element_located(seletor))
                    logger.info(f"✅ Tabela encontrada com seletor: {seletor}")
                    tabela_encontrada = True
                    break
                except:
                    continue
            
            if not tabela_encontrada:
                logger.warning("❌ Tabela de resultados não encontrada!")
                # Verificar se há mensagem de "nenhum resultado"
                page_source = session['driver'].page_source.lower()
                if "nenhum" in page_source or "não encontrado" in page_source or "não foi encontrado" in page_source:
                    logger.info("ℹ️ Nenhum processo encontrado na busca")
                    return []
                
                # Verificar se foi redirecionado diretamente para um processo
                if "corpo_dados_processo" in page_source:
                    logger.info("ℹ️ Redirecionado diretamente para um processo")
                    # Extrair informações do processo atual
                    soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
                    
                    # Tentar encontrar número do processo
                    numero_processo = ""
                    elementos_numero = soup.find_all('span', string=re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'))
                    if elementos_numero:
                        numero_processo = elementos_numero[0].get_text(strip=True)
                    else:
                        # Tentar encontrar em outros elementos
                        for elemento in soup.find_all(['span', 'div', 'td']):
                            texto = elemento.get_text(strip=True)
                            if re.match(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto):
                                numero_processo = texto
                                break
                    
                    if numero_processo:
                        processo = {
                            'numero': numero_processo,
                            'classe': "Processo encontrado",
                            'assunto': "Processo acessado diretamente",
                            'id': f"processo_direto_{numero_processo}",
                            'indice': 1
                        }
                        return [processo]
                
                return []
            
            # Extrair dados da tabela
            soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
            tabela = soup.find('table', {'id': 'Tabela'})
            
            if not tabela:
                # Tentar encontrar qualquer tabela
                tabelas = soup.find_all('table')
                if tabelas:
                    tabela = tabelas[0]  # Usar a primeira tabela encontrada
                    logger.info("ℹ️ Usando primeira tabela encontrada")
            
            if not tabela:
                logger.warning("❌ Nenhuma tabela encontrada!")
                return []
            
            processos = []
            linhas = tabela.find_all('tr', class_=re.compile(r'TabelaLinha|filtro-entrada'))
            
            # Se não encontrar linhas com classe específica, tentar todas as linhas
            if not linhas:
                linhas = tabela.find_all('tr')
                logger.info(f"ℹ️ Usando todas as {len(linhas)} linhas da tabela")
            
            for i, linha in enumerate(linhas):
                tds = linha.find_all('td')
                if len(tds) >= 3:
                    numero = tds[0].get_text(strip=True)
                    classe = tds[1].get_text(strip=True) if len(tds) > 1 else ""
                    assunto = tds[2].get_text(strip=True) if len(tds) > 2 else ""
                    
                    # Verificar se é uma linha válida (não cabeçalho)
                    if numero and not numero.startswith('Número') and not numero.startswith('Processo'):
                        # Extrair ID do processo do onclick do botão editar
                        btn_editar = linha.find('button', {'name': 'formLocalizarimgEditar'})
                        if not btn_editar:
                            btn_editar = linha.find('input', {'type': 'button', 'name': 'formLocalizarimgEditar'})
                        
                        if btn_editar:
                            onclick = btn_editar.get('onclick', '')
                            match = re.search(r"Id_Processo','([^']+)'", onclick)
                            if match:
                                id_processo = match.group(1)
                            else:
                                id_processo = f"processo_{i}"
                        else:
                            id_processo = f"processo_{i}"
                        
                        processo = {
                            'numero': numero,
                            'classe': classe,
                            'assunto': assunto,
                            'id': id_processo,
                            'indice': len(processos) + 1  # Adicionar índice baseado na posição na lista
                        }
                        processos.append(processo)
            
            logger.info(f"✅ {len(processos)} processos encontrados!")
            return processos
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter lista de processos: {e}")
            return []
    
    def acessar_processo(self, session, processo_info, extrair_anexos=False):
        """Acessa um processo específico"""
        try:
            logger.info(f"📄 Acessando processo {processo_info.get('numero', 'N/A')}: {processo_info.get('numero', 'N/A')}")
            
            # Estratégia 1: Usar JavaScript para clicar no botão correto baseado no índice
            if 'indice' in processo_info:
                indice = processo_info['indice']
                
                # Tentar diferentes seletores para botões de editar
                scripts = [
                    f"""
                    var botoes = document.querySelectorAll('button[name="formLocalizarimgEditar"]');
                    if (botoes.length >= {indice}) {{
                        botoes[{indice - 1}].click();
                        return true;
                    }}
                    return false;
                    """,
                    f"""
                    var botoes = document.querySelectorAll('input[type="button"][name="formLocalizarimgEditar"]');
                    if (botoes.length >= {indice}) {{
                        botoes[{indice - 1}].click();
                        return true;
                    }}
                    return false;
                    """,
                    f"""
                    var botoes = document.querySelectorAll('button[onclick*="Id_Processo"]');
                    if (botoes.length >= {indice}) {{
                        botoes[{indice - 1}].click();
                        return true;
                    }}
                    return false;
                    """,
                    f"""
                    var botoes = document.querySelectorAll('input[type="button"][onclick*="Id_Processo"]');
                    if (botoes.length >= {indice}) {{
                        botoes[{indice - 1}].click();
                        return true;
                    }}
                    return false;
                    """,
                    f"""
                    var botoes = document.querySelectorAll('button');
                    if (botoes.length >= {indice}) {{
                        botoes[{indice - 1}].click();
                        return true;
                    }}
                    return false;
                    """
                ]
                
                for i, script in enumerate(scripts):
                    try:
                        resultado = session['driver'].execute_script(script)
                        if resultado:
                            time.sleep(5)
                            logger.info(f"✅ Processo acessado com sucesso via JavaScript (script {i+1})!")
                            return True
                    except Exception as e:
                        logger.warning(f"⚠️ Script {i+1} falhou: {e}")
                        continue
                
                logger.error(f"❌ Falha ao acessar processo {indice} via JavaScript")
            
            # Estratégia 2: Fallback com diferentes seletores para o botão editar
            btn_editar = None
            seletores = [
                (By.XPATH, f"//button[@name='formLocalizarimgEditar' and contains(@onclick, '{processo_info.get('id', '')}')]"),
                (By.XPATH, f"//input[@type='button' and @name='formLocalizarimgEditar' and contains(@onclick, '{processo_info.get('id', '')}')]"),
                (By.XPATH, f"//button[contains(@onclick, '{processo_info.get('id', '')}')]"),
                (By.XPATH, f"//input[@type='button' and contains(@onclick, '{processo_info.get('id', '')}')]"),
                (By.XPATH, f"//button[contains(@onclick, 'Id_Processo')]"),
                (By.XPATH, f"//input[@type='button' and contains(@onclick, 'Id_Processo')]"),
                (By.XPATH, "//button[@name='formLocalizarimgEditar']"),
                (By.XPATH, "//input[@type='button' and @name='formLocalizarimgEditar']"),
                (By.XPATH, "//button[contains(text(), 'Editar')]"),
                (By.XPATH, "//input[@type='button' and contains(@value, 'Editar')]"),
                (By.XPATH, "//button"),
                (By.XPATH, "//input[@type='button']")
            ]
            
            for seletor in seletores:
                try:
                    elementos = session['driver'].find_elements(*seletor)
                    if elementos:
                        # Se há múltiplos elementos, usar o primeiro ou baseado no índice
                        if 'indice' in processo_info and len(elementos) >= processo_info['indice']:
                            btn_editar = elementos[processo_info['indice'] - 1]
                        else:
                            btn_editar = elementos[0]
                        logger.info(f"✅ Botão editar encontrado com seletor: {seletor}")
                        break
                except:
                    continue
            
            if not btn_editar:
                logger.error("❌ Botão editar não encontrado!")
                return False
            
            # Clicar no botão editar
            try:
                btn_editar.click()
                time.sleep(5)
                logger.info("✅ Processo acessado com sucesso!")
                
                # Se extrair_anexos for True, solicitar acesso logo ao entrar no processo
                if extrair_anexos:
                    logger.info("📎 Extrair anexos ativado - solicitando acesso ao processo")
                    resultado_solicitar = self._solicitar_acesso_processo(session)
                    logger.info(f"📎 Resultado da solicitação de acesso: {resultado_solicitar}")
                
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao clicar no botão: {e}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Falha ao acessar processo: {e}")
            return False
    
    def extrair_movimentacoes(self, session, processo_info, limite_movimentacoes=None, extrair_anexos=False):
        """Extrai as movimentações de um processo"""
        try:
            logger.info("📋 Extraindo movimentações...")
            
            # Aguardar tabela de movimentações com diferentes seletores
            tabela_encontrada = False
            seletores_tabela = [
                (By.ID, "TabelaArquivos"),  # Tabela principal de movimentações
                (By.ID, "Tabela"),  # Fallback para tabela genérica
                (By.CLASS_NAME, "Tabela"),
                (By.XPATH, "//table[contains(@class, 'Tabela')]"),
                (By.XPATH, "//table[contains(@id, 'Tabela')]"),
                (By.XPATH, "//table")
            ]
            
            for seletor in seletores_tabela:
                try:
                    session['wait'].until(EC.presence_of_element_located(seletor))
                    logger.info(f"✅ Tabela de movimentações encontrada com seletor: {seletor}")
                    tabela_encontrada = True
                    break
                except:
                    continue
            
            if not tabela_encontrada:
                logger.warning("⚠️ Tabela de movimentações não encontrada")
                return []
            
            # Extrair dados da tabela
            soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
            
            # Tentar encontrar a tabela de movimentações
            tabela = soup.find('table', {'id': 'TabelaArquivos'})
            if not tabela:
                tabela = soup.find('table', {'id': 'Tabela'})
            if not tabela:
                # Tentar encontrar qualquer tabela que contenha movimentações
                tabelas = soup.find_all('table')
                for t in tabelas:
                    if t.find('td', string=re.compile(r'movimentação|movimentacao', re.I)):
                        tabela = t
                        break
                if not tabela and tabelas:
                    tabela = tabelas[0]  # Usar a primeira tabela como fallback
            
            if not tabela:
                logger.warning("❌ Tabela de movimentações não encontrada!")
                return []
            
            movimentacoes = []
            linhas = tabela.find_all('tr', class_=re.compile(r'TabelaLinha|filtro-entrada'))
            
            # Se não encontrar linhas com classe específica, tentar todas as linhas
            if not linhas:
                linhas = tabela.find_all('tr')
                logger.info(f"ℹ️ Usando todas as {len(linhas)} linhas da tabela")
            
            # Limitar número de movimentações se especificado
            if limite_movimentacoes:
                if isinstance(limite_movimentacoes, str) and limite_movimentacoes == 'ultimas3':
                    linhas = linhas[:3]
                elif isinstance(limite_movimentacoes, int):
                    linhas = linhas[:limite_movimentacoes]
            
            for linha in linhas:
                tds = linha.find_all('td')
                if len(tds) >= 2:  # Reduzir para 2 colunas mínimas
                    # Tentar diferentes padrões de colunas
                    if len(tds) >= 4:
                        # Padrão: Data | Movimentação | Usuário | ...
                        data = tds[0].get_text(strip=True)
                        tipo = tds[1].get_text(strip=True)
                        usuario = tds[2].get_text(strip=True) if len(tds) > 2 else ""
                        info_adicional = tds[3].get_text(strip=True) if len(tds) > 3 else ""
                    elif len(tds) >= 2:
                        # Padrão: Movimentação | Data
                        tipo = tds[0].get_text(strip=True)
                        data = tds[1].get_text(strip=True)
                        usuario = ""
                        info_adicional = ""
                    else:
                        continue
                    
                    # Verificar se tem anexo
                    tem_anexo = bool(linha.find('img', {'src': 'imagens/22x22/go-bottom.png'}))
                    
                    # Extrair código da movimentação
                    codigo_movimentacao = ""
                    btn_anexo = linha.find('img', {'src': 'imagens/22x22/go-bottom.png'})
                    if btn_anexo:
                        onclick = btn_anexo.get('onclick', '')
                        # Tentar diferentes padrões
                        match = re.search(r"buscarArquivosMovimentacaoJSON\('([^']+)'", onclick)
                        if match:
                            codigo_movimentacao = match.group(1)
                        else:
                            match = re.search(r"Id_MovimentacaoArquivo',\s*'([^']+)'", onclick)
                            if match:
                                codigo_movimentacao = match.group(1)
                    
                    # Se não encontrou pelo onclick, tentar pelo id_movi no HTML
                    if not codigo_movimentacao:
                        id_movi_match = re.search(r'id_movi="([^"]+)"', str(linha))
                        if id_movi_match:
                            codigo_movimentacao = id_movi_match.group(1)
                    
                    # Verificar se é uma linha válida de movimentação
                    if tipo and data and not tipo.startswith('Data') and not tipo.startswith('Movimentação'):
                        movimentacao = {
                            'numero': len(movimentacoes) + 1,
                            'tipo': tipo,
                            'data': data,
                            'usuario': usuario,
                            'tem_anexo': tem_anexo,
                            'codigo_movimentacao': codigo_movimentacao,
                            'anexos': [],
                            'html_completo': str(linha),
                            'info_adicional': info_adicional,
                            'onclick': ""
                        }
                        
                        # Extrair anexos se solicitado
                        if extrair_anexos and tem_anexo:
                            try:
                                anexos = self._extrair_anexos_movimentacao(session, codigo_movimentacao)
                                movimentacao['anexos'] = anexos
                            except Exception as e:
                                logger.warning(f"⚠️ Erro ao extrair anexos: {e}")
                        
                        movimentacoes.append(movimentacao)
            
            logger.info(f"✅ {len(movimentacoes)} movimentações extraídas")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair movimentações: {e}")
            return []

    def extrair_partes_envolvidas(self, session, processo_info):
        """Extrai as partes envolvidas de um processo"""
        try:
            logger.info("👥 Extraindo partes envolvidas...")
            
            # Aguardar carregamento da página principal
            time.sleep(2)
            
            # Procurar pelo link das partes envolvidas de forma mais abrangente
            partes_links = []
            
            # 1. Buscar por textos relacionados a partes (baseado na interface real do PROJUDI)
            textos_partes = [
                "Visualizar Partes no Processo",
                "Visualizar todas as partes", 
                "Visualizar partes",
                "Ver partes",
                "Partes no Processo",
                "partes envolvidas", 
                "dados das partes",
                "informações das partes",
                "e outras",
                "outras",
                "partes",
                "participantes"
            ]
            
            logger.info("🔍 Procurando links por texto...")
            for texto in textos_partes:
                try:
                    # Buscar por texto exato e parcial
                    links_exato = session['driver'].find_elements(By.LINK_TEXT, texto)
                    links_parcial = session['driver'].find_elements(By.PARTIAL_LINK_TEXT, texto)
                    
                    if links_exato:
                        partes_links.extend(links_exato)
                        logger.info(f"✅ Encontrado link exato: '{texto}'")
                        break
                    elif links_parcial:
                        partes_links.extend(links_parcial)
                        logger.info(f"✅ Encontrado link parcial: '{texto}'")
                        break
                except:
                    continue
            
            # 2. Buscar por padrões mais específicos do PROJUDI
            if not partes_links:
                logger.info("🔍 Procurando por padrões PROJUDI...")
                try:
                    # Buscar links com href contendo palavras-chave específicas do PROJUDI
                    xpath_queries = [
                        "//a[contains(text(), 'Visualizar Partes') or contains(text(), 'Visualizar partes')]",
                        "//a[contains(text(), 'Visualizar todas as partes')]", 
                        "//a[contains(text(), 'Ver partes') or contains(text(), 'Ver Partes')]",
                        "//a[contains(text(), 'Partes no Processo')]",
                        "//a[contains(@href, 'parte') or contains(@href, 'Parte')]",
                        "//a[contains(@href, 'participante') or contains(@href, 'Participante')]",
                        "//a[contains(@href, 'dados') and contains(@href, 'parte')]",
                        "//a[contains(text(), 'outras') or contains(text(), 'Outras')]",
                        "//a[contains(text(), 'parte') or contains(text(), 'Parte')]",
                        "//a[contains(@onclick, 'parte') or contains(@onclick, 'Parte')]",
                        "//a[contains(@onclick, 'participante')]"
                    ]
                    
                    for xpath in xpath_queries:
                        try:
                            elementos = session['driver'].find_elements(By.XPATH, xpath)
                            if elementos:
                                partes_links.extend(elementos)
                                logger.info(f"✅ Encontrado via xpath: {xpath}")
                                break
                        except:
                            continue
                except:
                    pass
            
            # 3. Buscar em abas ou menus suspensos 
            if not partes_links:
                logger.info("🔍 Procurando em abas e menus...")
                try:
                    # Buscar por elementos tipo tab, button ou menu
                    elementos_interativos = [
                        "//button[contains(text(), 'parte') or contains(text(), 'outras')]",
                        "//div[@class='tab' or @class='menu']//a[contains(text(), 'parte') or contains(text(), 'outras')]",
                        "//li//a[contains(text(), 'parte') or contains(text(), 'outras')]",
                        "//span[contains(text(), 'parte') or contains(text(), 'outras')]//ancestor::a",
                        "//td//a[contains(text(), 'outras') or contains(text(), 'parte')]"
                    ]
                    
                    for xpath in elementos_interativos:
                        try:
                            elementos = session['driver'].find_elements(By.XPATH, xpath)
                            if elementos:
                                partes_links.extend(elementos)
                                logger.info(f"✅ Encontrado em interface: {xpath}")
                                break
                        except:
                            continue
                except:
                    pass
            
            # 4. Como último recurso, buscar qualquer link que possa ser relevante
            if not partes_links:
                logger.info("🔍 Busca ampla por links relevantes...")
                try:
                    soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
                    
                    # Buscar todos os links e analisar seu conteúdo
                    todos_links = soup.find_all('a', href=True)
                    for link in todos_links:
                        texto_link = link.get_text(strip=True).lower()
                        href_link = link.get('href', '').lower()
                        
                        # Verificar se o link pode ser das partes
                        palavras_chave = ['parte', 'outras', 'participante', 'dados', 'informações']
                        
                        if any(palavra in texto_link or palavra in href_link for palavra in palavras_chave):
                            try:
                                # Tentar encontrar o elemento na página
                                href_original = link.get('href')
                                if href_original:
                                    elemento = session['driver'].find_element(By.XPATH, f"//a[@href='{href_original}']")
                                    partes_links.append(elemento)
                                    logger.info(f"✅ Encontrado link candidato: '{texto_link}' - {href_original}")
                                    break
                            except:
                                continue
                except Exception as e:
                    logger.warning(f"⚠️ Erro na busca ampla: {e}")
            
            if not partes_links:
                logger.warning("⚠️ Link para partes envolvidas não encontrado")
                return []
            
            # Clicar no primeiro link encontrado
            link_partes = partes_links[0]
            try:
                session['driver'].execute_script("arguments[0].click();", link_partes)
                logger.info("🔗 Clicou no link das partes envolvidas")
                time.sleep(3)
            except:
                try:
                    link_partes.click()
                    logger.info("🔗 Clicou no link das partes envolvidas (método alternativo)")
                    time.sleep(3)
                except Exception as e:
                    logger.error(f"❌ Erro ao clicar no link das partes: {e}")
                    return []
            
            # Aguardar carregamento da página das partes
            time.sleep(2)
            
            # Extrair informações das partes
            soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
            partes = []
            
            # Primeiro, tentar extrair usando a estrutura específica do PROJUDI (POLO ATIVO/PASSIVO)
            logger.info("🔍 Procurando por estrutura POLO ATIVO/PASSIVO...")
            
            polos_encontrados = False
            
            # Buscar por elementos que contenham "POLO ATIVO" ou "POLO PASSIVO"
            elementos_polo = soup.find_all(text=re.compile(r'POLO\s+(ATIVO|PASSIVO)', re.I))
            
            for elemento_texto in elementos_polo:
                try:
                    # Encontrar o elemento pai que contém o polo
                    elemento_pai = elemento_texto.parent
                    while elemento_pai and elemento_pai.name:
                        texto_completo = elemento_pai.get_text()
                        
                        # Verificar se é POLO ATIVO ou PASSIVO
                        if 'POLO ATIVO' in texto_completo.upper():
                            tipo_polo = 'Polo Ativo'
                        elif 'POLO PASSIVO' in texto_completo.upper():
                            tipo_polo = 'Polo Passivo'
                        else:
                            elemento_pai = elemento_pai.parent
                            continue
                        
                        # Extrair nome do polo
                        nome_match = re.search(r'Nome\s+([^\n\r]+)', texto_completo, re.I)
                        nome = nome_match.group(1).strip() if nome_match else ''
                        
                        # Se não encontrou nome com "Nome", tentar extrair o texto após o tipo do polo
                        if not nome:
                            texto_limpo = re.sub(r'POLO\s+(ATIVO|PASSIVO)', '', texto_completo, flags=re.I).strip()
                            linhas = [linha.strip() for linha in texto_limpo.split('\n') if linha.strip()]
                            if linhas:
                                # Pegar a primeira linha não vazia que não seja "Nome"
                                for linha in linhas:
                                    if linha.lower() != 'nome' and len(linha) > 3:
                                        nome = linha
                                        break
                        
                        if nome:
                            parte_info = {
                                'nome': nome,
                                'tipo': tipo_polo,
                                'cpf_cnpj': '',
                                'rg': '',
                                'endereco': '',
                                'telefone': '',
                                'email': '',
                                'advogado': '',
                                'oab': '',
                                'html_completo': str(elemento_pai),
                                'texto_completo': texto_completo
                            }
                            
                            # Tentar extrair mais informações do texto
                            self._extrair_detalhes_parte(parte_info, texto_completo)
                            
                            partes.append(parte_info)
                            polos_encontrados = True
                            logger.info(f"✅ Encontrado {tipo_polo}: {nome}")
                        
                        break
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar polo: {e}")
                    continue
            
            # Se não encontrou polos, usar estratégia anterior (busca geral)
            if not polos_encontrados:
                logger.info("🔍 Estrutura POLO não encontrada, usando busca geral...")
                
                # Procurar por diferentes padrões de estrutura da página de partes
                estruturas_candidatas = [
                    soup.find_all('table'),
                    soup.find_all('div', class_=re.compile(r'parte|participante|polo', re.I)),
                    soup.find_all('div', {'id': re.compile(r'parte|participante|polo', re.I)}),
                    soup.find_all('tr'),
                    soup.find_all('div')
                ]
            
            for estruturas in estruturas_candidatas:
                if not estruturas:
                    continue
                    
                for elemento in estruturas:
                    texto_elemento = elemento.get_text(strip=True).lower()
                    
                    # Verificar se o elemento contém informações de uma parte
                    if any(palavra in texto_elemento for palavra in [
                        'advogado', 'nome:', 'cpf:', 'rg:', 'endereço:', 'telefone:',
                        'autor', 'réu', 'requerente', 'requerido', 'impetrante',
                        'impetrado', 'apelante', 'apelado'
                    ]):
                        # Extrair informações estruturadas
                        parte_info = {
                            'nome': '',
                            'tipo': '',
                            'cpf_cnpj': '',
                            'rg': '',
                            'endereco': '',
                            'telefone': '',
                            'email': '',
                            'advogado': '',
                            'oab': '',
                            'html_completo': str(elemento),
                            'texto_completo': elemento.get_text(strip=True)
                        }
                        
                        # Tentar extrair informações específicas usando regex
                        texto_completo = elemento.get_text()
                        
                        # Usar função auxiliar para extrair detalhes
                        self._extrair_detalhes_parte(parte_info, texto_completo)
                        
                        # Tipo da parte (autor, réu, etc.) - só se não foi definido ainda
                        if not parte_info['tipo']:
                            for tipo in ['autor', 'réu', 'requerente', 'requerido', 'impetrante', 'impetrado', 'apelante', 'apelado']:
                                if tipo in texto_elemento:
                                    parte_info['tipo'] = tipo.title()
                                    break
                        
                        # Só adicionar se encontrou pelo menos nome ou alguma informação relevante
                        if (parte_info['nome'] or parte_info['cpf_cnpj'] or 
                            parte_info['advogado'] or len(parte_info['texto_completo']) > 50):
                            
                            # Evitar duplicatas
                            duplicata = False
                            for parte_existente in partes:
                                if (parte_existente['texto_completo'] == parte_info['texto_completo'] or
                                    (parte_info['nome'] and parte_existente['nome'] == parte_info['nome'])):
                                    duplicata = True
                                    break
                            
                            if not duplicata:
                                partes.append(parte_info)
                
                # Se encontrou partes, parar de procurar
                if partes:
                    break
            
            # Tentar voltar à página principal do processo
            try:
                logger.info("🔙 Tentando voltar à página principal do processo...")
                
                # Tentar diferentes métodos para voltar
                voltar_sucesso = False
                
                # 1. Usar botão "Voltar" do navegador
                try:
                    session['driver'].back()
                    time.sleep(2)
                    voltar_sucesso = True
                    logger.info("✅ Voltou usando botão voltar do navegador")
                except:
                    pass
                
                # 2. Se não conseguiu, tentar encontrar botão "Voltar" na página
                if not voltar_sucesso:
                    try:
                        botoes_voltar = session['driver'].find_elements(By.XPATH, 
                            "//a[contains(text(), 'Voltar') or contains(text(), 'voltar') or contains(@onclick, 'history.back')]")
                        if botoes_voltar:
                            botoes_voltar[0].click()
                            time.sleep(2)
                            voltar_sucesso = True
                            logger.info("✅ Voltou usando botão voltar da página")
                    except:
                        pass
                
                if not voltar_sucesso:
                    logger.warning("⚠️ Não conseguiu voltar automaticamente à página principal")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao tentar voltar: {e}")
            
            logger.info(f"✅ {len(partes)} partes envolvidas extraídas")
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes envolvidas: {e}")
            # Tentar voltar mesmo em caso de erro
            try:
                session['driver'].back()
                time.sleep(1)
            except:
                pass
            return []
    
    def _extrair_detalhes_parte(self, parte_info, texto_completo):
        """Função auxiliar para extrair detalhes específicos de uma parte"""
        try:
            # Nome (geralmente após "Nome:" ou em posição de destaque)
            if not parte_info['nome']:
                nome_match = re.search(r'(?:Nome:|nome:)\s*([^\n\r]+)', texto_completo, re.I)
                if nome_match:
                    parte_info['nome'] = nome_match.group(1).strip()
            
            # CPF/CNPJ
            cpf_match = re.search(r'(?:CPF|CNPJ)[\s:]*(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', texto_completo, re.I)
            if cpf_match:
                parte_info['cpf_cnpj'] = cpf_match.group(1)
            
            # RG
            rg_match = re.search(r'RG[\s:]*([^\n\r,]+)', texto_completo, re.I)
            if rg_match:
                parte_info['rg'] = rg_match.group(1).strip()
            
            # Endereço
            endereco_match = re.search(r'(?:Endereço|endereço)[\s:]*([^\n\r]+)', texto_completo, re.I)
            if endereco_match:
                parte_info['endereco'] = endereco_match.group(1).strip()
            
            # Telefone
            telefone_match = re.search(r'(?:Telefone|telefone|Tel|tel)[\s:]*([^\n\r,]+)', texto_completo, re.I)
            if telefone_match:
                parte_info['telefone'] = telefone_match.group(1).strip()
            
            # Email
            email_match = re.search(r'(?:E-mail|email|Email)[\s:]*([^\n\r\s]+@[^\n\r\s]+)', texto_completo, re.I)
            if email_match:
                parte_info['email'] = email_match.group(1).strip()
            
            # Advogado
            advogado_match = re.search(r'(?:Advogado|advogado)[\s:]*([^\n\r]+)', texto_completo, re.I)
            if advogado_match:
                parte_info['advogado'] = advogado_match.group(1).strip()
            
            # OAB
            oab_match = re.search(r'OAB[\s:]*([^\n\r,]+)', texto_completo, re.I)
            if oab_match:
                parte_info['oab'] = oab_match.group(1).strip()
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair detalhes da parte: {e}")
    
    def _solicitar_acesso_processo(self, session):
        """Solicita acesso aos anexos do processo inteiro"""
        try:
            logger.info("🔓 Solicitando acesso aos anexos do processo")
            
            # Aguardar carregamento da página do processo
            try:
                session['wait'].until(EC.presence_of_element_located((By.ID, "TabelaArquivos")))
                time.sleep(2)
            except:
                logger.warning("⚠️ Tabela de movimentações não encontrada para solicitar acesso")
                return False
            
            # Tentar encontrar o menu "Outras" na página do processo
            try:
                # Procurar por diferentes locais onde pode estar o menu "Outras"
                menu_outras = None
                
                # Tentar encontrar por ID
                try:
                    menu_outras = session['driver'].find_element(By.ID, "menu_outras")
                except:
                    pass
                
                # Tentar encontrar por texto
                if not menu_outras:
                    try:
                        menu_outras = session['driver'].find_element(By.XPATH, "//a[contains(text(), 'Outras')]")
                    except:
                        pass
                
                # Tentar encontrar por classe
                if not menu_outras:
                    try:
                        menu_outras = session['driver'].find_element(By.CLASS_NAME, "menuEspecial")
                    except:
                        pass
                
                if menu_outras:
                    # Clicar em "Outras"
                    menu_outras.click()
                    time.sleep(1)
                    logger.info("✅ Menu 'Outras' encontrado e clicado")
                    
                    # Clicar em "Solicitar Acesso"
                    try:
                        link_solicitar = session['driver'].find_element(
                            By.XPATH, 
                            "//a[contains(text(), 'Solicitar Acesso')]"
                        )
                        link_solicitar.click()
                        time.sleep(2)
                        logger.info("✅ 'Solicitar Acesso' clicado")
                        
                        # Tratar popup ou nova aba
                        try:
                            # Verificar se há popup
                            alert = session['driver'].switch_to.alert
                            alert.accept()
                            logger.info("✅ Popup de confirmação aceito")
                            session['driver'].switch_to.default_content()
                        except:
                            # Se não há popup, verificar se abriu nova aba
                            try:
                                if len(session['driver'].window_handles) > 1:
                                    # Fechar aba extra se abriu
                                    session['driver'].switch_to.window(session['driver'].window_handles[-1])
                                    session['driver'].close()
                                    session['driver'].switch_to.window(session['driver'].window_handles[0])
                                    logger.info("✅ Nova aba fechada")
                            except:
                                pass
                        
                        # Aguardar um pouco para o sistema processar
                        time.sleep(3)
                        logger.info("✅ Acesso aos anexos solicitado com sucesso")
                        return True
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao clicar em 'Solicitar Acesso': {e}")
                        return False
                else:
                    logger.warning("⚠️ Menu 'Outras' não encontrado na página do processo")
                    return False
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao solicitar acesso: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao solicitar acesso ao processo: {e}")
            return False

    def _extrair_anexos_movimentacao(self, session, codigo_movimentacao):
        """Extrai anexos de uma movimentação específica (após acesso já solicitado)"""
        try:
            logger.info(f"📎 Verificando anexos para movimentação {codigo_movimentacao}")
            
            # Clicar no botão de anexos da movimentação
            try:
                # Tentar diferentes seletores para o botão de anexos
                btn_anexo = None
                
                # Seletor 1: Por onclick específico
                try:
                    btn_anexo = session['driver'].find_element(
                        By.XPATH, 
                        f"//img[@src='imagens/22x22/go-bottom.png' and @onclick[contains(., '{codigo_movimentacao}')]]"
                    )
                except:
                    pass
                
                # Seletor 2: Por ID específico
                if not btn_anexo:
                    try:
                        btn_anexo = session['driver'].find_element(
                            By.XPATH, 
                            f"//img[@src='imagens/22x22/go-bottom.png' and @id[contains(., '{codigo_movimentacao}')]]"
                        )
                    except:
                        pass
                
                # Seletor 3: Qualquer botão de anexos (mais genérico)
                if not btn_anexo:
                    try:
                        btn_anexo = session['driver'].find_element(
                            By.XPATH, 
                            "//img[@src='imagens/22x22/go-bottom.png']"
                        )
                    except:
                        pass
                
                if btn_anexo:
                    btn_anexo.click()
                    time.sleep(2)
                    logger.info(f"✅ Botão de anexos clicado para movimentação {codigo_movimentacao}")
                else:
                    logger.warning(f"⚠️ Botão de anexos não encontrado para movimentação {codigo_movimentacao}")
                    return []
                    
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível clicar no botão de anexos: {e}")
                return []
            
            # Aguardar carregamento da página de anexos
            try:
                session['wait'].until(EC.presence_of_element_located((By.ID, "TabelaArquivos")))
                logger.info("✅ Página de anexos carregada")
            except:
                logger.warning("⚠️ Página de anexos não carregou corretamente")
                return []
            
            # Verificar se há anexos disponíveis (já que o acesso foi solicitado no início)
            try:
                # Tentar encontrar links de anexos
                links_anexos = session['driver'].find_elements(
                    By.XPATH, 
                    "//a[contains(@href, 'DownloadArquivo') or contains(@href, 'VisualizarArquivo')]"
                )
                
                if links_anexos:
                    logger.info(f"✅ {len(links_anexos)} anexos encontrados")
                    return [link.get_attribute('href') for link in links_anexos]
                else:
                    logger.info("ℹ️ Nenhum anexo encontrado")
                    return []
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao verificar anexos: {e}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Erro ao extrair anexos: {e}")
            return []
    
    def voltar_para_lista(self, session, tipo_busca, valor):
        """Volta para a lista de processos"""
        try:
            logger.info("🔙 Voltando para lista de processos...")
            
            # Clicar no botão voltar
            try:
                btn_voltar = session['driver'].find_element(By.XPATH, "//input[@value='Voltar']")
                btn_voltar.click()
                time.sleep(5)
                logger.info("✅ Retornou para lista de processos")
                return True
            except:
                # Se não encontrar botão voltar, tentar navegar de volta
                session['driver'].back()
                time.sleep(5)
                logger.info("✅ Navegou de volta para lista de processos")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao voltar para lista: {e}")
            return False
    
    def processar_busca(self, tipo_busca, valor, limite_movimentacoes=None, extrair_anexos=False):
        """Processa uma busca completa com pool de sessões e refresh automático ROBUSTO"""
        request_id = str(uuid.uuid4())
        logger.info(f"🚀 Iniciando busca {request_id}: {tipo_busca} = {valor}")
        
        session = None
        max_retries = 5  # Aumentado para 5 tentativas
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Obter sessão do pool com verificação de saúde
                session = self._get_session_with_health_check()
                if not session:
                    logger.error(f"❌ Não foi possível obter sessão saudável para busca {request_id}")
                    return {"error": "Não foi possível obter sessão", "request_id": request_id}
                
                logger.info(f"🔧 Usando sessão {session['id']} para busca {request_id}")
                
                # Fazer login com sistema robusto
                if not self._robust_operation(session, self.fazer_login, "Login", None, None, None):
                    logger.error(f"❌ Falha no login para busca {request_id}")
                    if attempt < max_retries - 1:
                        logger.info(f"🔄 Tentativa {attempt + 1}/{max_retries} - Tentando refresh da sessão")
                        if self._refresh_session_auto(session):
                            continue
                    self.session_pool.release_session(session)
                    return {"error": "Falha no login", "request_id": request_id}
                
                # Executar busca baseada no tipo com sistema robusto
                busca_success = False
                if tipo_busca == 'cpf':
                    busca_success = self._robust_operation(session, self.buscar_por_cpf, "Busca por CPF", valor)
                elif tipo_busca == 'nome':
                    busca_success = self._robust_operation(session, self.buscar_por_nome, "Busca por Nome", valor)
                elif tipo_busca == 'processo':
                    busca_success = self._robust_operation(session, self.buscar_por_processo, "Busca por Processo", valor)
                else:
                    self.session_pool.release_session(session)
                    return {"error": f"Tipo de busca '{tipo_busca}' não suportado", "request_id": request_id}
                
                if not busca_success:
                    logger.error(f"❌ Falha na busca {tipo_busca} para {request_id}")
                    if attempt < max_retries - 1:
                        logger.info(f"🔄 Tentativa {attempt + 1}/{max_retries} - Tentando refresh da sessão")
                        if self._refresh_session_auto(session):
                            continue
                    self.session_pool.release_session(session)
                    return {"error": f"Falha na busca por {tipo_busca}", "request_id": request_id}
                
                # Tratar busca por processo de forma especial
                if tipo_busca == 'processo':
                    logger.info(f"📄 Busca por processo específico - extraindo diretamente da página")
                    
                    # Para busca por processo, já estamos na página do processo
                    # Criar um processo fictício para extrair dados
                    processo_ficticio = {
                        'numero': valor,
                        'id': 'processo_direto',
                        'classe': 'Processo Específico',
                        'assunto': 'Busca Direta'
                    }
                    
                    # Extrair movimentações diretamente
                    movimentacoes = self._robust_operation(session, self.extrair_movimentacoes, "Extrair Movimentações", processo_ficticio, limite_movimentacoes, extrair_anexos)
                    if not movimentacoes:
                        movimentacoes = []
                    
                    # Extrair partes envolvidas diretamente
                    partes_envolvidas = self._robust_operation(session, self.extrair_partes_envolvidas, "Extrair Partes Envolvidas", processo_ficticio)
                    if not partes_envolvidas:
                        partes_envolvidas = []
                    
                    # Criar resultado único
                    resultado_processo = {
                        "numero": valor,
                        "id": "processo_direto",
                        "classe": "Processo Específico",
                        "assunto": "Busca Direta",
                        "movimentacoes": movimentacoes,
                        "total_movimentacoes": len(movimentacoes),
                        "ultima_movimentacao": movimentacoes[-1]['numero'] if movimentacoes else '',
                        "partes_envolvidas": partes_envolvidas,
                        "total_partes": len(partes_envolvidas)
                    }
                    
                    # Calcular tempo total
                    tempo_total = time.time() - start_time
                    logger.info(f"🎉 Busca por processo {request_id} concluída em {tempo_total:.2f}s")
                    
                    # Liberar sessão
                    self.session_pool.release_session(session)
                    
                    return {
                        "status": "success",
                        "tipo_busca": tipo_busca,
                        "valor_busca": valor,
                        "total_processos": 1,
                        "processos_processados": 1,
                        "resultados": [resultado_processo],
                        "request_id": request_id,
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Para outros tipos de busca (CPF, nome), obter lista de processos
                processos = self._robust_operation(session, self.obter_lista_processos, "Obter Lista de Processos")
                if not processos:
                    logger.warning(f"⚠️ Nenhum processo encontrado para {request_id}")
                    self.session_pool.release_session(session)
                    return {
                        "status": "success",
                        "tipo_busca": tipo_busca,
                        "valor_busca": valor,
                        "total_processos": 0,
                        "processos_processados": 0,
                        "resultados": [],
                        "request_id": request_id,
                        "timestamp": datetime.now().isoformat()
                    }
                
                logger.info(f"📊 Encontrados {len(processos)} processos para {request_id}")
                
                # Processar cada processo com sistema robusto
                resultados = []
                for i, processo in enumerate(processos):
                    try:
                        logger.info(f"📄 Processando processo {i+1}/{len(processos)} para {request_id}")
                        
                        # Acessar processo com sistema robusto
                        if not self._robust_operation(session, self.acessar_processo, "Acessar Processo", processo, extrair_anexos):
                            logger.warning(f"❌ Falha ao processar processo {i+1} para {request_id}")
                            continue
                        
                        # Extrair movimentações com sistema robusto
                        movimentacoes = self._robust_operation(session, self.extrair_movimentacoes, "Extrair Movimentações", processo, limite_movimentacoes, extrair_anexos)
                        if not movimentacoes:
                            movimentacoes = []
                        
                        # Extrair partes envolvidas com sistema robusto
                        partes_envolvidas = self._robust_operation(session, self.extrair_partes_envolvidas, "Extrair Partes Envolvidas", processo)
                        if not partes_envolvidas:
                            partes_envolvidas = []
                        
                        # Adicionar ao resultado
                        resultado_processo = {
                            "numero": str(i+1),
                            "id": processo.get('id', ''),
                            "classe": processo.get('classe', ''),
                            "assunto": processo.get('assunto', ''),
                            "movimentacoes": movimentacoes,
                            "total_movimentacoes": len(movimentacoes),
                            "ultima_movimentacao": movimentacoes[-1]['numero'] if movimentacoes else '',
                            "partes_envolvidas": partes_envolvidas,
                            "total_partes": len(partes_envolvidas)
                        }
                        resultados.append(resultado_processo)
                        
                        logger.info(f"✅ Processo {i+1} processado com sucesso para {request_id}")
                        
                        # Voltar para lista (sempre, exceto no último processo)
                        if i < len(processos) - 1:
                            if not self._robust_operation(session, self.voltar_para_lista, "Voltar para Lista", tipo_busca, valor):
                                logger.warning(f"⚠️ Falha ao voltar para lista após processo {i+1}")
                                break
                                
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar processo {i+1} para {request_id}: {e}")
                        continue
                
                # Calcular tempo total
                tempo_total = time.time() - start_time
                logger.info(f"🎉 Busca {request_id} concluída em {tempo_total:.2f}s")
                
                # Liberar sessão
                self.session_pool.release_session(session)
                
                return {
                    "status": "success",
                    "tipo_busca": tipo_busca,
                    "valor_busca": valor,
                    "total_processos": len(processos),
                    "processos_processados": len(resultados),
                    "resultados": resultados,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Erro geral na busca {request_id} (tentativa {attempt + 1}): {e}")
                if session:
                    self.session_pool.release_session(session)
                
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Tentativa {attempt + 1}/{max_retries} - Tentando novamente")
                    time.sleep(3)  # Aguardar mais tempo entre tentativas
                else:
                    return {"error": f"Erro após {max_retries} tentativas: {str(e)}", "request_id": request_id} 