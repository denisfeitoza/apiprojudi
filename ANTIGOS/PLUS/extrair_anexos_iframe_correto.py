#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import os
from datetime import datetime
from projudi_api import ProjudiAPI
from session_pool import SessionPool

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



def coletar_partes_processo_pagina_especifica(session):
    """Coleta informações sobre partes do processo na página ProcessoParte - versão otimizada"""
    try:
        logger.info("📋 Coletando partes do processo na página ProcessoParte...")
        
        # Aguardar carregamento da página
        time.sleep(1)
        
        # Verificar se a sessão não expirou
        page_source = session['driver'].page_source
        if "Usuário inválido ou sessão expirada" in page_source:
            logger.error("❌ Sessão expirada na página ProcessoParte")
            return {
                'partes': [],
                'movimentacoes': [],
                'total_partes': 0,
                'total_movimentacoes': 0,
                'erro': 'Sessão expirada'
            }
        
        partes = []
        
        # Estratégias otimizadas para a página ProcessoParte
        estrategias_partes = [
            # Estratégia 1: Procurar por tabelas de partes
            "//table[contains(@class, 'parte') or contains(@class, 'envolvido') or contains(@class, 'table')]//tr",
            # Estratégia 2: Procurar por divs com informações de partes
            "//div[contains(@class, 'parte') or contains(@class, 'envolvido') or contains(@class, 'info')]",
            # Estratégia 3: Procurar por elementos com texto relacionado a partes
            "//*[contains(text(), 'Parte') or contains(text(), 'Autor') or contains(text(), 'Réu') or contains(text(), 'Advogado')]",
            # Estratégia 4: Procurar por tabelas em geral
            "//table//tr"
        ]
        
        # Tentar encontrar partes usando Selenium
        for estrategia in estrategias_partes:
            try:
                elementos = session['driver'].find_elements(By.XPATH, estrategia)
                if elementos:
                    logger.info(f"📋 Encontrados {len(elementos)} elementos de partes com estratégia: {estrategia}")
                    for i, elemento in enumerate(elementos[:15]):  # Limitar a 15
                        try:
                            texto = elemento.text.strip()
                            if texto and len(texto) > 15:  # Filtrar textos muito curtos
                                partes.append({
                                    'indice': i + 1,
                                    'texto': texto,
                                    'estrategia': estrategia
                                })
                        except:
                            continue
                    if partes:  # Se encontrou partes, parar
                        break
            except:
                continue
        
        # Se não encontrou nada, tentar com BeautifulSoup
        if not partes:
            logger.info("🔍 Nenhuma parte encontrada com Selenium, tentando com BeautifulSoup...")
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Procurar por tabelas
            tabelas = soup.find_all('table')
            for i, tabela in enumerate(tabelas):
                linhas = tabela.find_all('tr')
                for j, linha in enumerate(linhas):
                    texto = linha.get_text(strip=True)
                    if texto and len(texto) > 20:
                        if any(palavra in texto.lower() for palavra in ['parte', 'autor', 'réu', 'advogado', 'envolvido']):
                            partes.append({
                                'indice': len(partes) + 1,
                                'texto': texto,
                                'tabela': i + 1,
                                'linha': j + 1
                            })
        
        resultado = {
            'partes': partes,
            'movimentacoes': [],
            'total_partes': len(partes),
            'total_movimentacoes': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"📋 Partes do processo coletadas: {len(partes)} partes")
        
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Erro ao coletar partes do processo: {e}")
        return {
            'partes': [],
            'movimentacoes': [],
            'total_partes': 0,
            'total_movimentacoes': 0,
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }

def fechar_aba_confirmacao_solicitar_acesso(session):
    """Fecha aba de confirmação de solicitar acesso se existir"""
    try:
        handles = session['driver'].window_handles
        abas_fechadas = 0
        
        for handle in handles:
            session['driver'].switch_to.window(handle)
            url = session['driver'].current_url
            title = session['driver'].title
            
            # Verificar se é aba de confirmação
            if "confirmacao" in url.lower() or "popup" in url.lower() or "confirm" in url.lower():
                session['driver'].close()
                abas_fechadas += 1
                logger.info(f"🚫 Aba de confirmação fechada: {url}")
        
        # Voltar para a primeira aba disponível
        if session['driver'].window_handles:
            session['driver'].switch_to.window(session['driver'].window_handles[0])
        
        logger.info(f"✅ {abas_fechadas} abas de confirmação fechadas")
        return abas_fechadas
        
    except Exception as e:
        logger.error(f"Erro ao fechar abas de confirmação: {e}")
        return 0

def fechar_abas_descartar_pendencia(session):
    """Fecha todas as abas que contenham DescartarPendenciaProcesso"""
    try:
        handles = session['driver'].window_handles
        abas_fechadas = 0
        
        for handle in handles:
            session['driver'].switch_to.window(handle)
            url = session['driver'].current_url
            
            if "DescartarPendenciaProcesso" in url:
                session['driver'].close()
                abas_fechadas += 1
                logger.info(f"🚫 Aba DescartarPendenciaProcesso fechada: {url}")
        
        # Voltar para a primeira aba disponível
        if session['driver'].window_handles:
            session['driver'].switch_to.window(session['driver'].window_handles[0])
        
        logger.info(f"✅ {abas_fechadas} abas DescartarPendenciaProcesso fechadas")
        return abas_fechadas
        
    except Exception as e:
        logger.error(f"Erro ao fechar abas DescartarPendenciaProcesso: {e}")
        return 0

def tentar_baixar_pdf(session, nome_arquivo, id_arquivo=None):
    """Tenta baixar o PDF abrindo em nova aba com Cmd+Click no link"""
    try:
        logger.info(f"  📥 Tentando baixar PDF em nova aba: {nome_arquivo}")
        
        # Guardar a aba atual
        aba_atual = session['driver'].current_window_handle
        logger.info(f"  📋 Aba atual: {aba_atual}")
        
        # Procurar o link do PDF pelo ID se fornecido
        link_pdf = None
        if id_arquivo:
            try:
                # Procurar por link que contenha o ID
                xpath_id = f"//a[contains(@href, 'Id_MovimentacaoArquivo={id_arquivo}')]"
                link_pdf = session['driver'].find_element(By.XPATH, xpath_id)
                logger.info(f"  📥 Encontrou link do PDF com ID: {id_arquivo}")
            except:
                # Se não encontrar pelo XPath, procurar por todos os links
                links = session['driver'].find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if href and f'Id_MovimentacaoArquivo={id_arquivo}' in href:
                            link_pdf = link
                            logger.info(f"  📥 Encontrou link do PDF com ID: {id_arquivo}")
                            break
                    except:
                        continue
        
        # Se não encontrou pelo ID, procurar pelo nome do arquivo
        if not link_pdf:
            elementos = session['driver'].find_elements(By.XPATH, f"//*[contains(text(), '{nome_arquivo}')]")
            for elemento in elementos:
                if elemento.is_enabled() and elemento.is_displayed():
                    link_pdf = elemento
                    logger.info(f"  📥 Encontrou elemento com nome do arquivo: {nome_arquivo}")
                    break
        
        if link_pdf:
            # Obter a URL do link
            try:
                href = link_pdf.get_attribute('href')
                if href:
                    logger.info(f"  📥 Encontrou URL do PDF: {href}")
                    
                    # Fazer request direto para obter a URL final do S3
                    try:
                        import requests
                        
                        # Obter cookies da sessão do Selenium
                        cookies = session['driver'].get_cookies()
                        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                        
                        # Fazer request com cookies da sessão
                        response = requests.get(href, cookies=cookie_dict, allow_redirects=True, timeout=10)
                        url_final = response.url
                        logger.info(f"  📄 URL final do S3: {url_final}")
                        
                        # Baixar o PDF diretamente
                        if 's3.tjgo.jus.br' in url_final:
                            # Extrair nome do arquivo da URL
                            nome_arquivo_limpo = nome_arquivo.replace('.pdf', '')
                            nome_arquivo_final = f"{nome_arquivo_limpo}_{int(time.time())}.pdf"
                            
                            # Fazer download direto com cookies
                            pdf_response = requests.get(url_final, cookies=cookie_dict, timeout=30)
                            if pdf_response.status_code == 200:
                                with open(nome_arquivo_final, 'wb') as f:
                                    f.write(pdf_response.content)
                                logger.info(f"  ✅ PDF baixado diretamente: {nome_arquivo_final}")
                                return True
                            else:
                                logger.error(f"  ❌ Erro ao baixar PDF: Status {pdf_response.status_code}")
                                return False
                        else:
                            logger.error(f"  ❌ URL não é do S3: {url_final}")
                            return False
                            
                    except Exception as e:
                        logger.error(f"  ❌ Erro ao fazer request direto: {e}")
                        return False
                else:
                    logger.error(f"  ❌ Link não tem href")
                    return False
            except Exception as e:
                logger.error(f"  ❌ Erro ao obter href do link: {e}")
                return False
        else:
            logger.error(f"  ❌ Link do PDF não encontrado")
            return False
        
    except Exception as e:
        logger.error(f"  ❌ Erro ao tentar baixar PDF em nova aba: {e}")
        return False

def tentar_baixar_pdf_direto(session, nome_arquivo):
    """Tenta baixar o PDF abrindo em nova aba e usando comando de teclado"""
    try:
        logger.info(f"  📥 Tentando baixar PDF em nova aba: {nome_arquivo}")
        
        # Procurar por elementos que contenham o nome do arquivo (pode ser link ou texto clicável)
        elementos = session['driver'].find_elements(By.XPATH, f"//*[contains(text(), '{nome_arquivo}')]")
        
        if not elementos:
            # Se não encontrar, procurar por links que contenham o nome
            elementos = session['driver'].find_elements(By.TAG_NAME, "a")
        
        for elemento in elementos:
            try:
                texto_elemento = elemento.text.strip()
                
                # Verificar se o elemento contém o nome do arquivo
                if nome_arquivo.lower() in texto_elemento.lower():
                    logger.info(f"  📥 Encontrou elemento com nome do arquivo: {texto_elemento}")
                    
                    # Verificar se é clicável
                    if elemento.is_enabled() and elemento.is_displayed():
                        logger.info(f"  ✅ Elemento é clicável")
                    
                    # Guardar a aba atual
                    aba_atual = session['driver'].current_window_handle
                    logger.info(f"  📋 Aba atual: {aba_atual}")
                    
                    # Abrir elemento em nova aba (Cmd+Click ou Ctrl+Click)
                    actions = ActionChains(session['driver'])
                    
                    # Tentar Cmd+Click (macOS) primeiro
                    try:
                        actions.key_down(Keys.COMMAND).click(elemento).key_up(Keys.COMMAND).perform()
                        logger.info(f"  🌐 Abrindo PDF em nova aba com Cmd+Click...")
                    except:
                        # Se não funcionar, tentar Ctrl+Click (Windows/Linux)
                        try:
                            actions.key_down(Keys.CONTROL).click(elemento).key_up(Keys.CONTROL).perform()
                            logger.info(f"  🌐 Abrindo PDF em nova aba com Ctrl+Click...")
                        except Exception as e:
                            logger.error(f"  ❌ Erro ao abrir nova aba: {e}")
                            continue
                    
                    # Aguardar nova aba abrir
                    time.sleep(3)
                    
                    # Obter todas as abas
                    todas_abas = session['driver'].window_handles
                    logger.info(f"  📋 Total de abas: {len(todas_abas)}")
                    
                    # Encontrar a nova aba
                    nova_aba = None
                    for aba in todas_abas:
                        if aba != aba_atual:
                            nova_aba = aba
                            break
                    
                    if nova_aba:
                        logger.info(f"  🔄 Mudando para nova aba: {nova_aba}")
                        session['driver'].switch_to.window(nova_aba)
                        
                        # Aguardar carregamento da página
                        time.sleep(5)
                        
                        # Verificar se é realmente um PDF
                        url_atual = session['driver'].current_url
                        logger.info(f"  📄 URL da nova aba: {url_atual}")
                        
                        # Tentar baixar com Cmd+S
                        try:
                            body = session['driver'].find_element(By.TAG_NAME, "body")
                            actions = ActionChains(session['driver'])
                            actions.click(body).perform()
                            time.sleep(1)
                            
                            # Tentar Cmd+S (macOS) primeiro
                            try:
                                actions.key_down(Keys.COMMAND).send_keys('s').key_up(Keys.COMMAND).perform()
                                logger.info(f"  📥 Download iniciado com Cmd+S para: {nome_arquivo}")
                                time.sleep(3)
                                download_realizado = True
                            except:
                                # Se não funcionar, tentar Ctrl+S (Windows/Linux)
                                try:
                                    actions.key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
                                    logger.info(f"  📥 Download iniciado com Ctrl+S para: {nome_arquivo}")
                                    time.sleep(3)
                                    download_realizado = True
                                except Exception as e:
                                    logger.error(f"  ❌ Erro com Ctrl+S: {e}")
                                    download_realizado = False
                            
                            # Aguardar download
                            if download_realizado:
                                time.sleep(5)
                                logger.info(f"  ✅ Download realizado com sucesso para: {nome_arquivo}")
                            
                        except Exception as e:
                            logger.error(f"  ❌ Erro ao tentar download na nova aba: {e}")
                            download_realizado = False
                        
                        # Fechar a aba do PDF
                        logger.info(f"  🔒 Fechando aba do PDF...")
                        session['driver'].close()
                        
                        # Voltar para a aba original
                        session['driver'].switch_to.window(aba_atual)
                        logger.info(f"  🔄 Voltando para aba original: {aba_atual}")
                        
                        return download_realizado
                    else:
                        logger.error(f"  ❌ Nova aba não encontrada")
                        continue
                    
            except Exception as e:
                logger.error(f"  ❌ Erro ao processar link: {e}")
                continue
        
        logger.info(f"  ⚠️ Nenhum link encontrado para abrir em nova aba: {nome_arquivo}")
        return False
        
    except Exception as e:
        logger.error(f"  ❌ Erro ao tentar baixar PDF em nova aba: {e}")
        return False

def extrair_texto_do_iframe(session):
    """Extrai texto do iframe onde o conteúdo do anexo está"""
    try:
        # Aguardar carregamento
        time.sleep(5)
        
        # Mudar para o iframe onde o conteúdo do anexo está
        iframe = session['driver'].find_element(By.ID, "arquivo")
        session['driver'].switch_to.frame(iframe)
        
        # Aguardar carregamento do conteúdo do iframe
        time.sleep(3)
        
        # Extrair o HTML do iframe
        html_content = session['driver'].page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Verificar se é um PDF (procurar por elementos típicos)
        is_pdf = False
        if "pdf" in html_content.lower() or "application/pdf" in html_content.lower():
            is_pdf = True
            logger.info(f"  📄 PDF detectado no iframe")
        
        # Remover scripts e styles
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extrair todo o texto
        texto_completo = soup.get_text()
        
        # Limpar o texto
        texto_limpo = re.sub(r'\s+', ' ', texto_completo).strip()
        
        # Voltar para o contexto principal
        session['driver'].switch_to.default_content()
        
        # Pegar os primeiros 10000 caracteres se for muito longo
        if len(texto_limpo) > 10000:
            texto_limpo = texto_limpo[:10000] + "..."
        
        return texto_limpo, html_content, is_pdf
        
    except Exception as e:
        logger.error(f"Erro ao extrair texto do iframe: {e}")
        # Voltar para o contexto principal em caso de erro
        try:
            session['driver'].switch_to.default_content()
        except:
            pass
        return "Erro na extração do texto do iframe", "", False

def forcar_atualizacao_iframe(session):
    """Força a atualização do iframe usando múltiplas estratégias"""
    try:
        # Estratégia 1: Limpar o src do iframe e recarregar
        js_limpar_iframe = """
        var iframe = document.getElementById('arquivo');
        if (iframe) {
            iframe.src = '';
            iframe.src = './paginaInicialNavegacaoArquivos.html';
            return 'Iframe limpo e recarregado';
        }
        return 'Iframe não encontrado';
        """
        resultado1 = session['driver'].execute_script(js_limpar_iframe)
        logger.info(f"  🔄 {resultado1}")
        time.sleep(2)
        
        # Estratégia 2: Remover e recriar o iframe
        js_recriar_iframe = """
        var iframe = document.getElementById('arquivo');
        if (iframe) {
            var parent = iframe.parentNode;
            var newIframe = document.createElement('iframe');
            newIframe.id = 'arquivo';
            newIframe.name = 'arquivo';
            newIframe.width = '100%';
            newIframe.height = '100%';
            newIframe.frameborder = '0';
            newIframe.scrolling = 'auto';
            newIframe.src = './paginaInicialNavegacaoArquivos.html';
            parent.replaceChild(newIframe, iframe);
            return 'Iframe recriado';
        }
        return 'Iframe não encontrado para recriar';
        """
        resultado2 = session['driver'].execute_script(js_recriar_iframe)
        logger.info(f"  🔄 {resultado2}")
        time.sleep(2)
        
        # Estratégia 3: Forçar reload do iframe via JavaScript
        js_reload_iframe = """
        var iframe = document.getElementById('arquivo');
        if (iframe) {
            iframe.contentWindow.location.reload(true);
            return 'Iframe reloadado via contentWindow';
        }
        return 'Iframe não encontrado para reload';
        """
        resultado3 = session['driver'].execute_script(js_reload_iframe)
        logger.info(f"  🔄 {resultado3}")
        time.sleep(2)
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro ao forçar atualização do iframe: {e}")
        return False

def clicar_nome_arquivo_com_estrategias(session, nome_arquivo):
    """Clica no nome do arquivo usando múltiplas estratégias"""
    try:
        # Estratégia 1: Clique direto por XPath
        try:
            link_anexo = session['driver'].find_element(By.XPATH, f"//a[contains(text(), '{nome_arquivo}')]")
            if link_anexo.is_enabled() and link_anexo.is_displayed():
                link_anexo.click()
                logger.info(f"  ✅ Clique direto funcionou: {nome_arquivo}")
                return True
        except Exception as e:
            logger.info(f"  ⚠️ Clique direto falhou: {e}")
        
        # Estratégia 2: JavaScript com múltiplas tentativas
        js_cliques = [
            # Tentativa 1: Clique simples
            f"""
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {{
                if (links[i].textContent && links[i].textContent.includes('{nome_arquivo}')) {{
                    links[i].click();
                    return 'Clique JavaScript simples';
                }}
            }}
            return 'Link não encontrado';
            """,
            
            # Tentativa 2: Clique com dispatch de evento
            f"""
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {{
                if (links[i].textContent && links[i].textContent.includes('{nome_arquivo}')) {{
                    var event = new MouseEvent('click', {{
                        view: window,
                        bubbles: true,
                        cancelable: true
                    }});
                    links[i].dispatchEvent(event);
                    return 'Clique com dispatch de evento';
                }}
            }}
            return 'Link não encontrado para dispatch';
            """,
            
            # Tentativa 3: Clique via href direto
            f"""
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {{
                if (links[i].textContent && links[i].textContent.includes('{nome_arquivo}')) {{
                    var href = links[i].getAttribute('href');
                    if (href) {{
                        window.location.href = href;
                        return 'Navegação direta via href';
                    }}
                }}
            }}
            return 'Href não encontrado';
            """
        ]
        
        for i, js_script in enumerate(js_cliques, 1):
            try:
                resultado = session['driver'].execute_script(js_script)
                logger.info(f"  ✅ Tentativa {i}: {resultado}")
                if "não encontrado" not in resultado and "falhou" not in resultado:
                    return True
            except Exception as e:
                logger.info(f"  ⚠️ Tentativa {i} falhou: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"  ❌ Erro geral ao clicar no arquivo {nome_arquivo}: {e}")
        return False

def extrair_anexos_das_ultimas_movimentacoes(session, num_movimentacoes=5):
    """Extrai anexos das últimas X movimentações, identificando corretamente cada link"""
    try:
        logger.info(f"📁 PASSO 7: Trabalhando com anexos na aba de navegação...")
        
        # Aguardar carregamento da página
        time.sleep(3)
        
        # Identificar a aba de navegação
        abas = session['driver'].window_handles
        aba_navegacao = None
        
        for i, aba in enumerate(abas, 1):
            session['driver'].switch_to.window(aba)
            url_atual = session['driver'].current_url
            titulo = session['driver'].title
            
            logger.info(f"Aba {i}: {url_atual} | Título: {titulo}")
            
            if "BuscaProcesso?PaginaAtual=9&PassoBusca=4" in url_atual:
                aba_navegacao = aba
                logger.info(f"✅ Aba de navegação identificada: Aba {i}")
                break
        
        if not aba_navegacao:
            logger.error("❌ Aba de navegação não encontrada")
            return []
        
        # Garantir que estamos na aba de navegação
        session['driver'].switch_to.window(aba_navegacao)
        
        # Aguardar carregamento da página
        time.sleep(3)
        
        # Procurar por movimentações na página
        movimentacoes_encontradas = []
        
        # Estratégia 1: Procurar por elementos que podem conter movimentações
        elementos_movimentacao = session['driver'].find_elements(By.XPATH, "//tr[contains(@class, 'linha') or contains(@class, 'movimentacao')]")
        
        for elemento in elementos_movimentacao:
            try:
                # Procurar por links de anexos dentro da movimentação
                links_anexos = elemento.find_elements(By.TAG_NAME, "a")
                
                for link in links_anexos:
                    try:
                        href = link.get_attribute('href')
                        texto = link.text.strip()
                        
                        if href and 'Id_MovimentacaoArquivo=' in href and texto:
                            # Extrair ID da movimentação do href
                            id_arquivo = href.split('Id_MovimentacaoArquivo=')[-1].split('&')[0]
                            
                            # Procurar pela data da movimentação (pode estar em células próximas)
                            data_movimentacao = ""
                            try:
                                # Procurar por data na mesma linha ou linha anterior
                                linha_pai = link.find_element(By.XPATH, "./..")
                                texto_linha = linha_pai.text
                                # Extrair data (formato DD/MM/AAAA)
                                import re
                                datas = re.findall(r'\d{2}/\d{2}/\d{4}', texto_linha)
                                if datas:
                                    data_movimentacao = datas[0]
                            except:
                                pass
                            
                            movimentacoes_encontradas.append({
                                'texto': texto,
                                'href': href,
                                'id_arquivo': id_arquivo,
                                'data_movimentacao': data_movimentacao,
                                'elemento': link
                            })
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
        
        # Estratégia 2: Se não encontrou nada, procurar por todos os links da página
        if not movimentacoes_encontradas:
            logger.info(f"  🔍 Estratégia 1 não encontrou anexos, tentando estratégia 2...")
            links_anexos = session['driver'].find_elements(By.TAG_NAME, "a")
            
            for link in links_anexos:
                try:
                    href = link.get_attribute('href')
                    texto = link.text.strip()
                    
                    if href and 'Id_MovimentacaoArquivo=' in href and texto:
                        # Extrair ID da movimentação do href
                        id_arquivo = href.split('Id_MovimentacaoArquivo=')[-1].split('&')[0]
                        
                        movimentacoes_encontradas.append({
                            'texto': texto,
                            'href': href,
                            'id_arquivo': id_arquivo,
                            'data_movimentacao': "",
                            'elemento': link
                        })
                except Exception as e:
                    continue
        
        # Estratégia 3: Se ainda não encontrou, usar BeautifulSoup para extrair
        if not movimentacoes_encontradas:
            logger.info(f"  🔍 Estratégia 2 não encontrou anexos, tentando estratégia 3...")
            html_content = session['driver'].page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                texto = link.get_text(strip=True)
                
                if 'Id_MovimentacaoArquivo=' in href and texto:
                    id_arquivo = href.split('Id_MovimentacaoArquivo=')[-1].split('&')[0]
                    
                    movimentacoes_encontradas.append({
                        'texto': texto,
                        'href': href,
                        'id_arquivo': id_arquivo,
                        'data_movimentacao': "",
                        'elemento': None
                    })
        
        logger.info(f"📋 Total de anexos encontrados: {len(movimentacoes_encontradas)}")
        
        # Pegar as últimas X movimentações (mais recentes primeiro)
        ultimas_movimentacoes = movimentacoes_encontradas[-num_movimentacoes:] if len(movimentacoes_encontradas) >= num_movimentacoes else movimentacoes_encontradas
        ultimas_movimentacoes = list(reversed(ultimas_movimentacoes))  # Inverter para mais recentes primeiro
        
        logger.info(f"🎯 Processando as últimas {len(ultimas_movimentacoes)} movimentações")
        
        anexos_extraidos = []
        
        for i, movimentacao_info in enumerate(ultimas_movimentacoes, 1):
            logger.info(f"🔍 Processando anexo {i}/{len(ultimas_movimentacoes)}: {movimentacao_info['texto']} (ID: {movimentacao_info['id_arquivo']})")
            
            try:
                # Garantir que estamos na aba de navegação
                session['driver'].switch_to.window(aba_navegacao)
                
                # REFRESH: Recarregar a página antes de cada anexo para evitar conteúdo fantasma
                logger.info(f"  🔄 Fazendo refresh da página antes do anexo {i}...")
                session['driver'].refresh()
                time.sleep(3)
                
                # Se não estiver na URL correta, navegar para ela
                if "BuscaProcesso?PaginaAtual=9&PassoBusca=4" not in session['driver'].current_url:
                    session['driver'].get("https://projudi.tjgo.jus.br/BuscaProcesso?PaginaAtual=9&PassoBusca=4")
                    time.sleep(3)
                
                # Aguardar carregamento da página
                time.sleep(2)
                
                # FORÇAR ATUALIZAÇÃO DO IFRAME antes do clique
                logger.info(f"  🔄 Forçando atualização do iframe para anexo {i}...")
                forcar_atualizacao_iframe(session)
                
                # Clicar no link específico usando o ID único
                if clicar_link_por_id(session, movimentacao_info['id_arquivo']):
                    # Aguardar carregamento
                    time.sleep(5)
                    
                    # Extrair texto do iframe
                    texto_extraido, html_content, is_pdf = extrair_texto_do_iframe(session)
                    
                    # Gerar timestamp para referência
                    timestamp = int(time.time())
                    
                    # Se for PDF, tentar baixar
                    download_realizado = False
                    if is_pdf or movimentacao_info['texto'].lower().endswith('.pdf'):
                        logger.info(f"  📄 Tentando baixar PDF...")
                        download_realizado = tentar_baixar_pdf(session, movimentacao_info['texto'], movimentacao_info['id_arquivo'])
                        if download_realizado:
                            logger.info(f"  📥 Download do PDF iniciado!")
                        else:
                            logger.info(f"  ⚠️ Não foi possível baixar o PDF")
                    
                    anexo_extraido = {
                        'index': i,
                        'nome_arquivo': movimentacao_info['texto'],
                        'id_arquivo': movimentacao_info['id_arquivo'],
                        'data_movimentacao': movimentacao_info['data_movimentacao'],
                        'texto_extraido': texto_extraido,
                        'tamanho_texto': len(texto_extraido),
                        'html_content': html_content,
                        'timestamp': timestamp,
                        'is_pdf': is_pdf,
                        'download_realizado': download_realizado
                    }
                    
                    anexos_extraidos.append(anexo_extraido)
                    
                    logger.info(f"  ✅ Anexo extraído: {len(texto_extraido)} caracteres")
                    if is_pdf:
                        logger.info(f"  📄 Tipo: PDF (download tentado: {'Sim' if download_realizado else 'Não'})")
                    else:
                        logger.info(f"  📄 Tipo: HTML")
                else:
                    logger.error(f"  ❌ Não foi possível clicar no anexo: {movimentacao_info['texto']}")
                
            except Exception as e:
                logger.error(f"  ❌ Erro ao processar anexo {movimentacao_info['texto']}: {e}")
        
        return anexos_extraidos
        
    except Exception as e:
        logger.error(f"❌ Erro ao extrair anexos das movimentações: {e}")
        return []

def clicar_link_por_id(session, id_arquivo):
    """Clica no link específico usando o ID único do arquivo"""
    try:
        # Estratégia 1: Procurar pelo link que contém o ID específico no href
        xpath_id = f"//a[contains(@href, 'Id_MovimentacaoArquivo={id_arquivo}')]"
        
        try:
            link = session['driver'].find_element(By.XPATH, xpath_id)
            if link.is_enabled() and link.is_displayed():
                link.click()
                logger.info(f"  ✅ Clique direto no link com ID {id_arquivo} funcionou")
                return True
            else:
                # Tentar com JavaScript
                session['driver'].execute_script("arguments[0].click();", link)
                logger.info(f"  ✅ Clique JavaScript no link com ID {id_arquivo} funcionou")
                return True
        except Exception as e:
            logger.info(f"  ⚠️ Estratégia 1 falhou: {e}")
        
        # Estratégia 2: Procurar por todos os links e encontrar o que tem o ID correto
        links = session['driver'].find_elements(By.TAG_NAME, "a")
        
        for link in links:
            try:
                href = link.get_attribute('href')
                if href and f'Id_MovimentacaoArquivo={id_arquivo}' in href:
                    if link.is_enabled() and link.is_displayed():
                        link.click()
                        logger.info(f"  ✅ Clique direto no link encontrado com ID {id_arquivo}")
                        return True
                    else:
                        session['driver'].execute_script("arguments[0].click();", link)
                        logger.info(f"  ✅ Clique JavaScript no link encontrado com ID {id_arquivo}")
                        return True
            except Exception as e:
                continue
        
        # Estratégia 3: Usar JavaScript para encontrar e clicar no link
        js_script = f"""
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {{
            var href = links[i].getAttribute('href');
            if (href && href.includes('Id_MovimentacaoArquivo={id_arquivo}')) {{
                links[i].click();
                return 'Link encontrado e clicado via JavaScript';
            }}
        }}
        return 'Link não encontrado';
        """
        
        resultado = session['driver'].execute_script(js_script)
        if "Link encontrado" in resultado:
            logger.info(f"  ✅ {resultado} para ID {id_arquivo}")
            return True
        
        logger.error(f"  ❌ Nenhuma estratégia funcionou para o ID {id_arquivo}")
        return False
            
    except Exception as e:
        logger.error(f"  ❌ Erro ao clicar no link com ID {id_arquivo}: {e}")
        return False

def clicar_link_especifico(session, href):
    """Clica no link específico usando o href"""
    try:
        # Procurar pelo link com o href específico
        link = session['driver'].find_element(By.XPATH, f"//a[@href='{href}']")
        
        if link.is_enabled() and link.is_displayed():
            link.click()
            logger.info(f"  ✅ Clique direto no link específico funcionou")
            return True
        else:
            # Tentar com JavaScript
            session['driver'].execute_script("arguments[0].click();", link)
            logger.info(f"  ✅ Clique JavaScript no link específico funcionou")
            return True
            
    except Exception as e:
        logger.error(f"  ❌ Erro ao clicar no link específico: {e}")
        return False

def extrair_anexos_iframe_correto():
    """Extrai anexos acessando o conteúdo do iframe"""
    api = ProjudiAPI()
    
    try:
        # Obter sessão
        session = api.session_pool.get_session()
        logger.info("Sessão obtida com sucesso")
        
        # Fazer login
        if api.fazer_login(session):
            logger.info("Login realizado com sucesso")
            
            # Buscar processo
            if api.buscar_por_processo(session, "5466798-41.2019.8.09.0051"):
                logger.info("Processo encontrado")
                
                # Obter lista de processos
                processos = api.obter_lista_processos(session)
                if processos:
                    processo_info = processos[0]
                    logger.info(f"Processo obtido: {processo_info}")
                    
                    # Verificar se já estamos na página do processo
                    if "corpo_dados_processo" in session['driver'].page_source:
                        logger.info("Já estamos na página do processo, pulando acessar_processo")
                    else:
                        # Acessar processo
                        if not api.acessar_processo(session, processo_info):
                            logger.error("Falha ao acessar processo")
                            return
                    
                    logger.info("Processo acessado com sucesso")
                    
                    # PASSO 1: Iniciando extração de anexos
                    logger.info("🔓 PASSO 1: Iniciando extração de anexos...")
                    
                    # PASSO 2: Navegando diretamente para a página de navegação de arquivos
                    logger.info("📁 PASSO 2: Navegando para a página de navegação de arquivos...")
                    
                    # PASSO 3: Navegar para a página de navegação de arquivos
                    session['driver'].get("https://projudi.tjgo.jus.br/BuscaProcesso?PaginaAtual=9&PassoBusca=4")
                    time.sleep(3)
                    
                    # Aguardar carregamento da página
                    logger.info("⏳ Aguardando carregamento da página de navegação...")
                    time.sleep(5)
                    
                    # PASSO 3: Extrair anexos das últimas movimentações (tudo na mesma aba)
                    logger.info("📁 PASSO 3: Extraindo anexos das últimas movimentações...")
                    
                    # Extrair anexos das últimas 3 movimentações
                    anexos_extraidos = extrair_anexos_das_ultimas_movimentacoes(session, num_movimentacoes=3)
                    
                    # Preparar resultado final
                    resultado_final = {
                        'processo': '5466798-41.2019.8.09.0051',
                        'total_anexos_processados': len(anexos_extraidos),
                        'anexos': anexos_extraidos,
                        'timestamp_extração': int(time.time())
                    }
                    
                    # Salvar resultado para debug (opcional)
                    with open('resultado_extração.json', 'w', encoding='utf-8') as f:
                        json.dump(resultado_final, f, indent=2, ensure_ascii=False)
                    
                    logger.info("💾 Resultado salvo em: resultado_extração.json")
                    
                    # Mostrar resumo
                    logger.info("📊 RESUMO DA EXTRAÇÃO:")
                    for anexo in anexos_extraidos:
                        logger.info(f"  📋 Anexo {anexo['index']}: {anexo['nome_arquivo']}")
                        logger.info(f"     📝 {anexo['tamanho_texto']} caracteres extraídos")
                        if anexo.get('data_movimentacao'):
                            logger.info(f"     📅 Data: {anexo['data_movimentacao']}")
                        if anexo.get('is_pdf'):
                            logger.info(f"     📄 PDF baixado: {'Sim' if anexo.get('download_realizado') else 'Não'}")
                    
                    logger.info("🎯 EXTRAÇÃO COMPLETA! Dados prontos para retorno HTTP.")
                else:
                    logger.error("Nenhum processo encontrado na lista")
            else:
                logger.error("Processo não encontrado")
        else:
            logger.error("Falha no login")
            
    except Exception as e:
        logger.error(f"Erro geral: {e}")
    finally:
        logger.info("🔚 Finalizando...")
        # Liberar a sessão
        api.session_pool.release_session(session)

if __name__ == "__main__":
    extrair_anexos_iframe_correto() 