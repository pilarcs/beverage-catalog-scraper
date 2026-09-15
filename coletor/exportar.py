"""Geração dos CSVs a partir do bruto (fonte da verdade). Nenhuma deduplicação (D4)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from coletor import bruto
from coletor.arquivos import gravar_texto_atomico
from coletor.config import NcmAlvo
from coletor.estado import info_ncm

COLUNAS_CONTROLE = ["registro_id", "fonte", "ncm_consultado", "pagina", "posicao", "coletado_em", "responsavel"]
COLUNAS_GTINS = [
    "registro_id", "produto_gtin", "gtin", "e_o_proprio", "type_packaging", "quantity_packaging",
    "ballast", "layer", "fonte", "pagina", "coletado_em", "responsavel",
]


def texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (list, dict)):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)


def achatar_produto(produto: dict) -> dict[str, str]:
    linha: dict[str, str] = {}

    def visitar(objeto: dict, prefixo: str) -> None:
        for chave, valor in objeto.items():
            nome = f"{prefixo}{chave}"
            if not prefixo and chave == "gtins":
                linha["gtins_qtd"] = str(len(valor)) if isinstance(valor, list) else "0"
            elif isinstance(valor, dict):
                visitar(valor, f"{nome}_")
            else:
                linha[nome] = texto(valor)

    visitar(produto, "")
    return linha


def registro_id(coleta: dict, posicao: int) -> str:
    return f"{coleta['fonte']}|p{coleta['pagina']:04d}|{coleta['coletado_em']}|{posicao:02d}"


def _produtos(paginas: Sequence[dict]) -> Iterator[tuple[dict, int, dict]]:
    for documento in paginas:
        for posicao, produto in enumerate(documento["resposta"].get("products") or [], start=1):
            yield documento["coleta"], posicao, produto


def linhas_produtos(paginas: Sequence[dict]) -> tuple[list[str], list[dict[str, str]]]:
    colunas = list(COLUNAS_CONTROLE)
    vistas = set(colunas)
    linhas: list[dict[str, str]] = []
    for coleta, posicao, produto in _produtos(paginas):
        linha = {
            "registro_id": registro_id(coleta, posicao),
            "fonte": coleta["fonte"],
            "ncm_consultado": coleta["ncm"],
            "pagina": str(coleta["pagina"]),
            "posicao": str(posicao),
            "coletado_em": coleta["coletado_em"],
            "responsavel": coleta.get("responsavel", ""),
        }
        for nome, valor in achatar_produto(produto).items():
            linha[nome] = valor
            if nome not in vistas:
                vistas.add(nome)
                colunas.append(nome)
        linhas.append(linha)
    return [c for c in colunas if not _objeto_sempre_nulo(c, colunas, linhas)], linhas


def _objeto_sempre_nulo(coluna: str, colunas: list[str], linhas: list[dict[str, str]]) -> bool:
    # "brand" vazio + "brand_name" preenchido em outra linha: a coluna "brand" não carrega informação.
    if coluna in COLUNAS_CONTROLE or not any(c.startswith(f"{coluna}_") for c in colunas):
        return False
    return all(linha.get(coluna, "") == "" for linha in linhas)


def linhas_gtins(paginas: Sequence[dict]) -> list[dict[str, str]]:
    linhas: list[dict[str, str]] = []
    for coleta, posicao, produto in _produtos(paginas):
        produto_gtin = texto(produto.get("gtin"))
        for item in produto.get("gtins") or []:
            unidade = item.get("commercial_unit") or {}
            gtin = texto(item.get("gtin"))
            linhas.append({
                "registro_id": registro_id(coleta, posicao),
                "produto_gtin": produto_gtin,
                "gtin": gtin,
                "e_o_proprio": "sim" if gtin == produto_gtin else "não",
                "type_packaging": texto(unidade.get("type_packaging")),
                "quantity_packaging": texto(unidade.get("quantity_packaging")),
                "ballast": texto(unidade.get("ballast")),
                "layer": texto(unidade.get("layer")),
                "fonte": coleta["fonte"],
                "pagina": str(coleta["pagina"]),
                "coletado_em": coleta["coletado_em"],
                "responsavel": coleta.get("responsavel", ""),
            })
    return linhas


def gravar_csv(caminho: Path, colunas: Sequence[str], linhas: Iterable[dict]) -> int:
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=list(colunas), delimiter=";", restval="", extrasaction="ignore")
    escritor.writeheader()
    quantidade = 0
    for linha in linhas:
        escritor.writerow(linha)
        quantidade += 1
    gravar_texto_atomico(caminho, buffer.getvalue(), encoding="utf-8-sig")
    return quantidade


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


COLUNAS_CONFERENCIA = [
    "ncm", "descricao", "total_api", "total_lido_em", "paginas_coletadas", "total_paginas",
    "linhas_baixadas", "gtins_distintos", "diferenca", "status",
]
COLUNAS_EXECUCOES = [
    "inicio", "fim", "responsavel", "consultas_feitas", "paginas_concluidas", "produtos_baixados",
    "motivo_parada", "alertas", "paginas_restantes", "dias_previstos",
]


def linhas_conferencia(ncms: Sequence[NcmAlvo], estado: dict, paginas: Sequence[dict]) -> list[dict[str, str]]:
    linhas: list[dict[str, str]] = []
    for alvo in ncms:
        documentos = [d for d in paginas if d["coleta"]["ncm"] == alvo.ncm]
        produtos = [p for d in documentos for p in d["resposta"].get("products") or []]
        gtins_distintos = len({texto(p.get("gtin")) for p in produtos})
        info = info_ncm(estado, alvo.ncm)
        linha = {
            "ncm": alvo.ncm,
            "descricao": alvo.descricao,
            "total_api": "",
            "total_lido_em": "",
            "paginas_coletadas": str(len({d["coleta"]["pagina"] for d in documentos})),
            "total_paginas": "",
            "linhas_baixadas": str(len(produtos)),
            "gtins_distintos": str(gtins_distintos),
            "diferenca": "",
            "status": "não iniciado",
        }
        if info is not None:
            diferenca = info["total_produtos"] - gtins_distintos
            if info["concluido_em"] is None:
                status = "em andamento"
            elif diferenca <= 0:
                status = "concluído"
            else:
                status = "concluído com falta"
            linha.update({
                "total_api": str(info["total_produtos"]),
                "total_lido_em": info["total_lido_em"] or "",
                "total_paginas": str(info["total_paginas"]),
                "diferenca": str(diferenca),
                "status": status,
            })
        linhas.append(linha)
    return linhas


def registrar_execucao(caminho: Path, registro: dict) -> None:
    linhas = ler_csv(caminho) + [{coluna: texto(registro.get(coluna)) for coluna in COLUNAS_EXECUCOES}]
    gravar_csv(caminho, COLUNAS_EXECUCOES, linhas)


def gerar_csvs(raiz_bruto: Path, pasta_saida: Path, ncms: Sequence[NcmAlvo], estado: dict) -> dict[str, int]:
    paginas = bruto.listar_paginas(raiz_bruto)
    colunas, produtos = linhas_produtos(paginas)
    return {
        "produtos.csv": gravar_csv(pasta_saida / "produtos.csv", colunas, produtos),
        "gtins.csv": gravar_csv(pasta_saida / "gtins.csv", COLUNAS_GTINS, linhas_gtins(paginas)),
        "conferencia_ncm.csv": gravar_csv(
            pasta_saida / "conferencia_ncm.csv", COLUNAS_CONFERENCIA, linhas_conferencia(ncms, estado, paginas)
        ),
    }
