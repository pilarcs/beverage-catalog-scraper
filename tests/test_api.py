import io
import json
import urllib.error
import urllib.request

import pytest

from coletor import api

TOKEN = "token-secreto-123"


def _transporte(itens):
    fila = list(itens)
    pedidos = []

    def transporte(pedido, timeout):
        pedidos.append(pedido)
        item = fila.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    transporte.pedidos = pedidos
    return transporte


def _cliente(itens, ganchos=None):
    ganchos = ganchos if ganchos is not None else []
    dormidas = []
    transporte = _transporte(itens)
    cliente = api.ClienteCosmos(TOKEN, lambda: ganchos.append(1), transporte=transporte, dormir=dormidas.append)
    return cliente, transporte, ganchos, dormidas


def _ok(produtos=()):
    return 200, json.dumps({"products": list(produtos), "total_pages": 1, "total_count": 0}).encode("utf-8")


def test_sucesso_devolve_json_e_envia_cabecalhos():
    cliente, transporte, ganchos, _ = _cliente([_ok([{"gtin": 1}])])
    assert cliente.buscar_pagina("22030000", 3)["products"] == [{"gtin": 1}]
    pedido = transporte.pedidos[0]
    assert pedido.full_url == "https://cosmos.bluesoft.com.br/api/ncms/22030000/products?page=3"
    assert pedido.get_header("X-cosmos-token") == TOKEN
    assert pedido.get_header("User-agent") == "Cosmos-API-Request"
    assert ganchos == [1]


def test_5xx_tenta_de_novo_e_conta_cada_tentativa():
    cliente, _, ganchos, dormidas = _cliente([(500, b""), (502, b""), _ok()])
    cliente.buscar_pagina("22030000", 1)
    assert (len(ganchos), dormidas) == (3, [2, 4])


def test_5xx_persistente_vira_falha_temporaria():
    cliente, _, ganchos, dormidas = _cliente([(500, b"")] * 4)
    with pytest.raises(api.FalhaTemporaria):
        cliente.buscar_pagina("22030000", 1)
    assert (len(ganchos), dormidas) == (4, [2, 4, 8])


def test_erro_de_rede_persistente_vira_falha_temporaria():
    cliente, _, _, _ = _cliente([urllib.error.URLError("sem rede")] * 3 + [TimeoutError()])
    with pytest.raises(api.FalhaTemporaria):
        cliente.buscar_pagina("22030000", 1)


def test_429_vira_cota_esgotada_sem_nova_tentativa():
    cliente, _, ganchos, dormidas = _cliente([(429, b'{"message":"Limite de requests excedido"}')])
    with pytest.raises(api.CotaEsgotada):
        cliente.buscar_pagina("22030000", 1)
    assert (len(ganchos), dormidas) == (1, [])


@pytest.mark.parametrize("status", [401, 403])
def test_401_403_viram_token_invalido(status):
    cliente, _, _, _ = _cliente([(status, b"")])
    with pytest.raises(api.TokenInvalido):
        cliente.buscar_pagina("22030000", 1)


@pytest.mark.parametrize("item", [(200, b"{quebrado"), (200, b'{"sem_products": 1}'), (200, b"\xff"), (404, b"nao existe")])
def test_resposta_inesperada_vira_resposta_invalida(item):
    cliente, _, _, _ = _cliente([item])
    with pytest.raises(api.RespostaInvalida):
        cliente.buscar_pagina("22030000", 1)


def test_token_nunca_aparece_na_mensagem_de_erro():
    cliente, _, _, _ = _cliente([(429, f"token {TOKEN} excedeu".encode("utf-8"))])
    with pytest.raises(api.CotaEsgotada) as erro:
        cliente.buscar_pagina("22030000", 1)
    assert TOKEN not in str(erro.value)


def test_gancho_que_lanca_impede_o_envio():
    class Parar(Exception):
        pass

    def gancho():
        raise Parar()

    transporte = _transporte([_ok()])
    cliente = api.ClienteCosmos(TOKEN, gancho, transporte=transporte, dormir=lambda s: None)
    with pytest.raises(Parar):
        cliente.buscar_pagina("22030000", 1)
    assert transporte.pedidos == []


class _RespostaHttp:
    status = 200

    def __init__(self, corpo):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_transporte_urllib_devolve_status_e_corpo(monkeypatch):
    monkeypatch.setattr(api.urllib.request, "urlopen", lambda pedido, timeout: _RespostaHttp(b"{}"))
    assert api.transporte_urllib(urllib.request.Request("https://exemplo.test"), 1) == (200, b"{}")


def test_transporte_urllib_converte_http_error(monkeypatch):
    def urlopen(pedido, timeout):
        raise urllib.error.HTTPError(pedido.full_url, 429, "Too Many Requests", {}, io.BytesIO(b"limite"))

    monkeypatch.setattr(api.urllib.request, "urlopen", urlopen)
    assert api.transporte_urllib(urllib.request.Request("https://exemplo.test"), 1) == (429, b"limite")
