# Catálogo de bebidas alcoólicas — coleta via API do Bluesoft Cosmos

Coleta diária, pela API oficial do [Bluesoft Cosmos](https://cosmos.bluesoft.com.br/), dos produtos
cadastrados nos NCMs de bebidas alcoólicas vendidas ao consumidor final (e cerveja sem álcool), para pesquisa.

## Fonte e limites
- Os dados vêm do Bluesoft Cosmos, uma base **colaborativa**: podem conter erros, duplicatas e lacunas.
- O uso está sujeito aos [Termos de Uso do Cosmos](https://cosmos.bluesoft.com.br/termos_de_servico).
- Plano gratuito da API: 25 consultas/dia. O coletor usa **no máximo 23 por janela de 24 h** — não 24: em
  16/09/2026 a 25ª consulta do dia recebeu HTTP 429, então 24 não deixava folga para requisições que o
  Cosmos conte e nós não.

## Estrutura
| Caminho | Conteúdo |
|---|---|
| `coletor/` | Código do coletor (Python 3.12, só biblioteca padrão) |
| `ncms_alvo.csv` | NCMs coletados (`status = alvo`) |
| `dados/bruto/` | Respostas da API, uma por página, nunca alteradas |
| `dados/estado.json` | Progresso por NCM e histórico de consultas |
| `saida/` | `produtos.csv`, `gtins.csv`, `conferencia_ncm.csv`, `execucoes.csv` |
| `documentos/` | Decisões e práticas, NCMs-alvo, referências, spec e plano de implementação |

## Sobre os CSVs
- UTF-8 com BOM, separador `;`.
- `produtos.csv` **não é deduplicado**: uma linha por produto por página coletada. A deduplicação é etapa de tratamento.
- `registro_id` liga cada linha de `gtins.csv` ao produto em `produtos.csv`.
- Para não perder dígitos do GTIN no Excel: *Dados → De Texto/CSV*, com as colunas `gtin` e `produto_gtin` como **Texto**.
- **Aviso de segurança**: a base é colaborativa e os campos de texto (ex.: descrição, marca) podem começar com
  `=`, `+`, `-` ou `@`. Abra os CSVs **somente** por *Dados → De Texto/CSV* (Power Query) — nunca por duplo clique —
  para que nenhum texto seja interpretado como fórmula pela planilha. Os valores são mantidos exatamente como
  vieram da API, sem qualquer escape.

## Desenvolvimento
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
.venv/Scripts/python -m pytest --cov=coletor
```

## Rodar a coleta localmente (só para teste pontual)
1. Crie um arquivo `.env` na raiz do projeto com duas linhas (nunca é commitado, está no `.gitignore`):
   ```
   COSMOS_TOKEN=<seu token>
   COLETOR_RESPONSAVEL=PILAR
   ```
   - `COLETOR_RESPONSAVEL` identifica **quem coletou**: é gravado em cada página bruta e nas colunas de
     `produtos.csv`, `gtins.csv` e `execucoes.csv`. A cota de 23 consultas por 24 h é contada **por responsável**.
   - Os dois são obrigatórios: sem um deles, o coletor para com erro de configuração e não consulta a API.
2. Rode `.venv/Scripts/python -m coletor`.

> **Atenção**: isso consome cota real da API (compartilhada com a coleta diária) e altera o `dados/estado.json`
> e os CSVs **locais**, deixando-os fora de sincronia com o estado do repositório. Evite rodar localmente
> enquanto a coleta diária estiver ativa.

## Execução diária
O workflow `.github/workflows/coleta.yml` só roda por `workflow_dispatch`. Ele é disparado 1x por dia pelo
cron-job.org. O nome da pessoa aparece **uma única vez** no workflow, na linha `cred: [PILAR]`: dela saem o
secret usado (`PILAR_COSMOS_TOKEN`, entregue ao coletor como `COSMOS_TOKEN`) e o rótulo gravado nos dados
(`COLETOR_RESPONSAVEL`). Ao final, ele commita `dados/` e `saida/`,
mesmo se a coleta falhar.

Se o `git push` falhar (por exemplo, duas execuções coincidindo e criando os mesmos arquivos), o workflow
reconcilia: as páginas brutas nunca conflitam, o `estado.json` é fundido (união das consultas por
responsável, maior página por NCM) e os CSVs derivados são regerados a partir do bruto — e tenta de novo,
até 5 vezes. Se ainda assim falhar, os dados daquela execução ficam disponíveis como *artifact* da execução
(aba Actions, 30 dias de retenção).

A configuração no cron-job.org faz um POST em horário fixo diário para
`https://api.github.com/repos/pilarcs/webscrapping-bev/actions/workflows/coleta.yml/dispatches`, com os
cabeçalhos:
- `Authorization: Bearer <token do GitHub, fine-grained, restrito a este repositório, permissão Actions: Read and write>`
- `Accept: application/vnd.github+json`
- `X-GitHub-Api-Version: <versão indicada na documentação do endpoint>` — opcional, mas recomendado:
  fixa a versão da API e evita surpresa se o padrão mudar

e corpo `{"ref":"main"}`. Qualquer resposta `2xx` é considerada sucesso (o disparo é assíncrono; o resultado da
coleta em si só aparece depois, na aba Actions do repositório).

Disparar o workflow manualmente também consome cota real e desloca a janela de 24 h: a execução agendada
seguinte pode então parar em `limite` sem consultar a API.

Antes de mexer no repositório localmente, rode `git pull`: o workflow commita dados todos os dias.

## Sucessão (quando outra pessoa assumir a coleta)
Só uma pessoa coleta por vez, cada uma com a própria conta do Cosmos.
1. Quem assume vira colaboradora do repositório e cria o *secret* dela
   (ex.: `ORIENTADORA_COSMOS_TOKEN`), em *Settings → Secrets and variables → Actions*.
2. No `.github/workflows/coleta.yml`, troca **uma palavra**: a linha `cred: [PILAR]` passa a
   `cred: [ORIENTADORA]`. Dela saem o secret usado e o rótulo gravado nos dados, então não há como o
   rótulo discordar do token. Nenhuma linha de Python muda, e a lista deve ter sempre um único nome.
3. Commita a mudança. O commit fica no histórico, datado e no nome dela: é o registro de quando a coleta
   mudou de mãos.
4. A partir da execução seguinte, os registros saem com o rótulo dela e a janela de 24 h dela começa vazia.
5. Se ela usar o próprio job no cron-job.org, o job anterior deve ser desativado, para não haver dois
   disparos no mesmo dia.
