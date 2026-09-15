from dataclasses import replace
from datetime import timedelta

from coletor import estado as est
from coletor import exportar, principal
from coletor.config import NcmAlvo
from tests.ajudantes import INICIO, ApiFalsa, Relogio, roteiro_paginas

NCMS = (NcmAlvo("22030000", "Cervejas"), NcmAlvo("22085000", "Gim"))


def _rodar(config, roteiro, relogio):
    apis = []

    def fabrica(antes_de_enviar):
        api = ApiFalsa(antes_de_enviar, roteiro)
        apis.append(api)
        return api

    saida = []
    codigo = principal.executar(config, fabrica, agora=relogio, dormir=relogio.dormir, saida=saida.append)
    return codigo, apis[0] if apis else None, saida


def _execucoes(config):
    return exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")


def test_proxima_pagina_prioriza_ncms_sem_contagem():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 5, 150, INICIO)
    assert principal.proxima_pagina(NCMS, estado) == ("22085000", 1)
    est.atualizar_ncm(estado, "22085000", 1, 1, 10, INICIO)
    assert principal.proxima_pagina(NCMS, estado) == ("22030000", 2)
    est.atualizar_ncm(estado, "22030000", 5, 5, 150, INICIO)
    assert principal.proxima_pagina(NCMS, estado) is None


def test_primeira_execucao_pega_pagina_1_de_todos_e_depois_segue_em_ordem(config, relogio):
    codigo, api, _ = _rodar(config, roteiro_paginas({"22030000": 3, "22085000": 2}), relogio)
    assert api.chamadas == [("22030000", 1), ("22085000", 1), ("22030000", 2), ("22030000", 3), ("22085000", 2)]
    assert codigo == 0
    assert _execucoes(config)[-1]["motivo_parada"] == "concluido"


def test_para_no_limite_sem_chamar_a_api(config, relogio):
    config = replace(config, limite_consultas=3)
    codigo, api, _ = _rodar(config, roteiro_paginas({"22030000": 10, "22085000": 10}), relogio)
    assert (codigo, len(api.chamadas)) == (0, 3)
    registro = _execucoes(config)[-1]
    assert (registro["motivo_parada"], registro["consultas_feitas"]) == ("limite", "3")
    assert len(est.carregar(config.raiz / "dados" / "estado.json")["consultas"]) == 3


def test_retoma_da_pagina_seguinte_no_dia_seguinte(config):
    config = replace(config, limite_consultas=3)
    roteiro = roteiro_paginas({"22030000": 10, "22085000": 10})
    _rodar(config, roteiro, Relogio(INICIO))
    _, api, _ = _rodar(config, roteiro, Relogio(INICIO + timedelta(hours=25)))
    assert api.chamadas == [("22030000", 3), ("22030000", 4), ("22030000", 5)]
    assert len(_execucoes(config)) == 2


def _preparar_consultas(config, momentos):
    estado = est.estado_vazio()
    for momento in momentos:
        est.registrar_consulta(estado, momento)
    est.salvar(config.raiz / "dados" / "estado.json", estado)


def test_espera_quando_a_janela_libera_em_poucos_minutos(config, relogio):
    _preparar_consultas(config, [INICIO - timedelta(hours=23, minutes=50)] + [INICIO - timedelta(hours=1)] * 23)
    codigo, api, saida = _rodar(config, roteiro_paginas({"22030000": 10, "22085000": 10}), relogio)
    assert relogio.dormidas == [599.0]
    assert api.chamadas == [("22030000", 1)]
    assert codigo == 0 and _execucoes(config)[-1]["motivo_parada"] == "limite"
    assert any("Aguardando" in linha for linha in saida)


def test_nao_espera_quando_a_janela_demora(config, relogio):
    _preparar_consultas(config, [INICIO - timedelta(hours=1)] * 24)
    codigo, api, _ = _rodar(config, roteiro_paginas({"22030000": 10, "22085000": 10}), relogio)
    assert (codigo, api.chamadas, relogio.dormidas) == (0, [], [])
    assert _execucoes(config)[-1]["alertas"] == "nenhuma consulta feita: janela de cota ainda cheia"


def test_calcular_progresso():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 5, 200, 5981, INICIO)
    assert principal.calcular_progresso(NCMS, estado, 24) == {
        "paginas_feitas": 5, "paginas_conhecidas": 200, "ncms_sem_contagem": 1,
        "paginas_restantes": 196, "dias_previstos": 9,
    }
