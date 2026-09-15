# Spec — Fase 1: coleta por NCM do catálogo de bebidas alcoólicas (Cosmos)

- **Data:** 2026-09-15
- **Status:** aguardando revisão da Pilar
- **Origem:** brainstorming de 15/09/2026. As decisões citadas (Dn) estão em `documentos/plano-e-praticas.md`, seção 5.
- **Documentos relacionados:** `ncms-alvo.md`, `referencias.md`, `plano-e-praticas.md`

---

## 1. Objetivo e critérios de sucesso

Coletar pela API oficial do Bluesoft Cosmos **todos os produtos cadastrados nos NCMs-alvo** e
guardar a resposta bruta de forma reprodutível, gerando CSVs prontos para o tratamento.

A Fase 1 está **concluída** quando:
1. Todos os NCMs com status `alvo` em `ncms_alvo.csv` tiverem todas as páginas coletadas.
2. `conferencia_ncm.csv` mostrar, para cada NCM, o total da API, os GTINs distintos coletados e a diferença.
3. Nenhuma execução tiver perdido dados: toda página consultada com sucesso está em `dados/bruto/`.
4. Os testes passarem, com cobertura ≥ 80% (D25).

## 2. Escopo

**Dentro:**
- os 21 NCMs com status `alvo` em `ncms-alvo.md` (D2, D3, D7, D8);
- coleta **do zero**: os dados de teste de 15/09 não entram (D26);
- a execução diária no GitHub Actions, disparada pelo cron-job.org (D11, D20, D21, D27);
- os CSVs de saída (D14, D16, D22);
- o README (D24).

**Fora (Fase 2 ou descartado):**
- busca textual e enriquecimento (D10);
- endpoint de detalhe `/gtins/{gtin}` (D15);
- GPC;
- deduplicação, validação e correção de dados, que ficam no tratamento (D4);
- refazer NCMs automaticamente;
- download de imagens;
- raspagem de HTML (D1).

## 3. Restrições

| Restrição | Origem |
|---|---|
| Máximo de **24 consultas por janela móvel de 24 h** | Plano gratuito = 25/dia; 1 de folga (D9, D18, D20) |
| Paginação fixa de 30 itens; NCM só com 8 dígitos | Fatos verificados (plano, seção 3) |
| **Uma única conta e um único token** | Termos de Uso (D12) |
| Repositório **público** (código e dados); segredos nunca no repositório | D21 |
| Nenhuma consulta à API fora do coletor | Prática 3 do plano |
| Em produção só a biblioteca padrão do Python 3.12; testes com `pytest` e `pytest-cov` | Parte 4 do desenho |

## 4. Arquitetura

```
cron-job.org (1x a cada 24 h, horário fixo) ── POST na API do GitHub (workflow_dispatch)
  ↓
GitHub Actions (também pode ser disparado manualmente; nunca 2 execuções simultâneas)
  └─ python -m coletor
       ├─ config.carregar_ncms()        → lista de NCMs "alvo"
       ├─ estado.carregar()             → progresso + histórico de consultas
       ├─ laço de coleta:
       │    cota.pode_consultar()?  → senão: espera curta ou para com motivo "limite"
       │    api.buscar_pagina(ncm, página)
       │    bruto.gravar(resposta)       (gravação atômica, nunca sobrescreve)
       │    estado.salvar()              (gravação atômica, a cada página)
       └─ FINALIZAÇÃO (sempre, qualquer motivo de parada)
            estado.salvar() → exportar.gerar_csvs() → registrar execução → resumo no terminal
  └─ passo "commit dos dados" (roda mesmo se o coletor falhar)
```

### 4.1 Componentes

| Módulo | Responsabilidade | Depende de |
|---|---|---|
| `coletor/config.py` | Ler `ncms_alvo.csv` e devolver os NCMs com status `alvo`, na ordem do arquivo; ler o limite e a espera máxima das variáveis de ambiente | — |
| `coletor/api.py` | Fazer **1 requisição HTTP** e traduzir o resultado em resposta ou em exceção tipada: `CotaEsgotada` (429), `TokenInvalido` (401/403), `FalhaTemporaria` (5xx, rede; até 4 tentativas no total, com espera de 2/4/8 s entre elas), `RespostaInvalida` (JSON inválido). Nunca expõe o token em mensagens | stdlib `urllib` |
| `coletor/cota.py` | Dada a lista de horários das consultas, dizer se pode consultar agora e, se não, em quantos segundos libera | — |
| `coletor/estado.py` | Ler e gravar `dados/estado.json` de forma atômica | — |
| `coletor/bruto.py` | Gravar cada página em `dados/bruto/` de forma atômica, sem sobrescrever; listar os arquivos brutos | — |
| `coletor/exportar.py` | Ler todo o bruto e gerar os 4 CSVs (seção 6) | `bruto` |
| `coletor/principal.py` | Orquestrar: ordem de coleta, laço, captura de todos os motivos de parada, finalização garantida, código de saída | todos |
| `coletor/__main__.py` | Ponto de entrada (`python -m coletor`) | `principal` |

A API é **injetada** em `principal` (um objeto com `buscar_pagina`). Assim os testes usam uma API falsa.

## 5. Coleta

### 5.1 Ordem
1. **Primeiro, a 1ª página de cada NCM-alvo que ainda não tem contagem no estado.** Como a coleta começa
   do zero (D26), a 1ª execução pega a página 1 dos 21 NCMs (21 consultas) e já sai com o volume total e o
   cronograma, **com dados reais**, sem consulta descartável (D28). As 3 consultas restantes do dia seguem o passo 2.
2. Depois, **um NCM de cada vez**, na ordem de `ncms_alvo.csv`, da página seguinte à última concluída até a última.
3. A execução termina quando: atinge o limite de cota; recebe 429; ocorre um erro; ou todos os NCMs estão completos.

**NCM completo** = `ultima_pagina ≥ total_paginas`, usando o `total_pages` da **resposta mais recente**
daquele NCM. Se o total crescer durante a coleta, as páginas novas também são coletadas. NCM com 0 produtos
(a API devolve `total_pages: 1`) fica completo depois da página 1.

### 5.2 Cota (D18, D20)
- Cada **requisição HTTP enviada** (inclusive novas tentativas e as que retornam erro) tem o horário registrado em `estado.consultas`.
  O histórico guarda as últimas 48 h.
- Antes de cada requisição: se houve **≥ 24 requisições nas últimas 24 h**:
  - se a mais antiga da janela libera em **≤ 120 minutos** (`ESPERA_MAXIMA_MIN`), o coletor **espera** e continua;
    isso cobre um eventual atraso na fila do GitHub depois do disparo;
  - senão, para com motivo `limite` (execução com sucesso).
- `LIMITE_CONSULTAS` (padrão 24) e `ESPERA_MAXIMA_MIN` (padrão 120) são configuráveis por variável de ambiente.
- HTTP 429 é tratado como proteção extra: para com motivo `429` (sucesso) e registra o horário.

### 5.3 Estado — `dados/estado.json`
```json
{
  "versao": 1,
  "consultas": ["2026-09-16T06:00:03Z", "..."],
  "ncms": {
    "22030000": {
      "ultima_pagina": 25,
      "total_paginas": 200,
      "total_produtos": 5981,
      "total_lido_em": "2026-09-16T06:00:41Z",
      "concluido_em": null
    }
  }
}
```
Gravação atômica: escreve em `estado.json.tmp` e depois troca pelo definitivo. O estado é salvo **depois** da página bruta.
Se houver queda entre as duas gravações, a página é baixada de novo na execução seguinte (custa 1 consulta, não perde dados).

### 5.4 Bruto — `dados/bruto/`
- Um arquivo por página baixada: `dados/bruto/ncm_22030000/p0002_20260916T060041Z.json`.
  O horário no nome garante que **nunca há sobrescrita** (D4, D13).
- Conteúdo:
```json
{
  "coleta": {
    "fonte": "ncm:22030000", "ncm": "22030000", "pagina": 2,
    "url": "https://cosmos.bluesoft.com.br/api/ncms/22030000/products?page=2",
    "coletado_em": "2026-09-16T06:00:41Z"
  },
  "resposta": { "...": "JSON da API, completo e sem alteração" }
}
```

### 5.5 Motivos de parada e finalização (D19)

| Motivo | Registrado como | Código de saída |
|---|---|---|
| Limite de cota atingido | `limite` | 0 |
| HTTP 429 | `429` | 0 |
| Todos os NCMs completos | `concluido` | 0 |
| Token inválido (401/403) | `erro: token` | 1 |
| Falha temporária persistente (5xx/rede) | `erro: rede` | 1 |
| Resposta inválida | `erro: resposta` | 1 |
| Qualquer outra exceção | `erro: <tipo>` | 1 |
| Cancelamento (SIGINT/SIGTERM) | `cancelado` | 1 |

A finalização roda em **todos** os casos acima:
1. salva o estado;
2. gera os CSVs;
3. acrescenta uma linha em `execucoes.csv`;
4. imprime o resumo.

Se a própria geração dos CSVs falhar, o erro é registrado na execução e o estado já está salvo.
Queda brusca da máquina é o único caso sem finalização; perde-se no máximo a página em andamento.

**Página vazia inesperada** (0 produtos antes da última página): registra alerta na execução e segue.

### 5.6 Saída no terminal (visível no registro do GitHub Actions)
Formato ilustrativo; os números abaixo são fictícios.
```
[2026-09-16 06:00:03Z] Início. Consultas nas últimas 24 h: 0/24
  ncm:22029100 p1/3 (72 produtos no total) — 30 itens
  ...
  ncm:22030000 p25/200 — 30 itens
Parada: limite (24/24 consultas)
CSVs: produtos.csv (1.153 linhas), gtins.csv (1.420), conferencia_ncm.csv (21), execucoes.csv (+1)
Progresso: 57/1.312 páginas (4,3%) — previsão: ~53 dias
```

## 6. Saídas — `saida/`

Formato de todos os CSVs: UTF-8 **com BOM**, separador `;`, uma linha de cabeçalho.
GTIN e NCM são gravados **exatamente como texto de dígitos**, sem conversão numérica.

> Nota: se o CSV for aberto com duplo clique, o Excel pode exibir GTINs em notação científica.
> Para preservar os dígitos, importe por *Dados → De Texto/CSV* definindo essas colunas como Texto.
> O arquivo em si nunca é alterado.

### 6.1 `produtos.csv` — 1 linha por produto por página baixada (sem deduplicação, D4)
- Colunas de controle, primeiro: `registro_id`, `fonte`, `ncm_consultado`, `pagina`, `posicao`, `coletado_em`.
- Depois, **todos os campos do produto** devolvidos pela API (D14):
  - objetos aninhados viram colunas com prefixo e `_` (ex.: `ncm_code`, `brand_name`, `cest_description`, `category_parent_id`);
  - `gtins` não vira coluna: vai para `gtins.csv`, e aqui fica só `gtins_qtd`;
  - outras listas que aparecerem são gravadas como texto JSON.
- Ordem das colunas: a da primeira aparição, lendo o bruto em ordem cronológica. Campos novos vão para o final.
- `registro_id` = `{fonte}|p{pagina:04d}|{coletado_em}|{posicao:02d}`, com posição de 1 a 30 na página.

### 6.2 `gtins.csv` — 1 linha por GTIN listado (D16, D22)
`registro_id`, `produto_gtin`, `gtin`, `e_o_proprio` (`sim`/`não`), `type_packaging`, `quantity_packaging`,
`ballast`, `layer`, `fonte`, `pagina`, `coletado_em`. Nunca há substituição: GTIN repetido gera linhas repetidas.

### 6.3 `conferencia_ncm.csv` — 1 linha por NCM-alvo
`ncm`, `descricao`, `total_api`, `total_lido_em`, `paginas_coletadas`, `total_paginas`, `linhas_baixadas`,
`gtins_distintos`, `diferenca` (= `total_api − gtins_distintos`), `status`.

Valores de `status`:
- `não iniciado`;
- `em andamento`;
- `concluído`, quando todas as páginas foram coletadas e `diferenca ≤ 0`;
- `concluído com falta`, quando todas as páginas foram coletadas e `diferenca > 0`.

Refazer um NCM é **decisão manual**.

### 6.4 `execucoes.csv` — 1 linha por execução
`inicio`, `fim`, `consultas_feitas`, `paginas_concluidas`, `produtos_baixados`, `motivo_parada`,
`alertas`, `paginas_restantes`, `dias_previstos`.

## 7. Execução diária — cron-job.org + GitHub Actions (D27)

### 7.1 Workflow `.github/workflows/coleta.yml`
- Gatilho: **somente `workflow_dispatch`**, sem `schedule`. Isso evita os atrasos e descartes do agendamento
  do GitHub e a desativação por 60 dias sem atividade, que só afeta `schedule` (referência 14).
- `concurrency` com grupo único e `cancel-in-progress: false`, para nunca haver 2 execuções simultâneas.
- `permissions: contents: write`.
- Sem `timeout-minutes` próprio (D20).
- Passos:
  1. checkout;
  2. Python 3.12;
  3. `python -m coletor`, com `COSMOS_TOKEN` vindo de `secrets.COSMOS_TOKEN`;
  4. **commit e push de `dados/` e `saida/` com `if: always()`**, somente se houver mudanças.
- O token do Cosmos só existe como *secret* e nunca é impresso.

### 7.2 Job no cron-job.org (configurado pela Pilar)
- Frequência: 1x a cada 24 h, horário fixo; sugestão fora da hora cheia, por exemplo 03:17 BRT.
- Requisição (referências 16 e 17 em `referencias.md`):
  - `POST https://api.github.com/repos/{usuario}/{repositorio}/actions/workflows/coleta.yml/dispatches`
  - Cabeçalhos: `Authorization: Bearer <token GitHub>`, `Accept: application/vnd.github+json`,
    `X-GitHub-Api-Version: <versão indicada na documentação no dia da configuração>`
  - Corpo: `{"ref": "main"}`
  - Sucesso: HTTP 200, segundo a documentação consultada em 15/09/2026. Confirmar no teste manual.
- **Token GitHub:** *fine-grained personal access token* restrito **só a este repositório**, com a permissão
  mínima que a documentação exigir para disparar workflows (a página consultada não detalha; **confirmar na
  configuração**). A validade deve cobrir a coleta com folga: ≥ 120 dias, com lembrete antes de expirar.
  Esse token fica guardado no cron-job.org, que é um terceiro, por isso a permissão precisa ser mínima.
- Ativar as **notificações de falha** do cron-job.org.
  Elas indicam só que o disparo falhou. Falhas *dentro* da execução são avisadas pelo GitHub por e-mail.
- **Primeira execução:** nunca antes de **16/09/2026 12:16 BRT**, quando termina a janela de 24 h das
  consultas de teste de 15/09. O estado começa sem esse histórico (D26).

## 8. Segurança (D21)
- `.gitignore`: `.env`, `documentos/*.html`, `documentos/*_files/`, `*.tmp`, `__pycache__/`, `.pytest_cache/`, `.coverage`, `.serena/`.
- Um teste automatizado garante que esses caminhos são ignorados pelo git, e **antes do primeiro commit** a lista de arquivos é conferida com a Pilar.
- Mensagens de erro da API são truncadas e nunca incluem cabeçalhos da requisição.

## 9. Dados de teste de 15/09 (D26, D28)
- Os arquivos de teste (`saida/produtos.jsonl`, `saida/estado.json`, `saida/bebidas_alcoolicas.csv`) são
  **movidos** para `documentos/exploracao/2026-09-15/`, marcados como exploratórios. Nada é apagado sem confirmação.
- Eles **não** são lidos pelo coletor e **não** entram em `dados/` nem nos CSVs de saída.
- O coletor começa com `dados/estado.json` vazio.

## 10. Testes (TDD, D25)
Todos com API falsa, sem consultas reais. As respostas de exemplo são uma página real dos testes de 15/09 (`documentos/exploracao/`), usada só como modelo nos testes.

| Área | Casos |
|---|---|
| `cota` | 23 consultas → pode; 24 → não pode; mais antiga libera em 10 min → espera; em 5 h → para |
| `api` | 200 → resposta; 429 → `CotaEsgotada`; 401/403 → `TokenInvalido`; 500 três vezes → `FalhaTemporaria`; JSON quebrado → `RespostaInvalida`; token ausente das mensagens |
| `estado` / `bruto` | Gravação atômica; mesma página 2x → 2 arquivos; estado inexistente → estado vazio |
| `principal` | Ordem (contagens primeiro); retomada da página seguinte; **cada motivo da tabela 5.5** gera estado salvo + CSVs + linha em `execucoes.csv` + código de saída correto; página vazia gera alerta |
| `exportar` | Todos os campos; campo novo no final; `registro_id` idêntico nos 2 CSVs; GTIN repetido gera 2 linhas; `e_o_proprio`; status da conferência; BOM e `;` |
| segurança | `.env` e HTML ignorados pelo git |

Cobertura ≥ 80% com `pytest --cov=coletor`. Depois da implementação: revisão de código e de segurança.

## 11. Documentação
- `README.md` (D24): o que é, fonte dos dados e Termos de Uso, como rodar local e no Actions, onde estão as decisões e as saídas.
- `documentos/plano-e-praticas.md`, `ncms-alvo.md` e `referencias.md` são mantidos e publicados.
- `ncms_alvo.csv` (`ncm;descricao;status`) é gerado a partir de `ncms-alvo.md` e passa a ser a configuração usada pelo coletor.
- O protótipo `cosmos_bebidas.py` é removido **após** o coletor novo passar nos testes, com confirmação da Pilar.

## 12. Riscos conhecidos

| Risco | Mitigação |
|---|---|
| A lista muda entre dias e itens escorregam entre páginas | `conferencia_ncm.csv` + decisão manual de refazer o NCM |
| Não se sabe se o 429 conta como consulta, nem a hora exata em que a cota renova | Limite 24, contagem conservadora de toda requisição, janela móvel |
| Disparo diário falhar (cron-job.org fora do ar, token GitHub expirado ou revogado) | Notificação de falha do cron-job.org; validade do token ≥ 120 dias com lembrete; disparo manual disponível; a coleta retoma de onde parou |
| Fila do GitHub atrasar o início após o disparo | Espera de até 120 min pela janela de cota (seção 5.2) |
| Token GitHub guardado em terceiro (cron-job.org) | Token fino, restrito a este repositório, com permissão mínima |
| Dados públicos versus Termos de Uso | Risco aceito e documentado (D21) |
| Token vazar | *Secret*, `.gitignore`, teste automatizado e conferência antes do 1º commit |
