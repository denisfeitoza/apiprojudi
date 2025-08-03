#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import logging
import re
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import requests
from projudi_api import ProjudiAPI
from session_pool import SessionPool

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProjudiAnexosAvancado(ProjudiAPI):
    """
    Classe avançada para extração de anexos do PROJUDI
    Integra funcionalidades do extrair_anexos_iframe_correto.py com projudi_api.py
    """
    
    def __init__(self):
        super().__init__()
        logger.info("🚀 Inicializando ProjudiAnexosAvancado")
        
        # Lista para armazenar PDFs baixados para processamento posterior
        self.pdfs_baixados = {}
        
        # Lista para rastrear arquivos temporários para limpeza
        self.arquivos_temporarios = []
    
    def _limpar_arquivos_temporarios(self):
        """Remove arquivos temporários criados durante a execução"""
        try:
            # Remover arquivo de debug se existir
            if os.path.exists('debug_pagina.html'):
                os.remove('debug_pagina.html')
                logger.info("🧹 Arquivo debug_pagina.html removido")
            
            # Remover arquivo de debug das partes se existir
            if os.path.exists('debug_partes.html'):
                os.remove('debug_partes.html')
                logger.info("🧹 Arquivo debug_partes.html removido")
            
            # Remover arquivo de debug da página 6 se existir
            if os.path.exists('debug_partes_pagina6.html'):
                os.remove('debug_partes_pagina6.html')
                logger.info("🧹 Arquivo debug_partes_pagina6.html removido")
            
            # Remover PDFs temporários se configurado
            for pdf_info in self.pdfs_baixados.values():
                caminho_pdf = pdf_info.get('caminho_pdf')
                if caminho_pdf and os.path.exists(caminho_pdf):
                    os.remove(caminho_pdf)
                    logger.info(f"🧹 PDF temporário removido: {os.path.basename(caminho_pdf)}")
            
            # Remover arquivos temporários de imagem do OCR
            for arquivo in os.listdir('.'):
                if arquivo.startswith('temp_page_') and arquivo.endswith('.png'):
                    try:
                        os.remove(arquivo)
                        logger.info(f"🧹 Arquivo temporário OCR removido: {arquivo}")
                    except:
                        pass
            
            logger.info("✅ Limpeza de arquivos temporários concluída")
            
        except Exception as e:
            logger.error(f"❌ Erro na limpeza de arquivos temporários: {e}")
    
    def _solicitar_acesso_processo_seguro(self, session):
        """Solicita acesso aos anexos usando JavaScript de forma segura"""
        try:
            logger.info("🔓 Solicitando acesso aos anexos com JavaScript...")
            
            # Script 1: Tentar clicar no menu "Outras"
            try:
                script_outras = """
                var menuOutras = document.querySelector('a[href*="Outras"]');
                if (menuOutras) {
                    menuOutras.click();
                    return true;
                }
                return false;
                """
                resultado = session['driver'].execute_script(script_outras)
                if resultado:
                    logger.info("✅ Menu 'Outras' clicado com script 1")
                    time.sleep(1)  # Reduzido de 2 para 1 segundo
                else:
                    raise Exception("Menu Outras não encontrado")
            except Exception as e:
                logger.warning(f"⚠️ Script 1 falhou: {e}")
                
                # Script 2: Tentar clicar diretamente em "Solicitar Acesso"
                try:
                    script_solicitar = """
                    var links = document.querySelectorAll('a');
                    for (var i = 0; i < links.length; i++) {
                        if (links[i].textContent.includes('Solicitar Acesso')) {
                            links[i].click();
                            return true;
                        }
                    }
                    return false;
                    """
                    resultado = session['driver'].execute_script(script_solicitar)
                    if resultado:
                        logger.info("✅ 'Solicitar Acesso' clicado com script 2")
                        time.sleep(1)  # Reduzido de 2 para 1 segundo
                    else:
                        raise Exception("Solicitar Acesso não encontrado")
                except Exception as e:
                    logger.warning(f"⚠️ Script 2 falhou: {e}")
                    
                    # Script 3: Tentar por ID ou classe específica
                    try:
                        script_alternativo = """
                        var elementos = document.querySelectorAll('[id*="solicitar"], [class*="solicitar"], [onclick*="solicitar"]');
                        for (var i = 0; i < elementos.length; i++) {
                            if (elementos[i].textContent.toLowerCase().includes('solicitar')) {
                                elementos[i].click();
                                return true;
                            }
                        }
                        return false;
                        """
                        resultado = session['driver'].execute_script(script_alternativo)
                        if resultado:
                            logger.info("✅ Menu 'Outras' clicado com script 3")
                            time.sleep(1)  # Reduzido de 2 para 1 segundo
                        else:
                            raise Exception("Nenhum elemento encontrado")
                    except Exception as e:
                        logger.warning(f"⚠️ Script 3 falhou: {e}")
                        return False
            
            # Aguardar popup de confirmação (se houver)
            time.sleep(1)  # Reduzido de 3 para 1 segundo
            
            # Verificar se apareceu popup de confirmação
            try:
                popup = session['driver'].find_element(By.ID, "popup")
                if popup.is_displayed():
                    # Clicar em confirmar se houver botão
                    try:
                        botao_confirmar = popup.find_element(By.XPATH, "//input[@value='Confirmar']")
                        botao_confirmar.click()
                        logger.info("✅ Popup de confirmação confirmado")
                        time.sleep(1)  # Reduzido de 2 para 1 segundo
                    except:
                        logger.info("ℹ️ Popup encontrado mas sem botão de confirmação")
            except:
                logger.info("ℹ️ Nenhum popup de confirmação encontrado")
            
            logger.info("✅ Acesso aos anexos solicitado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao solicitar acesso aos anexos: {e}")
            return False
    
    def extrair_anexos_ultimas_movimentacoes(self, session, processo_info, num_movimentacoes=5):
        """
        Extrai anexos das últimas X movimentações seguindo a estratégia do extrair_anexos_iframe_correto.py
        """
        try:
            logger.info(f"📁 Extraindo anexos das últimas {num_movimentacoes} movimentações...")
            
            # Aguardar carregamento da página
            time.sleep(3)
            
            # Procurar por movimentações na página de navegação
            movimentacoes_encontradas = []
            
            # Estratégia 1: Procurar por elementos que podem conter movimentações
            elementos_movimentacao = session['driver'].find_elements(By.XPATH, "//tr[contains(@class, 'linha') or contains(@class, 'movimentacao')]")
            
            # Dicionário para agrupar anexos por movimentação
            movimentacoes_agrupadas = {}
            
            # Se não encontrou elementos específicos, usar BeautifulSoup para extrair
            if not elementos_movimentacao:
                logger.info(f"  🔍 Usando BeautifulSoup para extrair movimentações...")
                html_content = session['driver'].page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Debug: Salvar HTML para análise
                with open('debug_pagina.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"  📄 HTML da página salvo em debug_pagina.html")
                
                # Procurar pela estrutura de movimentações (ul com li que contém <b> número)
                menu_navegacao = soup.find('div', {'id': 'menuNavegacao'})
                if menu_navegacao:
                    # Procurar por todas as movimentações (li com <b> número)
                    movimentacoes_li = menu_navegacao.find_all('li')
                    
                    for li in movimentacoes_li:
                        # Procurar por <b> que contém o número da movimentação
                        b_tag = li.find('b')
                        if b_tag:
                            numero_movimentacao = b_tag.get_text(strip=True)
                            
                            # Extrair texto da movimentação (tudo após o número)
                            texto_completo = li.get_text(strip=True)
                            # Remover o número do início
                            texto_movimentacao = texto_completo.replace(f"{numero_movimentacao} -", "").strip()
                            
                            # Procurar por anexos dentro desta movimentação
                            anexos = []
                            links_anexos = li.find_all('a', href=True)
                            
                            for link in links_anexos:
                                href = link.get('href', '')
                                texto_anexo = link.get_text(strip=True)
                                
                                if 'Id_MovimentacaoArquivo=' in href and texto_anexo:
                                    id_arquivo = href.split('Id_MovimentacaoArquivo=')[-1].split('&')[0]
                                    anexos.append({
                                        'nome_arquivo': texto_anexo,
                                        'href': href,
                                        'id_arquivo': id_arquivo
                                    })
                            
                            # Adicionar à lista de movimentações
                            if numero_movimentacao.isdigit():
                                movimentacoes_agrupadas[int(numero_movimentacao)] = {
                                    'numero': int(numero_movimentacao),
                                    'texto': texto_movimentacao,
                                    'anexos': anexos
                                }
                                logger.info(f"  📋 Encontrada movimentação {numero_movimentacao} com {len(anexos)} anexos")
                
                # Se não encontrou movimentações, tentar estratégia alternativa
                if not movimentacoes_agrupadas:
                    logger.info(f"  🔍 Estratégia alternativa: procurando por links de anexos...")
                    links_anexos = soup.find_all('a', href=True)
                    
                    for link in links_anexos:
                        href = link.get('href', '')
                        texto = link.get_text(strip=True)
                        
                        if 'Id_MovimentacaoArquivo=' in href and texto:
                            id_arquivo = href.split('Id_MovimentacaoArquivo=')[-1].split('&')[0]
                            
                            # Tentar extrair número da movimentação do contexto
                            # Procurar pelo li pai que contém <b> número
                            li_pai = link.find_parent('li')
                            if li_pai:
                                b_tag = li_pai.find('b')
                                if b_tag:
                                    numero_movimentacao = b_tag.get_text(strip=True)
                                    if numero_movimentacao.isdigit():
                                        if int(numero_movimentacao) not in movimentacoes_agrupadas:
                                            movimentacoes_agrupadas[int(numero_movimentacao)] = {
                                                'numero': int(numero_movimentacao),
                                                'texto': li_pai.get_text(strip=True).replace(f"{numero_movimentacao} -", "").strip(),
                                                'anexos': []
                                            }
                                        
                                        movimentacoes_agrupadas[int(numero_movimentacao)]['anexos'].append({
                                            'nome_arquivo': texto,
                                            'href': href,
                                            'id_arquivo': id_arquivo
                                        })
            
            logger.info(f"📋 Total de anexos encontrados: {sum(len(mov['anexos']) for mov in movimentacoes_agrupadas.values())} em {len(movimentacoes_agrupadas)} movimentações")
            
            # Pegar as últimas X movimentações (mais recentes primeiro)
            chaves_movimentacoes = sorted(movimentacoes_agrupadas.keys(), reverse=True)
            ultimas_movimentacoes_chaves = chaves_movimentacoes[:num_movimentacoes]
            
            logger.info(f"🎯 Processando as últimas {len(ultimas_movimentacoes_chaves)} movimentações")
            
            anexos_extraidos = []
            
            for i, chave_movimentacao in enumerate(ultimas_movimentacoes_chaves, 1):
                movimentacao = movimentacoes_agrupadas[chave_movimentacao]
                logger.info(f"🔍 Processando movimentação {i}/{len(ultimas_movimentacoes_chaves)}: Movimentação {movimentacao['numero']} ({len(movimentacao['anexos'])} anexos)")
                
                for j, anexo in enumerate(movimentacao['anexos'], 1):
                    logger.info(f"  📄 Processando anexo {j}/{len(movimentacao['anexos'])} da movimentação {movimentacao['numero']}: {anexo['nome_arquivo']} (ID: {anexo['id_arquivo']})")
                    
                    try:
                        # Garantir que estamos na aba de navegação
                        aba_navegacao = session['driver'].current_window_handle
                        session['driver'].switch_to.window(aba_navegacao)
                        
                        # REFRESH: Recarregar a página antes de cada anexo para evitar conteúdo fantasma
                        logger.info(f"    🔄 Fazendo refresh da página antes do anexo...")
                        session['driver'].refresh()
                        time.sleep(3)
                        
                        # Se não estiver na URL correta, navegar para ela
                        if "BuscaProcesso?PaginaAtual=9&PassoBusca=4" not in session['driver'].current_url:
                            session['driver'].get("https://projudi.tjgo.jus.br/BuscaProcesso?PaginaAtual=9&PassoBusca=4")
                            time.sleep(3)
                        
                        # Aguardar carregamento da página
                        time.sleep(2)
                        
                        # FORÇAR ATUALIZAÇÃO DO IFRAME antes do clique
                        logger.info(f"    🔄 Forçando atualização do iframe...")
                        self._forcar_atualizacao_iframe(session)
                        
                        # Clicar no link específico usando o ID único
                        if self._clicar_link_por_id(session, anexo['id_arquivo']):
                            # Aguardar carregamento
                            time.sleep(5)
                            
                            # Verificar se é PDF ou HTML
                            is_pdf = anexo['nome_arquivo'].lower().endswith('.pdf')
                            
                            if is_pdf:
                                logger.info(f"    📄 PDF detectado, baixando diretamente...")
                                download_realizado = self._tentar_baixar_pdf(session, anexo['nome_arquivo'], anexo['id_arquivo'])
                                if download_realizado:
                                    logger.info(f"    📥 PDF baixado com sucesso!")
                                    texto_extraido = "PDF baixado com sucesso"
                                    html_content = ""
                                else:
                                    logger.info(f"    ⚠️ Não foi possível baixar o PDF")
                                    texto_extraido = "Erro ao baixar PDF"
                                    html_content = ""
                            else:
                                logger.info(f"    📄 HTML detectado, extraindo conteúdo...")
                                texto_extraido, html_content, _ = self._extrair_texto_do_iframe(session)
                                download_realizado = False
                            
                            # Gerar timestamp para referência
                            timestamp = int(time.time())
                            
                            anexo_extraido = {
                                'index': len(anexos_extraidos) + 1,
                                'nome_arquivo': anexo['nome_arquivo'],
                                'id_arquivo': anexo['id_arquivo'],
                                'movimentacao_numero': movimentacao['numero'],
                                'movimentacao_texto': movimentacao['texto'],
                                'texto_extraido': texto_extraido,
                                'tamanho_texto': len(texto_extraido),
                                'html_content': html_content,
                                'timestamp': timestamp,
                                'is_pdf': is_pdf,
                                'download_realizado': download_realizado
                            }
                            
                            anexos_extraidos.append(anexo_extraido)
                            
                            logger.info(f"    ✅ Anexo extraído: {len(texto_extraido)} caracteres")
                            if is_pdf:
                                logger.info(f"    📄 Tipo: PDF (download tentado: {'Sim' if download_realizado else 'Não'})")
                            else:
                                logger.info(f"    📄 Tipo: HTML")
                        else:
                            logger.error(f"    ❌ Não foi possível clicar no anexo: {anexo['nome_arquivo']}")
                        
                    except Exception as e:
                        logger.error(f"    ❌ Erro ao processar anexo {anexo['nome_arquivo']}: {e}")
            
            return anexos_extraidos
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair anexos das movimentações: {e}")
            return []
    
    def _extrair_movimentacoes_tabela(self, session, num_movimentacoes):
        """Extrai movimentações da tabela de navegação de arquivos"""
        try:
            logger.info("📋 Extraindo movimentações da tabela...")
            
            # Aguardar carregamento da tabela
            time.sleep(3)
            
            # Extrair dados da tabela
            soup = BeautifulSoup(session['driver'].page_source, 'html.parser')
            tabela = soup.find('table', {'id': 'TabelaArquivos'})
            
            if not tabela:
                logger.error("❌ Tabela de movimentações não encontrada")
                return []
            
            movimentacoes = []
            linhas = tabela.find_all('tr', class_=re.compile(r'TabelaLinha|filtro-entrada'))
            
            # Se não encontrar linhas com classe específica, tentar todas as linhas
            if not linhas:
                linhas = tabela.find_all('tr')
                logger.info(f"ℹ️ Usando todas as {len(linhas)} linhas da tabela")
            
            # Pegar as últimas X movimentações (mais recentes)
            linhas_limite = linhas[-num_movimentacoes:] if len(linhas) >= num_movimentacoes else linhas
            
            for linha in linhas_limite:
                tds = linha.find_all('td')
                if len(tds) >= 5:
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
                            texto_completo = movimentacao_celula.get_text(strip=True)
                            descricao_movimentacao = texto_completo.replace(tipo_movimentacao, '').strip()
                    else:
                        tipo_movimentacao = movimentacao_celula.get_text(strip=True)
                    
                    # Verificar se tem anexo
                    tem_anexo = bool(arquivos_celula.find('img', {'src': 'imagens/22x22/go-bottom.png'}))
                    
                    # Extrair IDs de anexos da célula de arquivos
                    ids_anexos = self._extrair_ids_anexos_celula(arquivos_celula)
                    
                    # Verificar se é uma linha válida
                    if numero and tipo_movimentacao and not numero.startswith('Nº') and not numero.startswith('Número'):
                        movimentacao = {
                            'numero': int(numero) if numero.isdigit() else len(movimentacoes) + 1,
                            'tipo': tipo_movimentacao,
                            'descricao': descricao_movimentacao,
                            'data': data,
                            'usuario': usuario,
                            'tem_anexo': tem_anexo,
                            'ids_anexos': ids_anexos,
                            'html_completo': str(linha)
                        }
                        
                        movimentacoes.append(movimentacao)
            
            # Ordenar por número (mais recentes primeiro)
            movimentacoes.sort(key=lambda x: x['numero'], reverse=True)
            
            logger.info(f"✅ {len(movimentacoes)} movimentações extraídas da tabela")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair movimentações da tabela: {e}")
            return []
    
    def _extrair_ids_anexos_celula(self, arquivos_celula):
        """Extrai IDs de anexos de uma célula da tabela"""
        ids_anexos = []
        
        try:
            # Estratégia 1: Procurar por links com javascript:buscarArquivosMovimentacaoJSON
            links = arquivos_celula.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                if 'buscarArquivosMovimentacaoJSON' in href:
                    # Extrair código da movimentação do javascript
                    match = re.search(r"buscarArquivosMovimentacaoJSON\('([^']+)'", href)
                    if match:
                        codigo_movimentacao = match.group(1)
                        texto = link.get_text(strip=True)
                        ids_anexos.append({
                            'id': codigo_movimentacao,
                            'nome': texto or f'Anexo_{codigo_movimentacao}',
                            'href': href,
                            'tipo': 'javascript_buscar'
                        })
            
            # Estratégia 2: Procurar por links com Id_MovimentacaoArquivo
            for link in links:
                href = link.get('href', '')
                if 'Id_MovimentacaoArquivo=' in href:
                    # Extrair ID do anexo
                    match = re.search(r"Id_MovimentacaoArquivo=(\d+)", href)
                    if match:
                        anexo_id = match.group(1)
                        texto = link.get_text(strip=True)
                        
                        # Verificar se já não foi adicionado
                        if not any(a['id'] == anexo_id for a in ids_anexos):
                            ids_anexos.append({
                                'id': anexo_id,
                                'nome': texto or f'Anexo_{anexo_id}',
                                'href': href,
                                'tipo': 'href_direto'
                            })
            
            # Estratégia 3: Procurar por elementos com onclick
            elementos_onclick = arquivos_celula.find_all(attrs={'onclick': True})
            
            for elem in elementos_onclick:
                onclick = elem.get('onclick', '')
                if 'Id_MovimentacaoArquivo=' in onclick:
                    match = re.search(r"Id_MovimentacaoArquivo=(\d+)", onclick)
                    if match:
                        anexo_id = match.group(1)
                        texto = elem.get_text(strip=True)
                        
                        # Verificar se já não foi adicionado
                        if not any(a['id'] == anexo_id for a in ids_anexos):
                            ids_anexos.append({
                                'id': anexo_id,
                                'nome': texto or f'Anexo_{anexo_id}',
                                'href': f"BuscaProcesso?PaginaAtual=6&Id_MovimentacaoArquivo={anexo_id}",
                                'tipo': 'onclick_extraido'
                            })
            
            # Estratégia 4: Se tem anexo mas não encontrou IDs, usar o ID da movimentação
            if not ids_anexos:
                # Procurar pelo ID da movimentação na linha pai
                linha_pai = arquivos_celula.find_parent('tr')
                if linha_pai:
                    div_drop = linha_pai.find('div', class_='dropMovimentacao')
                    if div_drop:
                        id_movimentacao = div_drop.get('id_movi', '')
                        if id_movimentacao:
                            ids_anexos.append({
                                'id': id_movimentacao,
                                'nome': f'Anexo_Movimentacao_{id_movimentacao}',
                                'href': f"BuscaProcesso?PaginaAtual=6&Id_MovimentacaoArquivo={id_movimentacao}",
                                'tipo': 'id_movimentacao'
                            })
        
        except Exception as e:
            logger.error(f"❌ Erro ao extrair IDs de anexos: {e}")
        
        return ids_anexos
    
    def _extrair_anexos_movimentacao_avancado(self, session, movimentacao):
        """Extrai anexos de uma movimentação específica usando técnicas avançadas"""
        try:
            anexos = []
            
            if not movimentacao.get('ids_anexos'):
                logger.info(f"  ℹ️ Nenhum anexo encontrado para movimentação {movimentacao['numero']}")
                return anexos
            
            logger.info(f"  📎 Processando {len(movimentacao['ids_anexos'])} anexos da movimentação {movimentacao['numero']}")
            
            for i, anexo_info in enumerate(movimentacao['ids_anexos'], 1):
                logger.info(f"    🔍 Processando anexo {i}/{len(movimentacao['ids_anexos'])}: {anexo_info['nome']}")
                
                # Garantir que estamos na página de navegação
                if "TabelaArquivos" not in session['driver'].page_source:
                    self._acessar_pagina_navegacao_arquivos(session)
                    time.sleep(3)
                
                # REFRESH: Recarregar a página antes de cada anexo
                logger.info(f"    🔄 Fazendo refresh da página...")
                session['driver'].refresh()
                time.sleep(3)
                
                # Forçar atualização do iframe
                self._forcar_atualizacao_iframe(session)
                
                # Clicar no anexo específico
                if self._clicar_anexo_por_id(session, anexo_info):
                    # Aguardar carregamento
                    time.sleep(5)
                    
                    # Extrair conteúdo do iframe
                    texto_extraido, html_content, is_pdf = self._extrair_texto_do_iframe(session)
                    
                    # Tentar baixar PDF se for o caso
                    download_realizado = False
                    if is_pdf or anexo_info['nome'].lower().endswith('.pdf'):
                        logger.info(f"    📄 Tentando baixar PDF...")
                        # Aguardar um pouco mais para os links aparecerem
                        time.sleep(3)
                        download_realizado = self._tentar_baixar_pdf(session, anexo_info['nome'], anexo_info['id'])
                    
                    anexo = {
                        'id': anexo_info['id'],
                        'nome': anexo_info['nome'],
                        'href': anexo_info['href'],
                        'texto_extraido': texto_extraido,
                        'tamanho_texto': len(texto_extraido),
                        'html_content': html_content,
                        'is_pdf': is_pdf,
                        'download_realizado': download_realizado,
                        'timestamp': int(time.time())
                    }
                    
                    anexos.append(anexo)
                    
                    logger.info(f"    ✅ Anexo extraído: {len(texto_extraido)} caracteres")
                    if is_pdf:
                        logger.info(f"    📄 PDF baixado: {'Sim' if download_realizado else 'Não'}")
                else:
                    logger.error(f"    ❌ Não foi possível clicar no anexo: {anexo_info['nome']}")
            
            return anexos
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair anexos da movimentação: {e}")
            return []
    
    def _forcar_atualizacao_iframe(self, session):
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
            logger.info(f"    🔄 {resultado1}")
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
            logger.info(f"    🔄 {resultado2}")
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"    ❌ Erro ao forçar atualização do iframe: {e}")
            return False
    
    def _clicar_anexo_por_id(self, session, anexo_info):
        """Clica no anexo específico usando as informações do anexo"""
        try:
            id_arquivo = anexo_info['id']
            tipo_anexo = anexo_info.get('tipo', 'desconhecido')
            href = anexo_info.get('href', '')
            
            logger.info(f"    🎯 Tentando clicar no anexo ID {id_arquivo} (tipo: {tipo_anexo})")
            
            # Estratégia 1: Para anexos do tipo javascript_buscar
            if tipo_anexo == 'javascript_buscar':
                try:
                    # Executar o JavaScript diretamente
                    js_script = f"""
                    buscarArquivosMovimentacaoJSON('{id_arquivo}', 'BuscaProcesso', 'Id_MovimentacaoArquivo', 6, 'false');
                    return 'JavaScript executado para buscarArquivosMovimentacaoJSON';
                    """
                    resultado = session['driver'].execute_script(js_script)
                    logger.info(f"    ✅ {resultado}")
                    time.sleep(3)  # Aguardar carregamento
                    return True
                except Exception as e:
                    logger.info(f"    ⚠️ Estratégia javascript_buscar falhou: {e}")
            
            # Estratégia 2: Procurar pelo link que contém o ID específico
            xpath_id = f"//a[contains(@href, 'Id_MovimentacaoArquivo={id_arquivo}')]"
            
            try:
                link = session['driver'].find_element(By.XPATH, xpath_id)
                if link.is_enabled() and link.is_displayed():
                    link.click()
                    logger.info(f"    ✅ Clique direto no anexo ID {id_arquivo}")
                    return True
                else:
                    session['driver'].execute_script("arguments[0].click();", link)
                    logger.info(f"    ✅ Clique JavaScript no anexo ID {id_arquivo}")
                    return True
            except Exception as e:
                logger.info(f"    ⚠️ Estratégia 2 falhou: {e}")
            
            # Estratégia 3: Procurar por todos os links
            links = session['driver'].find_elements(By.TAG_NAME, "a")
            
            for link in links:
                try:
                    href_link = link.get_attribute('href')
                    if href_link and f'Id_MovimentacaoArquivo={id_arquivo}' in href_link:
                        if link.is_enabled() and link.is_displayed():
                            link.click()
                            logger.info(f"    ✅ Clique direto no anexo encontrado ID {id_arquivo}")
                            return True
                        else:
                            session['driver'].execute_script("arguments[0].click();", link)
                            logger.info(f"    ✅ Clique JavaScript no anexo encontrado ID {id_arquivo}")
                            return True
                except Exception as e:
                    continue
            
            # Estratégia 4: Procurar por links com buscarArquivosMovimentacaoJSON
            for link in links:
                try:
                    href_link = link.get_attribute('href')
                    if href_link and 'buscarArquivosMovimentacaoJSON' in href_link and id_arquivo in href_link:
                        if link.is_enabled() and link.is_displayed():
                            link.click()
                            logger.info(f"    ✅ Clique direto no anexo buscarArquivosMovimentacaoJSON ID {id_arquivo}")
                            return True
                        else:
                            session['driver'].execute_script("arguments[0].click();", link)
                            logger.info(f"    ✅ Clique JavaScript no anexo buscarArquivosMovimentacaoJSON ID {id_arquivo}")
                            return True
                except Exception as e:
                    continue
            
            # Estratégia 5: JavaScript genérico
            js_script = f"""
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {{
                var href = links[i].getAttribute('href');
                if (href && (href.includes('Id_MovimentacaoArquivo={id_arquivo}') || href.includes('{id_arquivo}'))) {{
                    links[i].click();
                    return 'Anexo encontrado e clicado via JavaScript';
                }}
            }}
            return 'Anexo não encontrado';
            """
            
            resultado = session['driver'].execute_script(js_script)
            if "Anexo encontrado" in resultado:
                logger.info(f"    ✅ {resultado} para ID {id_arquivo}")
                return True
            
            logger.error(f"    ❌ Nenhuma estratégia funcionou para o ID {id_arquivo}")
            return False
                
        except Exception as e:
            logger.error(f"    ❌ Erro ao clicar no anexo ID {id_arquivo}: {e}")
            return False

    def _clicar_link_por_id(self, session, id_arquivo):
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
    
    def _extrair_texto_do_iframe(self, session):
        """Extrai texto do iframe onde o conteúdo do anexo está"""
        try:
            # Aguardar carregamento
            time.sleep(5)
            
            # Estratégia 1: Tentar encontrar o iframe com ID "arquivo"
            try:
                iframe = session['driver'].find_element(By.ID, "arquivo")
                session['driver'].switch_to.frame(iframe)
                logger.info(f"    📄 Iframe 'arquivo' encontrado")
            except:
                # Estratégia 2: Procurar por qualquer iframe na página
                iframes = session['driver'].find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    iframe = iframes[0]  # Usar o primeiro iframe
                    session['driver'].switch_to.frame(iframe)
                    logger.info(f"    📄 Iframe encontrado (primeiro da página)")
                else:
                    # Estratégia 3: Se não há iframe, tentar extrair do conteúdo principal
                    logger.info(f"    📄 Nenhum iframe encontrado, extraindo do conteúdo principal")
                    return self._extrair_texto_sem_iframe(session)
            
            # Aguardar carregamento do conteúdo
            time.sleep(3)
            
            # Extrair o HTML do iframe
            html_content = session['driver'].page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Verificar se é um PDF
            is_pdf = False
            if "pdf" in html_content.lower() or "application/pdf" in html_content.lower():
                is_pdf = True
                logger.info(f"    📄 PDF detectado no iframe")
            
            # Remover scripts e styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extrair todo o texto
            texto_completo = soup.get_text()
            
            # Limpar o texto
            texto_limpo = re.sub(r'\s+', ' ', texto_completo).strip()
            
            # Voltar para o contexto principal
            session['driver'].switch_to.default_content()
            
            # Se o texto está vazio ou muito pequeno, tentar estratégias alternativas
            if len(texto_limpo) < 10:
                logger.info(f"    ⚠️ Texto muito pequeno ({len(texto_limpo)} chars), tentando estratégias alternativas")
                return self._extrair_texto_estrategias_alternativas(session)
            
            # Limitar tamanho se for muito longo
            if len(texto_limpo) > 10000:
                texto_limpo = texto_limpo[:10000] + "..."
            
            return texto_limpo, html_content, is_pdf
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair texto do iframe: {e}")
            # Voltar para o contexto principal em caso de erro
            try:
                session['driver'].switch_to.default_content()
            except:
                pass
            return "Erro na extração do texto do iframe", "", False
    
    def _extrair_texto_sem_iframe(self, session):
        """Extrai texto quando não há iframe disponível"""
        try:
            logger.info(f"    📄 Extraindo texto sem iframe...")
            
            # Extrair HTML da página principal
            html_content = session['driver'].page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Procurar por elementos que podem conter o conteúdo do anexo
            elementos_conteudo = []
            
            # Estratégia 1: Procurar por divs com conteúdo
            divs = soup.find_all('div', class_=re.compile(r'conteudo|texto|arquivo|anexo', re.I))
            elementos_conteudo.extend(divs)
            
            # Estratégia 2: Procurar por elementos com texto longo
            elementos = soup.find_all(['div', 'p', 'span', 'td'])
            for elem in elementos:
                texto = elem.get_text(strip=True)
                if len(texto) > 100:  # Elementos com texto significativo
                    elementos_conteudo.append(elem)
            
            # Estratégia 3: Procurar por elementos específicos do PROJUDI
            elementos_projudi = soup.find_all(['div', 'span'], id=re.compile(r'arquivo|conteudo|texto', re.I))
            elementos_conteudo.extend(elementos_projudi)
            
            # Combinar textos dos elementos encontrados
            textos = []
            for elem in elementos_conteudo:
                texto = elem.get_text(strip=True)
                if texto and len(texto) > 20:
                    textos.append(texto)
            
            # Remover duplicatas
            textos_unicos = list(dict.fromkeys(textos))
            
            # Combinar todos os textos
            texto_completo = " ".join(textos_unicos)
            
            # Verificar se é PDF
            is_pdf = "pdf" in html_content.lower() or "application/pdf" in html_content.lower()
            
            return texto_completo, html_content, is_pdf
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair texto sem iframe: {e}")
            return "Erro na extração do texto sem iframe", "", False
    
    def _extrair_texto_estrategias_alternativas(self, session):
        """Tenta estratégias alternativas para extrair texto quando o iframe não funciona"""
        try:
            logger.info(f"    🔄 Tentando estratégias alternativas...")
            
            # Voltar para o contexto principal
            session['driver'].switch_to.default_content()
            
            # Estratégia 1: Aguardar mais tempo e tentar novamente
            time.sleep(5)
            
            # Estratégia 2: Procurar por elementos que apareceram após o clique
            elementos_novos = session['driver'].find_elements(By.XPATH, "//*[contains(@class, 'arquivo') or contains(@class, 'conteudo') or contains(@class, 'texto')]")
            
            if elementos_novos:
                logger.info(f"    📄 Encontrados {len(elementos_novos)} elementos de conteúdo")
                textos = []
                for elem in elementos_novos:
                    try:
                        texto = elem.text.strip()
                        if texto and len(texto) > 20:
                            textos.append(texto)
                    except:
                        continue
                
                if textos:
                    texto_completo = " ".join(textos)
                    return texto_completo, "", False
            
            # Estratégia 3: Procurar por links de download
            links_download = session['driver'].find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, '.doc') or contains(@href, '.txt')]")
            
            if links_download:
                logger.info(f"    📄 Encontrados {len(links_download)} links de download")
                nomes_arquivos = []
                for link in links_download:
                    try:
                        nome = link.text.strip()
                        if nome:
                            nomes_arquivos.append(nome)
                    except:
                        continue
                
                if nomes_arquivos:
                    texto_completo = f"Arquivos disponíveis: {', '.join(nomes_arquivos)}"
                    return texto_completo, "", True  # Assumir que são PDFs
            
            # Estratégia 4: Verificar se há mensagem de erro ou aviso
            elementos_mensagem = session['driver'].find_elements(By.XPATH, "//*[contains(text(), 'erro') or contains(text(), 'aviso') or contains(text(), 'não encontrado') or contains(text(), 'indisponível')]")
            
            if elementos_mensagem:
                mensagens = []
                for elem in elementos_mensagem:
                    try:
                        texto = elem.text.strip()
                        if texto:
                            mensagens.append(texto)
                    except:
                        continue
                
                if mensagens:
                    texto_completo = f"Mensagens do sistema: {'; '.join(mensagens)}"
                    return texto_completo, "", False
            
            return "Conteúdo não disponível ou não foi possível extrair", "", False
            
        except Exception as e:
            logger.error(f"❌ Erro nas estratégias alternativas: {e}")
            return "Erro nas estratégias alternativas", "", False
    
    def _tentar_baixar_pdf(self, session, nome_arquivo, id_arquivo=None):
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
                                    
                                    # Adicionar à lista de PDFs baixados
                                    if id_arquivo:
                                        self.pdfs_baixados[id_arquivo] = {
                                            'nome_arquivo': nome_arquivo,
                                            'caminho_pdf': nome_arquivo_final,
                                            'id_arquivo': id_arquivo
                                        }
                                    
                                    return True
                                else:
                                    logger.error(f"  ❌ Erro ao baixar PDF: Status {pdf_response.status_code}")
                                    return False
                            else:
                                # Tentar baixar mesmo que não seja URL do S3
                                logger.info(f"  ⚠️ URL não é do S3, tentando baixar mesmo assim: {url_final}")
                                
                                # Extrair nome do arquivo da URL
                                nome_arquivo_limpo = nome_arquivo.replace('.pdf', '')
                                nome_arquivo_final = f"{nome_arquivo_limpo}_{int(time.time())}.pdf"
                                
                                # Fazer download direto com cookies
                                pdf_response = requests.get(url_final, cookies=cookie_dict, timeout=30)
                                if pdf_response.status_code == 200:
                                    # Verificar se o conteúdo é realmente um PDF
                                    if pdf_response.headers.get('content-type', '').lower() == 'application/pdf' or pdf_response.content.startswith(b'%PDF'):
                                        with open(nome_arquivo_final, 'wb') as f:
                                            f.write(pdf_response.content)
                                        logger.info(f"  ✅ PDF baixado (URL não-S3): {nome_arquivo_final}")
                                        
                                        # Adicionar à lista de PDFs baixados
                                        if id_arquivo:
                                            self.pdfs_baixados[id_arquivo] = {
                                                'nome_arquivo': nome_arquivo,
                                                'caminho_pdf': nome_arquivo_final,
                                                'id_arquivo': id_arquivo
                                            }
                                        
                                        return True
                                    else:
                                        logger.error(f"  ❌ Conteúdo não é PDF válido")
                                        return False
                                else:
                                    logger.error(f"  ❌ Erro ao baixar PDF (URL não-S3): Status {pdf_response.status_code}")
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
    
    def _extrair_conteudo_pdf(self, caminho_pdf):
        """Extrai conteúdo de um PDF usando múltiplas estratégias incluindo OCR"""
        try:
            logger.info(f"    📄 Processando PDF: {os.path.basename(caminho_pdf)}")
            logger.info(f"    📁 Caminho: {caminho_pdf}")
            
            # Verificar se arquivo existe
            if not os.path.exists(caminho_pdf):
                logger.error(f"    ❌ Arquivo PDF não encontrado: {caminho_pdf}")
                return {'conteudo_extraido': '', 'tamanho_conteudo': 0, 'processado': False, 'metodo': 'erro'}
            
            # Obter tamanho do arquivo
            tamanho_arquivo = os.path.getsize(caminho_pdf)
            logger.info(f"    📏 Tamanho do arquivo: {tamanho_arquivo} bytes")
            
            conteudo_total = ""
            metodo_utilizado = "nenhum"
            
            # ESTRATÉGIA 1: PyMuPDF (fitz)
            try:
                import fitz
                doc = fitz.open(caminho_pdf)
                texto_pymupdf = ""
                
                for num_pagina in range(len(doc)):
                    pagina = doc.load_page(num_pagina)
                    texto_pagina = pagina.get_text()
                    texto_pymupdf += texto_pagina
                    logger.info(f"    📄 Página {num_pagina + 1}: {len(texto_pagina)} caracteres")
                
                doc.close()
                
                if texto_pymupdf.strip():
                    conteudo_total = texto_pymupdf
                    metodo_utilizado = "PyMuPDF"
                    logger.info(f"    ✅ Texto extraído com PyMuPDF: {len(texto_pymupdf)} caracteres")
                else:
                    logger.info(f"    ⚠️ PyMuPDF não extraiu texto, tentando PyPDF2...")
                    
            except Exception as e:
                logger.warning(f"    ⚠️ Erro com PyMuPDF: {e}")
            
            # ESTRATÉGIA 2: PyPDF2 (se PyMuPDF não funcionou)
            if not conteudo_total:
                try:
                    import PyPDF2
                    with open(caminho_pdf, 'rb') as arquivo:
                        leitor = PyPDF2.PdfReader(arquivo)
                        texto_pypdf2 = ""
                        
                        for num_pagina in range(len(leitor.pages)):
                            pagina = leitor.pages[num_pagina]
                            texto_pagina = pagina.extract_text()
                            texto_pypdf2 += texto_pagina
                            logger.info(f"    📄 Página {num_pagina + 1}: {len(texto_pagina)} caracteres")
                        
                        if texto_pypdf2.strip():
                            conteudo_total = texto_pypdf2
                            metodo_utilizado = "PyPDF2"
                            logger.info(f"    ✅ Texto extraído com PyPDF2: {len(texto_pypdf2)} caracteres")
                        else:
                            logger.info(f"    ⚠️ PyPDF2 não extraiu texto, tentando OCR...")
                            
                except Exception as e:
                    logger.warning(f"    ⚠️ Erro com PyPDF2: {e}")
            
            # ESTRATÉGIA 3: OCR com pytesseract (se nenhum método extraiu texto)
            if not conteudo_total:
                try:
                    import pytesseract
                    from PIL import Image
                    import fitz
                    
                    logger.info(f"    🔍 Iniciando OCR para extrair texto de imagens...")
                    
                    # Abrir PDF com PyMuPDF para extrair imagens
                    doc = fitz.open(caminho_pdf)
                    texto_ocr = ""
                    
                    for num_pagina in range(len(doc)):
                        pagina = doc.load_page(num_pagina)
                        
                        # Converter página para imagem
                        mat = fitz.Matrix(2, 2)  # Aumentar resolução para melhor OCR
                        pix = pagina.get_pixmap(matrix=mat)
                        
                        # Salvar imagem temporária
                        img_temp = f"temp_page_{num_pagina}.png"
                        pix.save(img_temp)
                        
                        try:
                            # Abrir imagem com PIL
                            imagem = Image.open(img_temp)
                            
                            # Configurar OCR para português
                            texto_pagina = pytesseract.image_to_string(imagem, lang='por')
                            texto_ocr += texto_pagina
                            
                            logger.info(f"    📄 Página {num_pagina + 1} (OCR): {len(texto_pagina)} caracteres")
                            
                            # Limpar arquivo temporário
                            imagem.close()
                            os.remove(img_temp)
                            
                        except Exception as e:
                            logger.warning(f"    ⚠️ Erro no OCR da página {num_pagina + 1}: {e}")
                            if os.path.exists(img_temp):
                                os.remove(img_temp)
                    
                    doc.close()
                    
                    if texto_ocr.strip():
                        conteudo_total = texto_ocr
                        metodo_utilizado = "OCR"
                        logger.info(f"    ✅ Texto extraído com OCR: {len(texto_ocr)} caracteres")
                    else:
                        logger.warning(f"    ⚠️ OCR não conseguiu extrair texto")
                        
                except ImportError:
                    logger.warning(f"    ⚠️ pytesseract não instalado, OCR não disponível")
                except Exception as e:
                    logger.warning(f"    ⚠️ Erro no OCR: {e}")
            
            # Resultado final
            tamanho_conteudo = len(conteudo_total)
            processado = tamanho_conteudo > 0
            
            logger.info(f"    ✅ PDF processado: {os.path.basename(caminho_pdf)} ({tamanho_conteudo} caracteres)")
            if processado:
                logger.info(f"    🎯 Método utilizado: {metodo_utilizado}")
            
            return {
                'conteudo_extraido': conteudo_total,
                'tamanho_conteudo': tamanho_conteudo,
                'processado': processado,
                'metodo': metodo_utilizado
            }
            
        except Exception as e:
            logger.error(f"    ❌ Erro ao processar PDF: {e}")
            return {'conteudo_extraido': '', 'tamanho_conteudo': 0, 'processado': False, 'metodo': 'erro'}
    
    def _processar_pdfs_baixados(self, pdfs_baixados):
        """Processa PDFs baixados e extrai seu conteúdo"""
        try:
            logger.info(f"📄 Processando {len(pdfs_baixados)} PDFs baixados...")
            
            resultados = {}
            
            for id_arquivo, pdf_info in pdfs_baixados.items():
                nome_arquivo = pdf_info.get('nome_arquivo', '')
                caminho_pdf = pdf_info.get('caminho_pdf', '')
                
                if caminho_pdf and os.path.exists(caminho_pdf):
                    # Extrair conteúdo do PDF
                    resultado_pdf = self._extrair_conteudo_pdf(caminho_pdf)
                    
                    # Adicionar informações do PDF ao resultado
                    resultado_pdf['nome_arquivo'] = nome_arquivo
                    resultado_pdf['caminho_pdf'] = caminho_pdf
                    resultado_pdf['id_arquivo'] = id_arquivo
                    
                    resultados[id_arquivo] = resultado_pdf
                    
                    logger.info(f"  ✅ PDF processado: {nome_arquivo} ({resultado_pdf['tamanho_conteudo']} caracteres)")
                else:
                    logger.warning(f"  ⚠️ Caminho do PDF não encontrado: {caminho_pdf}")
                    resultados[id_arquivo] = {
                        'nome_arquivo': nome_arquivo,
                        'caminho_pdf': caminho_pdf,
                        'id_arquivo': id_arquivo,
                        'conteudo_extraido': '',
                        'tamanho_conteudo': 0,
                        'processado': False,
                        'metodo': 'arquivo_nao_encontrado'
                    }
            
            return resultados
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar PDFs baixados: {e}")
            return {}
    
    def processar_processo_com_anexos(self, numero_processo, num_movimentacoes=5):
        """Processa um processo completo e extrai anexos das últimas X movimentações"""
        logger.info(f"🚀 Iniciando processamento do processo: {numero_processo}")
        
        session = None
        try:
            # Obter sessão
            session = self.session_pool.get_session()
            logger.info("✅ Sessão obtida com sucesso")
            
            # Fazer login
            if self.fazer_login(session):
                logger.info("✅ Login realizado com sucesso")
                
                # Buscar processo
                if self.buscar_por_processo(session, numero_processo):
                    logger.info("✅ Processo encontrado")
                    
                    # Obter lista de processos
                    processos = self.obter_lista_processos(session)
                    if processos:
                        processo_info = processos[0]
                        logger.info(f"✅ Processo obtido: {processo_info}")
                        
                        # Verificar se já estamos na página do processo
                        if "corpo_dados_processo" in session['driver'].page_source:
                            logger.info("Já estamos na página do processo, pulando acessar_processo")
                        else:
                            # Acessar processo
                            if not self.acessar_processo(session, processo_info):
                                logger.error("Falha ao acessar processo")
                                return None
                        
                        logger.info("✅ Processo acessado com sucesso")
                        
                        # PASSO 1: Solicitar acesso aos anexos na página principal
                        logger.info("🔓 PASSO 1: Solicitando acesso aos anexos...")
                        if self._solicitar_acesso_processo_seguro(session):
                            logger.info("✅ Acesso aos anexos solicitado com sucesso")
                        else:
                            logger.warning("⚠️ Não foi possível solicitar acesso aos anexos, continuando...")
                        
                        # PASSO 2: Navegar para a página de navegação de arquivos
                        logger.info("📁 PASSO 2: Navegando para a página de navegação de arquivos...")
                        
                        # Navegar diretamente para a página de navegação
                        url_navegacao = "https://projudi.tjgo.jus.br/BuscaProcesso?PaginaAtual=9&PassoBusca=4"
                        session['driver'].get(url_navegacao)
                        
                        # Aguardar carregamento da página (reduzido de 5 para 3 segundos)
                        logger.info("⏳ Aguardando carregamento da página de navegação...")
                        time.sleep(3)
                        
                        # PASSO 3: Extrair anexos das últimas movimentações
                        logger.info("📁 PASSO 3: Extraindo anexos das últimas movimentações...")
                        
                        # Extrair anexos das últimas X movimentações
                        anexos_extraidos = self.extrair_anexos_ultimas_movimentacoes(session, processo_info, num_movimentacoes)
                        
                        # PASSO 4: Processar PDFs baixados (após toda a extração)
                        logger.info("📄 PASSO 4: Processando PDFs baixados...")
                        resultados_pdfs = self._processar_pdfs_baixados(self.pdfs_baixados)
                        
                        # PASSO 5: Integrar conteúdo dos PDFs nos anexos
                        logger.info("🔗 PASSO 5: Integrando conteúdo dos PDFs...")
                        for anexo in anexos_extraidos:
                            if anexo.get('is_pdf') and anexo.get('download_realizado'):
                                id_arquivo = anexo.get('id_arquivo')
                                if id_arquivo in resultados_pdfs:
                                    pdf_resultado = resultados_pdfs[id_arquivo]
                                    anexo['conteudo_pdf'] = pdf_resultado['conteudo_extraido']
                                    anexo['tamanho_conteudo_pdf'] = pdf_resultado['tamanho_conteudo']
                                    anexo['pdf_processado'] = pdf_resultado['processado']
                                    anexo['metodo_extracao'] = pdf_resultado.get('metodo', 'desconhecido')
                                    # Atualizar o tamanho_texto com o conteúdo real do PDF
                                    anexo['tamanho_texto'] = pdf_resultado['tamanho_conteudo']
                                    anexo['texto_extraido'] = pdf_resultado['conteudo_extraido']
                                    logger.info(f"  ✅ Conteúdo do PDF integrado: {anexo['nome_arquivo']} ({pdf_resultado['tamanho_conteudo']} caracteres) - Método: {pdf_resultado.get('metodo', 'desconhecido')}")
                                else:
                                    anexo['conteudo_pdf'] = "PDF não foi processado"
                                    anexo['tamanho_conteudo_pdf'] = 0
                                    anexo['pdf_processado'] = False
                            else:
                                anexo['conteudo_pdf'] = ""
                                anexo['tamanho_conteudo_pdf'] = 0
                                anexo['pdf_processado'] = False
                        
                        # PASSO 6: Extrair partes envolvidas no processo
                        partes_processo = self._extrair_partes_processo(session)
                        
                        # Preparar resultado final
                        resultado_final = {
                            'processo': numero_processo,
                            'total_movimentacoes_processadas': num_movimentacoes,
                            'total_anexos_extraidos': len(anexos_extraidos),
                            'total_pdfs_processados': len([pdf for pdf in resultados_pdfs.values() if pdf['processado']]),
                            'anexos': anexos_extraidos,
                            'pdfs_processados': resultados_pdfs,
                            'partes_processo': partes_processo,
                            'timestamp_extração': int(time.time())
                        }
                        
                        # Validar resultado antes de salvar
                        if not self._validar_resultado(resultado_final):
                            logger.error("❌ Validação do resultado falhou")
                            return None
                        
                        # Salvar resultado para debug
                        nome_arquivo_resultado = f"resultado_anexos_{numero_processo}_{int(time.time())}.json"
                        with open(nome_arquivo_resultado, 'w', encoding='utf-8') as f:
                            json.dump(resultado_final, f, indent=2, ensure_ascii=False)
                        
                        logger.info(f"💾 Resultado salvo em: {nome_arquivo_resultado}")
                        
                        # Mostrar resumo
                        self._mostrar_resumo_extração(resultado_final)
                        
                        return resultado_final
                    else:
                        logger.error("Nenhum processo encontrado na lista")
                        return None
                else:
                    logger.error("Processo não encontrado")
                    return None
            else:
                logger.error("Falha no login")
                return None
                
        except Exception as e:
            logger.error(f"Erro geral: {e}")
            return None
        finally:
            logger.info("🔚 Sessão liberada")
            # Liberar a sessão
            if session:
                self.session_pool.release_session(session)
            self._limpar_arquivos_temporarios() # Limpar arquivos temporários
    
    def _mostrar_resumo_extração(self, resultado):
        """Mostra um resumo da extração realizada"""
        logger.info("📊 RESUMO DA EXTRAÇÃO:")
        logger.info(f"  📋 Processo: {resultado['processo']}")
        logger.info(f"  📁 Movimentações processadas: {resultado['total_movimentacoes_processadas']}")
        logger.info(f"  📎 Total de anexos extraídos: {resultado['total_anexos_extraidos']}")
        logger.info(f"  📄 PDFs processados: {resultado['total_pdfs_processados']}")
        
        # Resumo das partes
        partes = resultado.get('partes_processo', {})
        logger.info(f"  👥 PARTES ENVOLVIDAS:")
        logger.info(f"    📋 Polo Ativo: {len(partes.get('polo_ativo', []))} partes")
        logger.info(f"    📋 Polo Passivo: {len(partes.get('polo_passivo', []))} partes")
        logger.info(f"    📋 Outros: {len(partes.get('outros', []))} partes")
        
        # Detalhes das partes
        for polo, partes_list in partes.items():
            if partes_list:
                logger.info(f"    📋 {polo.replace('_', ' ').title()}:")
                for i, parte in enumerate(partes_list, 1):
                    nome = parte.get('nome', 'N/A')
                    documento = parte.get('documento', '')
                    tipo = parte.get('tipo', '')
                    endereco = parte.get('endereco', '')
                    
                    logger.info(f"      {i}. {nome}")
                    if documento:
                        logger.info(f"         📄 Documento: {documento}")
                    if tipo:
                        logger.info(f"         🏷️ Tipo: {tipo}")
                    if endereco:
                        logger.info(f"         📍 Endereço: {endereco}")
        
        for i, anexo in enumerate(resultado['anexos'], 1):
            logger.info(f"  📄 Anexo {i}: {anexo['nome_arquivo']}")
            logger.info(f"     📝 {anexo['tamanho_texto']} caracteres")
            if anexo.get('data_movimentacao'):
                logger.info(f"     📅 Data: {anexo['data_movimentacao']}")
            if anexo.get('is_pdf'):
                logger.info(f"     📥 PDF baixado: {'Sim' if anexo.get('download_realizado') else 'Não'}")
                if anexo.get('pdf_processado'):
                    logger.info(f"     📄 Conteúdo PDF: {anexo.get('tamanho_conteudo_pdf', 0)} caracteres")
                else:
                    logger.info(f"     📄 Conteúdo PDF: Não processado")
        
        logger.info("🎯 EXTRAÇÃO COMPLETA! Dados prontos para uso.")

    def _aguardar_elemento(self, session, by, value, timeout=10, descricao="elemento"):
        """Aguarda um elemento carregar dinamicamente usando WebDriverWait"""
        try:
            wait = WebDriverWait(session['driver'], timeout)
            elemento = wait.until(EC.presence_of_element_located((by, value)))
            logger.info(f"✅ {descricao} carregado em {timeout}s")
            return elemento
        except Exception as e:
            logger.warning(f"⚠️ {descricao} não carregou em {timeout}s: {e}")
            return None
    
    def _aguardar_elemento_clicavel(self, session, by, value, timeout=10, descricao="elemento"):
        """Aguarda um elemento ficar clicável dinamicamente"""
        try:
            wait = WebDriverWait(session['driver'], timeout)
            elemento = wait.until(EC.element_to_be_clickable((by, value)))
            logger.info(f"✅ {descricao} ficou clicável em {timeout}s")
            return elemento
        except Exception as e:
            logger.warning(f"⚠️ {descricao} não ficou clicável em {timeout}s: {e}")
            return None

    def _validar_resultado(self, resultado):
        """Valida se o resultado da extração está consistente"""
        try:
            if not resultado:
                logger.error("❌ Resultado é None")
                return False
            
            campos_obrigatorios = ['processo', 'total_movimentacoes_processadas', 'total_anexos_extraidos', 'anexos', 'partes_processo']
            for campo in campos_obrigatorios:
                if campo not in resultado:
                    logger.error(f"❌ Campo obrigatório '{campo}' não encontrado no resultado")
                    return False
            
            # Validar anexos
            for i, anexo in enumerate(resultado['anexos']):
                campos_anexo = ['nome_arquivo', 'tamanho_texto', 'is_pdf']
                for campo in campos_anexo:
                    if campo not in anexo:
                        logger.error(f"❌ Campo obrigatório '{campo}' não encontrado no anexo {i+1}")
                        return False
                
                # Validar tamanho_texto
                if anexo['tamanho_texto'] < 0:
                    logger.error(f"❌ tamanho_texto negativo no anexo {i+1}: {anexo['tamanho_texto']}")
                    return False
            
            # Validar partes do processo
            if not isinstance(resultado['partes_processo'], dict):
                logger.error("❌ partes_processo não é um dicionário")
                return False
            
            polos_esperados = ['polo_ativo', 'polo_passivo', 'outros']
            for polo in polos_esperados:
                if polo not in resultado['partes_processo']:
                    logger.error(f"❌ Polo '{polo}' não encontrado em partes_processo")
                    return False
                if not isinstance(resultado['partes_processo'][polo], list):
                    logger.error(f"❌ Polo '{polo}' não é uma lista")
                    return False
            
            logger.info("✅ Validação do resultado concluída com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na validação do resultado: {e}")
            return False
    
    def _extrair_partes_processo(self, session):
        """Extrai as partes envolvidas no processo (polo ativo e passivo)"""
        try:
            logger.info("👥 PASSO 6: Extraindo partes envolvidas no processo...")
            
            # Tentar primeiro a página 4 (estrutura com endereços)
            url_partes_pagina4 = "https://projudi.tjgo.jus.br/ProcessoParte?PaginaAtual=4"
            session['driver'].get(url_partes_pagina4)
            time.sleep(2)  # Reduzido de 3 para 2 segundos
            
            # Aguardar carregamento da página
            logger.info("⏳ Aguardando carregamento da página de partes (página 4)...")
            time.sleep(3)  # Reduzido de 5 para 3 segundos
            
            # Verificar se a página carregou corretamente
            if "Usuário inválido ou sessão expirada" in session['driver'].page_source:
                logger.error("❌ Sessão expirada ao acessar página de partes")
                return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
            
            # Salvar HTML para debug
            html_content = session['driver'].page_source
            with open('debug_partes.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info("📄 HTML da página de partes salvo em debug_partes.html")
            
            # Tentar extrair com estrutura da página 4
            partes = self._extrair_partes_pagina4(html_content)
            
            # Se não encontrou partes na página 4, tentar página 2
            if not partes['polo_ativo'] and not partes['polo_passivo']:
                logger.info("⚠️ Nenhuma parte encontrada na página 4, tentando página 2...")
                
                url_partes_pagina2 = "https://projudi.tjgo.jus.br/ProcessoParte?PaginaAtual=2"
                session['driver'].get(url_partes_pagina2)
                time.sleep(2)
                
                logger.info("⏳ Aguardando carregamento da página de partes (página 2)...")
                time.sleep(3)
                
                # Verificar se a página carregou corretamente
                if "Usuário inválido ou sessão expirada" in session['driver'].page_source:
                    logger.error("❌ Sessão expirada ao acessar página 2 de partes")
                    return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
                
                # Salvar HTML da página 2 para debug
                html_content_pagina2 = session['driver'].page_source
                with open('debug_partes_pagina2.html', 'w', encoding='utf-8') as f:
                    f.write(html_content_pagina2)
                logger.info("📄 HTML da página 2 de partes salvo em debug_partes_pagina2.html")
                
                # Extrair com estrutura da página 2
                partes = self._extrair_partes_pagina2(html_content_pagina2)
            
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes do processo: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
    
    def _extrair_partes_pagina4(self, html_content):
        """Extrai partes da página 4 (estrutura com endereços)"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            logger.info("🔍 Analisando estrutura da página 4...")
            
            partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
            
            # Na página 4, procurar por seções de partes com endereços
            # Estrutura: procurar por elementos que contenham nomes e endereços
            elementos_parte = soup.find_all(['tr', 'div'], class_=lambda x: x and ('parte' in x.lower() or 'nome' in x.lower()))
            
            if not elementos_parte:
                # Tentar encontrar por texto que contenha "Nome"
                elementos_parte = soup.find_all(string=re.compile(r'Nome', re.IGNORECASE))
                elementos_parte = [elem.parent for elem in elementos_parte if elem.parent]
            
            logger.info(f"📋 Encontrados {len(elementos_parte)} elementos de parte na página 4")
            
            for elemento in elementos_parte:
                texto_completo = elemento.get_text(strip=True)
                
                # Extrair nome da parte (após "Nome")
                match = re.search(r'Nome\s+(.+)', texto_completo, re.IGNORECASE)
                if match:
                    nome_parte = match.group(1).strip()
                    nome_limpo = self._limpar_nome_parte(nome_parte)
                    
                    # Determinar tipo baseado no contexto
                    tipo_parte = self._determinar_tipo_parte(texto_completo)
                    
                    # Extrair endereço se disponível
                    endereco = self._extrair_endereco_parte(elemento)
                    
                    parte_info = {
                        'nome': nome_limpo,
                        'tipo': tipo_parte,
                        'endereco': endereco
                    }
                    
                    # Adicionar ao polo apropriado (assumir passivo se não especificado)
                    if 'ativo' in texto_completo.lower() or 'promovente' in texto_completo.lower():
                        partes['polo_ativo'].append(parte_info)
                        logger.info(f"  👤 Parte encontrada: {nome_limpo} (polo_ativo)")
                    else:
                        partes['polo_passivo'].append(parte_info)
                        logger.info(f"  👤 Parte encontrada: {nome_limpo} (polo_passivo)")
            
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes da página 4: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
    
    def _extrair_partes_pagina2(self, html_content):
        """Extrai partes da página 2 (estrutura padrão)"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Procurar por fieldsets que contêm as partes
            fieldsets = soup.find_all('fieldset')
            logger.info(f"📋 Encontrados {len(fieldsets)} fieldsets de partes")
            
            partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
            
            for fieldset in fieldsets:
                # Verificar o título do fieldset
                legend = fieldset.find('legend')
                if not legend:
                    continue
                
                titulo = legend.get_text(strip=True).upper()
                logger.info(f"🔍 Analisando fieldset: {titulo}")
                
                if 'POLO ATIVO' in titulo:
                    partes_encontradas = self._extrair_partes_do_fieldset(fieldset, 'polo_ativo')
                    partes['polo_ativo'].extend(partes_encontradas)
                elif 'POLO PASSIVO' in titulo:
                    partes_encontradas = self._extrair_partes_do_fieldset(fieldset, 'polo_passivo')
                    partes['polo_passivo'].extend(partes_encontradas)
                elif 'OUTRAS' in titulo or 'SUJEITOS' in titulo:
                    partes_encontradas = self._extrair_partes_do_fieldset(fieldset, 'outros')
                    partes['outros'].extend(partes_encontradas)
            
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes da página 2: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
    
    def _extrair_partes_pagina6(self, html_content):
        """Extrai partes da página 6 (estrutura alternativa)"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            logger.info("🔍 Analisando estrutura da página 6...")
            
            partes = {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
            
            # Na página 6, procurar por tabelas ou divs com as partes
            # Estrutura alternativa: procurar por elementos que contenham nomes
            elementos_parte = soup.find_all(['tr', 'div'], class_=lambda x: x and ('parte' in x.lower() or 'nome' in x.lower()))
            
            if not elementos_parte:
                # Tentar encontrar por texto que contenha "Nome"
                elementos_parte = soup.find_all(text=re.compile(r'Nome', re.IGNORECASE))
                elementos_parte = [elem.parent for elem in elementos_parte if elem.parent]
            
            logger.info(f"📋 Encontrados {len(elementos_parte)} elementos de parte na página 6")
            
            for elemento in elementos_parte:
                texto_completo = elemento.get_text(strip=True)
                
                # Extrair nome da parte (após "Nome")
                match = re.search(r'Nome\s+(.+)', texto_completo, re.IGNORECASE)
                if match:
                    nome_parte = match.group(1).strip()
                    nome_limpo = self._limpar_nome_parte(nome_parte)
                    
                    # Determinar tipo baseado no contexto
                    tipo_parte = self._determinar_tipo_parte(texto_completo)
                    
                    # Extrair endereço se disponível
                    endereco = self._extrair_endereco_parte(elemento)
                    
                    parte_info = {
                        'nome': nome_limpo,
                        'tipo': tipo_parte,
                        'endereco': endereco
                    }
                    
                    # Adicionar ao polo apropriado (assumir passivo se não especificado)
                    if 'ativo' in texto_completo.lower() or 'promovente' in texto_completo.lower():
                        partes['polo_ativo'].append(parte_info)
                        logger.info(f"  👤 Parte encontrada: {nome_limpo} (polo_ativo)")
                    else:
                        partes['polo_passivo'].append(parte_info)
                        logger.info(f"  👤 Parte encontrada: {nome_limpo} (polo_passivo)")
            
            return partes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes da página 6: {e}")
            return {'polo_ativo': [], 'polo_passivo': [], 'outros': []}
    
    def _extrair_partes_do_fieldset(self, fieldset, tipo_polo):
        """Extrai partes de um fieldset específico"""
        partes_encontradas = []
        
        try:
            # Procurar por elementos que contenham nomes de partes
            elementos_nome = fieldset.find_all(['td', 'div', 'span'], string=re.compile(r'Nome', re.IGNORECASE))
            
            for elemento in elementos_nome:
                # Pegar o próximo elemento que contenha o nome
                nome_elemento = elemento.find_next_sibling()
                if not nome_elemento:
                    continue
                
                nome_parte = nome_elemento.get_text(strip=True)
                if nome_parte and nome_parte != 'Nome':
                    nome_limpo = self._limpar_nome_parte(nome_parte)
                    
                    # Determinar tipo da parte
                    tipo_parte = self._determinar_tipo_parte(nome_elemento.get_text())
                    
                    # Extrair endereço
                    endereco = self._extrair_endereco_parte(nome_elemento.parent)
                    
                    parte_info = {
                        'nome': nome_limpo,
                        'tipo': tipo_parte,
                        'endereco': endereco
                    }
                    
                    partes_encontradas.append(parte_info)
                    logger.info(f"  👤 Parte encontrada: {nome_limpo} ({tipo_polo})")
            
            return partes_encontradas
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair partes do fieldset: {e}")
            return []
    
    def _determinar_tipo_parte(self, texto):
        """Determina o tipo da parte baseado no texto"""
        texto_lower = texto.lower()
        
        if 'promovente' in texto_lower:
            return 'Promovente'
        elif 'promovido' in texto_lower:
            return 'Promovido'
        elif 'citado' in texto_lower:
            return 'Citado'
        elif 'réu' in texto_lower:
            return 'Réu'
        elif 'autor' in texto_lower:
            return 'Autor'
        else:
            return 'Parte'
    
    def _extrair_endereco_parte(self, elemento):
        """Extrai endereço da parte do elemento HTML"""
        try:
            # Procurar por elementos que contenham endereço
            endereco_elementos = elemento.find_all(['td', 'div', 'span'], string=re.compile(r'Endereço|Rua|Av\.|Avenida|Bairro|CEP', re.IGNORECASE))
            
            for elem in endereco_elementos:
                texto_endereco = elem.get_text(strip=True)
                if len(texto_endereco) > 10:  # Endereço deve ter pelo menos 10 caracteres
                    return texto_endereco
            
            # Se não encontrou elementos específicos, procurar por texto que pareça endereço
            texto_completo = elemento.get_text()
            # Padrão para endereços brasileiros
            padrao_endereco = r'[A-Z][A-Z\s]+nº?\s*\d+[^.]*'
            match = re.search(padrao_endereco, texto_completo)
            if match:
                return match.group(0).strip()
            
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair endereço: {e}")
            return ""
    
    def _limpar_nome_parte(self, nome_completo):
        """Limpa o nome da parte removendo tags HTML e informações extras"""
        try:
            # Remover tags HTML
            nome_limpo = re.sub(r'<[^>]+>', '', nome_completo)
            
            # Remover palavras-chave como "Citado", "Réu", etc.
            palavras_remover = ['citado', 'réu', 'autor', 'requerente', 'requerido']
            for palavra in palavras_remover:
                nome_limpo = re.sub(rf'\b{palavra}\b', '', nome_limpo, flags=re.IGNORECASE)
                # Também remover sem espaços (ex: "ClubeCitado" -> "Clube")
                nome_limpo = re.sub(rf'{palavra}', '', nome_limpo, flags=re.IGNORECASE)
            
            # Limpar espaços extras e caracteres especiais
            nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()
            nome_limpo = re.sub(r'[^\w\s\.\-]', '', nome_limpo)  # Manter apenas letras, números, espaços, pontos e hífens
            
            # Remover espaços duplos novamente após limpeza
            nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()
            
            return nome_limpo
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar nome da parte: {e}")
            return nome_completo


def main():
    """Função principal para testar a extração de anexos"""
    try:
        # Criar instância da classe
        projudi_anexos = ProjudiAnexosAvancado()
        
        # Número do processo para teste
        numero_processo = "0508844-37.2007.8.09.0024"
        
        # Processar processo com anexos das últimas 5 movimentações
        resultado = projudi_anexos.processar_processo_com_anexos(numero_processo, num_movimentacoes=5)
        
        if resultado:
            print("\n" + "="*80)
            print("🎯 RESULTADO FINAL DA API")
            print("="*80)
            
            # Resumo da resposta da API
            print(f"📋 Processo: {resultado['processo']}")
            print(f"📁 Movimentações processadas: {resultado['total_movimentacoes_processadas']}")
            print(f"📎 Total de anexos extraídos: {resultado['total_anexos_extraidos']}")
            print(f"📄 PDFs processados: {resultado['total_pdfs_processados']}")
            print(f"⏰ Timestamp: {resultado['timestamp_extração']}")
            
            # Resumo das partes
            partes = resultado.get('partes_processo', {})
            print(f"\n👥 PARTES ENVOLVIDAS:")
            print(f"  📋 Polo Ativo: {len(partes.get('polo_ativo', []))} partes")
            print(f"  📋 Polo Passivo: {len(partes.get('polo_passivo', []))} partes")
            print(f"  📋 Outros: {len(partes.get('outros', []))} partes")
            
            # Detalhes das partes
            for polo, partes_list in partes.items():
                if partes_list:
                    print(f"\n  📋 {polo.replace('_', ' ').title()}:")
                    for i, parte in enumerate(partes_list, 1):
                        nome = parte.get('nome', 'N/A')
                        documento = parte.get('documento', '')
                        tipo = parte.get('tipo', '')
                        endereco = parte.get('endereco', '')
                        
                        print(f"    {i}. {nome}")
                        if documento:
                            print(f"       📄 Documento: {documento}")
                        if tipo:
                            print(f"       🏷️ Tipo: {tipo}")
                        if endereco:
                            print(f"       📍 Endereço: {endereco}")
            
            print(f"\n📄 ANEXOS EXTRAÍDOS:")
            for i, anexo in enumerate(resultado['anexos'], 1):
                print(f"   {i}. {anexo['nome_arquivo']}")
                print(f"     📝 Tamanho: {anexo['tamanho_texto']} caracteres")
                print(f"     📅 Movimentação: {anexo.get('movimentacao_numero', 'N/A')}")
                print(f"     📄 Tipo: {'PDF' if anexo.get('is_pdf') else 'HTML'}")
                print(f"     📥 Download: {'Sim' if anexo.get('download_realizado') else 'Não'}")
                if anexo.get('conteudo_pdf'):
                    print(f"     📄 Conteúdo PDF: {anexo.get('tamanho_conteudo_pdf', 0)} caracteres")
                    if anexo.get('metodo_extracao'):
                        print(f"     🔍 Método: {anexo.get('metodo_extracao')}")
                print()
            
            print("✅ Extração concluída com sucesso!")
        else:
            print("❌ Falha na extração")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 