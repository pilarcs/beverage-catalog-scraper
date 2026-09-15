import json
from datetime import datetime, timezone

from coletor import bruto
from tests.ajudantes import produto, resposta

MOMENTO = datetime(2026, 9, 16, 6, 17, 5, tzinfo=timezone.utc)
URL = "https://cosmos.bluesoft.com.br/api/ncms/22030000/products?page=2"


def test_gravar_pagina_cria_arquivo_com_coleta_e_resposta(tmp_path):
    corpo = resposta("22030000", 2, 200, [produto(7896657720018)])
    caminho = bruto.gravar_pagina(tmp_path, "22030000", 2, URL, MOMENTO, corpo)
    assert caminho == tmp_path / "ncm_22030000" / "p0002_20260916T061705Z.json"
    assert json.loads(caminho.read_text(encoding="utf-8")) == {
        "coleta": {"fonte": "ncm:22030000", "ncm": "22030000", "pagina": 2, "url": URL, "coletado_em": "2026-09-16T06:17:05Z"},
        "resposta": corpo,
    }


def test_mesma_pagina_no_mesmo_segundo_nao_sobrescreve(tmp_path):
    primeiro = bruto.gravar_pagina(tmp_path, "22030000", 2, URL, MOMENTO, resposta("22030000", 2, 200, []))
    segundo = bruto.gravar_pagina(tmp_path, "22030000", 2, URL, MOMENTO, resposta("22030000", 2, 201, []))
    assert primeiro != segundo and segundo.name == "p0002_20260916T061705Z_2.json"
    assert len(list((tmp_path / "ncm_22030000").glob("*.json"))) == 2


def test_listar_paginas_em_ordem_cronologica_e_ignora_temporarios(tmp_path):
    depois = datetime(2026, 9, 17, 6, 17, 5, tzinfo=timezone.utc)
    bruto.gravar_pagina(tmp_path, "22085000", 1, URL, depois, resposta("22085000", 1, 1, []))
    bruto.gravar_pagina(tmp_path, "22030000", 1, URL, MOMENTO, resposta("22030000", 1, 1, []))
    (tmp_path / "ncm_22030000" / "p0009_x.json.tmp").write_text("{", encoding="utf-8")
    ordem = [(d["coleta"]["ncm"], d["coleta"]["coletado_em"]) for d in bruto.listar_paginas(tmp_path)]
    assert ordem == [("22030000", "2026-09-16T06:17:05Z"), ("22085000", "2026-09-17T06:17:05Z")]


def test_listar_paginas_sem_pasta(tmp_path):
    assert bruto.listar_paginas(tmp_path / "nao_existe") == []
