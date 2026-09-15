"""Uma execução da coleta: laço de páginas dentro da cota e finalização garantida."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol, Sequence

from coletor import bruto, exportar
from coletor import estado as estado_mod
from coletor.api import CotaEsgotada, FalhaTemporaria, RespostaInvalida, TokenInvalido
from coletor.config import Config, NcmAlvo
from coletor.cota import consultas_na_janela, segundos_para_liberar
from coletor.tempo import agora_utc, para_iso


class LimiteAtingido(Exception):
    """A janela de 24 h está cheia e não libera dentro da espera máxima."""


class Cancelado(Exception):
    """A execução recebeu sinal de término."""


class Cliente(Protocol):
    def url_pagina(self, ncm: str, pagina: int) -> str: ...

    def buscar_pagina(self, ncm: str, pagina: int) -> dict: ...


FabricaCliente = Callable[[Callable[[], None]], Cliente]


@dataclass(frozen=True)
class Caminhos:
    estado: Path
    bruto: Path
    saida: Path

    @classmethod
    def de(cls, raiz: Path) -> "Caminhos":
        return cls(estado=raiz / "dados" / "estado.json", bruto=raiz / "dados" / "bruto", saida=raiz / "saida")


@dataclass
class Execucao:
    inicio: datetime
    consultas_feitas: int = 0
    paginas_concluidas: int = 0
    produtos_baixados: int = 0
    alertas: list[str] = field(default_factory=list)


def proxima_pagina(ncms: Sequence[NcmAlvo], estado: dict) -> tuple[str, int] | None:
    for alvo in ncms:
        if estado_mod.info_ncm(estado, alvo.ncm) is None:
            return alvo.ncm, 1
    for alvo in ncms:
        info = estado_mod.info_ncm(estado, alvo.ncm)
        if info["ultima_pagina"] < info["total_paginas"]:
            return alvo.ncm, info["ultima_pagina"] + 1
    return None


def calcular_progresso(ncms: Sequence[NcmAlvo], estado: dict, limite: int) -> dict[str, int]:
    feitas = conhecidas = sem_contagem = 0
    for alvo in ncms:
        info = estado_mod.info_ncm(estado, alvo.ncm)
        if info is None:
            sem_contagem += 1
            continue
        feitas += min(info["ultima_pagina"], info["total_paginas"])
        conhecidas += info["total_paginas"]
    restantes = (conhecidas - feitas) + sem_contagem
    return {
        "paginas_feitas": feitas,
        "paginas_conhecidas": conhecidas,
        "ncms_sem_contagem": sem_contagem,
        "paginas_restantes": restantes,
        "dias_previstos": math.ceil(restantes / limite) if restantes else 0,
    }


def classificar_parada(erro: BaseException | None) -> tuple[str, int]:
    if erro is None:
        return "concluido", 0
    if isinstance(erro, LimiteAtingido):
        return "limite", 0
    if isinstance(erro, CotaEsgotada):
        return "429", 0
    if isinstance(erro, TokenInvalido):
        return "erro: token", 1
    if isinstance(erro, FalhaTemporaria):
        return "erro: rede", 1
    if isinstance(erro, RespostaInvalida):
        return "erro: resposta", 1
    if isinstance(erro, (KeyboardInterrupt, Cancelado)):
        return "cancelado", 1
    return f"erro: {type(erro).__name__}", 1


def executar(
    config: Config,
    fabrica_cliente: FabricaCliente,
    *,
    agora: Callable[[], datetime] = agora_utc,
    dormir: Callable[[float], None] = time.sleep,
    saida: Callable[[str], None] = print,
) -> int:
    caminhos = Caminhos.de(config.raiz)
    execucao = Execucao(inicio=agora())
    estado: dict | None = None
    erro: BaseException | None = None
    try:
        estado = estado_mod.carregar(caminhos.estado)
        _coletar(config, fabrica_cliente, estado, execucao, caminhos, agora, dormir, saida)
    except (Exception, KeyboardInterrupt) as capturado:
        erro = capturado
    motivo, codigo = classificar_parada(erro)
    if erro is not None and codigo == 1:
        saida(f"Erro: {type(erro).__name__}: {str(erro)[:300]}")
    return _finalizar(config, estado, execucao, motivo, codigo, caminhos, agora, saida)


def _coletar(config, fabrica_cliente, estado, execucao, caminhos, agora, dormir, saida) -> None:
    def antes_de_enviar() -> None:
        momento = agora()
        espera = segundos_para_liberar(estado_mod.consultas(estado), momento, config.limite_consultas)
        if espera > 0:
            if espera > config.espera_maxima_min * 60:
                raise LimiteAtingido(f"janela de cota libera em {math.ceil(espera / 60)} min")
            saida(f"Aguardando {math.ceil(espera / 60)} min pela janela de cota...")
            dormir(espera)
            momento = agora()
        estado_mod.registrar_consulta(estado, momento)
        execucao.consultas_feitas += 1

    cliente = fabrica_cliente(antes_de_enviar)
    usadas = consultas_na_janela(estado_mod.consultas(estado), execucao.inicio)
    saida(f"[{para_iso(execucao.inicio)}] Início. Consultas nas últimas 24 h: {usadas}/{config.limite_consultas}")
    while (proxima := proxima_pagina(config.ncms, estado)) is not None:
        ncm, pagina = proxima
        resposta = cliente.buscar_pagina(ncm, pagina)
        coletado_em = agora()
        bruto.gravar_pagina(caminhos.bruto, ncm, pagina, cliente.url_pagina(ncm, pagina), coletado_em, resposta)
        produtos = resposta.get("products") or []
        total_paginas = int(resposta.get("total_pages") or 0)
        total_produtos = int(resposta.get("total_count") or 0)
        estado_mod.atualizar_ncm(estado, ncm, pagina, total_paginas, total_produtos, coletado_em)
        if not produtos and pagina < total_paginas:
            execucao.alertas.append(f"ncm:{ncm} p{pagina} vazia")
        estado_mod.salvar(caminhos.estado, estado)
        execucao.paginas_concluidas += 1
        execucao.produtos_baixados += len(produtos)
        saida(f"  ncm:{ncm} p{pagina}/{total_paginas} ({total_produtos} produtos no total) — {len(produtos)} itens")


def _finalizar(config, estado, execucao, motivo, codigo, caminhos, agora, saida) -> int:
    fim = agora()
    contagens: dict[str, int] = {}
    if estado is None:
        execucao.alertas.append("estado não carregado: estado e CSVs não foram alterados")
    else:
        try:
            estado_mod.podar_consultas(estado, fim)
            estado_mod.salvar(caminhos.estado, estado)
        except Exception as falha:
            execucao.alertas.append(f"falha ao salvar estado: {type(falha).__name__}")
            codigo = 1
        try:
            contagens = exportar.gerar_csvs(caminhos.bruto, caminhos.saida, config.ncms, estado)
        except Exception as falha:
            execucao.alertas.append(f"falha ao gerar CSVs: {type(falha).__name__}")
            codigo = 1
    progresso = calcular_progresso(config.ncms, estado or estado_mod.estado_vazio(), config.limite_consultas)
    try:
        exportar.registrar_execucao(caminhos.saida / "execucoes.csv", {
            "inicio": para_iso(execucao.inicio),
            "fim": para_iso(fim),
            "consultas_feitas": execucao.consultas_feitas,
            "paginas_concluidas": execucao.paginas_concluidas,
            "produtos_baixados": execucao.produtos_baixados,
            "motivo_parada": motivo,
            "alertas": " | ".join(execucao.alertas),
            "paginas_restantes": progresso["paginas_restantes"],
            "dias_previstos": progresso["dias_previstos"],
        })
    except Exception as falha:
        saida(f"Falha ao registrar a execução: {type(falha).__name__}")
        codigo = 1
    saida(f"Parada: {motivo} ({execucao.consultas_feitas} consultas nesta execução)")
    if contagens:
        saida("CSVs: " + ", ".join(f"{nome} ({linhas} linhas)" for nome, linhas in contagens.items()))
    saida(
        f"Progresso: {progresso['paginas_feitas']}/{progresso['paginas_conhecidas']} páginas conhecidas; "
        f"{progresso['ncms_sem_contagem']} NCMs sem contagem; previsão: ~{progresso['dias_previstos']} dias"
    )
    if execucao.alertas:
        saida("Alertas: " + " | ".join(execucao.alertas))
    return codigo
