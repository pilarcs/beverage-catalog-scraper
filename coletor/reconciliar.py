"""Reconciliação do estado e dos CSVs depois de um conflito de push (D-2026-09-16). Sem chamada à API."""

from __future__ import annotations

from pathlib import Path

from coletor import bruto, config, exportar
from coletor import estado as estado_mod


def _uniao_consultas(a: dict[str, list[str]], b: dict[str, list[str]]) -> dict[str, list[str]]:
    responsaveis = set(a) | set(b)
    return {responsavel: sorted(set(a.get(responsavel, [])) | set(b.get(responsavel, []))) for responsavel in responsaveis}


def _fundir_ncm(info_a: dict | None, info_b: dict | None) -> dict:
    if info_a is None:
        return dict(info_b)  # type: ignore[arg-type]
    if info_b is None:
        return dict(info_a)
    lido_a = info_a.get("total_lido_em") or ""
    lido_b = info_b.get("total_lido_em") or ""
    fonte = info_a if lido_a >= lido_b else info_b
    concluido_a = info_a.get("concluido_em")
    concluido_b = info_b.get("concluido_em")
    if concluido_a and concluido_b:
        concluido_em = min(concluido_a, concluido_b)
    else:
        concluido_em = concluido_a or concluido_b
    return {
        "ultima_pagina": max(info_a["ultima_pagina"], info_b["ultima_pagina"]),
        "total_paginas": fonte["total_paginas"],
        "total_produtos": fonte["total_produtos"],
        "total_lido_em": fonte["total_lido_em"],
        "concluido_em": concluido_em,
    }


def _fundir_ncms(a: dict[str, dict], b: dict[str, dict]) -> dict[str, dict]:
    return {ncm: _fundir_ncm(a.get(ncm), b.get(ncm)) for ncm in set(a) | set(b)}


def _fundir_estado(atual: dict, anterior: dict | None) -> dict:
    if anterior is None:
        return atual
    return {
        "versao": estado_mod.VERSAO,
        "consultas": _uniao_consultas(atual["consultas"], anterior["consultas"]),
        "ncms": _fundir_ncms(atual["ncms"], anterior["ncms"]),
    }


def _maior_pagina_no_bruto(raiz_bruto: Path) -> dict[str, tuple[int, str]]:
    maiores: dict[str, tuple[int, str]] = {}
    for documento in bruto.listar_paginas(raiz_bruto):
        coleta = documento["coleta"]
        ncm, pagina, coletado_em = coleta["ncm"], coleta["pagina"], coleta["coletado_em"]
        atual = maiores.get(ncm)
        if atual is None or pagina >= atual[0]:
            maiores[ncm] = (pagina, coletado_em)
    return maiores


def _ajustar_ao_disco(estado_fundido: dict, raiz_bruto: Path) -> None:
    maiores = _maior_pagina_no_bruto(raiz_bruto)
    for ncm, info in estado_fundido["ncms"].items():
        pagina_disco, coletado_em_disco = maiores.get(ncm, (0, None))
        info["ultima_pagina"] = max(info["ultima_pagina"], pagina_disco)
        pronto_para_concluir = (
            info["concluido_em"] is None
            and info["total_paginas"] > 0
            and info["ultima_pagina"] >= info["total_paginas"]
            and info["ultima_pagina"] == pagina_disco
        )
        if pronto_para_concluir:
            info["concluido_em"] = coletado_em_disco


def _resolver_execucoes(caminho_atual: Path, caminho_anterior: Path | None) -> int:
    if caminho_anterior is None or not caminho_anterior.exists():
        return len(exportar.ler_csv(caminho_atual))
    linhas = exportar.ler_csv(caminho_atual)
    vistas = {tuple(linha.get(coluna, "") for coluna in exportar.COLUNAS_EXECUCOES) for linha in linhas}
    for linha in exportar.ler_csv(caminho_anterior):
        chave = tuple(linha.get(coluna, "") for coluna in exportar.COLUNAS_EXECUCOES)
        if chave not in vistas:
            vistas.add(chave)
            linhas.append(linha)
    linhas.sort(key=lambda linha: linha.get("inicio", ""))
    return exportar.gravar_csv(caminho_atual, exportar.COLUNAS_EXECUCOES, linhas)


def reconciliar(raiz: Path, anterior: Path | None) -> dict[str, int]:
    caminho_estado = raiz / "dados" / "estado.json"
    estado = estado_mod.carregar(caminho_estado)

    estado_anterior: dict | None = None
    if anterior is not None:
        caminho_estado_anterior = anterior / "dados" / "estado.json"
        if caminho_estado_anterior.exists():
            estado_anterior = estado_mod.carregar(caminho_estado_anterior)

    estado_fundido = _fundir_estado(estado, estado_anterior)
    _ajustar_ao_disco(estado_fundido, raiz / "dados" / "bruto")

    caminho_execucoes_anterior = anterior / "saida" / "execucoes.csv" if anterior is not None else None
    total_execucoes = _resolver_execucoes(raiz / "saida" / "execucoes.csv", caminho_execucoes_anterior)

    ncms = config.carregar_ncms(raiz / "ncms_alvo.csv")
    contagens = exportar.gerar_csvs(raiz / "dados" / "bruto", raiz / "saida", ncms, estado_fundido)

    estado_mod.salvar(caminho_estado, estado_fundido)

    return {
        **contagens,
        "consultas_unidas": sum(len(horarios) for horarios in estado_fundido["consultas"].values()),
        "execucoes": total_execucoes,
    }
