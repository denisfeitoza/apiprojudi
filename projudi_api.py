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
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select

from session_pool import SessionPool

logger = logging.getLogger(__name__)

# Configurações da API
USUARIO = os.getenv('PROJUDI_USER', '34930230144')
SENHA = os.getenv('PROJUDI_PASS', 'Joaquim1*')
SERVENTIA_PADRAO = os.getenv('DEFAULT_SERVENTIA', 'Advogados - OAB/Matrícula: 25348-N-GO')

class ProjudiAPI:
    def __init__(self):
        # Configurar pool de sessões via variável de ambiente
        max_sessions = None  # Deixar o SessionPool decidir baseado na variável de ambiente
        self.session_pool = SessionPool(max_sessions=max_sessions)
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
        """Estratégia de fallback robusta com relogin automático"""
        try:
            logger.info(f"🔄 Fallback {operation_name} - Tentativa 1/{max_attempts} na sessão {session['id']}")
            
            # Verificar se a sessão caiu (não está logada)
            if self._session_logged_out(session):
                logger.warning(f"⚠️ Sessão {session['id']} caiu, fazendo relogin completo...")
                return self._relogin_session(session)
            
            # Verificar se a sessão ainda está válida
            if not self._check_session_health(session):
                logger.warning(f"⚠️ Sessão {session['id']} não está saudável, tentando refresh...")
                if not self._refresh_session_auto(session, max_retries=2):
                    logger.error(f"❌ Falha ao refresh da sessão {session['id']}")
                    return False
            
            # Aguardar um tempo reduzido antes de tentar novamente
            time.sleep(1)
            
            # Tentar a operação novamente
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro no fallback {operation_name}: {e}")
        return False
    
    def _session_logged_out(self, session):
        """Verifica se a sessão caiu (não está logada)"""
        try:
            current_url = session['driver'].current_url
            page_source = session['driver'].page_source
            
            # Verificar se está na página de login ou se há elementos de login
            login_indicators = [
                "Usuario" in page_source,
                "Senha" in page_source,
                "login" in current_url.lower(),
                "usuario" in current_url.lower(),
                "entrar" in page_source.lower(),
                "acessar" in page_source.lower()
            ]
            
            return any(login_indicators)
        except:
            return True  # Se não conseguir verificar, assume que caiu
    
    def _relogin_session(self, session):
        """Faz relogin completo da sessão com refresh e verificação"""
        try:
            logger.info(f"🔄 Iniciando relogin da sessão {session['id']}")
            
            # 1. Fazer refresh da página de login
            session['driver'].get("https://projudi.tjgo.jus.br/LogOn?PaginaAtual=-200")
            time.sleep(3)
            
            # 2. Verificar se já está logado (se não há campos de login)
            page_source = session['driver'].page_source
            if "Usuario" not in page_source and "Senha" not in page_source:
                logger.info(f"✅ Sessão {session['id']} já está logada")
                return True
            
            # 3. Fazer login completo
            if self.fazer_login(session):
                logger.info(f"✅ Relogin da sessão {session['id']} realizado com sucesso")
                return True
            else:
                logger.error(f"❌ Falha no relogin da sessão {session['id']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no relogin da sessão {session['id']}: {e}")
            return False
    
    def _robust_operation(self, session, operation_func, operation_name, *args, **kwargs):
        """Executa uma operação com fallback automático otimizado"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                result = operation_func(session, *args, **kwargs)
                if result:
                    return result
                else:
                    logger.warning(f"⚠️ {operation_name} falhou na tentativa {attempt + 1}")
                    if attempt < max_retries - 1:
                        # Se falhou na primeira tentativa, fazer fallback imediatamente
                        if attempt == 0:
                            logger.info(f"🔄 Primeira tentativa falhou, fazendo fallback imediato...")
                        if not self._fallback_strategy(session, operation_name):
                            logger.error(f"❌ Fallback para {operation_name} falhou")
                            continue
            except Exception as e:
                logger.error(f"❌ Erro em {operation_name} (tentativa {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    # Se deu erro na primeira tentativa, fazer fallback imediatamente
                    if attempt == 0:
                        logger.info(f"🔄 Primeira tentativa com erro, fazendo fallback imediato...")
                    if not self._fallback_strategy(session, operation_name):
                        logger.error(f"❌ Fallback para {operation_name} falhou")
                        continue
                    time.sleep(1)  # Reduzido de 2s para 1s
        
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
        """Busca processos por CPF - VERSÃO CORRIGIDA COM CAMPO CORRETO"""
        try:
            logger.info(f"🔍 Buscando processos do CPF na sessão {session['id']}: {cpf}")
            
            # Navegar para página de busca
            session['driver'].get(self.BUSCA_URL)
            time.sleep(3)
            
            # Aguardar campo CPF com múltiplos seletores
            cpf_field = None
            seletores_cpf = [
                (By.NAME, "CpfCnpjParte"),  # Campo correto baseado no HTML
                (By.ID, "CpfCnpjParte"),    # ID do campo
                (By.NAME, "CPF"),           # Fallback para nome genérico
                (By.XPATH, "//input[@placeholder='CPF/CNPJ da Parte']"),  # Por placeholder
                (By.XPATH, "//input[contains(@title, 'CPF')]")  # Por título
            ]
            
            for seletor in seletores_cpf:
                try:
                    cpf_field = session['wait'].until(
                        EC.presence_of_element_located(seletor)
                    )
                    logger.info(f"✅ Campo CPF encontrado com seletor: {seletor}")
                    break
                except:
                    continue
            
            if not cpf_field:
                logger.error(f"❌ Campo CPF não encontrado na sessão {session['id']}")
                return False
            
            # Preencher CPF
            try:
                cpf_field.clear()
                cpf_field.send_keys(cpf)
                logger.info(f"✅ CPF preenchido na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao preencher CPF na sessão {session['id']}: {e}")
                return False
            
            # Clicar em buscar com múltiplos seletores
            btn_buscar = None
            seletores_botao = [
                (By.XPATH, "//input[@value='Buscar']"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Buscar')]"),
                (By.NAME, "imgSubmeter"),
                (By.ID, "btnBuscar")
            ]
            
            for seletor in seletores_botao:
                try:
                    btn_buscar = session['driver'].find_element(*seletor)
                    logger.info(f"✅ Botão buscar encontrado com seletor: {seletor}")
                    break
                except:
                    continue
            
            if not btn_buscar:
                logger.error(f"❌ Botão buscar não encontrado na sessão {session['id']}")
                return False
            
            # Clicar no botão
            try:
                btn_buscar.click()
                logger.info(f"✅ Botão buscar clicado na sessão {session['id']}")
            except Exception as e:
                logger.error(f"❌ Erro ao clicar em buscar na sessão {session['id']}: {e}")
                return False
            
            # Aguardar resultado
            time.sleep(3)
            
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
        """Obtém a lista de processos encontrados - VERSÃO CORRIGIDA"""
        try:
            logger.info("📋 Obtendo lista de processos...")
            
            # Aguardar carregamento da página
            time.sleep(2)
            
            # Verificar se há mensagem de "nenhum resultado" primeiro
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
            
            # Aguardar tabela de resultados com timeout reduzido
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
                            'indice': len(processos) + 1
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
        """Extrai as movimentações de um processo - NOVA VERSÃO COM NAVEGAÇÃO DE ARQUIVOS"""
        try:
            logger.info("📋 Extraindo movimentações da página de navegação de arquivos...")
            
            # Usar o novo método de navegação de arquivos
            movimentacoes = self.extrair_movimentacoes_navegacao_arquivos(
                session=session,
                processo_info=processo_info,
                limite_movimentacoes=limite_movimentacoes,
                extrair_anexos=extrair_anexos
            )
            
            logger.info(f"✅ {len(movimentacoes)} movimentações extraídas da página de navegação")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair movimentações: {e}")
            return []
    
    def extrair_partes_envolvidas(self, session, processo_info):
        """Extrai as partes envolvidas de um processo - VERSÃO CORRIGIDA"""
        try:
            logger.info("👥 Extraindo partes envolvidas...")
            
            # Aguardar carregamento da página principal
            time.sleep(1)
            
            # Primeiro, tentar extrair partes diretamente da página atual
            partes_envolvidas = []
            
            # Buscar por informações de partes na página atual
            try:
                # Buscar por elementos que contenham informações de partes
                elementos_partes = session['driver'].find_elements(By.XPATH, "//*[contains(text(), 'Polo') or contains(text(), 'Autor') or contains(text(), 'Réu') or contains(text(), 'Requerente') or contains(text(), 'Requerido')]")
                
                for elemento in elementos_partes:
                    try:
                        texto = elemento.text.strip()
                        if texto and len(texto) > 10:  # Filtrar textos muito curtos
                            # Verificar se contém informações relevantes
                            if any(palavra in texto.lower() for palavra in ['polo', 'autor', 'réu', 'requerente', 'requerido', 'advogado', 'cpf', 'cnpj']):
                                logger.info(f"✅ Encontrado: {texto[:100]}...")
                                partes_envolvidas.append({
                                    'nome': texto,
                                    'tipo': 'Parte Envolvida',
                                    'processo': processo_info.get('numero', '')
                                })
                    except Exception as e:
                        logger.debug(f"⚠️ Erro ao processar elemento: {e}")
                    continue
            
                # Se encontrou partes, retornar
                if partes_envolvidas:
                    logger.info(f"✅ Extraídas {len(partes_envolvidas)} partes da página atual")
                    return partes_envolvidas
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair partes da página atual: {e}")
            
            # Se não encontrou partes na página atual, tentar buscar por links específicos
            logger.info("🔍 Procurando por links de partes...")
            
            # Buscar por links que possam levar às partes
            seletores_links = [
                (By.XPATH, "//a[contains(text(), 'Partes')]"),
                (By.XPATH, "//a[contains(text(), 'Envolvidas')]"),
                (By.XPATH, "//a[contains(text(), 'Visualizar')]"),
                (By.XPATH, "//a[contains(@href, 'parte')]"),
                (By.XPATH, "//a[contains(@onclick, 'parte')]"),
                (By.XPATH, "//button[contains(text(), 'Partes')]"),
                (By.XPATH, "//button[contains(text(), 'Visualizar')]"),
            ]
            
            link_encontrado = None
            for seletor_tipo, seletor_valor in seletores_links:
                try:
                    elementos = session['driver'].find_elements(seletor_tipo, seletor_valor)
                    if elementos:
                        link_encontrado = elementos[0]
                        logger.info(f"✅ Link encontrado: {seletor_tipo}={seletor_valor}")
                        break
                except Exception as e:
                    continue
            
            if link_encontrado:
                try:
                    # Clicar no link
                    session['driver'].execute_script("arguments[0].scrollIntoView(true);", link_encontrado)
                    time.sleep(0.5)
                    link_encontrado.click()
                    logger.info("✅ Clicado no link das partes")
                    
                    # Aguardar carregamento
                    time.sleep(2)
                    
                    # Extrair informações das partes
                    elementos_partes = session['driver'].find_elements(By.XPATH, "//div[contains(@class, 'parte') or contains(@class, 'polo') or contains(@class, 'envolvido')]")
                    
                    for elemento in elementos_partes:
                        try:
                            texto = elemento.text.strip()
                            if texto and len(texto) > 10:
                                logger.info(f"✅ Encontrado: {texto[:100]}...")
                                partes_envolvidas.append({
                                    'nome': texto,
                                    'tipo': 'Parte Envolvida',
                                    'processo': processo_info.get('numero', '')
                                })
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao processar elemento parte: {e}")
                        continue
                    
                    # Voltar à página principal
                    session['driver'].back()
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao clicar no link das partes: {e}")
                    # Tentar voltar mesmo em caso de erro
                    try:
                        session['driver'].back()
                        time.sleep(1)
                    except:
                        pass
                
            # Se ainda não encontrou partes, tentar extrair das movimentações
            if not partes_envolvidas:
                logger.info("🔍 Tentando extrair partes das movimentações...")
                try:
                    # Buscar por informações de partes nas movimentações
                    elementos_mov = session['driver'].find_elements(By.XPATH, "//*[contains(text(), 'Intimação') or contains(text(), 'Citação') or contains(text(), 'Advogado')]")
                    
                    for elemento in elementos_mov:
                        try:
                            texto = elemento.text.strip()
                            if texto and len(texto) > 20:
                                # Verificar se contém informações de partes
                                if any(palavra in texto.lower() for palavra in ['advogado', 'intimação', 'citação', 'parte']):
                                    logger.info(f"✅ Encontrado nas movimentações: {texto[:100]}...")
                                    partes_envolvidas.append({
                                        'nome': texto,
                                        'tipo': 'Parte das Movimentações',
                                        'processo': processo_info.get('numero', '')
                                    })
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao processar elemento movimentação: {e}")
                            continue
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao extrair partes das movimentações: {e}")
            
            logger.info(f"✅ Extraídas {len(partes_envolvidas)} partes envolvidas")
            return partes_envolvidas
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes envolvidas: {e}")
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
    
    def _extrair_partes_das_movimentacoes(self, session):
        """Tenta extrair informações das partes diretamente das movimentações"""
        partes = []
        try:
            logger.info("🔍 Analisando movimentações para extrair partes...")
            
            soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
            
            # Buscar por padrões como "(Polo Ativo)" e "(Polo Passivo)" nas movimentações
            texto_pagina = soup.get_text()
            
            # Extrair informações de polos das movimentações
            padroes_polo = [
                r'\(Polo\s+Ativo\)\s+([^\(\n\r]+)',
                r'\(Polo\s+Passivo\)\s+([^\(\n\r]+)',
                r'Polo\s+Ativo[:\s]+([^\n\r\(]+)',
                r'Polo\s+Passivo[:\s]+([^\n\r\(]+)'
            ]
            
            nomes_encontrados = set()  # Para evitar duplicatas
            
            for padrao in padroes_polo:
                matches = re.finditer(padrao, texto_pagina, re.I)
                for match in matches:
                    nome = match.group(1).strip()
                    
                    # Limpar o nome (remover texto extra)
                    nome = re.sub(r'\s*\(.*?\)\s*', '', nome).strip()
                    nome = re.sub(r'\s*\-.*$', '', nome).strip()
                    
                    if nome and len(nome) > 3 and nome not in nomes_encontrados:
                        nomes_encontrados.add(nome)
                        
                        # Determinar tipo
                        if 'ativo' in match.group(0).lower():
                            tipo = 'Polo Ativo'
                        else:
                            tipo = 'Polo Passivo'
                        
                        parte_info = {
                            'nome': nome,
                            'tipo': tipo,
                            'cpf_cnpj': '',
                            'rg': '',
                            'endereco': '',
                            'telefone': '',
                            'email': '',
                            'advogado': '',
                            'oab': '',
                            'html_completo': '',
                            'texto_completo': match.group(0)
                        }
                        
                        partes.append(parte_info)
                        logger.info(f"✅ Extraído das movimentações - {tipo}: {nome}")
            
            # Buscar também por outros padrões comuns
            outros_padroes = [
                r'(?:Autor|AUTOR)[:\s]+([^\n\r\(]+)',
                r'(?:Réu|RÉU)[:\s]+([^\n\r\(]+)',
                r'(?:Requerente|REQUERENTE)[:\s]+([^\n\r\(]+)',
                r'(?:Requerido|REQUERIDO)[:\s]+([^\n\r\(]+)'
            ]
            
            for padrao in outros_padroes:
                matches = re.finditer(padrao, texto_pagina, re.I)
                for match in matches:
                    nome = match.group(1).strip()
                    nome = re.sub(r'\s*\(.*?\)\s*', '', nome).strip()
                    
                    if nome and len(nome) > 3 and nome not in nomes_encontrados:
                        nomes_encontrados.add(nome)
                        
                        tipo_match = match.group(0).split(':')[0].split()[0]
                        
                        parte_info = {
                            'nome': nome,
                            'tipo': tipo_match.title(),
                            'cpf_cnpj': '',
                            'rg': '',
                            'endereco': '',
                            'telefone': '',
                            'email': '',
                            'advogado': '',
                            'oab': '',
                            'html_completo': '',
                            'texto_completo': match.group(0)
                        }
                        
                        partes.append(parte_info)
                        logger.info(f"✅ Extraído das movimentações - {tipo_match}: {nome}")
            
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes das movimentações: {e}")
            return []
    
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
                        logger.warning(f"⚠️ Nenhuma movimentação encontrada para processo {valor}")
                    
                    # SÓ extrair partes se encontrou movimentações
                    partes_envolvidas = []
                    if movimentacoes:
                        logger.info(f"📋 Movimentações encontradas, extraindo partes envolvidas...")
                        partes_envolvidas = self._robust_operation(session, self.extrair_partes_envolvidas, "Extrair Partes Envolvidas", processo_ficticio)
                        if not partes_envolvidas:
                            partes_envolvidas = []
                    else:
                        logger.info(f"⚠️ Pulando extração de partes - nenhuma movimentação encontrada")
                    
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
                            logger.warning(f"⚠️ Nenhuma movimentação encontrada para processo {i+1}")
                        
                        # SÓ extrair partes se encontrou movimentações
                        partes_envolvidas = []
                        if movimentacoes:
                            logger.info(f"📋 Movimentações encontradas para processo {i+1}, extraindo partes...")
                            partes_envolvidas = self._robust_operation(session, self.extrair_partes_envolvidas, "Extrair Partes Envolvidas", processo)
                            if not partes_envolvidas:
                                partes_envolvidas = []
                        else:
                            logger.info(f"⚠️ Pulando extração de partes para processo {i+1} - nenhuma movimentação encontrada")
                        
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
    
    def baixar_paginas_navegacao_arquivo(self, numero_processo, extrair_anexos=True):
        """
        Método seguro para baixar páginas de navegação de arquivos
        Fluxo: Login -> Busca -> Acessar processo -> Solicitar acesso -> Baixar páginas
        """
        try:
            logger.info(f"🔍 Iniciando download das páginas de navegação para processo: {numero_processo}")
            
            # Obter sessão do pool
            session = self._get_session_with_health_check()
            if not session:
                logger.error("❌ Não foi possível obter sessão")
                return {"error": "Não foi possível obter sessão"}
            
            try:
                # 1. Fazer login
                logger.info("🔐 Fazendo login...")
                if not self._robust_operation(session, self.fazer_login, "Login", None, None, None):
                    logger.error("❌ Falha no login")
                    return {"error": "Falha no login"}
                
                # 2. Buscar processo
                logger.info(f"🔍 Buscando processo: {numero_processo}")
                if not self._robust_operation(session, self.buscar_por_processo, "Busca por Processo", numero_processo):
                    logger.error("❌ Falha na busca do processo")
                    return {"error": "Falha na busca do processo"}
                
                # 3. Aguardar carregamento da página do processo
                time.sleep(3)
                
                # 4. Salvar página principal do processo
                logger.info("💾 Salvando página principal do processo...")
                html_pagina_principal = session['driver'].page_source
                
                # Salvar arquivo da página principal
                nome_arquivo_principal = f"pagina_principal_processo_{numero_processo.replace('/', '_').replace('.', '_')}.html"
                with open(nome_arquivo_principal, 'w', encoding='utf-8') as f:
                    f.write(html_pagina_principal)
                logger.info(f"✅ Página principal salva: {nome_arquivo_principal}")
                
                # 5. Se extrair_anexos=True, solicitar acesso
                if extrair_anexos:
                    logger.info("🔓 Solicitando acesso aos anexos...")
                    self._solicitar_acesso_processo_seguro(session)
                
                # 6. Procurar e clicar no botão "Navegação de Arquivos"
                logger.info("🔍 Procurando botão 'Navegação de Arquivos'...")
                botao_encontrado = False
                
                # Seletores para o botão de navegação de arquivos
                seletores_navegacao = [
                    (By.XPATH, "//a[contains(text(), 'Navegação de Arquivo')]"),  # Correto - singular
                    (By.XPATH, "//span[contains(text(), 'Navegação de Arquivo')]"),
                    (By.XPATH, "//a[contains(@onclick, 'window.open') and contains(@onclick, 'BuscaProcesso')]"),
                    (By.XPATH, "//a[@id='ui-id-3']"),  # ID específico do botão
                    (By.XPATH, "//a[contains(text(), 'Navegação de Arquivos')]"),  # Fallback plural
                    (By.XPATH, "//a[contains(text(), 'Navegação') and contains(text(), 'Arquivo')]"),
                    (By.XPATH, "//a[contains(@onclick, 'navegacao')]"),
                    (By.XPATH, "//a[contains(@href, 'navegacao')]"),
                    (By.XPATH, "//button[contains(text(), 'Navegação de Arquivo')]"),
                    (By.XPATH, "//input[@value='Navegação de Arquivo']"),
                    (By.XPATH, "//a[contains(text(), 'Arquivos do Processo')]"),
                    (By.XPATH, "//a[contains(text(), 'Navegação')]"),
                ]
                
                for seletor in seletores_navegacao:
                    try:
                        elementos = session['driver'].find_elements(*seletor)
                        if elementos:
                            botao_navegacao = elementos[0]
                            logger.info(f"✅ Botão encontrado com seletor: {seletor}")
                            
                            # Scroll para o botão
                            session['driver'].execute_script("arguments[0].scrollIntoView(true);", botao_navegacao)
                            time.sleep(1)
                            
                            # Clicar no botão
                            botao_navegacao.click()
                            time.sleep(3)
                            botao_encontrado = True
                            logger.info("✅ Botão 'Navegação de Arquivos' clicado")
                            break
                    except Exception as e:
                        logger.debug(f"⚠️ Seletor {seletor} falhou: {e}")
                        continue
                
                if not botao_encontrado:
                    logger.warning("⚠️ Botão 'Navegação de Arquivos' não encontrado")
                    # Salvar página principal mesmo assim
                    return {
                        "status": "partial_success",
                        "pagina_principal": nome_arquivo_principal,
                        "navegacao_arquivos": None,
                        "mensagem": "Botão de navegação não encontrado"
                    }
                
                # 7. Tratar popup/nova aba
                logger.info("🔄 Tratando popup/nova aba...")
                handles_originais = session['driver'].window_handles
                
                # Aguardar nova aba/popup
                time.sleep(2)
                handles_atuais = session['driver'].window_handles
                
                if len(handles_atuais) > len(handles_originais):
                    # Nova aba foi aberta
                    logger.info("📑 Nova aba detectada, mudando para ela...")
                    nova_aba = handles_atuais[-1]
                    session['driver'].switch_to.window(nova_aba)
                    time.sleep(3)
                else:
                    # Pode ser um popup ou mudança na mesma aba
                    logger.info("ℹ️ Nenhuma nova aba detectada, continuando na mesma...")
                
                # 8. Salvar página de navegação de arquivos
                logger.info("💾 Salvando página de navegação de arquivos...")
                html_navegacao = session['driver'].page_source
                
                nome_arquivo_navegacao = f"navegacao_arquivos_processo_{numero_processo.replace('/', '_').replace('.', '_')}.html"
                with open(nome_arquivo_navegacao, 'w', encoding='utf-8') as f:
                    f.write(html_navegacao)
                logger.info(f"✅ Página de navegação salva: {nome_arquivo_navegacao}")
                
                # 9. Fechar popup/nova aba se necessário
                try:
                    if len(session['driver'].window_handles) > 1:
                        logger.info("🔒 Fechando nova aba...")
                        session['driver'].close()
                        session['driver'].switch_to.window(handles_originais[0])
                        time.sleep(1)
                except Exception as e:
                    logger.info(f"ℹ️ Erro ao fechar aba (normal): {e}")
                    # Tentar voltar para a aba original
                    try:
                        session['driver'].switch_to.window(handles_originais[0])
                    except:
                        pass
                
                # 10. Verificar se há popup de confirmação na página principal
                try:
                    alert = session['driver'].switch_to.alert
                    alert.accept()
                    logger.info("✅ Popup de confirmação aceito")
                    session['driver'].switch_to.default_content()
                except:
                    logger.info("ℹ️ Nenhum popup de confirmação encontrado")
                
                logger.info("🎉 Download das páginas concluído com sucesso!")
                
                return {
                    "status": "success",
                    "pagina_principal": nome_arquivo_principal,
                    "navegacao_arquivos": nome_arquivo_navegacao,
                    "processo": numero_processo,
                    "extrair_anexos": extrair_anexos
                }
                
            finally:
                # Liberar sessão
                self.session_pool.release_session(session)
                
        except Exception as e:
            logger.error(f"❌ Erro no download das páginas: {e}")
            return {"error": f"Erro: {str(e)}"}
    
    def _solicitar_acesso_processo_seguro(self, session):
        """Solicita acesso aos anexos de forma segura com JavaScript"""
        try:
            logger.info("🔓 Solicitando acesso aos anexos com JavaScript...")
            
            # Aguardar carregamento da página
            time.sleep(2)
            
            # Tentar encontrar o menu "Outras" com JavaScript
            scripts_menu = [
                """
                var menuOutras = document.querySelector('a[href*="outras"]');
                if (menuOutras) {
                    menuOutras.click();
                    return true;
                }
                return false;
                """,
                """
                var menuOutras = document.querySelector('a:contains("Outras")');
                if (menuOutras) {
                    menuOutras.click();
                    return true;
                }
                return false;
                """,
                """
                var links = document.querySelectorAll('a');
                for (var i = 0; i < links.length; i++) {
                    if (links[i].textContent.includes('Outras')) {
                        links[i].click();
                        return true;
                    }
                }
                return false;
                """,
                """
                var menuOutras = document.getElementById('menu_outras');
                if (menuOutras) {
                    menuOutras.click();
                    return true;
                }
                return false;
                """
            ]
            
            menu_clicado = False
            for i, script in enumerate(scripts_menu):
                try:
                    resultado = session['driver'].execute_script(script)
                    if resultado:
                        logger.info(f"✅ Menu 'Outras' clicado com script {i+1}")
                        menu_clicado = True
                        time.sleep(1)
                        break
                except Exception as e:
                    logger.debug(f"⚠️ Script {i+1} falhou: {e}")
                    continue
            
            if not menu_clicado:
                logger.warning("⚠️ Menu 'Outras' não encontrado")
                return False
            
            # Tentar clicar em "Solicitar Acesso" com JavaScript
            scripts_solicitar = [
                """
                var linkSolicitar = document.querySelector('a[href*="solicitar"]');
                if (linkSolicitar) {
                    linkSolicitar.click();
                    return true;
                }
                return false;
                """,
                """
                var links = document.querySelectorAll('a');
                for (var i = 0; i < links.length; i++) {
                    if (links[i].textContent.includes('Solicitar Acesso')) {
                        links[i].click();
                        return true;
                    }
                }
                return false;
                """,
                """
                var linkSolicitar = document.querySelector('a:contains("Solicitar Acesso")');
                if (linkSolicitar) {
                    linkSolicitar.click();
                    return true;
                }
                return false;
                """,
                """
                var elementos = document.querySelectorAll('*');
                for (var i = 0; i < elementos.length; i++) {
                    if (elementos[i].textContent && elementos[i].textContent.includes('Solicitar Acesso')) {
                        if (elementos[i].tagName === 'A' || elementos[i].onclick) {
                            elementos[i].click();
                            return true;
                        }
                    }
                }
                return false;
                """
            ]
            
            acesso_solicitado = False
            for i, script in enumerate(scripts_solicitar):
                try:
                    resultado = session['driver'].execute_script(script)
                    if resultado:
                        logger.info(f"✅ 'Solicitar Acesso' clicado com script {i+1}")
                        acesso_solicitado = True
                        time.sleep(2)
                        break
                except Exception as e:
                    logger.debug(f"⚠️ Script solicitar {i+1} falhou: {e}")
                    continue
            
            if not acesso_solicitado:
                logger.warning("⚠️ 'Solicitar Acesso' não encontrado")
                return False
            
            # Tratar possíveis popups
            try:
                alert = session['driver'].switch_to.alert
                alert.accept()
                logger.info("✅ Popup de confirmação aceito")
                session['driver'].switch_to.default_content()
            except:
                logger.info("ℹ️ Nenhum popup de confirmação encontrado")
            
            # Aguardar processamento
            time.sleep(3)
            logger.info("✅ Acesso aos anexos solicitado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao solicitar acesso: {e}")
            return False
    
    def extrair_movimentacoes_navegacao_arquivos(self, session, processo_info, limite_movimentacoes=None, extrair_anexos=False):
        """
        Extrai movimentações da página de navegação de arquivos (mais eficiente)
        Esta página tem as movimentações em ordem crescente (1, 2, 3...) e acesso direto aos anexos
        """
        try:
            logger.info("📋 Extraindo movimentações da página de navegação de arquivos...")
            
            # 1. Primeiro, acessar a página de navegação de arquivos
            if not self._acessar_pagina_navegacao_arquivos(session):
                logger.error("❌ Falha ao acessar página de navegação de arquivos")
                return []
            
            # 2. Aguardar carregamento da tabela
            time.sleep(3)
            
            # 3. Extrair dados da tabela de movimentações
            soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
            tabela = soup.find('table', {'id': 'TabelaArquivos'})
            
            if not tabela:
                logger.error("❌ Tabela de movimentações não encontrada na página de navegação")
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
                if len(tds) >= 5:  # A tabela tem 6 colunas: Nº, Movimentação, Data, Usuário, Arquivo(s), Opções
                    # Extrair dados das colunas
                    numero = tds[0].get_text(strip=True)
                    movimentacao_celula = tds[1]
                    data = tds[2].get_text(strip=True)
                    usuario = tds[3].get_text(strip=True)
                    arquivos_celula = tds[4]
                    
                    # Extrair tipo e descrição da movimentação
                    tipo_movimentacao = ""
                    descricao_movimentacao = ""
                    
                    span_tipo = movimentacao_celula.find('span', class_='filtro_tipo_movimentacao')
                    if span_tipo:
                        tipo_movimentacao = span_tipo.get_text(strip=True)
                        # Pegar o texto após o <br> para a descrição
                        br_element = movimentacao_celula.find('br')
                        if br_element and br_element.next_sibling:
                            descricao_movimentacao = br_element.next_sibling.strip()
                        else:
                            # Se não há <br>, pegar todo o texto exceto o tipo
                            texto_completo = movimentacao_celula.get_text(strip=True)
                            descricao_movimentacao = texto_completo.replace(tipo_movimentacao, '').strip()
                    else:
                        # Se não há span, pegar todo o texto
                        tipo_movimentacao = movimentacao_celula.get_text(strip=True)
                    
                    # Verificar se tem anexo
                    tem_anexo = bool(arquivos_celula.find('img', {'src': 'imagens/22x22/go-bottom.png'}))
                    
                    # Extrair código da movimentação para anexos
                    codigo_movimentacao = ""
                    link_anexo = arquivos_celula.find('a')
                    if link_anexo:
                        onclick = link_anexo.get('onclick', '')
                        match = re.search(r"buscarArquivosMovimentacaoJSON\('([^']+)'", onclick)
                        if match:
                            codigo_movimentacao = match.group(1)
                            logger.debug(f"📎 Código de anexo encontrado: {codigo_movimentacao}")
                    
                    # Extrair ID da movimentação
                    id_movimentacao = ""
                    div_drop = linha.find('div', class_='dropMovimentacao')
                    if div_drop:
                        id_movimentacao = div_drop.get('id_movi', '')
                    
                    # Verificar se é uma linha válida de movimentação
                    if numero and tipo_movimentacao and not numero.startswith('Nº') and not numero.startswith('Número'):
                        movimentacao = {
                            'numero': int(numero) if numero.isdigit() else len(movimentacoes) + 1,
                            'tipo': tipo_movimentacao,
                            'descricao': descricao_movimentacao,
                            'data': data,
                            'usuario': usuario,
                            'tem_anexo': tem_anexo,
                            'codigo_movimentacao': codigo_movimentacao,
                            'id_movimentacao': id_movimentacao,
                            'anexos': [],
                            'html_completo': str(linha)
                        }
                        
                        # Extrair anexos se solicitado
                        if extrair_anexos and tem_anexo and id_movimentacao:
                            try:
                                anexos = self._extrair_anexos_movimentacao_navegacao(session, id_movimentacao)
                                movimentacao['anexos'] = anexos
                            except Exception as e:
                                logger.warning(f"⚠️ Erro ao extrair anexos: {e}")
                        
                        movimentacoes.append(movimentacao)
            
            # Ordenar por número (já estão em ordem crescente, mas garantir)
            movimentacoes.sort(key=lambda x: x['numero'])
            
            logger.info(f"✅ {len(movimentacoes)} movimentações extraídas da página de navegação")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair movimentações da navegação: {e}")
            return []
    
    def _acessar_pagina_navegacao_arquivos(self, session):
        """Acessa a página de navegação de arquivos do processo"""
        try:
            logger.info("🔍 Acessando página de navegação de arquivos...")
            
            # 1. PRIMEIRO: Solicitar acesso aos anexos antes de acessar a página de navegação
            logger.info("🔓 Solicitando acesso aos anexos antes de acessar navegação...")
            self._solicitar_acesso_processo_seguro(session)
            
            # 2. Procurar e clicar no botão "Navegação de Arquivo"
            seletores_navegacao = [
                (By.XPATH, "//a[contains(text(), 'Navegação de Arquivo')]"),
                (By.XPATH, "//span[contains(text(), 'Navegação de Arquivo')]"),
                (By.XPATH, "//a[contains(@onclick, 'window.open') and contains(@onclick, 'BuscaProcesso')]"),
                (By.XPATH, "//a[@id='ui-id-3']"),
            ]
            
            botao_encontrado = False
            for seletor in seletores_navegacao:
                try:
                    elementos = session['driver'].find_elements(*seletor)
                    if elementos:
                        botao_navegacao = elementos[0]
                        logger.info(f"✅ Botão encontrado com seletor: {seletor}")
                        
                        # Scroll para o botão
                        session['driver'].execute_script("arguments[0].scrollIntoView(true);", botao_navegacao)
                        time.sleep(1)
                        
                        # Clicar no botão
                        botao_navegacao.click()
                        time.sleep(3)
                        botao_encontrado = True
                        logger.info("✅ Botão 'Navegação de Arquivo' clicado")
                        break
                except Exception as e:
                    logger.debug(f"⚠️ Seletor {seletor} falhou: {e}")
                    continue
            
            if not botao_encontrado:
                logger.error("❌ Botão 'Navegação de Arquivo' não encontrado")
                return False
            
            # 3. Tratar popup/nova aba
            handles_originais = session['driver'].window_handles
            time.sleep(2)
            handles_atuais = session['driver'].window_handles
            
            if len(handles_atuais) > len(handles_originais):
                # Nova aba foi aberta
                logger.info("📑 Nova aba detectada, mudando para ela...")
                nova_aba = handles_atuais[-1]
                session['driver'].switch_to.window(nova_aba)
                time.sleep(3)
            else:
                # Pode ser um popup ou mudança na mesma aba
                logger.info("ℹ️ Nenhuma nova aba detectada, continuando na mesma...")
            
            # 4. Aguardar carregamento da página
            time.sleep(3)
            
            # 5. Verificar se chegou na página correta
            if "TabelaArquivos" in session['driver'].page_source:
                logger.info("✅ Página de navegação de arquivos carregada com sucesso")
                return True
            else:
                logger.error("❌ Página de navegação não carregou corretamente")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao acessar página de navegação: {e}")
            return False
    
    def _extrair_anexos_movimentacao_navegacao(self, session, id_movimentacao):
        """Extrai anexos de uma movimentação específica na página de navegação usando o ID"""
        try:
            logger.info(f"📎 Verificando anexos para movimentação ID: {id_movimentacao}")
            
            # Clicar no botão de anexos da movimentação usando o ID
            try:
                # Usar o ID da movimentação para encontrar o botão
                btn_anexo = session['driver'].find_element(
                    By.ID, 
                    f"MostrarArquivos_{id_movimentacao}"
                )
                
                # Tentar fechar overlay se existir
                try:
                    overlay = session['driver'].find_element(By.CLASS_NAME, "ui-widget-overlay")
                    if overlay.is_displayed():
                        session['driver'].execute_script("arguments[0].style.display = 'none';", overlay)
                        time.sleep(1)
                        logger.info("✅ Overlay fechado")
                except:
                    pass
                
                # Scroll para o botão
                session['driver'].execute_script("arguments[0].scrollIntoView(true);", btn_anexo)
                time.sleep(1)
                
                # Tentar clicar com JavaScript se o clique normal falhar
                try:
                    btn_anexo.click()
                except:
                    session['driver'].execute_script("arguments[0].click();", btn_anexo)
                
                time.sleep(2)
                logger.info(f"✅ Botão de anexos clicado para movimentação ID: {id_movimentacao}")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível clicar no botão de anexos: {e}")
                return []
            
            # Aguardar carregamento dos anexos
            time.sleep(3)
            
            # Verificar se há anexos disponíveis
            try:
                # Tentar encontrar links de anexos
                links_anexos = session['driver'].find_elements(
                    By.XPATH, 
                    "//a[contains(@href, 'DownloadArquivo') or contains(@href, 'VisualizarArquivo')]"
                )
                
                if links_anexos:
                    anexos = []
                    for link in links_anexos:
                        href = link.get_attribute('href')
                        texto = link.get_text(strip=True)
                        anexos.append({
                            'url': href,
                            'nome': texto or 'Anexo',
                            'tipo': 'download'
                        })
                    
                    logger.info(f"✅ {len(anexos)} anexos encontrados para movimentação {id_movimentacao}")
                    return anexos
                else:
                    logger.info(f"ℹ️ Nenhum anexo encontrado para movimentação {id_movimentacao}")
                    return []
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao verificar anexos: {e}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Erro ao extrair anexos: {e}")
            return []