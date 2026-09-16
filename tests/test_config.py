from pathlib import Path

import pytest

from coletor.config import ConfigInvalida, NcmAlvo, carregar_config, carregar_ncms, encontrar_token, ler_arquivo_env

RAIZ = Path(__file__).resolve().parents[1]


def _csv(tmp_path: Path, conteudo: str) -> Path:
    caminho = tmp_path / "ncms_alvo.csv"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_carregar_ncms_devolve_so_alvo_na_ordem(tmp_path):
    caminho = _csv(tmp_path, "ncm;descricao;status\n22085000;Gim;alvo\n22043000;Mosto;fora\n22030000;Cerveja;alvo\n")
    assert carregar_ncms(caminho) == (NcmAlvo("22085000", "Gim"), NcmAlvo("22030000", "Cerveja"))


@pytest.mark.parametrize("ncm", ["2208", "2208500A", "220850001"])
def test_carregar_ncms_rejeita_ncm_invalido(tmp_path, ncm):
    caminho = _csv(tmp_path, f"ncm;descricao;status\n{ncm};X;alvo\n")
    with pytest.raises(ConfigInvalida):
        carregar_ncms(caminho)


def test_carregar_ncms_sem_alvo_e_invalido(tmp_path):
    caminho = _csv(tmp_path, "ncm;descricao;status\n22043000;Mosto;fora\n")
    with pytest.raises(ConfigInvalida):
        carregar_ncms(caminho)


def test_arquivo_real_tem_21_ncms_alvo():
    ncms = {alvo.ncm for alvo in carregar_ncms(RAIZ / "ncms_alvo.csv")}
    assert len(ncms) == 21
    assert "22029100" in ncms
    assert {"22042220", "22042920", "22043000", "22071010", "22072020"}.isdisjoint(ncms)


def test_ler_arquivo_env_ignora_comentarios_e_linhas_vazias(tmp_path):
    caminho = tmp_path / ".env"
    caminho.write_text("# comentário\n\nCOSMOS_TOKEN = abc=def \nINVALIDA\n", encoding="utf-8")
    assert ler_arquivo_env(caminho) == {"COSMOS_TOKEN": "abc=def"}


def test_ler_arquivo_env_aceita_bom(tmp_path):
    caminho = tmp_path / ".env"
    caminho.write_text("COSMOS_TOKEN=abc\n", encoding="utf-8-sig")
    assert ler_arquivo_env(caminho) == {"COSMOS_TOKEN": "abc"}


def test_ler_arquivo_env_inexistente(tmp_path):
    assert ler_arquivo_env(tmp_path / ".env") == {}


def test_carregar_config_usa_padroes(tmp_path):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    config = carregar_config(tmp_path, {"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR"})
    assert (config.token, config.responsavel, config.limite_consultas, config.espera_maxima_min, config.raiz) == (
        "tk", "PILAR", 23, 120, tmp_path,
    )


def test_carregar_config_aceita_valores_do_ambiente(tmp_path):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    config = carregar_config(
        tmp_path,
        {"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR", "LIMITE_CONSULTAS": "10", "ESPERA_MAXIMA_MIN": "0"},
    )
    assert (config.limite_consultas, config.espera_maxima_min) == (10, 0)


@pytest.mark.parametrize(
    "ambiente",
    [
        {},
        {"COSMOS_TOKEN": "  ", "COLETOR_RESPONSAVEL": "PILAR"},
        {"COSMOS_TOKEN": "tk"},  # sem COLETOR_RESPONSAVEL
        {"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR", "LIMITE_CONSULTAS": "26"},
        {"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR", "LIMITE_CONSULTAS": "0"},
        {"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR", "LIMITE_CONSULTAS": "vinte"},
        {"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR", "ESPERA_MAXIMA_MIN": "-1"},
    ],
)
def test_carregar_config_rejeita_valores_invalidos(tmp_path, ambiente):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    with pytest.raises(ConfigInvalida):
        carregar_config(tmp_path, ambiente)


def test_encontrar_token_le_nomes_fixos():
    assert encontrar_token({"COSMOS_TOKEN": " tk ", "COLETOR_RESPONSAVEL": " PILAR "}) == ("PILAR", "tk")


@pytest.mark.parametrize(
    "ambiente",
    [
        {},
        {"COLETOR_RESPONSAVEL": "PILAR"},
        {"COSMOS_TOKEN": "   ", "COLETOR_RESPONSAVEL": "PILAR"},
        {"COSMOS_TOKEN": "tk"},  # sem COLETOR_RESPONSAVEL
        {"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "  "},
    ],
)
def test_encontrar_token_exige_token_e_responsavel(ambiente):
    with pytest.raises(ConfigInvalida):
        encontrar_token(ambiente)


def test_encontrar_token_nao_vaza_o_token_na_mensagem():
    with pytest.raises(ConfigInvalida) as excinfo:
        encontrar_token({"COSMOS_TOKEN": "segredo-123"})
    assert "segredo-123" not in str(excinfo.value)
