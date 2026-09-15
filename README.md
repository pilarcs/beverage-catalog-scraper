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

## Desenvolvimento
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
.venv/Scripts/python -m pytest --cov=coletor
```

> **Não rode `python -m coletor` localmente enquanto a coleta diária estiver ativa**: isso consome a mesma
> cota e cria um estado local diferente do estado do repositório.

## Execução diária
O workflow `.github/workflows/coleta.yml` só roda por `workflow_dispatch`. Ele é disparado 1x por dia pelo
cron-job.org, e o token do Cosmos fica no *secret* `COSMOS_TOKEN`. Ao final, ele commita `dados/` e `saida/`,
mesmo se a coleta falhar.
