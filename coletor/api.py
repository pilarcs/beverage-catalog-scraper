"""Cliente da API do Bluesoft Cosmos: uma página por chamada, erros tipados, token nunca exposto."""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
from typing import Callable

BASE_URL = "https://cosmos.bluesoft.com.br/api"
USER_AGENT = "Cosmos-API-Request"
ESPERAS_S = (2, 4, 8)


class ErroApi(Exception):
    """Base dos erros da API."""


class CotaEsgotada(ErroApi):
    """HTTP 429."""


class TokenInvalido(ErroApi):
    """HTTP 401 ou 403."""


class FalhaTemporaria(ErroApi):
    """5xx ou erro de rede que persistiu após todas as tentativas."""


class RespostaInvalida(ErroApi):
    """Status inesperado ou corpo que não é a página esperada."""


def transporte_urllib(pedido: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            return resposta.status, resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read()


class ClienteCosmos:
    def __init__(
        self,
        token: str,
        antes_de_enviar: Callable[[], None],
        transporte: Callable[[urllib.request.Request, float], tuple[int, bytes]] = transporte_urllib,
        dormir: Callable[[float], None] = time.sleep,
        timeout: float = 60.0,
    ):
        self._token = token
        self._antes_de_enviar = antes_de_enviar
        self._transporte = transporte
        self._dormir = dormir
        self._timeout = timeout

    def url_pagina(self, ncm: str, pagina: int) -> str:
        return f"{BASE_URL}/ncms/{ncm}/products?page={pagina}"

    def buscar_pagina(self, ncm: str, pagina: int) -> dict:
        url = self.url_pagina(ncm, pagina)
        ultimo_problema = ""
        for tentativa in range(len(ESPERAS_S) + 1):
            if tentativa:
                self._dormir(ESPERAS_S[tentativa - 1])
            self._antes_de_enviar()
            pedido = urllib.request.Request(
                url,
                headers={"X-Cosmos-Token": self._token, "User-Agent": USER_AGENT, "Content-Type": "application/json"},
            )
            try:
                status, corpo = self._transporte(pedido, self._timeout)
            except (OSError, http.client.HTTPException) as erro:
                ultimo_problema = f"rede ({type(erro).__name__})"
                continue
            if status == 200:
                return self._interpretar(url, corpo)
            if status == 429:
                raise CotaEsgotada(f"HTTP 429: {self._trecho(corpo)}")
            if status in (401, 403):
                raise TokenInvalido(f"HTTP {status}: token recusado pela API")
            if status >= 500:
                ultimo_problema = f"HTTP {status}"
                continue
            raise RespostaInvalida(f"HTTP {status} em {url}: {self._trecho(corpo)}")
        raise FalhaTemporaria(f"{ultimo_problema} após {len(ESPERAS_S) + 1} tentativas em {url}")

    def _interpretar(self, url: str, corpo: bytes) -> dict:
        try:
            dados = json.loads(corpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RespostaInvalida(f"corpo não é JSON válido em {url}") from None
        if not isinstance(dados, dict) or not isinstance(dados.get("products"), list):
            raise RespostaInvalida(f"formato inesperado (sem 'products') em {url}")
        return dados

    def _trecho(self, corpo: bytes) -> str:
        return corpo.decode("utf-8", errors="replace")[:200].replace(self._token, "***")
