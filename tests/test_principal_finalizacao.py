import pytest

from coletor import estado as est
from coletor import exportar, principal
from coletor.api import CotaEsgotada, FalhaTemporaria, RespostaInvalida, TokenInvalido
from tests.ajudantes import ApiFalsa, produto, resposta


def _rodar(config, roteiro, relogio):
    saida = []
    codigo = principal.executar(
        config, lambda antes: ApiFalsa(antes, roteiro), agora=relogio, dormir=relogio.dormir, saida=saida.append
    )
    return codigo, saida


def _falha_no_segundo_ncm(erro):
    def roteiro(ncm, pagina):
        if ncm == "22085000":
            return erro
        return resposta(ncm, pagina, 5, [produto(111), produto(222)])

    return roteiro


@pytest.mark.parametrize(
    ("erro", "motivo", "codigo_esperado"),
    [
        (CotaEsgotada("HTTP 429"), "429", 0),
        (TokenInvalido("HTTP 401"), "erro: token", 1),
        (FalhaTemporaria("HTTP 500"), "erro: rede", 1),
        (RespostaInvalida("formato"), "erro: resposta", 1),
        (principal.Cancelado("sinal 15"), "cancelado", 1),
        (KeyboardInterrupt(), "cancelado", 1),
        (ValueError("inesperado"), "erro: ValueError", 1),
    ],
)
def test_toda_parada_salva_estado_csvs_e_execucao(config, relogio, erro, motivo, codigo_esperado):
    codigo, saida = _rodar(config, _falha_no_segundo_ncm(erro), relogio)

    assert codigo == codigo_esperado
    estado = est.carregar(config.raiz / "dados" / "estado.json")
    assert est.info_ncm(estado, "22030000")["ultima_pagina"] == 1
    assert len(estado["consultas"]) == 2
    assert len(exportar.ler_csv(config.raiz / "saida" / "produtos.csv")) == 2
    assert len(exportar.ler_csv(config.raiz / "saida" / "conferencia_ncm.csv")) == 2
    assert exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["motivo_parada"] == motivo
    assert any(linha.startswith(f"Parada: {motivo}") for linha in saida)


def test_pagina_vazia_inesperada_gera_alerta(config, relogio):
    def roteiro(ncm, pagina):
        itens = [] if (ncm, pagina) == ("22030000", 1) else [produto(pagina)]
        return resposta(ncm, pagina, 2, itens)

    codigo, _ = _rodar(config, roteiro, relogio)
    assert codigo == 0
    assert "ncm:22030000 p1 vazia" in exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["alertas"]


def test_estado_corrompido_nao_e_sobrescrito(config, relogio):
    caminho = config.raiz / "dados" / "estado.json"
    caminho.parent.mkdir(parents=True)
    caminho.write_text("{", encoding="utf-8")

    codigo, _ = _rodar(config, _falha_no_segundo_ncm(ValueError()), relogio)

    assert codigo == 1
    assert caminho.read_text(encoding="utf-8") == "{"
    registro = exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]
    assert registro["motivo_parada"] == "erro: EstadoInvalido"
    assert "estado não carregado" in registro["alertas"]
    assert not (config.raiz / "saida" / "produtos.csv").exists()


def test_pagina_bruta_fica_gravada_mesmo_se_salvar_estado_falhar(config, relogio, monkeypatch):
    def falhar(caminho, estado):
        raise OSError("disco cheio")

    monkeypatch.setattr(principal.estado_mod, "salvar", falhar)
    codigo, _ = _rodar(config, _falha_no_segundo_ncm(ValueError()), relogio)

    assert codigo == 1
    assert len(list((config.raiz / "dados" / "bruto" / "ncm_22030000").glob("p0001_*.json"))) == 1
    assert not (config.raiz / "dados" / "estado.json").exists()
    assert "falha ao salvar estado" in exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["alertas"]


def test_falha_ao_gerar_csvs_vira_codigo_1_e_fica_registrada(config, relogio, monkeypatch):
    def falhar(*args):
        raise OSError("sem espaço")

    monkeypatch.setattr(principal.exportar, "gerar_csvs", falhar)
    codigo, _ = _rodar(config, _falha_no_segundo_ncm(CotaEsgotada("429")), relogio)

    assert codigo == 1
    assert "falha ao gerar CSVs" in exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["alertas"]


def test_falha_ao_registrar_execucao_vira_codigo_1(config, relogio, monkeypatch):
    def falhar(*args):
        raise OSError("sem espaço")

    monkeypatch.setattr(principal.exportar, "registrar_execucao", falhar)
    codigo, saida = _rodar(config, _falha_no_segundo_ncm(CotaEsgotada("429")), relogio)

    assert codigo == 1
    assert any("Falha ao registrar a execução" in linha for linha in saida)
