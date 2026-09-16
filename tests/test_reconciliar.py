"""Reconciliação do estado e dos CSVs após conflito de push (D-YYYYMMDD, ver mudanca-reconciliacao.md). Sem rede."""

from pathlib import Path

import pytest

from coletor import estado as estado_mod
from coletor import exportar
from coletor.estado import EstadoInvalido
from coletor.reconciliar import reconciliar
from coletor.tempo import de_iso
from tests.ajudantes import produto, resposta

from coletor import bruto


def _ncms_csv(raiz: Path, conteudo: str = "22030000;Cerveja;alvo\n22085000;Gim;alvo\n") -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "ncms_alvo.csv").write_text(f"ncm;descricao;status\n{conteudo}", encoding="utf-8")


def _gravar_pagina(raiz: Path, ncm: str, pagina: int, total_paginas: int, coletado_em: str, n_produtos: int = 2) -> None:
    produtos = [produto(int(f"789{ncm}{pagina:03d}{i}")) for i in range(1, n_produtos + 1)]
    bruto.gravar_pagina(
        raiz / "dados" / "bruto",
        ncm,
        pagina,
        f"https://cosmos.bluesoft.com.br/api/ncms/{ncm}/products?page={pagina}",
        de_iso(coletado_em),
        resposta(ncm, pagina, total_paginas, produtos),
        "PILAR",
    )


def _estado_com(consultas: dict, ncms: dict) -> dict:
    return {"versao": estado_mod.VERSAO, "consultas": consultas, "ncms": ncms}


def test_reconciliar_une_consultas_de_dois_responsaveis_sem_duplicatas_ordenada(tmp_path):
    raiz, anterior = tmp_path / "raiz", tmp_path / "anterior"
    _ncms_csv(raiz)
    estado_mod.salvar(
        raiz / "dados" / "estado.json",
        _estado_com({"PILAR": ["2026-09-16T06:00:03Z", "2026-09-16T07:00:00Z"]}, {}),
    )
    estado_mod.salvar(
        anterior / "dados" / "estado.json",
        _estado_com(
            {"PILAR": ["2026-09-16T07:00:00Z", "2026-09-16T05:00:00Z"], "ORIENTADORA": ["2026-09-16T06:30:00Z"]}, {}
        ),
    )
    contagens = reconciliar(raiz, anterior)
    estado = estado_mod.carregar(raiz / "dados" / "estado.json")
    assert estado["consultas"] == {
        "PILAR": ["2026-09-16T05:00:00Z", "2026-09-16T06:00:03Z", "2026-09-16T07:00:00Z"],
        "ORIENTADORA": ["2026-09-16T06:30:00Z"],
    }
    assert contagens["consultas_unidas"] == 4


def test_reconciliar_ncms_maior_pagina_e_totais_do_mais_recente(tmp_path):
    raiz, anterior = tmp_path / "raiz", tmp_path / "anterior"
    _ncms_csv(raiz)
    estado_mod.salvar(
        raiz / "dados" / "estado.json",
        _estado_com(
            {},
            {
                "22030000": {
                    "ultima_pagina": 5, "total_paginas": 10, "total_produtos": 100,
                    "total_lido_em": "2026-09-16T06:00:00Z", "concluido_em": None,
                }
            },
        ),
    )
    estado_mod.salvar(
        anterior / "dados" / "estado.json",
        _estado_com(
            {},
            {
                "22030000": {
                    "ultima_pagina": 8, "total_paginas": 12, "total_produtos": 120,
                    "total_lido_em": "2026-09-16T07:00:00Z", "concluido_em": None,
                }
            },
        ),
    )
    reconciliar(raiz, anterior)
    info = estado_mod.info_ncm(estado_mod.carregar(raiz / "dados" / "estado.json"), "22030000")
    assert info["ultima_pagina"] == 8
    assert (info["total_paginas"], info["total_produtos"], info["total_lido_em"]) == (12, 120, "2026-09-16T07:00:00Z")


def test_reconciliar_concluido_em_existente_nao_e_sobrescrito(tmp_path):
    raiz, anterior = tmp_path / "raiz", tmp_path / "anterior"
    _ncms_csv(raiz)
    estado_mod.salvar(
        raiz / "dados" / "estado.json",
        _estado_com(
            {},
            {
                "22030000": {
                    "ultima_pagina": 10, "total_paginas": 10, "total_produtos": 100,
                    "total_lido_em": "2026-09-16T06:00:00Z", "concluido_em": "2026-09-16T06:00:00Z",
                }
            },
        ),
    )
    estado_mod.salvar(
        anterior / "dados" / "estado.json",
        _estado_com(
            {},
            {
                "22030000": {
                    "ultima_pagina": 10, "total_paginas": 10, "total_produtos": 100,
                    "total_lido_em": "2026-09-16T05:00:00Z", "concluido_em": None,
                }
            },
        ),
    )
    reconciliar(raiz, anterior)
    info = estado_mod.info_ncm(estado_mod.carregar(raiz / "dados" / "estado.json"), "22030000")
    assert info["concluido_em"] == "2026-09-16T06:00:00Z"


def test_reconciliar_concluido_em_prefere_o_mais_antigo_quando_os_dois_existem(tmp_path):
    raiz, anterior = tmp_path / "raiz", tmp_path / "anterior"
    _ncms_csv(raiz)
    estado_mod.salvar(
        raiz / "dados" / "estado.json",
        _estado_com(
            {},
            {
                "22030000": {
                    "ultima_pagina": 10, "total_paginas": 10, "total_produtos": 100,
                    "total_lido_em": "2026-09-16T06:00:00Z", "concluido_em": "2026-09-16T09:00:00Z",
                }
            },
        ),
    )
    estado_mod.salvar(
        anterior / "dados" / "estado.json",
        _estado_com(
            {},
            {
                "22030000": {
                    "ultima_pagina": 10, "total_paginas": 10, "total_produtos": 100,
                    "total_lido_em": "2026-09-16T05:00:00Z", "concluido_em": "2026-09-16T08:00:00Z",
                }
            },
        ),
    )
    reconciliar(raiz, anterior)
    info = estado_mod.info_ncm(estado_mod.carregar(raiz / "dados" / "estado.json"), "22030000")
    assert info["concluido_em"] == "2026-09-16T08:00:00Z"


def test_reconciliar_ncm_presente_em_um_so_lado_e_mantido_como_esta(tmp_path):
    raiz, anterior = tmp_path / "raiz", tmp_path / "anterior"
    _ncms_csv(raiz)
    info_so_no_atual = {
        "ultima_pagina": 2, "total_paginas": 5, "total_produtos": 50,
        "total_lido_em": "2026-09-16T06:00:00Z", "concluido_em": None,
    }
    info_so_no_anterior = {
        "ultima_pagina": 3, "total_paginas": 4, "total_produtos": 40,
        "total_lido_em": "2026-09-16T05:00:00Z", "concluido_em": None,
    }
    estado_mod.salvar(raiz / "dados" / "estado.json", _estado_com({}, {"22030000": info_so_no_atual}))
    estado_mod.salvar(anterior / "dados" / "estado.json", _estado_com({}, {"22085000": info_so_no_anterior}))
    reconciliar(raiz, anterior)
    estado = estado_mod.carregar(raiz / "dados" / "estado.json")
    assert estado_mod.info_ncm(estado, "22030000") == info_so_no_atual
    assert estado_mod.info_ncm(estado, "22085000") == info_so_no_anterior


def test_reconciliar_ultima_pagina_sobe_conforme_bruto_no_disco(tmp_path):
    raiz = tmp_path / "raiz"
    _ncms_csv(raiz)
    estado_mod.salvar(
        raiz / "dados" / "estado.json",
        _estado_com(
            {},
            {
                "22030000": {
                    "ultima_pagina": 1, "total_paginas": 3, "total_produtos": 6,
                    "total_lido_em": "2026-09-16T06:00:00Z", "concluido_em": None,
                }
            },
        ),
    )
    for pagina in (1, 2, 3):
        _gravar_pagina(raiz, "22030000", pagina, 3, f"2026-09-16T06:0{pagina}:00Z")
    reconciliar(raiz, None)
    info = estado_mod.info_ncm(estado_mod.carregar(raiz / "dados" / "estado.json"), "22030000")
    assert info["ultima_pagina"] == 3
    assert info["concluido_em"] == "2026-09-16T06:03:00Z"


def test_reconciliar_funde_execucoes_sem_duplicatas_ordenadas_por_inicio(tmp_path):
    raiz, anterior = tmp_path / "raiz", tmp_path / "anterior"
    _ncms_csv(raiz)
    estado_mod.salvar(raiz / "dados" / "estado.json", estado_mod.estado_vazio())
    linha_comum = {
        "inicio": "2026-09-16T06:00:00Z", "fim": "2026-09-16T06:05:00Z", "responsavel": "PILAR",
        "consultas_feitas": "3", "paginas_concluidas": "3", "produtos_baixados": "6",
        "motivo_parada": "concluido", "alertas": "", "paginas_restantes": "0", "dias_previstos": "0",
    }
    linha_raiz = {**linha_comum, "inicio": "2026-09-16T07:00:00Z"}
    linha_anterior = {**linha_comum, "inicio": "2026-09-16T05:00:00Z"}
    exportar.gravar_csv(raiz / "saida" / "execucoes.csv", exportar.COLUNAS_EXECUCOES, [linha_comum, linha_raiz])
    exportar.gravar_csv(anterior / "saida" / "execucoes.csv", exportar.COLUNAS_EXECUCOES, [linha_comum, linha_anterior])
    contagens = reconciliar(raiz, anterior)
    linhas = exportar.ler_csv(raiz / "saida" / "execucoes.csv")
    assert [linha["inicio"] for linha in linhas] == [
        "2026-09-16T05:00:00Z", "2026-09-16T06:00:00Z", "2026-09-16T07:00:00Z",
    ]
    assert contagens["execucoes"] == 3


def test_reconciliar_regenera_csvs_com_todas_as_paginas_brutas(tmp_path):
    raiz = tmp_path / "raiz"
    _ncms_csv(raiz)
    estado_mod.salvar(raiz / "dados" / "estado.json", estado_mod.estado_vazio())
    _gravar_pagina(raiz, "22030000", 1, 1, "2026-09-16T06:00:00Z", n_produtos=2)
    _gravar_pagina(raiz, "22085000", 1, 1, "2026-09-16T06:01:00Z", n_produtos=3)
    contagens = reconciliar(raiz, None)
    assert contagens["produtos.csv"] == 5
    assert len(exportar.ler_csv(raiz / "saida" / "produtos.csv")) == 5
    assert len(exportar.ler_csv(raiz / "saida" / "conferencia_ncm.csv")) == 2


def test_reconciliar_sem_anterior_usa_so_o_estado_do_repositorio(tmp_path):
    raiz = tmp_path / "raiz"
    _ncms_csv(raiz)
    estado_mod.salvar(raiz / "dados" / "estado.json", _estado_com({"PILAR": ["2026-09-16T06:00:00Z"]}, {}))
    reconciliar(raiz, None)
    estado = estado_mod.carregar(raiz / "dados" / "estado.json")
    assert estado["consultas"] == {"PILAR": ["2026-09-16T06:00:00Z"]}


def test_reconciliar_anterior_sem_estado_json_equivale_a_nao_ter_anterior(tmp_path):
    raiz, anterior = tmp_path / "raiz", tmp_path / "anterior"  # anterior não existe no disco
    _ncms_csv(raiz)
    estado_mod.salvar(raiz / "dados" / "estado.json", _estado_com({"PILAR": ["2026-09-16T06:00:00Z"]}, {}))
    reconciliar(raiz, anterior)
    estado = estado_mod.carregar(raiz / "dados" / "estado.json")
    assert estado["consultas"] == {"PILAR": ["2026-09-16T06:00:00Z"]}


def test_reconciliar_estado_corrompido_levanta_estado_invalido(tmp_path):
    raiz = tmp_path / "raiz"
    _ncms_csv(raiz)
    (raiz / "dados").mkdir(parents=True)
    (raiz / "dados" / "estado.json").write_text("{não é json", encoding="utf-8")
    with pytest.raises(EstadoInvalido):
        reconciliar(raiz, None)
