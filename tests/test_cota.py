from datetime import datetime, timedelta, timezone

from coletor.cota import consultas_na_janela, podar, segundos_para_liberar

AGORA = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)


def _ha(horas: float = 0, minutos: float = 0) -> datetime:
    return AGORA - timedelta(hours=horas, minutes=minutos)


def test_23_consultas_pode_consultar():
    assert segundos_para_liberar([_ha(1)] * 23, AGORA, 24) == 0.0


def test_24_consultas_nao_pode_consultar():
    assert segundos_para_liberar([_ha(1)] * 24, AGORA, 24) == 23 * 3600


def test_mais_antiga_libera_em_10_minutos():
    consultas = [_ha(23, 50)] + [_ha(1)] * 23
    assert segundos_para_liberar(consultas, AGORA, 24) == 600


def test_consultas_fora_da_janela_nao_contam():
    consultas = [_ha(24)] * 30 + [_ha(1)] * 23
    assert consultas_na_janela(consultas, AGORA) == 23
    assert segundos_para_liberar(consultas, AGORA, 24) == 0.0


def test_acima_do_limite_espera_liberar_o_excedente():
    consultas = [_ha(23, 50), _ha(23, 40)] + [_ha(1)] * 23
    assert segundos_para_liberar(consultas, AGORA, 24) == 1200


def test_podar_mantem_so_48_horas():
    assert podar([_ha(49), _ha(47), _ha(1)], AGORA) == [_ha(47), _ha(1)]
