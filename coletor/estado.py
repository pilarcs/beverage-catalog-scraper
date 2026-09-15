"""Progresso da coleta e histórico de consultas, persistidos em dados/estado.json."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from coletor.arquivos import gravar_json_atomico
from coletor.cota import podar
from coletor.tempo import de_iso, para_iso

VERSAO = 2


class EstadoInvalido(Exception):
    """estado.json ilegível ou de versão desconhecida (nunca é sobrescrito nesse caso)."""


def estado_vazio() -> dict:
    return {"versao": VERSAO, "consultas": {}, "ncms": {}}


def carregar(caminho: Path) -> dict:
    if not caminho.exists():
        return estado_vazio()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise EstadoInvalido(f"{caminho.name} não é JSON válido") from erro
    if not isinstance(dados, dict) or dados.get("versao") != VERSAO:
        raise EstadoInvalido(f"{caminho.name} tem formato ou versão desconhecida")
    return dados


def salvar(caminho: Path, estado: dict) -> None:
    gravar_json_atomico(caminho, estado)


def consultas(estado: dict, responsavel: str) -> list[datetime]:
    return [de_iso(texto) for texto in estado["consultas"].get(responsavel, [])]


def registrar_consulta(estado: dict, responsavel: str, momento: datetime) -> None:
    estado["consultas"].setdefault(responsavel, []).append(para_iso(momento))


def podar_consultas(estado: dict, agora: datetime) -> None:
    podadas = {
        responsavel: [para_iso(momento) for momento in podar(consultas(estado, responsavel), agora)]
        for responsavel in estado["consultas"]
    }
    estado["consultas"] = {responsavel: lista for responsavel, lista in podadas.items() if lista}


def info_ncm(estado: dict, ncm: str) -> dict | None:
    return estado["ncms"].get(ncm)


def atualizar_ncm(estado: dict, ncm: str, pagina: int, total_paginas: int, total_produtos: int, lido_em: datetime) -> None:
    info = estado["ncms"].setdefault(
        ncm,
        {"ultima_pagina": 0, "total_paginas": 0, "total_produtos": 0, "total_lido_em": None, "concluido_em": None},
    )
    info["ultima_pagina"] = max(info["ultima_pagina"], pagina)
    info["total_paginas"] = total_paginas
    info["total_produtos"] = total_produtos
    info["total_lido_em"] = para_iso(lido_em)
    if info["concluido_em"] is None and info["ultima_pagina"] >= total_paginas:
        info["concluido_em"] = para_iso(lido_em)
