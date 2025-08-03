#!/usr/bin/env python3
"""
Modelos Pydantic para a API PROJUDI v4
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Modelos de Request

class ParametroN8N(BaseModel):
    """Parâmetro individual do N8N"""
    name: str
    value: str

class BuscaRequestN8N(BaseModel):
    """Request do N8N com estrutura bodyParameters"""
    bodyParameters: Dict[str, List[ParametroN8N]] = Field(alias="bodyParameters")
    
    def to_busca_request(self) -> 'BuscaRequest':
        """Converte para BuscaRequest padrão"""
        params = {}
        
        # Extrair parâmetros da estrutura N8N
        if "parameters" in self.bodyParameters:
            for param in self.bodyParameters["parameters"]:
                # Converter valores booleanos
                if param.name in ["movimentacoes", "extrair_anexos", "extrair_partes"]:
                    params[param.name] = param.value.lower() in ["true", "1", "yes", "sim"]
                # Converter valores numéricos
                elif param.name == "limite_movimentacoes" and param.value:
                    try:
                        params[param.name] = int(param.value)
                    except ValueError:
                        params[param.name] = None
                else:
                    params[param.name] = param.value
        
        # Valores padrão se não fornecidos
        defaults = {
            "movimentacoes": True,
            "extrair_anexos": False,
            "extrair_partes": True,
            "limite_movimentacoes": None,
        }
        
        for key, default_value in defaults.items():
            if key not in params:
                params[key] = default_value
        
        return BuscaRequest(**params)
class BuscaRequest(BaseModel):
    """Request para busca de processos"""
    tipo_busca: Literal["cpf", "nome", "processo"] = Field(..., description="Tipo de busca a ser realizada")
    valor: str = Field(..., description="Valor a ser buscado")
    limite_movimentacoes: Optional[int] = Field(default=None, description="Limite de movimentações a extrair")
    extrair_anexos: bool = Field(default=False, description="Se deve extrair anexos")
    extrair_partes: bool = Field(default=True, description="Se deve extrair partes envolvidas")
    movimentacoes: bool = Field(default=True, description="Se deve extrair movimentações")
    
    # Credenciais customizadas (opcional - usa .env como fallback)
    usuario: Optional[str] = Field(default=None, description="Usuário PROJUDI customizado")
    senha: Optional[str] = Field(default=None, description="Senha PROJUDI customizada")
    serventia: Optional[str] = Field(default=None, description="Serventia customizada")

class BuscaMultiplaRequest(BaseModel):
    """Request para múltiplas buscas"""
    buscas: List[BuscaRequest] = Field(..., description="Lista de buscas a serem realizadas")
    paralelo: bool = Field(default=True, description="Se deve executar em paralelo")

# Modelos de Response
class ProcessoSimples(BaseModel):
    """Processo encontrado na busca"""
    numero: str
    classe: str
    assunto: str
    id_processo: str
    indice: int

class MovimentacaoResponse(BaseModel):
    """Movimentação de um processo"""
    numero: int
    tipo: str
    descricao: str
    data: str
    usuario: str
    tem_anexo: bool

class ParteEnvolvidaResponse(BaseModel):
    """Parte envolvida no processo"""
    nome: str
    tipo: str
    documento: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    advogado: Optional[str] = None
    oab: Optional[str] = None

class AnexoResponse(BaseModel):
    """Anexo processado"""
    id_arquivo: str
    nome_arquivo: str
    tipo_arquivo: str
    tamanho_bytes: int
    movimentacao_numero: int
    conteudo_extraido: str
    tamanho_conteudo: int
    metodo_extracao: str
    sucesso_processamento: bool
    tempo_processamento: float

class ProcessoDetalhadoResponse(BaseModel):
    """Processo com dados detalhados"""
    numero: str
    classe: str
    assunto: str
    situacao: Optional[str] = None
    data_autuacao: Optional[str] = None
    data_distribuicao: Optional[str] = None
    valor_causa: Optional[str] = None
    orgao_julgador: Optional[str] = None
    
    # Movimentações
    movimentacoes: List[MovimentacaoResponse] = []
    total_movimentacoes: int = 0
    
    # Partes
    partes_polo_ativo: List[ParteEnvolvidaResponse] = []
    partes_polo_passivo: List[ParteEnvolvidaResponse] = []
    outras_partes: List[ParteEnvolvidaResponse] = []
    total_partes: int = 0
    
    # Anexos
    anexos: List[AnexoResponse] = []
    total_anexos: int = 0

class BuscaResponse(BaseModel):
    """Response para busca"""
    status: Literal["success", "error"] = "success"
    request_id: str
    tipo_busca: str
    valor_busca: str
    
    # Resultados da busca
    total_processos_encontrados: int = 0
    processos_simples: List[ProcessoSimples] = []
    
    # Dados detalhados (se solicitado)
    processos_detalhados: List[ProcessoDetalhadoResponse] = []
    
    # Metadados
    tempo_execucao: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    erro: Optional[str] = None

class BuscaMultiplaResponse(BaseModel):
    """Response para múltiplas buscas"""
    status: Literal["success", "error", "partial"] = "success"
    total_buscas: int
    buscas_concluidas: int
    resultados: Dict[str, BuscaResponse]
    tempo_total: float
    timestamp: datetime = Field(default_factory=datetime.now)

class StatusResponse(BaseModel):
    """Status da API"""
    status: Literal["online", "offline", "maintenance"] = "online"
    versao: str = "4.0.0"
    total_sessoes: int
    sessoes_ocupadas: int
    sessoes_disponiveis: int
    uptime: str
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthResponse(BaseModel):
    """Health check da API"""
    healthy: bool = True
    services: Dict[str, bool]
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None