# Referências e sites acessados

**Regra:** todo site ou endpoint acessado durante o projeto, seja pela Pilar ou pelo
Claude, é registrado aqui com link e data de acesso. Isso serve para as referências
bibliográficas e para a reprodutibilidade.

- `Quem`: Pilar ou Claude.
- `Como`: navegador, API (curl/script) ou WebFetch.
- Datas no formato AAAA-MM-DD.

## 1. Registro de acessos

| # | Data | Quem | Como | URL | O que foi obtido / uso |
|---|---|---|---|---|---|
| 1 | 2026-09-14 | Pilar | navegador | https://cosmos.bluesoft.com.br/ | Site do Bluesoft Cosmos (catálogo colaborativo de produtos) |
| 2 | 2026-09-15 | Pilar | navegador | https://portalunico.siscomex.gov.br/classif/#/nomenclatura/tabela?perfil=publico | Download da Tabela NCM vigente (`Tabela_NCM_Vigente_20260915.xlsx`) |
| 3 | 2026-09-15 | Pilar | navegador | https://cosmos.bluesoft.com.br/api | Página da documentação da API, salva em `documentos/` (contém o token pessoal, não compartilhar) |
| 4 | 2026-09-15 | Claude | API | https://cosmos.bluesoft.com.br/api/ncms/{ncm}/products | Teste de paginação e contagem por NCM; coleta piloto (1ª página de 19 NCMs) |
| 5 | 2026-09-15 | Claude | API | https://cosmos.bluesoft.com.br/api/gpcs/{gpc} | Teste do endpoint GPC (10000159 Cerveja; 50202200 Bebidas alcoólicas) |
| 6 | 2026-09-15 | Claude | API | https://cosmos.bluesoft.com.br/api/gtins/7891910000197 | Teste para ver se o limite de requisições reinicia (HTTP 429 após 2 e 12 min) |
| 7 | 2026-09-15 | Claude | curl | https://cosmos.bluesoft.com.br/gpcs/50202200 | Tentativa de listar os bricks GPC: **bloqueado (HTTP 403, Cloudflare)** |
| 8 | 2026-09-15 | Claude | WebFetch | https://cosmos.bluesoft.com.br/api-pricings | Planos e limites da API (Básico: 25 consultas/dia; Simple: 100; Standard: 200; Pro: 500) |
| 9 | 2026-09-15 | Claude | curl | https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json?perfil=PUBLICO | Tabela NCM em JSON (usada para listar os NCMs do capítulo 22) |
| 10 | 2026-09-15 | Pilar | navegador | https://cosmos.bluesoft.com.br/ (aba de busca, termo "cerveja") ³ | 15 mil+ resultados; ~3 mil+ com NCM começando em 22; muitos itens relacionados que não são bebida (ex.: abridor) |
| 11 | 2026-09-15 | Claude | arquivo local | https://cosmos.bluesoft.com.br/termos_de_servico (conteúdo lido do HTML salvo em `documentos/`) | Termos de Uso: cláusulas sobre conta única, intransferibilidade e uso profissional |
| 12 | 2026-09-15 | Claude | WebFetch | https://docs.github.com/en/billing/concepts/product-billing/github-actions | Cobrança do GitHub Actions: plano Free tem 2.000 min/mês, cobrados por conta (dono do repositório); gratuito e ilimitado em repositórios públicos; 500 MB de artifacts compartilhados com Packages |
| 13 | 2026-09-15 | Claude | WebFetch | https://docs.github.com/en/actions/reference/limits | Limites dos runners: 20 jobs simultâneos no Free; até 6 h por job |
| 14 | 2026-09-15 | Claude | WebFetch | https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows | Evento `schedule`: pode atrasar em alta carga (sobretudo no início de cada hora), execuções podem ser descartadas, horário em UTC, intervalo mínimo 5 min; em repositório público o agendamento é desativado após 60 dias sem atividade |
| 15 | 2026-09-15 | Pilar | navegador | https://cron-job.org/en/ | Serviço gratuito de cron escolhido para disparar a coleta diária |
| 16 | 2026-09-15 | Claude | WebFetch | https://cron-job.org/en/ | Recursos: requisições com método, cabeçalhos e corpo personalizados; gratuito; até 60x/hora; notificações de falha; histórico de execuções |
| 17 | 2026-09-15 | Claude | WebFetch | https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event | Endpoint para disparar workflow: `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches`, corpo `ref`, cabeçalhos, sucesso 200; permissão de token fino não detalhada na página |
| 18 | 2026-09-15 | Claude | WebFetch | https://github.com/actions/checkout/releases/latest | Versão mais recente de actions/checkout: v7.0.1 (usada no workflow como @v7) |
| 19 | 2026-09-15 | Claude | WebFetch | https://github.com/actions/setup-python/releases/latest | Versão mais recente de actions/setup-python: v7.0.0 (usada no workflow como @v7) |
| 20 | 2026-09-15 | Claude | WebFetch | https://docs.github.com/en/account-and-profile/reference/permission-levels-for-a-personal-account-repository | Níveis de permissão em repositório de conta pessoal (a página não trata de secrets/variáveis do Actions) |
| 21 | 2026-09-15 | Claude | WebFetch | https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets | Secrets: em repositório de conta pessoal, colaboradores podem criar/atualizar; o workflow lê o valor atual via contexto `secrets`; secret não definido vira texto vazio |
| 22 | 2026-09-15 | Claude | WebFetch | https://docs.github.com/en/actions/reference/workflows-and-actions/contexts | Contextos do Actions: sintaxe de índice, disponibilidade de `env`/`vars` em `steps[*].env`; a página não confirma acesso a secret por nome dinâmico (`secrets[format(...)]`), por isso não foi usado |
| 23 | 2026-09-15 | Claude | WebFetch | https://docs.cron-job.org/rest-api.html | cron-job.org: não há configuração de códigos HTTP aceitos; 2xx (inclusive 204) já é sucesso, e `redirectSuccess` trata apenas 3xx |

As datas dos acessos 1 e 3 foram confirmadas pela Pilar em 2026-09-15.

³ URL exata da página de resultados não registrada. **Pilar: colar a URL da busca, se possível.**

## 2. Referências formatadas (rascunho ABNT NBR 6023)

> Revisar autoria institucional e títulos antes de usar em trabalho acadêmico.

BLUESOFT. **Cosmos**: catálogo de produtos, GTIN, NCM, tributação e marca. [S. l.]:
Bluesoft, [2026]. Disponível em: https://cosmos.bluesoft.com.br/. Acesso em: 14 set. 2026.

BLUESOFT. **Cosmos API**: documentação. [S. l.]: Bluesoft, [2026]. Disponível em:
https://cosmos.bluesoft.com.br/api. Acesso em: 15 set. 2026.

BLUESOFT. **Cosmos API**: planos e preços. [S. l.]: Bluesoft, [2026]. Disponível em:
https://cosmos.bluesoft.com.br/api-pricings. Acesso em: 15 set. 2026.

BLUESOFT. **Termos de Uso do Cosmos**. [S. l.]: Bluesoft, [2026]. Disponível em:
https://cosmos.bluesoft.com.br/termos_de_servico. Acesso em: 15 set. 2026.

BRASIL. Portal Único Siscomex. **Tabela NCM vigente**: nomenclatura comum do Mercosul.
Vigente em 15 set. 2026. Brasília, DF, 2026. Disponível em:
https://portalunico.siscomex.gov.br/classif/#/nomenclatura/tabela?perfil=publico.
Acesso em: 15 set. 2026.

## 3. Fontes citadas, mas ainda não acessadas

| Fonte | Onde apareceu | Observação |
|---|---|---|
| Resolução Gecex nº 926/2026 | Cabeçalho da Tabela NCM | Última atualização da tabela |
| Resolução Gecex nº 272/2021 | Coluna "Ato Legal Início" dos NCMs do cap. 22 | Ato de início de vigência dos códigos |
