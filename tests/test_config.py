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
    config = carregar_config(tmp_path, {"PILAR_COSMOS_TOKEN": "tk"})
    assert (config.token, config.responsavel, config.limite_consultas, config.espera_maxima_min, config.raiz) == (
        "tk", "PILAR", 24, 120, tmp_path,
    )


def test_carregar_config_aceita_valores_do_ambiente(tmp_path):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    config = carregar_config(
        tmp_path, {"PILAR_COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "10", "ESPERA_MAXIMA_MIN": "0"}
    )
    assert (config.limite_consultas, config.espera_maxima_min) == (10, 0)


@pytest.mark.parametrize(
    "ambiente",
    [
        {},
        {"PILAR_COSMOS_TOKEN": "  "},
        {"COSMOS_TOKEN": "tk"},
        {"PILAR_COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "26"},
        {"PILAR_COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "0"},
        {"PILAR_COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "vinte"},
        {"PILAR_COSMOS_TOKEN": "tk", "ESPERA_MAXIMA_MIN": "-1"},
    ],
)
def test_carregar_config_rejeita_valores_invalidos(tmp_path, ambiente):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    with pytest.raises(ConfigInvalida):
        carregar_config(tmp_path, ambiente)


def test_encontrar_token_um_rotulo_valido():
    assert encontrar_token({"PILAR_COSMOS_TOKEN": "tk"}) == ("PILAR", "tk")


def test_encontrar_token_nenhum_definido():
    with pytest.raises(ConfigInvalida) as excinfo:
        encontrar_token({})
    assert str(excinfo.value) == "nenhum <RÓTULO>_COSMOS_TOKEN definido (ex.: PILAR_COSMOS_TOKEN), no ambiente ou no .env"


def test_encontrar_token_mais_de_um_definido_cita_os_dois_em_ordem():
    with pytest.raises(ConfigInvalida) as excinfo:
        encontrar_token({"B_COSMOS_TOKEN": "y", "A_COSMOS_TOKEN": "x"})
    assert str(excinfo.value) == "mais de um <RÓTULO>_COSMOS_TOKEN definido: A_COSMOS_TOKEN, B_COSMOS_TOKEN; use apenas um por execução"


def test_encontrar_token_valor_so_com_espacos_e_ignorado():
    assert encontrar_token({"PILAR_COSMOS_TOKEN": "   ", "ORIENTADORA_COSMOS_TOKEN": "tk"}) == ("ORIENTADORA", "tk")


@pytest.mark.parametrize("chave", ["cosmos_token", "_COSMOS_TOKEN", "PILAR_COSMOS_TOKEN_X"])
def test_encontrar_token_chave_invalida_nao_e_aceita(chave):
    with pytest.raises(ConfigInvalida):
        encontrar_token({chave: "tk"})
