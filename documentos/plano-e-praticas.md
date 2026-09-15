# Plano e práticas — raspagem do catálogo de bebidas alcoólicas (Cosmos)

Documento vivo. Registra **definições**, **decisões tomadas (com data e motivo)**,
**práticas de trabalho** e **perguntas em aberto**. Não apague decisões antigas: se uma
mudar, marque como substituída e registre a nova.

## 1. Objetivo

Coletar, pela API oficial do Bluesoft Cosmos, o catálogo inteiro de bebidas alcoólicas
registrado na base, incluindo cerveja sem álcool. O resultado é uma base bruta
reprodutível, que depois passa por tratamento.

## 2. Definições

| Termo | Definição no projeto |
|---|---|
| **Cosmos** | Catálogo de produtos da Bluesoft. Base **colaborativa** (*crowdsourced*): varejistas e usuários cadastram e editam produtos, então os dados podem estar errados, incompletos ou duplicados |
| **GTIN/EAN** | Código de barras do produto (8, 12, 13 ou 14 dígitos). No Cosmos, cada registro é identificado por um GTIN, e um produto pode listar GTINs alternativos (campo `gtins`) |
| **Prefixo GS1** | Os 3 primeiros dígitos do GTIN-13. Indicam a **organização GS1 onde a empresa dona da marca registrou o código** (789/790 = GS1 Brasil). **Não** indicam país de fabricação nem país de venda |
| **NCM** | Nomenclatura Comum do Mercosul, com 8 dígitos. Classificação fiscal da mercadoria. No Cosmos é informada pelos usuários e pode estar errada |
| **GPC** | Global Product Classification (GS1). Hierarquia segmento > família > classe > *brick*. No Cosmos, a classe `50202200` é "Bebidas alcoólicas" (id interno 2981) |
| **Categoria Cosmos** | Campo `category` (ex.: "Cervejas", id 203, pai 140). É uma taxonomia própria do Cosmos, **não é exposta por endpoint da API** |
| **NCM-alvo** | Os NCMs listados em `ncms-alvo.md` com status `alvo` |
| **Fonte** | A consulta que trouxe o registro (ex.: `ncm:22030000`, `gpc:10000159`, `busca:cerveja`) |
| **Coleta** | Etapa que baixa e guarda os dados **brutos**, sem alterá-los |
| **Tratamento** | Etapa posterior: validação, deduplicação, correção e classificação |
| **Consulta (cota)** | Uma requisição HTTP à API. O plano Básico permite 25 por dia |

## 3. Fatos verificados sobre a API (15/09/2026)

- Autenticação por cabeçalhos `X-Cosmos-Token` e `User-Agent: Cosmos-API-Request`.
- Endpoints: `/gtins/{gtin}`, `/gpcs/{código}`, `/ncms/{código}/products`,
  `/products?query=`, `/products/by_date?date=` (janela máxima de 7 dias).
  Não há endpoint de categoria.
- Paginação fixa em 30 itens: `per_page` é ignorado, apesar de a documentação dizer que vai até 90. A última página é acessível.
- NCM precisa ter 8 dígitos; prefixo retorna 0.
- GPC de classe (`50202200`) devolve só os 42 produtos ligados diretamente a ela, sem somar os *bricks* filhos.
- Limite: **exatamente 25 consultas com sucesso** em 15/09/2026. A 26ª retornou HTTP 429
  "Limite de requests excedido" e o bloqueio continuou 12 minutos depois, o que bate com a página de preços
  (plano Básico = 25 consultas/dia). Cada consulta a uma lista traz **até 30 produtos**, então o máximo é 750 produtos/dia.
  Consultas que retornam 0 produtos também contam.
- Volume: 19 dos 23 NCMs de 2203–2208 somam 37.093 produtos, ou 1.247 páginas.
- A página pública `cosmos.bluesoft.com.br/gpcs/...` bloqueia scripts (HTTP 403).

## 3.1 Termos de Uso do Cosmos (lidos em 15/09/2026, a partir do HTML salvo)

Trechos relevantes (citação literal):
- "a não cadastrar mais de uma conta por pessoa, ou ainda a criação de novos cadastros por pessoas,
  cujos cadastros originais tenham sido cancelados", sob pena de "imediato bloqueio e cancelamento" e
  "ressarcimento por perdas e danos".
- "a não ceder, vender, alugar ou outra forma de transferência da conta"; login e senha têm
  "natureza pessoal e intransferível".
- O serviço é "para uso exclusivamente do usuário previamente cadastrado, sendo vedada a sua
  utilização [...] no contexto de quaisquer atividades empresariais e/ou profissionais, sem prévia
  anuência da Bluesoft ou acordo comercial específico entre as partes".

**Implicações:** (1) não multiplicar contas (D12); (2) para publicação, avaliar pedir **anuência
da Bluesoft** para uso em pesquisa. Isso fica em aberto (seção 7.4).

## 4. Achados da coleta piloto (433 produtos, 1ª página de 19 NCMs)

| Campo | Preenchido | Leitura |
|---|---|---|
| `ncm` | 100% | Esperado, pois a coleta foi por NCM |
| `category` | 32% | Categoria é pouco confiável para filtrar |
| `gpc` | 13% | GPC cobre pouco |
| `brand` | 31% | |
| `avg_price` | 0% | O endpoint de lista não traz preço |
| GTIN com prefixo 789/790 | 60% | 40% têm prefixo estrangeiro (779, 800, 560...) |
| GTIN com comprimento inválido (10 ou 11 dígitos) | 13 registros | Mostra que há GTINs digitados errado |
| Descrição "sem álcool" em NCM alcoólico | 3 | Mostra que há NCM errado |

### Busca manual no site (Pilar, 15/09/2026)
- Termo "cerveja": **15 mil+ resultados**, dos quais ~**3 mil+ com NCM começando em 22**.
- Muitos resultados são itens *relacionados* a cerveja que não são bebida (ex.: abridor).
- Comparação: o NCM 22030000 sozinho tem 5.981 produtos. Ou seja, a busca por "cerveja" **não** encontra
  todas as cervejas (descrições abreviadas como "CERV", ou só a marca), e ainda traz muito ruído.
- A API `/products?query=` **não tem filtro por NCM** (os filtros existem só no site). Todo filtro
  teria que ser aplicado depois da coleta, pagando a cota de todos os resultados.

## 4.1 Campos devolvidos pelo endpoint de lista (433 produtos da coleta piloto)

| Campo | Preenchido | Exemplo |
|---|---|---|
| `gtin` | 100% | 7896657720018 |
| `description` | 100% | CERVEJA A OUTRA CHOPP |
| `ncm.code` / `.description` / `.full_description` | 100% | 22030000 |
| `ncm.ex` | 0% | (exceção tarifária) |
| `created_at` / `updated_at` | 100% | 2014-04-24T11:07:34-03:00 |
| `origin` | 100% | COSMOS |
| `barcode_image` | 100% | URL da imagem do código de barras |
| `gtins[]` (GTINs do produto + `commercial_unit`: tipo e quantidade da embalagem, lastro, camada) | 99% (embalagem), 7% (lastro/camada) | Unidade, 1 |
| `thumbnail` | 47% | URL da foto |
| `category` (`description`, `id`, `parent_id`) | 32% | Cervejas / 203 / 140 |
| `brand` (`name`, `picture`) | 31% | A OUTRA |
| `cest` (`code`, `description`, `id`, `parent_id`) | 15% | 0302100, Cerveja em garrafa de vidro retornável |
| `gpc` (`code`, `description`) | 13% | 10000159 Cerveja |
| `net_weight` / `gross_weight` | 7% | |
| `width` / `height` / `length` | 1% | |
| `price`, `avg_price`, `min_price`, `max_price`, `release_date` | 0% | sempre vazios na lista |

**Todo produto tem GTIN**: o Cosmos identifica cada cadastro pelo GTIN, e a lista não traz outro
identificador (não há `id` do produto). O GTIN pode estar *errado* (13 com comprimento inválido), mas nunca vem *vazio*.

**GTINs múltiplos (130 de 433 produtos na amostra):**
- 112 produtos têm 2 GTINs e 18 têm 3.
- Hipótese da Pilar: um cadastro "master" agrupa versões ou tamanhos do mesmo produto.
- A amostra mostra que a maioria dos GTINs alternativos são **embalagens de agrupamento** do mesmo item:
  caixa com 12 (49), caixa com 6 (35), caixa com 24 (10) etc. Há também 21 alternativos com "Unidade, 1",
  que podem ser versões ou rótulos novos, e 25 com "Unidade" e quantidade > 1, o que é inconsistente.
- Em 1 produto, o GTIN principal **não** aparece na própria lista `gtins[]`.
- 1 GTIN alternativo também aparece como produto próprio. Isso confirma que haverá sobreposição a tratar.

**Não verificado:** se o endpoint de detalhe `/gtins/{gtin}` traz campos a mais (ex.: preços preenchidos).
A documentação mostra preço no exemplo. Testar custa 1 consulta. **Decidido não testar (D15).** Usar o detalhe para todos os produtos
custaria 1 consulta por produto (~37 mil consultas), o que é inviável no plano gratuito.

## 5. Decisões

| # | Data | Decisão | Motivo | Status |
|---|---|---|---|---|
| D1 | 2026-09-15 | Usar a **API oficial** do Cosmos, não raspar HTML | O HTML bloqueia scripts (403); a API é o canal documentado de acesso (Termos de Uso lidos em 15/09/2026, ver 3.1) | vigente |
| D2 | 2026-09-15 | A coleta principal é **por NCM de 8 dígitos**, usando a Tabela NCM vigente | Não há endpoint de categoria; NCM é o recorte com maior cobertura | vigente |
| D3 | 2026-09-15 | Incluir **cerveja sem álcool (2202.91.00)** | Decisão da Pilar | vigente |
| D4 | 2026-09-15 | **Coleta sem deduplicação semântica.** Guardar o bruto *append-only*, com fonte e data/hora da coleta. Deduplicar, validar GTIN/NCM/GPC e corrigir **no tratamento** | A base é colaborativa: decidir cedo qual registro "vale" perde informação e não dá para desfazer. Na coleta, só se evita **baixar de novo a mesma página** (controle de progresso), que é economia de cota e não deduplicação | vigente |
| D5 | 2026-09-15 | Todo site acessado vai para `referencias.md` com link e data | Referências bibliográficas e reprodutibilidade | vigente |
| D6 | 2026-09-15 | Usar os skills do **superpowers** em todas as etapas | Pedido da Pilar | vigente |
| D7 | 2026-09-15 | Escopo = bebidas **vendidas ao consumidor final para consumo humano**. Mostos (2204.22.20, 2204.29.20, 2204.30.00) e álcool etílico (2207.x) ficam **fora** | Decisão da Pilar | vigente |
| D8 | 2026-09-15 | Coletar também os NCMs de **granel** (2204.29.10 e 2208.30.10) e decidir **no tratamento**, produto a produto | Num catálogo de varejo, os produtos nesses NCMs provavelmente têm NCM errado. Custa ~7 consultas | vigente |
| D9 | 2026-09-15 | Usar o **plano gratuito** da API (Básico, 25 consultas/dia) | Decisão da Pilar. Consequência: coleta de ~2 meses, o que exige priorizar a ordem, rodar todo dia automaticamente e retomar de onde parou | vigente |
| D10 | 2026-09-15 | **Fase 1 = coleta completa por NCM-alvo.** A busca textual e outros enriquecimentos ficam para uma **Fase 2**, planejada com os dados da Fase 1 | Decisão da Pilar. Entrega uma base utilizável cedo. A busca é cara e ruidosa: "cerveja" traz 15 mil+ resultados, só ~3 mil+ com NCM 22 e muitos acessórios. A 30 itens por consulta, seriam ~500 consultas (~20 dias) só para esse termo | vigente |
| D11 | 2026-09-15 | Execução diária via **GitHub Actions** (token do Cosmos como *secret*) | Preferência da Pilar: roda com o PC desligado | vigente (repositório público: D21; disparo: D27) |
| D12 | 2026-09-15 | Usar **uma única conta e um único token** (os da Pilar). **Não** usar contas extras, próprias ou de terceiros, para aumentar a cota | Os Termos de Uso proíbem mais de uma conta por pessoa e a transferência de contas, com pena de bloqueio e perdas e danos (ver seção 3.1). Isso também protege a legitimidade dos dados para publicação | vigente |
| D13 | 2026-09-15 | Cada registro bruto guarda **fonte, número da página, data/hora da coleta** e a **resposta completa** da API (todos os campos, sem descartar nenhum). Os metadados da página (`total_count`, `total_pages`) também são guardados | Permite reconstruir a coleta, detectar deslocamento da paginação e datar cada dado (base colaborativa muda com o tempo) | vigente |
| D14 | 2026-09-15 | O CSV traz **todos os campos** devolvidos pela API, mais os de controle da coleta (fonte, página, data/hora). Objetos aninhados viram colunas com prefixo (ex.: `ncm_code`, `brand_name`, `cest_description`). Detalhes da lista `gtins[]` ficam para o desenho | Pedido da Pilar: nada fica só no JSONL | vigente |
| D15 | 2026-09-15 | **Não** consultar o endpoint de detalhe `/gtins/{gtin}` | Decisão da Pilar: não compensa gastar cota com isso | vigente |
| D16 | 2026-09-15 | A lista `gtins[]` vai para um segundo arquivo, **`gtins.csv`**, com uma linha por GTIN (GTIN do produto, GTIN listado, tipo e quantidade da embalagem, lastro, camada, mais o controle da coleta). Liga-se ao CSV principal pelo GTIN do produto | Dado importante para o tratamento (versões, embalagens, produto "master"). Opção B, "por ora" (Pilar) | vigente |
| D17 | 2026-09-15 | Dados brutos e estado ficam **no próprio repositório privado**, com commit a cada execução (opção A). Execução agendada **2x/dia** até descobrir a hora em que a cota renova | Simples, versionado, sem outro serviço. Artifacts expiram; armazenamento externo exige outra credencial | **substituída em parte por D20** (execução 2x/dia) |
| D18 | 2026-09-15 | **Limite próprio de consultas:** o programa conta as consultas das **últimas 24 h** (janela móvel, registrada no estado) e para **antes** de chegar ao limite (padrão **24**, configurável, ver D20). O HTTP 429 continua tratado, mas só como proteção extra | Pedido da Pilar: não forçar a conta batendo no 429 todo dia. A janela móvel funciona tanto se a cota renovar à meia-noite quanto 24 h depois do uso |  vigente |
| D19 | 2026-09-15 | **Salvamento garantido:** qualquer que seja o motivo da parada (limite, 429, erro de rede, token inválido, erro inesperado, cancelamento), o programa salva o estado, grava o registro da execução e gera os CSVs antes de terminar. No GitHub Actions, o commit dos dados roda **mesmo se o programa falhar** | Pedido da Pilar: nunca perder progresso | vigente |
| D20 | 2026-09-15 | **Uma execução a cada 24 h** (não 2x/dia), limite de **24 consultas** por janela de 24 h (1 de folga) e **sem tempo máximo** por execução | Decisão da Pilar: margem de segurança na cota e simplicidade | vigente |
| D21 | 2026-09-15 | Repositório **público**, com código **e dados** | Decisão da Pilar: minutos de Actions ilimitados. **Risco aceito e documentado:** a base coletada fica acessível a qualquer pessoa, o que pode conflitar com os Termos de Uso (uso restrito ao usuário cadastrado, seção 3.1); cópias e *forks* persistem mesmo se o repositório virar privado. **Obrigatório:** `.env`, o HTML salvo da página da API (contém token e link de perfil) e a pasta `*_files` **nunca** vão para o repositório (`.gitignore` + conferência antes do primeiro commit) | vigente |
| D22 | 2026-09-15 | **Chave de ligação `registro_id`** em `produtos.csv` e `gtins.csv`: identifica cada produto *como foi coletado* (fonte + página + data/hora da coleta + posição na página). `gtins.csv` também traz `produto_gtin` e `e_o_proprio` (se o GTIN listado é o do próprio produto). **Nunca há substituição:** se um mesmo GTIN aparece em dois produtos, ou no mesmo produto coletado duas vezes, são linhas separadas | O GTIN sozinho não identifica uma linha: o mesmo produto pode ser coletado mais de uma vez (D4), mudar entre coletas, e um GTIN pode aparecer na lista de dois produtos diferentes (1 caso já na amostra). Conflitos ficam visíveis para o tratamento | vigente |
| D23 | 2026-09-15 | **Converter os dados piloto** (433 produtos, 1ª página de 19 NCMs) para o formato novo, com data/hora **aproximada** (15/09/2026 ~12:03, pela data do arquivo) e marcação `piloto`. Os 3 NCMs de mosto são descartados na conversão | Decisão da Pilar (opção A): economiza 16 consultas | **substituída por D26** |
| D24 | 2026-09-15 | Criar um **README.md** curto no repositório | Decisão da Pilar: repositório público | vigente |
| D25 | 2026-09-15 | Cobertura mínima de testes de **80%** (`pytest-cov`), só como dependência de desenvolvimento | Regra global da Pilar (`~/.claude/rules/ecc/`), mantida para este projeto | vigente |
| D26 | 2026-09-15 | Os dados piloto e o histórico de consultas de 15/09 foram **só teste**. Depois de obter a contagem dos NCMs que faltam, a coleta é **zerada e começa do zero** (página 1 de todos os NCMs) | Decisão da Pilar: fidelidade (todos os registros coletados pelo mesmo programa, com data/hora exata) | vigente |
| D27 | 2026-09-15 | Disparo diário pelo **cron-job.org** (POST no endpoint `workflow_dispatch` do GitHub), sem `schedule` no workflow. Token GitHub fino, só deste repositório, permissão mínima, validade ≥ 120 dias | Decisão da Pilar: horário pontual. O `schedule` do GitHub pode atrasar ou ser descartado, e em repositório público é desativado após 60 dias sem atividade (referência 14) | vigente |
| D28 | 2026-09-15 | Sem etapa separada de contagem: a **1ª execução da coleta do zero** pega a página 1 dos 21 NCMs (contagens + dados reais). Dados de teste de 15/09 vão para `documentos/exploracao/2026-09-15/` (não usados pelo coletor) | Decisão da Pilar: nenhuma consulta descartável | vigente |

## 6. Práticas de trabalho

1. **Registrar referências:** qualquer acesso a site ou endpoint, feito pela Pilar ou pelo Claude, vai
   para `documentos/referencias.md` com URL, data (AAAA-MM-DD), quem, como e para quê.
2. **Superpowers em todas as etapas:**
   - Planejamento: `brainstorming`, depois spec, depois `writing-plans`.
   - Implementação: `test-driven-development`, executando o plano com `executing-plans` ou `subagent-driven-development`.
   - Bugs: `systematic-debugging`.
   - Antes de dizer que algo está pronto: `verification-before-completion`.
   - Revisão: `requesting-code-review`.
3. **Nenhuma consulta à API fora do programa**, porque consultas manuais não entram na contagem de 24 h (D18) e podem causar 429. Se for inevitável, anotar no estado.
3b. **Cota é recurso escasso:** nenhuma chamada exploratória à API sem dizer antes quantas
   consultas vai gastar e por quê.
4. **Dados brutos são imutáveis:** a coleta nunca sobrescreve nem limpa o bruto.
5. **Segredos:** o token fica em `.env`. Não compartilhar `.env` nem o HTML salvo da
   página da API, porque ele contém o token.
6. **Documentar decisões** na seção 5 deste arquivo, com data e motivo.

Estas práticas também estão na memória da Serena (`praticas_do_projeto`), para que valham
em sessões futuras.

## 7. Perguntas em aberto e hipóteses

### 7.1 Todos os produtos de bebidas alcoólicas têm NCM no Cosmos?
**Não sabemos, e a coleta por NCM não consegue responder.** O endpoint de NCM só devolve
quem tem aquele NCM. Um produto sem NCM, ou com NCM errado, é invisível para ele.
Formas de medir, que gastam cota:
- **Busca textual** `/products?query=` com termos de bebida (cerveja, vinho, whisky,
  cachaça, vodka...), contando quantos resultados vêm sem NCM ou com NCM fora do alvo.
- **GPC**: *bricks* de bebidas alcoólicas.

### 7.2 Dá para saber se a bebida é comercializada no Brasil?
**O Cosmos não tem campo de país de venda.** Indícios parciais:
- Prefixo GS1 789/790 indica marca registrada na GS1 Brasil, não venda no Brasil.
  Importados legítimos têm prefixo estrangeiro (40% da amostra).
- O Cosmos é alimentado por usuários e varejistas no Brasil. Estar cadastrado sugere que
  alguém no Brasil lidou com o produto, mas não prova venda atual. Há registros desde 2014
  que podem estar descontinuados.
- Hipótese a investigar: cruzar com uma fonte oficial de registro de bebidas no Brasil
  (ex.: cadastro do Ministério da Agricultura). **Ainda não acessada nem verificada.**

### 7.3 Como identificar bebidas alcoólicas sem NCM ou com NCM errado?
Candidatas, a comparar no brainstorming:
- (a) busca textual por vocabulário de bebidas;
- (b) *bricks* GPC de bebidas alcoólicas;
- (c) busca pelas marcas encontradas na coleta por NCM;
- (d) no tratamento, classificar pela descrição, para achar alcoólicos em NCMs vizinhos
  como 2202.99.00 e não alcoólicos dentro dos NCMs-alvo.

**Como filtrar o ruído da busca (Fase 2, no tratamento):** a API não filtra, então tudo é regra aplicada depois:
1. **NCM:** se tem NCM-alvo, o produto já veio na Fase 1. Se tem outro NCM que não é do capítulo 22, é suspeito (acessório ou NCM errado).
2. **Termos negativos:** abridor, copo, caneca, balde, kit sem bebida, camiseta, "sabor cerveja", tempero etc.
3. **Sinais positivos:** volume (ml, l, lata, long neck, garrafa), teor alcoólico (% vol) e **marcas que já apareceram na Fase 1**.
4. **Classificador treinado com a Fase 1:** as descrições coletadas por NCM servem de exemplos positivos para
   classificar as descrições que vierem sem NCM. Validar com uma amostra revisada manualmente.

### 7.4 Outras
- ~~Mostos e álcool etílico entram?~~ Resolvido por D7: fora.
- ~~NCMs de granel?~~ Resolvido por D8: coletar.
- ~~Qual plano da API usar?~~ Resolvido por D9: gratuito.
- ~~Repositório público?~~ Resolvido por D21: público, com risco documentado.
- Pedir à Bluesoft anuência ou cota de pesquisa? Também serviria como autorização documentada para o artigo.
- Há produtos com NCMs extintos no Cosmos?

## 8. Estado atual dos artefatos

- `cosmos_bebidas.py`: **protótipo da exploração de 15/09/2026, anterior a este plano.**
  Não tem 2202.91.00, não guarda data/hora da coleta e não tem testes. Será revisto
  depois que o plano for aprovado.
- `saida/`: coleta piloto (433 produtos) de 15/09/2026.
