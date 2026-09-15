from dataclasses import replace

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


def _sem_chave(chave):
    def ajuste(r):
        del r[chave]

    return ajuste


def _com_valor(chave, valor):
    def ajuste(r):
        r[chave] = valor

    return ajuste


@pytest.mark.parametrize(
    "ajuste",
    [
        _sem_chave("total_pages"),
        _com_valor("total_pages", 0),
        _com_valor("total_pages", None),
        _com_valor("total_pages", "3"),
        _sem_chave("total_count"),
    ],
)
def test_resposta_sem_total_valido_para_com_erro_e_nao_marca_ncm(config, relogio, ajuste):
    def roteiro(ncm, pagina):
        r = resposta(ncm, pagina, 5, [produto(111)])
        ajuste(r)
        return r

    codigo, _ = _rodar(config, roteiro, relogio)

    assert codigo == 1
    estado = est.carregar(config.raiz / "dados" / "estado.json")
    registro = exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]
    assert registro["motivo_parada"] == "erro: resposta"
    assert list((config.raiz / "dados" / "bruto" / "ncm_22030000").glob("p0001_*.json"))
    assert est.info_ncm(estado, "22030000") is None


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


def test_parada_por_limite_salva_estado_csvs_e_execucao(config, relogio):
    config_limite = replace(config, limite_consultas=1)

    def roteiro(ncm, pagina):
        return resposta(ncm, pagina, 5, [produto(111), produto(222)])

    codigo, saida = _rodar(config_limite, roteiro, relogio)

    assert codigo == 0
    estado = est.carregar(config.raiz / "dados" / "estado.json")
    assert est.info_ncm(estado, "22030000")["ultima_pagina"] == 1
    assert len(estado["consultas"]) == 1
    assert len(exportar.ler_csv(config.raiz / "saida" / "produtos.csv")) == 2
    assert len(exportar.ler_csv(config.raiz / "saida" / "conferencia_ncm.csv")) == 2
    assert exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["motivo_parada"] == "limite"
    assert any(linha.startswith("Parada: limite") for linha in saida)


def test_parada_por_conclusao_salva_estado_csvs_e_execucao(config, relogio):
    def roteiro(ncm, pagina):
        return resposta(ncm, pagina, 1, [produto(111), produto(222)])

    codigo, saida = _rodar(config, roteiro, relogio)

    assert codigo == 0
    estado = est.carregar(config.raiz / "dados" / "estado.json")
    assert est.info_ncm(estado, "22030000")["concluido_em"] is not None
    assert est.info_ncm(estado, "22085000")["concluido_em"] is not None
    assert len(exportar.ler_csv(config.raiz / "saida" / "produtos.csv")) == 4
    conferencia = exportar.ler_csv(config.raiz / "saida" / "conferencia_ncm.csv")
    assert all(linha["status"] == "concluído" for linha in conferencia)
    assert exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["motivo_parada"] == "concluido"
    assert any(linha.startswith("Parada: concluido") for linha in saida)
