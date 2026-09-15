"""Janela móvel de 24 h: funciona tanto se a cota renovar à meia-noite quanto 24 h após cada uso."""

from datetime import datetime, timedelta
from typing import Sequence

JANELA = timedelta(hours=24)
HISTORICO = timedelta(hours=48)


def _na_janela(consultas: Sequence[datetime], agora: datetime) -> list[datetime]:
    return sorted(c for c in consultas if agora - c < JANELA)


def consultas_na_janela(consultas: Sequence[datetime], agora: datetime) -> int:
    return len(_na_janela(consultas, agora))


def segundos_para_liberar(consultas: Sequence[datetime], agora: datetime, limite: int) -> float:
    na_janela = _na_janela(consultas, agora)
    if len(na_janela) < limite:
        return 0.0
    libera_em = na_janela[len(na_janela) - limite] + JANELA
    return max(0.0, (libera_em - agora).total_seconds())


def podar(consultas: Sequence[datetime], agora: datetime) -> list[datetime]:
    return [c for c in consultas if agora - c < HISTORICO]
