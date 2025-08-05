#!/usr/bin/env python3
"""
API Principal PROJUDI v4 com FastAPI e Playwright
"""

import asyncio
import os
import uuid
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from core.session_manager import session_manager, get_session
from core.cache_manager import cache_manager
from core.concurrency_manager import concurrency_manager
from nivel_1.busca import busca_manager, TipoBusca, ResultadoBusca
from nivel_2.processo import processo_manager, DadosProcesso
from nivel_3.anexos import anexos_manager

from api.models import (
    BuscaRequest, BuscaRequestN8N, BuscaMultiplaRequest, BuscaResponse, BuscaMultiplaResponse,
    StatusResponse, HealthResponse, ProcessoDetalhadoResponse,
    MovimentacaoResponse, ParteEnvolvidaResponse, AnexoResponse, ProcessoSimples
)

# Inicialização da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando PROJUDI API v4...")
    await session_manager.initialize()
    logger.info("✅ API inicializada com sucesso")
    
    yield
    
    # Shutdown
    logger.info("🔄 Finalizando PROJUDI API v4...")
    await session_manager.shutdown()
    anexos_manager.limpar_arquivos_temporarios()
    logger.info("✅ API finalizada")

# Criar aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API para extração de dados do sistema PROJUDI usando Playwright",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Armazenamento de requisições em andamento
requisicoes_ativas: Dict[str, Dict] = {}

class ProjudiService:
    """Serviço principal da API"""
    
    @staticmethod
    async def processar_busca_completa(
        request: BuscaRequest,
        request_id: str
    ) -> BuscaResponse:
        """Processa uma busca completa com todos os níveis"""
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Processando busca {request_id}: {request.tipo_busca} = {request.valor}")
            
            # Aplicar credenciais customizadas se fornecidas
            credenciais_originais = {}
            if request.usuario or request.senha or request.serventia:
                credenciais_originais = ProjudiService._aplicar_credenciais_customizadas(request)
            
            # Nível 1: Busca (ou busca direta para processo específico)
            async with get_session() as session:
                # Detectar automaticamente se é busca por processo específico
                # Se o valor não parece ser CPF nem nome, tratar como processo
                import re
                cpf_pattern = r'^\d{3}\.\d{3}\.\d{3}-\d{2}$'
                nome_pattern = r'^[A-Za-zÀ-ÿ\s]+$'
                
                is_processo_especifico = (
                    request.tipo_busca == "processo" or
                    (not re.match(cpf_pattern, request.valor) and 
                     not re.match(nome_pattern, request.valor) and
                     len(request.valor) > 10)  # Processos têm números longos
                )
                
                if is_processo_especifico:
                    logger.info(f"🔍 Busca por processo específico detectada: {request.valor}")
                    
                    # Buscar diretamente no nível 2
                    dados_processo = await processo_manager.buscar_processo_especifico(
                        session, 
                        request.valor,
                        request.limite_movimentacoes
                    )
                    
                    if dados_processo:
                        # Converter para response
                        processo_detalhado = await ProjudiService._converter_dados_processo(
                            dados_processo, 
                            []  # Sem anexos por padrão
                        )
                        
                        return BuscaResponse(
                            status="success",
                            request_id=request_id,
                            tipo_busca=request.tipo_busca,
                            valor_busca=request.valor,
                            total_processos_encontrados=1,
                            processos_simples=[
                                ProcessoSimples(
                                    numero=dados_processo.numero,
                                    classe=dados_processo.classe,
                                    assunto=dados_processo.assunto,
                                    id_processo="processo_direto",
                                    indice=1
                                )
                            ],
                            processos_detalhados=[processo_detalhado],
                            tempo_execucao=time.time() - start_time
                        )
                    else:
                        return BuscaResponse(
                            status="error",
                            request_id=request_id,
                            tipo_busca=request.tipo_busca,
                            valor_busca=request.valor,
                            erro="Processo não encontrado",
                            tempo_execucao=time.time() - start_time
                        )
                
                # Para CPF e NOME, usar método normal do nível 1
                resultado_busca = await busca_manager.executar_busca(
                    session, 
                    TipoBusca(request.tipo_busca), 
                    request.valor
                )
                
                if not resultado_busca.sucesso:
                    return BuscaResponse(
                        status="error",
                        request_id=request_id,
                        tipo_busca=request.tipo_busca,
                        valor_busca=request.valor,
                        erro=resultado_busca.mensagem,
                        tempo_execucao=time.time() - start_time
                    )
                
                # Converter processos encontrados para response
                processos_simples = [
                    ProcessoSimples(
                        numero=p.numero,
                        classe=p.classe,
                        assunto=p.assunto,
                        id_processo=p.id_processo,
                        indice=p.indice
                    )
                    for p in resultado_busca.processos
                ]
                
                processos_detalhados = []
                
                # Nível 2 e 3: Processar cada processo encontrado (se movimentacoes = True)
                if resultado_busca.processos and request.movimentacoes:
                    for i, processo in enumerate(resultado_busca.processos):
                        try:
                            logger.info(f"📄 Processando processo {i+1}/{len(resultado_busca.processos)}: {processo.numero}")
                            
                            # Para processos após o primeiro, voltar à lista
                            if i > 0:
                                try:
                                    await session.page.goto("https://projudi.tjgo.jus.br/BuscaProcesso", 
                                                          wait_until='domcontentloaded', timeout=60000)
                                    # Re-executar busca por CPF/nome/processo conforme tipo
                                    if request.tipo_busca == "cpf":
                                        await busca_manager._buscar_por_cpf(session.page, request.valor)
                                    elif request.tipo_busca == "nome":
                                        await busca_manager._buscar_por_nome(session.page, request.valor)
                                    elif request.tipo_busca == "processo":
                                        await busca_manager._buscar_por_processo(session.page, request.valor)
                                    await asyncio.sleep(2)  # Aguardar estabilizar
                                except Exception as nav_error:
                                    logger.warning(f"⚠️ Erro na re-navegação: {nav_error}")
                                    await asyncio.sleep(3)
                            
                            # Acessar processo
                            if await processo_manager.acessar_processo(session, processo):
                                
                                # Extrair dados do processo (Nível 2)
                                dados_processo = await processo_manager.extrair_dados_processo(
                                    session, 
                                    processo, 
                                    request.limite_movimentacoes
                                )
                                
                                # Extrair anexos se solicitado (Nível 3)
                                anexos_processados = []
                                if request.extrair_anexos and dados_processo.movimentacoes:
                                    # Solicitar acesso aos anexos
                                    await anexos_manager.solicitar_acesso_anexos(session)
                                    
                                    # Acessar página de navegação
                                    if await anexos_manager.acessar_navegacao_arquivos(session):
                                        anexos_processados = await anexos_manager.extrair_anexos_movimentacoes(
                                            session,
                                            dados_processo.movimentacoes,
                                            limite=3  # Limitar a 3 anexos por padrão
                                        )
                                
                                # Converter para response
                                processo_detalhado = await ProjudiService._converter_dados_processo(
                                    dados_processo, 
                                    anexos_processados
                                )
                                processos_detalhados.append(processo_detalhado)
                                
                        except Exception as e:
                            logger.error(f"❌ Erro ao processar processo {processo.numero}: {e}")
                            continue
                
                # Criar response final
                response = BuscaResponse(
                    request_id=request_id,
                    tipo_busca=request.tipo_busca,
                    valor_busca=request.valor,
                    total_processos_encontrados=len(processos_simples),
                    processos_simples=processos_simples,
                    processos_detalhados=processos_detalhados,
                    tempo_execucao=time.time() - start_time
                )
                
                logger.info(f"✅ Busca {request_id} concluída em {response.tempo_execucao:.2f}s")
                
                # Restaurar credenciais originais se foram alteradas
                if credenciais_originais:
                    ProjudiService._restaurar_credenciais_originais(credenciais_originais)
                
                return response
                
        except Exception as e:
            logger.error(f"❌ Erro na busca {request_id}: {e}")
            
            # Restaurar credenciais originais em caso de erro
            if 'credenciais_originais' in locals() and credenciais_originais:
                ProjudiService._restaurar_credenciais_originais(credenciais_originais)
            
            return BuscaResponse(
                status="error",
                request_id=request_id,
                tipo_busca=request.tipo_busca,
                valor_busca=request.valor,
                erro=str(e),
                tempo_execucao=time.time() - start_time
            )
    
    @staticmethod
    async def _converter_dados_processo(
        dados: DadosProcesso, 
        anexos: List
    ) -> ProcessoDetalhadoResponse:
        """Converte dados do processo para response"""
        
        # Converter movimentações
        movimentacoes = [
            MovimentacaoResponse(
                numero=m.numero,
                tipo=m.tipo,
                descricao=m.descricao,
                data=m.data,
                usuario=m.usuario,
                tem_anexo=m.tem_anexo,
                numero_processo=m.numero_processo
            )
            for m in dados.movimentacoes
        ]
        
        # Converter partes
        partes_ativo = [
            ParteEnvolvidaResponse(
                nome=p.nome,
                tipo=p.tipo,
                documento=p.documento,
                endereco=p.endereco,
                telefone=p.telefone,
                email=p.email,
                advogado=p.advogado,
                oab=p.oab
            )
            for p in dados.partes_polo_ativo
        ]
        
        partes_passivo = [
            ParteEnvolvidaResponse(
                nome=p.nome,
                tipo=p.tipo,
                documento=p.documento,
                endereco=p.endereco,
                telefone=p.telefone,
                email=p.email,
                advogado=p.advogado,
                oab=p.oab
            )
            for p in dados.partes_polo_passivo
        ]
        
        outras_partes = [
            ParteEnvolvidaResponse(
                nome=p.nome,
                tipo=p.tipo,
                documento=p.documento,
                endereco=p.endereco,
                telefone=p.telefone,
                email=p.email,
                advogado=p.advogado,
                oab=p.oab
            )
            for p in dados.outras_partes
        ]
        
        # Converter anexos
        anexos_response = [
            AnexoResponse(
                id_arquivo=a.anexo_info.id_arquivo,
                nome_arquivo=a.anexo_info.nome_arquivo,
                tipo_arquivo=a.anexo_info.tipo_arquivo,
                tamanho_bytes=a.anexo_info.tamanho_bytes,
                movimentacao_numero=a.anexo_info.movimentacao_numero,
                conteudo_extraido=a.conteudo_extraido,
                tamanho_conteudo=a.tamanho_conteudo,
                metodo_extracao=a.metodo_extracao,
                sucesso_processamento=a.sucesso_processamento,
                tempo_processamento=a.tempo_processamento
            )
            for a in anexos
        ]
        
        return ProcessoDetalhadoResponse(
            numero=dados.numero,
            classe=dados.classe,
            assunto=dados.assunto,
            situacao=dados.situacao,
            data_autuacao=dados.data_autuacao,
            data_distribuicao=dados.data_distribuicao,
            valor_causa=dados.valor_causa,
            orgao_julgador=dados.orgao_julgador,
            id_acesso=dados.id_acesso,
            movimentacoes=movimentacoes,
            total_movimentacoes=len(movimentacoes),
            partes_polo_ativo=partes_ativo,
            partes_polo_passivo=partes_passivo,
            outras_partes=outras_partes,
            total_partes=len(partes_ativo) + len(partes_passivo) + len(outras_partes),
            anexos=anexos_response,
            total_anexos=len(anexos_response)
        )
    
    @staticmethod
    def _aplicar_credenciais_customizadas(request: BuscaRequest) -> Dict[str, str]:
        """Aplica credenciais customizadas temporariamente"""
        credenciais_originais = {}
        
        if request.usuario:
            credenciais_originais['projudi_user'] = settings.projudi_user
            settings.projudi_user = request.usuario
            logger.info(f"🔐 Usando usuário customizado: {request.usuario}")
        
        if request.senha:
            credenciais_originais['projudi_pass'] = settings.projudi_pass
            settings.projudi_pass = request.senha
            logger.info("🔐 Usando senha customizada")
        
        if request.serventia:
            credenciais_originais['default_serventia'] = settings.default_serventia
            settings.default_serventia = request.serventia
            logger.info(f"🏢 Usando serventia customizada: {request.serventia}")
        
        return credenciais_originais
    
    @staticmethod
    def _restaurar_credenciais_originais(credenciais_originais: Dict[str, str]):
        """Restaura as credenciais originais"""
        if 'projudi_user' in credenciais_originais:
            settings.projudi_user = credenciais_originais['projudi_user']
        
        if 'projudi_pass' in credenciais_originais:
            settings.projudi_pass = credenciais_originais['projudi_pass']
        
        if 'default_serventia' in credenciais_originais:
            settings.default_serventia = credenciais_originais['default_serventia']
        
        logger.info("🔄 Credenciais originais restauradas")

# Endpoints da API

@app.get("/", response_model=Dict)
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "api": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "features": [
            "Playwright Integration",
            "Pool de Sessões Assíncronas",
            "Extração de Anexos",
            "Processamento de PDFs",
            "3 Níveis de Processamento",
            "API Assíncrona"
        ],
        "endpoints": {
            "/buscar": "Busca individual (POST)",
            "/buscar-n8n": "Busca compatível com N8N (POST)",
            "/buscar-multiplo": "Múltiplas buscas (POST)", 
            "/status": "Status da API (GET)",
            "/health": "Health check (GET)"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Status da API"""
    stats = session_manager.get_stats()
    
    # Adicionar informações de cache e concorrência
    cache_info = {
        "enabled": cache_manager.cache_enabled,
        "connected": cache_manager.is_connected,
        "url": settings.redis_url
    }
    
    concurrency_info = concurrency_manager.get_stats()
    
    return StatusResponse(
        total_sessoes=stats['total_sessions'],
        sessoes_ocupadas=stats['busy_sessions'],
        sessoes_disponiveis=stats['available_sessions'],
        uptime="Online",
        cache=cache_info,
        concurrency=concurrency_info
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check da API"""
    try:
        # Verificar serviços
        services = {
            "session_manager": session_manager.playwright is not None,
            "downloads_dir": settings.downloads_dir and os.path.exists(settings.downloads_dir)
        }
        
        healthy = all(services.values())
        
        return HealthResponse(
            healthy=healthy,
            services=services,
            details=session_manager.get_stats()
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no health check: {e}")
        return HealthResponse(
            healthy=False,
            services={"error": str(e)}
        )

@app.post("/buscar", response_model=BuscaResponse)
async def buscar_processo(request: BuscaRequest, background_tasks: BackgroundTasks):
    """Executa busca de processo"""
    try:
        request_id = str(uuid.uuid4())
        
        # Validar request
        if not request.valor.strip():
            raise HTTPException(status_code=400, detail="Valor de busca não pode estar vazio")
        
        # Adicionar à lista de requisições ativas
        requisicoes_ativas[request_id] = {
            "status": "processing",
            "start_time": time.time(),
            "request": request
        }
        
        # Processar busca
        try:
            response = await ProjudiService.processar_busca_completa(request, request_id)
            
            # Atualizar status
            requisicoes_ativas[request_id]["status"] = "completed"
            requisicoes_ativas[request_id]["response"] = response
            
            # Agendar limpeza
            background_tasks.add_task(
                limpar_requisicao_ativa, 
                request_id, 
                delay=300  # 5 minutos
            )
            
            return response
            
        except Exception as e:
            # Atualizar status de erro
            requisicoes_ativas[request_id]["status"] = "error"
            requisicoes_ativas[request_id]["error"] = str(e)
            raise
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /buscar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/buscar-n8n", response_model=BuscaResponse)
async def buscar_processo_n8n(request: BuscaRequestN8N, background_tasks: BackgroundTasks):
    """Executa busca de processo com formato N8N"""
    try:
        # Converter request N8N para formato padrão
        busca_request = request.to_busca_request()
        
        # Usar o endpoint padrão
        return await buscar_processo(busca_request, background_tasks)
        
    except ValueError as e:
        logger.error(f"❌ Erro de validação N8N: {e}")
        raise HTTPException(status_code=400, detail=f"Erro de validação: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /buscar-n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/buscar-multiplo", response_model=BuscaMultiplaResponse)
async def buscar_multiplo(request: BuscaMultiplaRequest):
    """Executa múltiplas buscas"""
    try:
        if not request.buscas:
            raise HTTPException(status_code=400, detail="Lista de buscas não pode estar vazia")
        
        if len(request.buscas) > 10:
            raise HTTPException(status_code=400, detail="Máximo de 10 buscas simultâneas")
        
        start_time = time.time()
        resultados = {}
        
        if request.paralelo:
            # Executar em paralelo
            tasks = []
            for i, busca in enumerate(request.buscas):
                request_id = f"batch_{int(time.time())}_{i}"
                task = ProjudiService.processar_busca_completa(busca, request_id)
                tasks.append((f"busca_{i}", task))
            
            # Aguardar todas as tasks
            for busca_id, task in tasks:
                try:
                    resultado = await task
                    resultados[busca_id] = resultado
                except Exception as e:
                    logger.error(f"❌ Erro na {busca_id}: {e}")
                    resultados[busca_id] = BuscaResponse(
                        status="error",
                        request_id="",
                        tipo_busca="",
                        valor_busca="",
                        erro=str(e)
                    )
        else:
            # Executar sequencialmente
            for i, busca in enumerate(request.buscas):
                try:
                    request_id = f"seq_{int(time.time())}_{i}"
                    resultado = await ProjudiService.processar_busca_completa(busca, request_id)
                    resultados[f"busca_{i}"] = resultado
                except Exception as e:
                    logger.error(f"❌ Erro na busca {i}: {e}")
                    resultados[f"busca_{i}"] = BuscaResponse(
                        status="error",
                        request_id="",
                        tipo_busca="",
                        valor_busca="",
                        erro=str(e)
                    )
        
        # Determinar status geral
        total_buscas = len(request.buscas)
        buscas_sucesso = sum(1 for r in resultados.values() if r.status == "success")
        
        if buscas_sucesso == total_buscas:
            status = "success"
        elif buscas_sucesso > 0:
            status = "partial"
        else:
            status = "error"
        
        return BuscaMultiplaResponse(
            status=status,
            total_buscas=total_buscas,
            buscas_concluidas=len(resultados),
            resultados=resultados,
            tempo_total=time.time() - start_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /buscar-multiplo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/requisicoes/{request_id}")
async def get_requisicao_status(request_id: str):
    """Obtém status de uma requisição"""
    if request_id not in requisicoes_ativas:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    
    return requisicoes_ativas[request_id]

@app.post("/cleanup")
async def cleanup():
    """Limpa recursos da API"""
    try:
        # Limpar arquivos temporários
        anexos_manager.limpar_arquivos_temporarios()
        
        # Limpar requisições antigas
        agora = time.time()
        antigas = [
            req_id for req_id, dados in requisicoes_ativas.items()
            if agora - dados["start_time"] > 3600  # 1 hora
        ]
        
        for req_id in antigas:
            del requisicoes_ativas[req_id]
        
        return {
            "status": "success",
            "arquivos_limpos": True,
            "requisicoes_antigas_removidas": len(antigas),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/status")
async def get_cache_status():
    """Retorna status do cache Redis"""
    try:
        stats = {
            "enabled": cache_manager.cache_enabled,
            "connected": cache_manager.is_connected,
            "url": settings.redis_url
        }
        
        if cache_manager.is_connected:
            # Testar conexão
            try:
                await cache_manager.redis_client.ping()
                stats["status"] = "online"
            except:
                stats["status"] = "error"
        else:
            stats["status"] = "disabled"
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar cache: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar cache: {str(e)}")

@app.post("/cache/clear")
async def clear_cache():
    """Limpa todo o cache Redis"""
    try:
        if not cache_manager.is_connected:
            return {"status": "disabled", "message": "Cache Redis não está habilitado"}
        
        success = await cache_manager.clear_all()
        if success:
            return {"status": "success", "message": "Cache limpo com sucesso"}
        else:
            return {"status": "error", "message": "Falha ao limpar cache"}
        
    except Exception as e:
        logger.error(f"❌ Erro ao limpar cache: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar cache: {str(e)}")

@app.get("/concurrency/stats")
async def get_concurrency_stats():
    """Retorna estatísticas de concorrência"""
    try:
        stats = concurrency_manager.get_stats()
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

@app.post("/concurrency/reset")
async def reset_concurrency_stats():
    """Reseta estatísticas de concorrência"""
    try:
        concurrency_manager.reset_stats()
        return {
            "status": "success",
            "message": "Estatísticas resetadas com sucesso",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao resetar estatísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao resetar estatísticas: {str(e)}")

# Funções auxiliares
async def limpar_requisicao_ativa(request_id: str, delay: int = 0):
    """Remove requisição da lista ativa após delay"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    if request_id in requisicoes_ativas:
        del requisicoes_ativas[request_id]
        logger.info(f"🧹 Requisição {request_id} removida da lista ativa")

# Executar aplicação
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )