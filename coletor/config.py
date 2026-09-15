"""Configuração do coletor: NCMs-alvo, token e limites."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigInvalida(Exception):
    """Configuração ausente ou com valor inválido."""


@dataclass(frozen=True)
class NcmAlvo:
    ncm: str
    descricao: str


@dataclass(frozen=True)
class Config:
    token: str
    responsavel: str
    ncms: tuple[NcmAlvo, ...]
    limite_consultas: int
    espera_maxima_min: int
    raiz: Path


_PADRAO_TOKEN = re.compile(r"^(?P<rotulo>[A-Z0-9][A-Z0-9_]*)_COSMOS_TOKEN$")


def encontrar_token(ambiente: Mapping[str, str]) -> tuple[str, str]:
    encontrados = []
    for chave, valor in ambiente.items():
        casamento = _PADRAO_TOKEN.match(chave)
        if casamento and valor.strip():
            encontrados.append((casamento.group("rotulo"), valor.strip(), chave))
    if not encontrados:
        raise ConfigInvalida("nenhum <RÓTULO>_COSMOS_TOKEN definido (ex.: PILAR_COSMOS_TOKEN), no ambiente ou no .env")
    if len(encontrados) > 1:
        nomes = ", ".join(sorted(chave for _, _, chave in encontrados))
        raise ConfigInvalida(f"mais de um <RÓTULO>_COSMOS_TOKEN definido: {nomes}; use apenas um por execução")
    rotulo, valor, _ = encontrados[0]
    return rotulo, valor


def carregar_ncms(caminho: Path) -> tuple[NcmAlvo, ...]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo, delimiter=";"))
    ncms: list[NcmAlvo] = []
    for linha in linhas:
        if linha["status"].strip() != "alvo":
            continue
        ncm = linha["ncm"].strip()
        if len(ncm) != 8 or not ncm.isdigit():
            raise ConfigInvalida(f"NCM inválido em {caminho.name}: {ncm!r}")
        ncms.append(NcmAlvo(ncm, linha["descricao"].strip()))
    if not ncms:
        raise ConfigInvalida(f"nenhum NCM com status 'alvo' em {caminho.name}")
    return tuple(ncms)


def ler_arquivo_env(caminho: Path) -> dict[str, str]:
    if not caminho.exists():
        return {}
    valores: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip()
    return valores


def _ler_inteiro(ambiente: Mapping[str, str], nome: str, padrao: int, minimo: int, maximo: int) -> int:
    texto = ambiente.get(nome, "").strip()
    if not texto:
        return padrao
    try:
        valor = int(texto)
    except ValueError:
        raise ConfigInvalida(f"{nome} deve ser um número inteiro, recebido {texto!r}") from None
    if not minimo <= valor <= maximo:
        raise ConfigInvalida(f"{nome} deve estar entre {minimo} e {maximo}, recebido {valor}")
    return valor


def carregar_config(raiz: Path, ambiente: Mapping[str, str]) -> Config:
    responsavel, token = encontrar_token(ambiente)
    return Config(
        token=token,
        responsavel=responsavel,
        ncms=carregar_ncms(raiz / "ncms_alvo.csv"),
        limite_consultas=_ler_inteiro(ambiente, "LIMITE_CONSULTAS", 24, 1, 25),
        espera_maxima_min=_ler_inteiro(ambiente, "ESPERA_MAXIMA_MIN", 120, 0, 1440),
        raiz=raiz,
    )
