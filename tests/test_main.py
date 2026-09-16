import pytest

from coletor import __main__ as entrada
from coletor import exportar
from coletor.principal import Cancelado
from tests.ajudantes import ApiFalsa, roteiro_paginas


def _raiz(tmp_path):
    (tmp_path / "ncms_alvo.csv").write_text("ncm;descricao;status\n22030000;Cerveja;alvo\n", encoding="utf-8")
    return tmp_path


def test_config_invalida_retorna_1_sem_criar_arquivos(tmp_path, capsys):
    codigo = entrada.main(raiz=_raiz(tmp_path), ambiente={}, argv=[], instalar_sinais=False)
    assert codigo == 1
    assert "COSMOS_TOKEN" in capsys.readouterr().err
    assert not (tmp_path / "saida").exists()


def test_execucao_completa_com_api_falsa(tmp_path):
    fabrica = lambda antes: ApiFalsa(antes, roteiro_paginas({"22030000": 2}))
    codigo = entrada.main(
        raiz=_raiz(tmp_path), ambiente={"COSMOS_TOKEN": "tk", "COLETOR_RESPONSAVEL": "PILAR"},
        fabrica_cliente=fabrica, argv=[], instalar_sinais=False,
    )
    assert codigo == 0
    assert exportar.ler_csv(tmp_path / "saida" / "execucoes.csv")[-1]["motivo_parada"] == "concluido"


def test_le_token_do_arquivo_env_quando_ambiente_nao_e_passado(tmp_path, monkeypatch):
    raiz = _raiz(tmp_path)
    monkeypatch.delenv("COSMOS_TOKEN", raising=False)
    monkeypatch.delenv("COLETOR_RESPONSAVEL", raising=False)
    fabrica = lambda antes: ApiFalsa(antes, roteiro_paginas({"22030000": 1}))
    assert entrada.main(raiz=raiz, fabrica_cliente=fabrica, argv=[], instalar_sinais=False) == 1
    (raiz / ".env").write_text("COSMOS_TOKEN=do-arquivo\nCOLETOR_RESPONSAVEL=PILAR\n", encoding="utf-8")
    assert entrada.main(raiz=raiz, fabrica_cliente=fabrica, argv=[], instalar_sinais=False) == 0


def test_sinal_vira_cancelado():
    with pytest.raises(Cancelado):
        entrada._ao_sinal(15, None)


def test_reconciliar_funciona_sem_cosmos_token_e_nao_chama_fabrica(tmp_path, monkeypatch):
    raiz = _raiz(tmp_path)
    monkeypatch.delenv("COSMOS_TOKEN", raising=False)
    monkeypatch.delenv("COLETOR_RESPONSAVEL", raising=False)

    def fabrica_que_levanta(antes_de_enviar):
        raise AssertionError("fábrica de cliente não deveria ser chamada em --reconciliar")

    codigo = entrada.main(
        raiz=raiz, ambiente={}, argv=["--reconciliar"], fabrica_cliente=fabrica_que_levanta, instalar_sinais=False
    )
    assert codigo == 0
    assert (raiz / "saida" / "produtos.csv").exists()


def test_reconciliar_repassa_anterior(tmp_path, monkeypatch):
    raiz = _raiz(tmp_path)
    anterior = tmp_path / "anterior"
    capturado = {}

    def reconciliar_falso(raiz_recebida, anterior_recebido):
        capturado["raiz"] = raiz_recebida
        capturado["anterior"] = anterior_recebido
        return {"produtos.csv": 0, "gtins.csv": 0, "conferencia_ncm.csv": 0, "execucoes": 0, "consultas_unidas": 0}

    monkeypatch.setattr(entrada.reconciliar_mod, "reconciliar", reconciliar_falso)
    codigo = entrada.main(
        raiz=raiz, ambiente={}, argv=["--reconciliar", "--anterior", str(anterior)], instalar_sinais=False
    )
    assert codigo == 0
    assert capturado == {"raiz": raiz, "anterior": anterior}


def test_reconciliar_com_estado_corrompido_devolve_1(tmp_path, capsys):
    raiz = _raiz(tmp_path)
    (raiz / "dados").mkdir()
    (raiz / "dados" / "estado.json").write_text("{não é json", encoding="utf-8")
    codigo = entrada.main(raiz=raiz, ambiente={}, argv=["--reconciliar"], instalar_sinais=False)
    assert codigo == 1
    assert capsys.readouterr().err


def test_argumento_desconhecido_devolve_2(tmp_path, capsys):
    codigo = entrada.main(raiz=_raiz(tmp_path), ambiente={}, argv=["--nao-existe"], instalar_sinais=False)
    assert codigo == 2
    assert capsys.readouterr().err


def test_anterior_sem_valor_devolve_2(tmp_path, capsys):
    codigo = entrada.main(raiz=_raiz(tmp_path), ambiente={}, argv=["--reconciliar", "--anterior"], instalar_sinais=False)
    assert codigo == 2
    assert capsys.readouterr().err
