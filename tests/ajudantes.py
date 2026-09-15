"""Fábricas e dublês de teste. Estrutura modelada em uma página real da API (15/09/2026)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

INICIO = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)


def produto(gtin: int, descricao: str = "CERVEJA TESTE LATA 350ML", gtins_extra: tuple[int, ...] = (), **extra) -> dict:
    base = {
        "description": descricao,
        "gtin": gtin,
        "width": None, "height": None, "length": None, "net_weight": None, "gross_weight": None,
        "created_at": "2014-04-24T11:07:34.000-03:00",
        "updated_at": "2026-09-02T16:48:59.000-03:00",
        "release_date": None, "price": None, "avg_price": None, "max_price": 0.0, "min_price": 0.0,
        "gtins": [{"gtin": gtin, "commercial_unit": {"type_packaging": "Unidade", "quantity_packaging": 1, "ballast": None, "layer": None}}]
        + [{"gtin": g, "commercial_unit": {"type_packaging": "Caixa", "quantity_packaging": 12, "ballast": 15, "layer": 4}} for g in gtins_extra],
        "origin": "COSMOS",
        "barcode_image": f"https://cosmos.bluesoft.com.br/products/barcode/{gtin}.png",
        "brand": {"name": "MARCA TESTE", "picture": "/assets/brand.png"},
        "gpc": None,
        "ncm": {"code": "22030000", "description": "Cervejas de malte.", "full_description": "Bebidas - Cervejas de malte.", "ex": None},
        "category": None,
    }
    base.update(extra)
    return base


def resposta(ncm: str, pagina: int, total_paginas: int, produtos: list[dict], total_count: int | None = None) -> dict:
    return {
        "code": ncm, "description": "descrição", "full_description": "descrição completa", "ex": None,
        "products": list(produtos), "current_page": pagina, "per_page": 30,
        "total_pages": total_paginas,
        "total_count": total_count if total_count is not None else total_paginas * 2,
    }


def documento(ncm: str, pagina: int, produtos: list[dict], coletado_em: str = "2026-09-16T06:17:05Z", total_paginas: int = 1) -> dict:
    return {
        "coleta": {
            "fonte": f"ncm:{ncm}", "ncm": ncm, "pagina": pagina,
            "url": f"https://cosmos.bluesoft.com.br/api/ncms/{ncm}/products?page={pagina}",
            "coletado_em": coletado_em,
        },
        "resposta": resposta(ncm, pagina, total_paginas, produtos),
    }


class Relogio:
    """Relógio falso: cada leitura avança 1 s; dormir() avança o tempo pedido e registra."""

    def __init__(self, inicio: datetime = INICIO):
        self.atual = inicio
        self.dormidas: list[float] = []

    def __call__(self) -> datetime:
        valor = self.atual
        self.atual += timedelta(seconds=1)
        return valor

    def dormir(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.atual += timedelta(seconds=segundos)


class ApiFalsa:
    """Imita ClienteCosmos: chama antes_de_enviar e devolve (ou lança) o que o roteiro mandar."""

    def __init__(self, antes_de_enviar: Callable[[], None], roteiro: Callable[[str, int], object]):
        self._antes = antes_de_enviar
        self._roteiro = roteiro
        self.chamadas: list[tuple[str, int]] = []

    def url_pagina(self, ncm: str, pagina: int) -> str:
        return f"https://cosmos.bluesoft.com.br/api/ncms/{ncm}/products?page={pagina}"

    def buscar_pagina(self, ncm: str, pagina: int) -> dict:
        self._antes()
        self.chamadas.append((ncm, pagina))
        resultado = self._roteiro(ncm, pagina)
        if isinstance(resultado, BaseException):
            raise resultado
        return resultado


def roteiro_paginas(totais: dict[str, int]) -> Callable[[str, int], dict]:
    """2 produtos por página, GTINs únicos por (ncm, página, posição)."""

    def roteiro(ncm: str, pagina: int) -> dict:
        itens = [produto(int(f"789{ncm}{pagina:03d}{i}")) for i in (1, 2)]
        return resposta(ncm, pagina, totais[ncm], itens)

    return roteiro
