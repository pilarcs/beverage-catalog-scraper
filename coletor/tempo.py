"""Data/hora em UTC e seus formatos de texto."""

from datetime import datetime, timezone

_FORMATO_ISO = "%Y-%m-%dT%H:%M:%SZ"
_FORMATO_NOME = "%Y%m%dT%H%M%SZ"


def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def para_iso(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime(_FORMATO_ISO)


def de_iso(texto: str) -> datetime:
    return datetime.strptime(texto, _FORMATO_ISO).replace(tzinfo=timezone.utc)


def para_nome_arquivo(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime(_FORMATO_NOME)
