from datetime import datetime, timedelta, timezone

import pytest

from coletor import estado as est

AGORA = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)


def test_estado_inexistente_devolve_vazio(tmp_path):
    assert est.carregar(tmp_path / "estado.json") == {"versao": 1, "consultas": [], "ncms": {}}


def test_salvar_e_carregar_ida_e_volta(tmp_path):
    caminho = tmp_path / "dados" / "estado.json"
    estado = est.estado_vazio()
    est.registrar_consulta(estado, AGORA)
    est.atualizar_ncm(estado, "22030000", 1, 200, 5981, AGORA)
    est.salvar(caminho, estado)
    assert est.carregar(caminho) == estado


@pytest.mark.parametrize("conteudo", ["{", '{"versao": 99, "consultas": [], "ncms": {}}', "[]"])
def test_estado_corrompido_ou_versao_desconhecida(tmp_path, conteudo):
    caminho = tmp_path / "estado.json"
    caminho.write_text(conteudo, encoding="utf-8")
    with pytest.raises(est.EstadoInvalido):
        est.carregar(caminho)


def test_atualizar_ncm_em_andamento_e_depois_concluido():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 2, 40, AGORA)
    assert est.info_ncm(estado, "22030000") == {
        "ultima_pagina": 1, "total_paginas": 2, "total_produtos": 40,
        "total_lido_em": "2026-09-16T06:17:00Z", "concluido_em": None,
    }
    depois = AGORA + timedelta(days=1)
    est.atualizar_ncm(estado, "22030000", 2, 2, 41, depois)
    info = est.info_ncm(estado, "22030000")
    assert (info["ultima_pagina"], info["total_produtos"], info["concluido_em"]) == (2, 41, "2026-09-17T06:17:00Z")


def test_ncm_sem_produtos_conclui_na_pagina_1():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22042219", 1, 1, 0, AGORA)
    assert est.info_ncm(estado, "22042219")["concluido_em"] == "2026-09-16T06:17:00Z"


def test_info_ncm_ausente():
    assert est.info_ncm(est.estado_vazio(), "22030000") is None


def test_consultas_registradas_e_podadas():
    estado = est.estado_vazio()
    est.registrar_consulta(estado, AGORA - timedelta(hours=49))
    est.registrar_consulta(estado, AGORA - timedelta(hours=1))
    est.podar_consultas(estado, AGORA)
    assert est.consultas(estado) == [AGORA - timedelta(hours=1)]
