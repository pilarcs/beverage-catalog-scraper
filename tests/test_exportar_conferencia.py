from datetime import datetime, timezone

from coletor import bruto, exportar
from coletor import estado as est
from coletor.config import NcmAlvo
from tests.ajudantes import documento, produto, resposta

AGORA = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)
CERVEJA = NcmAlvo("22030000", "Cervejas de malte")


def _conferencia(estado, paginas):
    return exportar.linhas_conferencia([CERVEJA], estado, paginas)[0]


def test_nao_iniciado():
    linha = _conferencia(est.estado_vazio(), [])
    assert (linha["status"], linha["total_api"], linha["diferenca"], linha["gtins_distintos"]) == ("não iniciado", "", "", "0")


def test_em_andamento():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 2, 4, AGORA)
    linha = _conferencia(estado, [documento("22030000", 1, [produto(1), produto(2)])])
    assert (linha["status"], linha["paginas_coletadas"], linha["total_paginas"], linha["diferenca"]) == ("em andamento", "1", "2", "2")


def test_concluido_conta_gtins_distintos_mesmo_com_pagina_repetida():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 1, 2, AGORA)
    paginas = [
        documento("22030000", 1, [produto(1), produto(2)]),
        documento("22030000", 1, [produto(1), produto(2)], coletado_em="2026-09-17T06:17:05Z"),
    ]
    linha = _conferencia(estado, paginas)
    assert (linha["status"], linha["linhas_baixadas"], linha["gtins_distintos"], linha["diferenca"]) == ("concluído", "4", "2", "0")


def test_concluido_com_falta():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 1, 3, AGORA)
    linha = _conferencia(estado, [documento("22030000", 1, [produto(1), produto(2)])])
    assert (linha["status"], linha["diferenca"]) == ("concluído com falta", "1")


def test_registrar_execucao_acrescenta_linhas(tmp_path):
    caminho = tmp_path / "execucoes.csv"
    exportar.registrar_execucao(caminho, {"inicio": "a", "motivo_parada": "limite", "consultas_feitas": 24})
    exportar.registrar_execucao(caminho, {"inicio": "b", "motivo_parada": "429"})
    linhas = exportar.ler_csv(caminho)
    assert [(l["inicio"], l["motivo_parada"], l["consultas_feitas"]) for l in linhas] == [("a", "limite", "24"), ("b", "429", "")]
    assert list(linhas[0].keys()) == exportar.COLUNAS_EXECUCOES


def test_gerar_csvs_escreve_os_tres_arquivos(tmp_path):
    raiz_bruto = tmp_path / "dados" / "bruto"
    bruto.gravar_pagina(raiz_bruto, "22030000", 1, "url", AGORA, resposta("22030000", 1, 1, [produto(1, gtins_extra=(9,))]))
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 1, 1, AGORA)
    contagens = exportar.gerar_csvs(raiz_bruto, tmp_path / "saida", [CERVEJA], estado)
    assert contagens == {"produtos.csv": 1, "gtins.csv": 2, "conferencia_ncm.csv": 1}
    assert exportar.ler_csv(tmp_path / "saida" / "conferencia_ncm.csv")[0]["status"] == "concluído"
