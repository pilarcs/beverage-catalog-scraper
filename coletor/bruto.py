"""Respostas brutas da API: um arquivo por página baixada, nunca sobrescrito."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from coletor.arquivos import gravar_json_atomico
from coletor.tempo import para_iso, para_nome_arquivo


def gravar_pagina(
    raiz_bruto: Path, ncm: str, pagina: int, url: str, coletado_em: datetime, resposta: dict, responsavel: str
) -> Path:
    pasta = raiz_bruto / f"ncm_{ncm}"
    base = f"p{pagina:04d}_{para_nome_arquivo(coletado_em)}"
    caminho = pasta / f"{base}.json"
    sufixo = 2
    while caminho.exists():
        caminho = pasta / f"{base}_{sufixo}.json"
        sufixo += 1
    documento = {
        "coleta": {
            "fonte": f"ncm:{ncm}", "ncm": ncm, "pagina": pagina, "url": url,
            "coletado_em": para_iso(coletado_em), "responsavel": responsavel,
        },
        "resposta": resposta,
    }
    gravar_json_atomico(caminho, documento)
    return caminho


def listar_paginas(raiz_bruto: Path) -> list[dict]:
    if not raiz_bruto.exists():
        return []
    itens = []
    for caminho in raiz_bruto.glob("ncm_*/p*.json"):
        documento = json.loads(caminho.read_text(encoding="utf-8"))
        coleta = documento["coleta"]
        itens.append(((coleta["coletado_em"], coleta["ncm"], coleta["pagina"], caminho.name), documento))
    return [documento for _, documento in sorted(itens, key=lambda item: item[0])]
