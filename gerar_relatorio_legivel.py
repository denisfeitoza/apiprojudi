#!/usr/bin/env python3
"""
Script para gerar relatórios legíveis em HTML e CSV
a partir dos dados organizados de busca múltipla
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Any

def gerar_relatorio_html(dados_organizados: Dict[str, Any], arquivo_saida: str = None) -> str:
    """
    Gera um relatório HTML legível e bem formatado
    
    Args:
        dados_organizados: Dados já organizados
        arquivo_saida: Caminho do arquivo de saída (opcional)
    
    Returns:
        Caminho do arquivo gerado
    """
    
    if arquivo_saida is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"relatorio_html_{timestamp}.html"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Busca Múltipla - {dados_organizados['resumo_execucao']['timestamp']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background-color: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .cpf-section {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .cpf-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .cpf-number {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }}
        .process-count {{
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        .process-list {{
            display: grid;
            gap: 10px;
        }}
        .process-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
        .process-number {{
            font-weight: bold;
            color: #333;
        }}
        .process-class {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .process-details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
            font-size: 0.85em;
        }}
        .detail-item {{
            color: #666;
        }}
        .no-processes {{
            text-align: center;
            color: #999;
            font-style: italic;
            padding: 20px;
        }}
        .timestamp {{
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 20px;
            padding: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Relatório de Busca Múltipla</h1>
            <div class="subtitle">Análise de Processos Judiciais por CPF</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{dados_organizados['resumo_execucao']['total_buscas']}</div>
                <div class="stat-label">Total de Buscas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{sum(1 for b in dados_organizados['buscas_realizadas'] if b['total_processos_encontrados'] > 0)}</div>
                <div class="stat-label">CPFs com Processos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{sum(b['total_processos_encontrados'] for b in dados_organizados['buscas_realizadas'])}</div>
                <div class="stat-label">Total de Processos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{dados_organizados['resumo_execucao']['tempo_total_segundos']}s</div>
                <div class="stat-label">Tempo de Execução</div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>🔍 Resultados por CPF</h2>
"""
    
    # Adicionar seções para cada CPF
    for busca in dados_organizados['buscas_realizadas']:
        cpf = busca['cpf_buscado']
        total_processos = busca['total_processos_encontrados']
        
        html_content += f"""
                <div class="cpf-section">
                    <div class="cpf-header">
                        <div class="cpf-number">CPF: {cpf}</div>
                        <div class="process-count">{total_processos} processo{'s' if total_processos != 1 else ''}</div>
                    </div>
"""
        
        if total_processos > 0:
            html_content += """
                    <div class="process-list">
"""
            for processo in busca['processos']:
                html_content += f"""
                        <div class="process-item">
                            <div class="process-number">{processo['numero_processo']}</div>
                            <div class="process-class">{processo['classe_processual']}</div>
                            <div class="process-details">
                                <div class="detail-item">
                                    <strong>Valor da Causa:</strong> {processo['valor_causa'] or 'N/A'}
                                </div>
                                <div class="detail-item">
                                    <strong>Última Movimentação:</strong> {processo['movimentacoes'][0]['data'] if processo['movimentacoes'] else 'N/A'}
                                </div>
                            </div>
                        </div>
"""
            html_content += """
                    </div>
"""
        else:
            html_content += """
                    <div class="no-processes">
                        Nenhum processo encontrado para este CPF
                    </div>
"""
        
        html_content += """
                </div>
"""
    
    html_content += f"""
            </div>
        </div>
        
        <div class="timestamp">
            Relatório gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
    
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📄 Relatório HTML gerado: {arquivo_saida}")
    return arquivo_saida

def gerar_relatorio_csv(dados_organizados: Dict[str, Any], arquivo_saida: str = None) -> str:
    """
    Gera um relatório CSV com os dados principais
    
    Args:
        dados_organizados: Dados já organizados
        arquivo_saida: Caminho do arquivo de saída (opcional)
    
    Returns:
        Caminho do arquivo gerado
    """
    
    if arquivo_saida is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"relatorio_csv_{timestamp}.csv"
    
    with open(arquivo_saida, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Cabeçalho
        writer.writerow([
            'CPF', 'Número do Processo', 'Classe Processual', 'Valor da Causa',
            'Última Movimentação', 'Data da Movimentação', 'Total de Partes',
            'Total de Movimentações', 'Status'
        ])
        
        # Dados
        for busca in dados_organizados['buscas_realizadas']:
            cpf = busca['cpf_buscado']
            
            if busca['total_processos_encontrados'] > 0:
                for processo in busca['processos']:
                    ultima_mov = processo['movimentacoes'][0] if processo['movimentacoes'] else {}
                    
                    writer.writerow([
                        cpf,
                        processo['numero_processo'],
                        processo['classe_processual'],
                        processo['valor_causa'] or 'N/A',
                        ultima_mov.get('tipo', 'N/A'),
                        ultima_mov.get('data', 'N/A'),
                        processo['total_partes'],
                        processo['total_movimentacoes'],
                        busca['status']
                    ])
            else:
                # CPF sem processos
                writer.writerow([
                    cpf, 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', busca['status']
                ])
    
    print(f"📊 Relatório CSV gerado: {arquivo_saida}")
    return arquivo_saida

if __name__ == "__main__":
    # Carregar dados organizados
    with open("resultado_organizado_20250805_033401.json", 'r', encoding='utf-8') as f:
        dados_organizados = json.load(f)
    
    # Gerar relatórios
    html_file = gerar_relatorio_html(dados_organizados)
    csv_file = gerar_relatorio_csv(dados_organizados)
    
    print(f"\n✅ Relatórios gerados com sucesso!")
    print(f"   📄 HTML: {html_file}")
    print(f"   📊 CSV: {csv_file}") 