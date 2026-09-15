# Catálogo de bebidas alcoólicas — coleta via API do Bluesoft Cosmos

Coleta diária, pela API oficial do [Bluesoft Cosmos](https://cosmos.bluesoft.com.br/), dos produtos
cadastrados nos NCMs de bebidas alcoólicas vendidas ao consumidor final (e cerveja sem álcool), para pesquisa.

## Fonte e limites
- Os dados vêm do Bluesoft Cosmos, uma base **colaborativa**: podem conter erros, duplicatas e lacunas.
- O uso está sujeito aos [Termos de Uso do Cosmos](https://cosmos.bluesoft.com.br/termos_de_servico).
- Plano gratuito da API: 25 consultas/dia. O coletor usa **no máximo 24 por janela de 24 h**.

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
1. Crie um arquivo `.env` na raiz do projeto com uma única linha: `COSMOS_TOKEN=<seu token>`. Esse arquivo
   nunca é commitado (está no `.gitignore`).
2. Rode `.venv/Scripts/python -m coletor`.

> **Atenção**: isso consome cota real da API (compartilhada com a coleta diária) e altera o `dados/estado.json`
> e os CSVs **locais**, deixando-os fora de sincronia com o estado do repositório. Evite rodar localmente
> enquanto a coleta diária estiver ativa.

## Execução diária
O workflow `.github/workflows/coleta.yml` só roda por `workflow_dispatch`. Ele é disparado 1x por dia pelo
cron-job.org, e o token do Cosmos fica no *secret* `COSMOS_TOKEN`. Ao final, ele commita `dados/` e `saida/`,
mesmo se a coleta falhar.

A configuração no cron-job.org faz um POST em horário fixo diário para
`https://api.github.com/repos/<usuario>/<repositorio>/actions/workflows/coleta.yml/dispatches`, com os
cabeçalhos:
- `Authorization: Bearer <token do GitHub, fine-grained, restrito a este repositório, permissão Actions: Read and write>`
- `Accept: application/vnd.github+json`

e corpo `{"ref":"main"}`. Qualquer resposta `2xx` é considerada sucesso (o disparo é assíncrono; o resultado da
coleta em si só aparece depois, na aba Actions do repositório).

Disparar o workflow manualmente também consome cota real e desloca a janela de 24 h: a execução agendada
seguinte pode então parar em `limite` sem consultar a API.

Antes de mexer no repositório localmente, rode `git pull`: o workflow commita dados todos os dias.
