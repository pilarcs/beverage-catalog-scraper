from coletor import exportar
from tests.ajudantes import documento, produto


def test_texto_converte_valores():
    assert [exportar.texto(v) for v in (None, True, 0.0, 7896657720018, [1], {"a": "É"})] == [
        "", "true", "0.0", "7896657720018", "[1]", '{"a": "É"}',
    ]


def test_achatar_produto_prefixa_objetos_e_conta_gtins():
    linha = exportar.achatar_produto(produto(7896657720018, gtins_extra=(17896657720015,)))
    assert linha["gtin"] == "7896657720018"
    assert linha["brand_name"] == "MARCA TESTE"
    assert linha["ncm_full_description"] == "Bebidas - Cervejas de malte."
    assert (linha["gtins_qtd"], linha["price"], linha["max_price"], linha["gpc"]) == ("2", "", "0.0", "")
    assert "gtins" not in linha


def test_registro_id():
    coleta = documento("22030000", 4, [])["coleta"]
    assert exportar.registro_id(coleta, 12) == "ncm:22030000|p0004|2026-09-16T06:17:05Z|12"


def test_linhas_produtos_controle_primeiro_e_campo_novo_no_final():
    paginas = [
        documento("22030000", 1, [produto(1), produto(2)]),
        documento("22030000", 2, [produto(3, campo_novo="x")], coletado_em="2026-09-17T06:17:05Z"),
    ]
    colunas, linhas = exportar.linhas_produtos(paginas)
    assert colunas[: len(exportar.COLUNAS_CONTROLE)] == exportar.COLUNAS_CONTROLE
    assert [linha["responsavel"] for linha in linhas] == ["PILAR", "PILAR", "PILAR"]
    assert colunas[-1] == "campo_novo"
    assert [l["posicao"] for l in linhas] == ["1", "2", "1"]
    assert linhas[2]["registro_id"] == "ncm:22030000|p0002|2026-09-17T06:17:05Z|01"


def test_objeto_nulo_nao_gera_coluna_vazia_quando_ha_subcampos():
    com_categoria = produto(2, category={"id": 203, "description": "Cervejas", "parent_id": 140})
    colunas, _ = exportar.linhas_produtos([documento("22030000", 1, [produto(1), com_categoria])])
    assert "category" not in colunas
    assert {"category_id", "category_description", "category_parent_id", "gpc"} <= set(colunas)


def test_linhas_gtins_uma_por_gtin_com_mesmo_registro_id():
    pagina = documento("22030000", 1, [produto(7898230715466, gtins_extra=(7898230715473,))])
    _, produtos = exportar.linhas_produtos([pagina])
    gtins = exportar.linhas_gtins([pagina])
    assert [(g["gtin"], g["e_o_proprio"], g["type_packaging"], g["quantity_packaging"]) for g in gtins] == [
        ("7898230715466", "sim", "Unidade", "1"),
        ("7898230715473", "não", "Caixa", "12"),
    ]
    assert {g["registro_id"] for g in gtins} == {produtos[0]["registro_id"]}


def test_gtin_repetido_em_dois_produtos_gera_duas_linhas():
    pagina = documento("22030000", 1, [produto(1, gtins_extra=(99,)), produto(2, gtins_extra=(99,))])
    repetidos = [g for g in exportar.linhas_gtins([pagina]) if g["gtin"] == "99"]
    assert [g["produto_gtin"] for g in repetidos] == ["1", "2"]


def test_produto_sem_lista_de_gtins(tmp_path):
    pagina = documento("22030000", 1, [produto(1, gtins=None)])
    assert exportar.linhas_gtins([pagina]) == []
    assert exportar.linhas_produtos([pagina])[1][0]["gtins_qtd"] == "0"


def test_gravar_e_ler_csv_utf8_bom_ponto_e_virgula(tmp_path):
    caminho = tmp_path / "saida" / "x.csv"
    n = exportar.gravar_csv(caminho, ["gtin", "descricao"], [{"gtin": "7896657720018", "descricao": "AÇÚCAR; UNIÃO"}])
    assert n == 1
    assert caminho.read_bytes().startswith(b"\xef\xbb\xbfgtin;descricao\r\n")
    assert exportar.ler_csv(caminho) == [{"gtin": "7896657720018", "descricao": "AÇÚCAR; UNIÃO"}]
    assert exportar.ler_csv(tmp_path / "nao_existe.csv") == []


def test_pagina_sem_responsavel_vira_vazio():
    pagina = documento("22030000", 1, [produto(1, gtins_extra=(9,))])
    del pagina["coleta"]["responsavel"]

    _, linhas = exportar.linhas_produtos([pagina])
    gtins = exportar.linhas_gtins([pagina])

    assert [linha["responsavel"] for linha in linhas] == [""]
    assert [g["responsavel"] for g in gtins] == ["", ""]
