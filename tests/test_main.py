import pytest

from coletor import __main__ as entrada
from coletor import exportar
from coletor.principal import Cancelado
from tests.ajudantes import ApiFalsa, roteiro_paginas


def _raiz(tmp_path):
    (tmp_path / "ncms_alvo.csv").write_text("ncm;descricao;status\n22030000;Cerveja;alvo\n", encoding="utf-8")
    return tmp_path


def test_config_invalida_retorna_1_sem_criar_arquivos(tmp_path, capsys):
    codigo = entrada.main(raiz=_raiz(tmp_path), ambiente={}, instalar_sinais=False)
    assert codigo == 1
    assert "COSMOS_TOKEN" in capsys.readouterr().err
    assert not (tmp_path / "saida").exists()


def test_execucao_completa_com_api_falsa(tmp_path):
    fabrica = lambda antes: ApiFalsa(antes, roteiro_paginas({"22030000": 2}))
    codigo = entrada.main(
        raiz=_raiz(tmp_path), ambiente={"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR"}, fabrica_cliente=fabrica, instalar_sinais=False
    )
    assert codigo == 0
    assert exportar.ler_csv(tmp_path / "saida" / "execucoes.csv")[-1]["motivo_parada"] == "concluido"


def test_le_token_do_arquivo_env_quando_ambiente_nao_e_passado(tmp_path, monkeypatch):
    raiz = _raiz(tmp_path)
    monkeypatch.delenv("COSMOS_TOKEN", raising=False)
    monkeypatch.delenv("COLETOR_RESPONSAVEL", raising=False)
    fabrica = lambda antes: ApiFalsa(antes, roteiro_paginas({"22030000": 1}))
    assert entrada.main(raiz=raiz, fabrica_cliente=fabrica, instalar_sinais=False) == 1
    (raiz / ".env").write_text("COSMOS_TOKEN=do-arquivo\nCOLETOR_RESPONSAVEL=PILAR\n", encoding="utf-8")
    assert entrada.main(raiz=raiz, fabrica_cliente=fabrica, instalar_sinais=False) == 0


def test_sinal_vira_cancelado():
    with pytest.raises(Cancelado):
        entrada._ao_sinal(15, None)
