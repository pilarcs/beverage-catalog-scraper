# NCMs-alvo — bebidas alcoólicas (e cerveja sem álcool)

**Fonte:** Tabela NCM vigente em 15/09/2026, baixada do Portal Único Siscomex
(`documentos/Tabela_NCM_Vigente_20260915.xlsx`; última atualização citada na planilha:
Resolução Gecex nº 926/2026). Ver `referencias.md`.

**Regra de coleta:** a API do Cosmos só aceita NCM **completo, com 8 dígitos**
(`/api/ncms/{8 dígitos}/products`). Prefixos (ex.: `2208`) retornam 0 produtos
(testado em 15/09/2026). Por isso a lista abaixo traz só os códigos de 8 dígitos (os "itens").

**Critério de escopo (D7, 15/09/2026):** entram só NCMs de bebidas **vendidas ao consumidor
final para consumo humano**. Insumos, mostos e álcool etílico ficam de fora.
NCMs de granel são coletados, porque o Cosmos tem produtos de varejo neles, e a exclusão é decidida produto a produto no tratamento (D8).

**Status:** `alvo` = será coletado · `a decidir` = depende de definição do projeto ·
`fora` = não será coletado (listado para documentar a exclusão).

## Lista

| NCM (8 dígitos) | NCM formatado | Descrição (Tabela NCM) | Posição | Status | Observação |
|---|---|---|---|---|---|
| 22029100 | 2202.91.00 | Cerveja sem álcool | 22.02 | alvo | Incluída por decisão do projeto |
| 22030000 | 2203.00.00 | Cervejas de malte | 22.03 | alvo | 5.981 produtos no Cosmos (15/09/2026) |
| 22041010 | 2204.10.10 | Vinhos espumantes — tipo champanha | 22.04 | alvo | 996 produtos |
| 22041090 | 2204.10.90 | Vinhos espumantes — outros | 22.04 | alvo | 1.326 produtos |
| 22042100 | 2204.21.00 | Outros vinhos, em recipientes ≤ 2 l | 22.04 | alvo | 22.821 produtos (maior NCM) |
| 22042211 | 2204.22.11 | Vinhos, recipientes > 2 l e ≤ 10 l, ≤ 5 l | 22.04 | alvo | 202 produtos |
| 22042219 | 2204.22.19 | Vinhos, recipientes > 2 l e ≤ 10 l, outros | 22.04 | alvo | 0 produtos |
| 22042220 | 2204.22.20 | Mostos, recipientes > 2 l e ≤ 10 l | 22.04 | fora | Mosto: não é vendido ao consumidor final (D7); 1 produto |
| 22042910 | 2204.29.10 | Vinhos, recipientes > 10 l | 22.04 | alvo | Granel pelo texto do NCM; 164 produtos, provavelmente com NCM errado. Coletar e decidir no tratamento (D8) |
| 22042920 | 2204.29.20 | Mostos, outros recipientes | 22.04 | fora | Mosto (D7); 5 produtos |
| 22043000 | 2204.30.00 | Outros mostos de uvas | 22.04 | fora | Mosto (D7); 45 produtos |
| 22051000 | 2205.10.00 | Vermutes e vinhos aromatizados, ≤ 2 l | 22.05 | alvo | 201 produtos |
| 22059000 | 2205.90.00 | Vermutes e vinhos aromatizados, outros | 22.05 | alvo | 146 produtos |
| 22060010 | 2206.00.10 | Sidra | 22.06 | alvo | 95 produtos |
| 22060090 | 2206.00.90 | Outras bebidas fermentadas (perada, hidromel, saquê, misturas) | 22.06 | alvo | 2.058 produtos |
| 22071010 | 2207.10.10 | Álcool etílico não desnaturado ≥ 80% vol, água ≤ 1% | 22.07 | fora | Álcool, não é bebida para consumo final (D7) |
| 22071090 | 2207.10.90 | Álcool etílico não desnaturado ≥ 80% vol, outros | 22.07 | fora | idem (D7) |
| 22072011 | 2207.20.11 | Álcool etílico desnaturado, água ≤ 1% | 22.07 | fora | Desnaturado, não é bebida |
| 22072019 | 2207.20.19 | Álcool etílico desnaturado, outros | 22.07 | fora | idem |
| 22072020 | 2207.20.20 | Aguardente desnaturada | 22.07 | fora | idem |
| 22082000 | 2208.20.00 | Aguardentes de vinho ou de bagaço de uvas | 22.08 | alvo | 197 produtos (conhaque, brandy, grappa) |
| 22083010 | 2208.30.10 | Uísques > 50% vol, recipientes ≥ 50 l | 22.08 | alvo | Granel pelo texto do NCM; 3 produtos. Coletar e decidir no tratamento (D8) |
| 22083020 | 2208.30.20 | Uísques, embalagens ≤ 2 l | 22.08 | alvo | 810 produtos |
| 22083090 | 2208.30.90 | Uísques, outros (embalagens > 2 l, exceto granel ≥ 50 l) | 22.08 | alvo | 4 produtos |
| 22084000 | 2208.40.00 | Rum e aguardentes de cana (inclui cachaça) | 22.08 | alvo | 2.038 produtos |
| 22085000 | 2208.50.00 | Gim e genebra | 22.08 | alvo | contagem pendente |
| 22086000 | 2208.60.00 | Vodca | 22.08 | alvo | contagem pendente |
| 22087000 | 2208.70.00 | Licores | 22.08 | alvo | contagem pendente |
| 22089000 | 2208.90.00 | Outros (tequila, bebidas mistas, etc.) | 22.08 | alvo | contagem pendente |

Os exemplos entre parênteses na coluna "Observação" (conhaque, cachaça, tequila etc.)
são ilustrativos. Eles **não** fazem parte do texto oficial da Tabela NCM.

As contagens vêm do campo `total_count` da API em 15/09/2026. O Cosmos é
colaborativo e essas contagens mudam com o tempo.

## Fora do escopo (documentado)

| NCM | Descrição | Motivo |
|---|---|---|
| 2201.10.00 / 2201.90.00 | Águas | Não alcoólicas |
| 2202.10.00 | Águas adicionadas de açúcar/aromatizadas | Não alcoólicas |
| 2202.99.00 | Outras bebidas não alcoólicas | Não alcoólicas. **Risco:** bebidas alcoólicas cadastradas com NCM errado podem estar aqui (ver `plano-e-praticas.md`) |
| 2106.90.10 | Preparações para elaboração de bebidas | Insumo, não bebida |
| 2209.00.00 | Vinagres | Não bebida |

## Pontos em aberto

- O Cosmos pode ter produtos com NCMs **extintos** (anteriores à tabela vigente). A
  API aceitou `22030000`, que ainda vale, mas não testamos códigos antigos.
