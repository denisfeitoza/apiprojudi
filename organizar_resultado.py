#!/usr/bin/env python3
"""
Script para reorganizar resultados de busca múltipla de CPFs
Mantém todas as informações mas com estrutura mais limpa e organizada
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

def organizar_resultado(arquivo_entrada: str, arquivo_saida: str = None) -> Dict[str, Any]:
    """
    Reorganiza o resultado JSON de busca múltipla para uma estrutura mais limpa
    
    Args:
        arquivo_entrada: Caminho do arquivo JSON original
        arquivo_saida: Caminho do arquivo de saída (opcional)
    
    Returns:
        Dicionário com a estrutura reorganizada
    """
    
    # Carregar dados originais
    with open(arquivo_entrada, 'r', encoding='utf-8') as f:
        dados_originais = json.load(f)
    
    # Estrutura reorganizada
    resultado_organizado = {
        "resumo_execucao": {
            "status": dados_originais[0]["status"],
            "total_buscas": dados_originais[0]["total_buscas"],
            "buscas_concluidas": dados_originais[0]["buscas_concluidas"],
            "tempo_total_segundos": round(dados_originais[0]["tempo_total"], 2),
            "timestamp": dados_originais[0]["timestamp"]
        },
        "buscas_realizadas": []
    }
    
    # Processar cada busca
    for i in range(dados_originais[0]["total_buscas"]):
        chave_busca = f"busca_{i}"
        busca_original = dados_originais[0]["resultados"][chave_busca]
        
        busca_organizada = {
            "indice": i + 1,
            "cpf_buscado": busca_original["valor_busca"],
            "status": busca_original["status"],
            "request_id": busca_original["request_id"],
            "tempo_execucao_segundos": round(busca_original["tempo_execucao"], 2),
            "timestamp": busca_original["timestamp"],
            "total_processos_encontrados": busca_original["total_processos_encontrados"],
            "processos": []
        }
        
        # Processar processos detalhados
        for processo in busca_original["processos_detalhados"]:
            processo_organizado = {
                "numero_processo": processo["numero"],
                "classe_processual": processo["classe"],
                "assunto": processo["assunto"],
                "valor_causa": processo["valor_causa"],
                "id_acesso": processo["id_acesso"],
                "situacao": processo["situacao"],
                "data_autuacao": processo["data_autuacao"],
                "data_distribuicao": processo["data_distribuicao"],
                "orgao_julgador": processo["orgao_julgador"],
                "partes": {
                    "polo_ativo": [
                        {
                            "nome": parte["nome"],
                            "tipo": parte["tipo"],
                            "documento": parte["documento"],
                            "endereco": parte["endereco"],
                            "telefone": parte["telefone"],
                            "email": parte["email"],
                            "advogado": parte["advogado"],
                            "oab": parte["oab"]
                        }
                        for parte in processo["partes_polo_ativo"]
                    ],
                    "polo_passivo": [
                        {
                            "nome": parte["nome"],
                            "tipo": parte["tipo"],
                            "documento": parte["documento"],
                            "endereco": parte["endereco"],
                            "telefone": parte["telefone"],
                            "email": parte["email"],
                            "advogado": parte["advogado"],
                            "oab": parte["oab"]
                        }
                        for parte in processo["partes_polo_passivo"]
                    ],
                    "outras_partes": [
                        {
                            "nome": parte["nome"],
                            "tipo": parte["tipo"],
                            "documento": parte["documento"],
                            "endereco": parte["endereco"],
                            "telefone": parte["telefone"],
                            "email": parte["email"],
                            "advogado": parte["advogado"],
                            "oab": parte["oab"]
                        }
                        for parte in processo["outras_partes"]
                    ]
                },
                "total_partes": processo["total_partes"],
                "movimentacoes": [
                    {
                        "numero": mov["numero"],
                        "tipo": mov["tipo"],
                        "descricao": mov["descricao"],
                        "data": mov["data"],
                        "usuario": mov["usuario"],
                        "tem_anexo": mov["tem_anexo"]
                    }
                    for mov in processo["movimentacoes"]
                ],
                "total_movimentacoes": processo["total_movimentacoes"],
                "anexos": processo["anexos"],
                "total_anexos": processo["total_anexos"]
            }
            
            busca_organizada["processos"].append(processo_organizado)
        
        resultado_organizado["buscas_realizadas"].append(busca_organizada)
    
    # Salvar arquivo organizado
    if arquivo_saida is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"resultado_organizado_{timestamp}.json"
    
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(resultado_organizado, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Resultado organizado salvo em: {arquivo_saida}")
    print(f"📊 Resumo:")
    print(f"   - Total de buscas: {resultado_organizado['resumo_execucao']['total_buscas']}")
    print(f"   - Buscas com processos: {sum(1 for b in resultado_organizado['buscas_realizadas'] if b['total_processos_encontrados'] > 0)}")
    print(f"   - Total de processos encontrados: {sum(b['total_processos_encontrados'] for b in resultado_organizado['buscas_realizadas'])}")
    print(f"   - Tempo total: {resultado_organizado['resumo_execucao']['tempo_total_segundos']} segundos")
    
    return resultado_organizado

def criar_relatorio_resumido(dados_organizados: Dict[str, Any], arquivo_saida: str = None) -> Dict[str, Any]:
    """
    Cria um relatório resumido com as informações mais importantes
    
    Args:
        dados_organizados: Dados já organizados
        arquivo_saida: Caminho do arquivo de saída (opcional)
    
    Returns:
        Dicionário com o relatório resumido
    """
    
    relatorio = {
        "resumo_execucao": dados_organizados["resumo_execucao"],
        "estatisticas": {
            "buscas_com_processos": 0,
            "buscas_sem_processos": 0,
            "total_processos": 0,
            "cpfs_com_processos": [],
            "cpfs_sem_processos": []
        },
        "processos_por_cpf": {}
    }
    
    for busca in dados_organizados["buscas_realizadas"]:
        cpf = busca["cpf_buscado"]
        
        if busca["total_processos_encontrados"] > 0:
            relatorio["estatisticas"]["buscas_com_processos"] += 1
            relatorio["estatisticas"]["total_processos"] += busca["total_processos_encontrados"]
            relatorio["estatisticas"]["cpfs_com_processos"].append(cpf)
            
            # Resumo dos processos por CPF
            relatorio["processos_por_cpf"][cpf] = {
                "total_processos": busca["total_processos_encontrados"],
                "processos": [
                    {
                        "numero": p["numero_processo"],
                        "classe": p["classe_processual"],
                        "valor_causa": p["valor_causa"],
                        "ultima_movimentacao": p["movimentacoes"][0]["data"] if p["movimentacoes"] else "N/A"
                    }
                    for p in busca["processos"]
                ]
            }
        else:
            relatorio["estatisticas"]["buscas_sem_processos"] += 1
            relatorio["estatisticas"]["cpfs_sem_processos"].append(cpf)
    
    # Salvar relatório resumido
    if arquivo_saida is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"relatorio_resumido_{timestamp}.json"
    
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)
    
    print(f"📋 Relatório resumido salvo em: {arquivo_saida}")
    
    return relatorio

if __name__ == "__main__":
    # Organizar o resultado original
    resultado_org = organizar_resultado("resultado.json")
    
    # Criar relatório resumido
    relatorio = criar_relatorio_resumido(resultado_org)
    
    print("\n🎯 Relatório Final:")
    print(f"   - CPFs com processos: {relatorio['estatisticas']['cpfs_com_processos']}")
    print(f"   - CPFs sem processos: {relatorio['estatisticas']['cpfs_sem_processos']}")
    print(f"   - Total de processos: {relatorio['estatisticas']['total_processos']}") 