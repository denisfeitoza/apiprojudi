#!/usr/bin/env python3
import os
import json
import time
from fastapi.testclient import TestClient

from api.main import app


def salvar_json(nome: str, data: dict, out_dir: str = "resultados_json") -> str:
    os.makedirs(out_dir, exist_ok=True)
    ts = time.strftime('%Y%m%d_%H%M%S')
    path = os.path.join(out_dir, f"{nome}_{ts}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"SALVO: {path}")
    return path


def run():
    client = TestClient(app)

    # 1) Processo direto
    print("[1/3] Teste processo direto 5479605-59.2020.8.09.0051...")
    payload_proc = {
        "tipo_busca": "processo",
        "valor": "5479605-59.2020.8.09.0051",
        "movimentacoes": True,
        "limite_movimentacoes": 10,
        "extrair_partes": True,
        "extrair_partes_detalhadas": True,
    }
    try:
        r1 = client.post('/buscar', json=payload_proc)
        print('PROC STATUS:', r1.status_code)
        salvar_json('processo_direto_5479605', r1.json())
    except Exception as e:
        print('PROC ERRO:', e)

    # 2) CPF
    print("[2/3] Teste CPF 084.036.781-34...")
    payload_cpf = {
        "tipo_busca": "cpf",
        "valor": "084.036.781-34",
        "movimentacoes": True,
        "limite_movimentacoes": 5,
        "extrair_partes": True,
        "extrair_partes_detalhadas": True,
    }
    try:
        r2 = client.post('/buscar', json=payload_cpf)
        print('CPF STATUS:', r2.status_code)
        salvar_json('cpf_08403678134', r2.json())
    except Exception as e:
        print('CPF ERRO:', e)

    # 3) Nome
    print("[3/3] Teste Nome PAULO ANTONIO MENEGAZZO...")
    payload_nome = {
        "tipo_busca": "nome",
        "valor": "PAULO ANTONIO MENEGAZZO",
        "movimentacoes": True,
        "limite_movimentacoes": 3,
        "extrair_partes": True,
        "extrair_partes_detalhadas": True,
    }
    try:
        r3 = client.post('/buscar', json=payload_nome)
        print('NOME STATUS:', r3.status_code)
        salvar_json('nome_PAULO_ANTONIO_MENEGAZZO', r3.json())
    except Exception as e:
        print('NOME ERRO:', e)


if __name__ == '__main__':
    run()


