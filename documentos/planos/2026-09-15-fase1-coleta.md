# Fase 1 — Coletor por NCM (Cosmos) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o coletor diário que baixa, pela API do Bluesoft Cosmos, todas as páginas dos 21 NCMs-alvo. Ele respeita 24 consultas por janela de 24 h, guarda o bruto imutável e gera 4 CSVs, com finalização garantida em qualquer parada.

**Architecture:** Pacote Python `coletor/` com módulos pequenos (config, tempo, arquivos, cota, estado, bruto, api, exportar, principal). A API é injetada no orquestrador, o que permite testar tudo com uma API falsa e um relógio falso, sem gastar cota. O GitHub Actions roda `python -m coletor` quando o cron-job.org dispara `workflow_dispatch` e commita `dados/` e `saida/` mesmo em caso de falha.

**Tech Stack:** Python 3.12 (em produção só a biblioteca padrão), pytest + pytest-cov (desenvolvimento), GitHub Actions, cron-job.org.

**Spec:** `documentos/specs/2026-09-15-fase1-coleta-design.md` (decisões Dn em `documentos/plano-e-praticas.md`, seção 5)

## Global Constraints

- Python **3.12**; o código em `coletor/` usa **somente a biblioteca padrão**. `pytest` e `pytest-cov` só em `requirements-dev.txt`.
- **Nenhuma consulta real à API do Cosmos durante a implementação ou os testes.** Toda API é falsa. Exceção única: a Task 12, passo de primeira execução, com confirmação da Pilar e **nunca antes de 16/09/2026 12:16 BRT**.
- Limite: **24 consultas por janela móvel de 24 h** (`LIMITE_CONSULTAS`, 1–25, padrão 24). Espera máxima pela janela: **120 min** (`ESPERA_MAXIMA_MIN`, 0–1440, padrão 120).
- Toda requisição HTTP enviada (inclusive novas tentativas e erros) conta na cota.
- Horários em UTC, formato `YYYY-MM-DDTHH:MM:SSZ`; em nomes de arquivo, `YYYYMMDDTHHMMSSZ`.
- CSVs: **UTF-8 com BOM**, separador `;`, GTIN/NCM gravados como texto exato.
- Bruto e estado gravados de forma **atômica** (arquivo `.tmp` + `os.replace`). O bruto **nunca** é sobrescrito.
- Repositório **público**: `.env`, `documentos/*.html`, `documentos/*_files/`, `.serena/` e `cosmos_bebidas.py` **nunca** são commitados.
- Commits: Conventional Commits (`feat:`, `test:`, `chore:`, `docs:`), arquivos adicionados **pelo nome** (nunca `git add -A`/`.`), sem `--no-verify`.
- Idioma dos identificadores, mensagens e documentação: português.
- Comandos assumem Git Bash no Windows, a partir da raiz do projeto `C:\Users\Pilar\Documents\Coding\raspagem-catalogo-bebidas`. Python do ambiente virtual: `.venv/Scripts/python`.
- Toda página web ou endpoint acessado durante a implementação é registrado em `documentos/referencias.md` (URL, data, quem, como, para quê).

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `.gitignore` | Impede commit de segredos e artefatos locais |
| `pyproject.toml` | Configuração do pytest e do coverage (mínimo 80%) |
| `requirements-dev.txt` | `pytest`, `pytest-cov` |
| `ncms_alvo.csv` | Lista de NCMs (`ncm;descricao;status`); o coletor usa só `alvo` |
| `coletor/__init__.py` | Marca o pacote |
| `coletor/tempo.py` | Relógio UTC e conversões de data/hora |
| `coletor/arquivos.py` | Gravação atômica de texto e JSON |
| `coletor/config.py` | `NcmAlvo`, `Config`, leitura de `ncms_alvo.csv`, `.env` e variáveis |
| `coletor/cota.py` | Janela móvel de 24 h: quantas consultas, quanto esperar, poda do histórico |
| `coletor/estado.py` | `dados/estado.json`: carregar, salvar e atualizar progresso e consultas |
| `coletor/bruto.py` | `dados/bruto/`: gravar página (sem sobrescrever) e listar em ordem |
| `coletor/api.py` | `ClienteCosmos`: 1 página por chamada, novas tentativas, exceções tipadas |
| `coletor/exportar.py` | `produtos.csv`, `gtins.csv`, `conferencia_ncm.csv`, `execucoes.csv` |
| `coletor/principal.py` | Ordem da coleta, laço, classificação da parada, finalização garantida |
| `coletor/__main__.py` | Entrada `python -m coletor`, sinais, montagem das dependências reais |
| `tests/__init__.py`, `tests/ajudantes.py`, `tests/conftest.py` | API falsa, relógio falso, fábricas de produto e página |
| `tests/test_*.py` | Um arquivo de teste por módulo + segurança + workflow |
| `.github/workflows/coleta.yml` | Execução disparada (workflow_dispatch) + commit dos dados |
| `README.md` | Apresentação do repositório público |

---

### Task 0: Preparar repositório, dados exploratórios e proteção de segredos

**Files:**
- Create: `.gitignore`, `pyproject.toml`, `requirements-dev.txt`, `tests/__init__.py`, `tests/test_seguranca.py`
- Move: `saida/produtos.jsonl`, `saida/estado.json`, `saida/bebidas_alcoolicas.csv` → `documentos/exploracao/2026-09-15/`

**Interfaces:**
- Consumes: nada
- Produces: repositório git em `main`, ambiente `.venv` com pytest, `.gitignore` validado por teste

- [ ] **Step 1: Mover os dados de teste de 15/09 e criar o ambiente virtual**

```bash
mkdir -p documentos/exploracao/2026-09-15
mv saida/produtos.jsonl saida/estado.json saida/bebidas_alcoolicas.csv documentos/exploracao/2026-09-15/
python -m venv .venv
```

- [ ] **Step 2: Criar `requirements-dev.txt`, `pyproject.toml` e `tests/__init__.py`, instalar e iniciar o git**

`requirements-dev.txt`:
```text
pytest>=8
pytest-cov>=5
```

`pyproject.toml`:
```toml
[project]
name = "raspagem-catalogo-bebidas"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"

[tool.coverage.run]
source = ["coletor"]
branch = true

[tool.coverage.report]
fail_under = 80
show_missing = true
```

`tests/__init__.py`: arquivo vazio.

```bash
.venv/Scripts/python -m pip install -r requirements-dev.txt
git init -b main
```

- [ ] **Step 3: Escrever o teste de segurança (falha antes do `.gitignore`)**

`tests/test_seguranca.py`:
```python
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
HTML = "documentos/Catálogo de Produtos, GTIN, NCM, Tributação e Marca - Cosmos.html"
PASTA_HTML = "documentos/Catálogo de Produtos, GTIN, NCM, Tributação e Marca - Cosmos_files/main.js.download"
PROIBIDOS = [".env", HTML, PASTA_HTML, ".serena/project.yml", "cosmos_bebidas.py", "coletor/x.json.tmp"]


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")


@pytest.fixture(scope="module", autouse=True)
def exige_git():
    if shutil.which("git") is None or _git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        pytest.skip("repositório git não inicializado")


@pytest.mark.parametrize("caminho", PROIBIDOS)
def test_arquivo_sensivel_e_ignorado_pelo_git(caminho):
    resultado = _git("check-ignore", "--no-index", "-q", caminho)
    assert resultado.returncode == 0, f"{caminho} NÃO está no .gitignore"


def test_nenhum_arquivo_sensivel_rastreado():
    rastreados = _git("ls-files").stdout.splitlines()
    sensiveis = [c for c in rastreados if c == ".env" or c.endswith(".html") or "_files/" in c]
    assert sensiveis == []
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_seguranca.py -v`
Expected: FAIL em `test_arquivo_sensivel_e_ignorado_pelo_git` para todos os caminhos ("NÃO está no .gitignore")

- [ ] **Step 5: Criar `.gitignore`**

```gitignore
# segredos e página salva da API (contém token e link de perfil)
.env
documentos/*.html
documentos/*_files/

# ferramentas locais
.serena/
.venv/
__pycache__/
.pytest_cache/
.coverage
htmlcov/
*.tmp

# protótipo de exploração (removido na Task 12)
cosmos_bebidas.py
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_seguranca.py -v`
Expected: PASS (7 testes)

- [ ] **Step 7: CHECKPOINT — conferir com a Pilar a lista de arquivos antes do primeiro commit (spec §8)**

Run: `git status --porcelain --untracked-files=all`
Mostrar a saída completa à Pilar. Conferir que **não** aparecem `.env`, `.html`, `*_files/`, `.serena/`, `cosmos_bebidas.py`. **Não commitar sem o "ok" dela.**

- [ ] **Step 8: Commit**

```bash
git add .gitignore pyproject.toml requirements-dev.txt tests/__init__.py tests/test_seguranca.py \
  "documentos/plano-e-praticas.md" "documentos/ncms-alvo.md" "documentos/referencias.md" \
  "documentos/sites acessados.txt" "documentos/Tabela_NCM_Vigente_20260915.xlsx" \
  "documentos/specs/2026-09-15-fase1-coleta-design.md" "documentos/planos/2026-09-15-fase1-coleta.md" \
  documentos/exploracao/2026-09-15/produtos.jsonl documentos/exploracao/2026-09-15/estado.json \
  documentos/exploracao/2026-09-15/bebidas_alcoolicas.csv
git commit -m "chore: estrutura inicial, documentação e proteção de segredos"
```

---

### Task 1: Configuração (`ncms_alvo.csv`, `.env`, variáveis)

**Files:**
- Create: `ncms_alvo.csv`, `coletor/__init__.py`, `coletor/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - `NcmAlvo(ncm: str, descricao: str)` (dataclass frozen)
  - `Config(token: str, ncms: tuple[NcmAlvo, ...], limite_consultas: int, espera_maxima_min: int, raiz: Path)` (dataclass frozen)
  - `ConfigInvalida(Exception)`
  - `carregar_ncms(caminho: Path) -> tuple[NcmAlvo, ...]`
  - `ler_arquivo_env(caminho: Path) -> dict[str, str]`
  - `carregar_config(raiz: Path, ambiente: Mapping[str, str]) -> Config`

- [ ] **Step 1: Escrever os testes**

`tests/test_config.py`:
```python
from pathlib import Path

import pytest

from coletor.config import ConfigInvalida, NcmAlvo, carregar_config, carregar_ncms, ler_arquivo_env

RAIZ = Path(__file__).resolve().parents[1]


def _csv(tmp_path: Path, conteudo: str) -> Path:
    caminho = tmp_path / "ncms_alvo.csv"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_carregar_ncms_devolve_so_alvo_na_ordem(tmp_path):
    caminho = _csv(tmp_path, "ncm;descricao;status\n22085000;Gim;alvo\n22043000;Mosto;fora\n22030000;Cerveja;alvo\n")
    assert carregar_ncms(caminho) == (NcmAlvo("22085000", "Gim"), NcmAlvo("22030000", "Cerveja"))


@pytest.mark.parametrize("ncm", ["2208", "2208500A", "220850001"])
def test_carregar_ncms_rejeita_ncm_invalido(tmp_path, ncm):
    caminho = _csv(tmp_path, f"ncm;descricao;status\n{ncm};X;alvo\n")
    with pytest.raises(ConfigInvalida):
        carregar_ncms(caminho)


def test_carregar_ncms_sem_alvo_e_invalido(tmp_path):
    caminho = _csv(tmp_path, "ncm;descricao;status\n22043000;Mosto;fora\n")
    with pytest.raises(ConfigInvalida):
        carregar_ncms(caminho)


def test_arquivo_real_tem_21_ncms_alvo():
    ncms = {alvo.ncm for alvo in carregar_ncms(RAIZ / "ncms_alvo.csv")}
    assert len(ncms) == 21
    assert "22029100" in ncms
    assert {"22042220", "22042920", "22043000", "22071010", "22072020"}.isdisjoint(ncms)


def test_ler_arquivo_env_ignora_comentarios_e_linhas_vazias(tmp_path):
    caminho = tmp_path / ".env"
    caminho.write_text("# comentário\n\nCOSMOS_TOKEN = abc=def \nINVALIDA\n", encoding="utf-8")
    assert ler_arquivo_env(caminho) == {"COSMOS_TOKEN": "abc=def"}


def test_ler_arquivo_env_inexistente(tmp_path):
    assert ler_arquivo_env(tmp_path / ".env") == {}


def test_carregar_config_usa_padroes(tmp_path):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    config = carregar_config(tmp_path, {"COSMOS_TOKEN": "tk"})
    assert (config.token, config.limite_consultas, config.espera_maxima_min, config.raiz) == ("tk", 24, 120, tmp_path)


def test_carregar_config_aceita_valores_do_ambiente(tmp_path):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    config = carregar_config(tmp_path, {"COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "10", "ESPERA_MAXIMA_MIN": "0"})
    assert (config.limite_consultas, config.espera_maxima_min) == (10, 0)


@pytest.mark.parametrize(
    "ambiente",
    [
        {},
        {"COSMOS_TOKEN": "  "},
        {"COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "26"},
        {"COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "0"},
        {"COSMOS_TOKEN": "tk", "LIMITE_CONSULTAS": "vinte"},
        {"COSMOS_TOKEN": "tk", "ESPERA_MAXIMA_MIN": "-1"},
    ],
)
def test_carregar_config_rejeita_valores_invalidos(tmp_path, ambiente):
    _csv(tmp_path, "ncm;descricao;status\n22030000;Cerveja;alvo\n")
    with pytest.raises(ConfigInvalida):
        carregar_config(tmp_path, ambiente)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'coletor'`

- [ ] **Step 3: Implementar**

`coletor/__init__.py`:
```python
"""Coletor diário do catálogo de bebidas alcoólicas do Bluesoft Cosmos."""
```

`ncms_alvo.csv` (UTF-8, sem BOM):
```text
ncm;descricao;status
22029100;Cerveja sem álcool;alvo
22030000;Cervejas de malte;alvo
22041010;Vinhos espumantes - tipo champanha;alvo
22041090;Vinhos espumantes - outros;alvo
22042100;Outros vinhos, recipientes <= 2 l;alvo
22042211;Vinhos, recipientes > 2 l e <= 10 l, <= 5 l;alvo
22042219;Vinhos, recipientes > 2 l e <= 10 l, outros;alvo
22042220;Mostos, recipientes > 2 l e <= 10 l;fora
22042910;Vinhos, recipientes > 10 l;alvo
22042920;Mostos, outros recipientes;fora
22043000;Outros mostos de uvas;fora
22051000;Vermutes e vinhos aromatizados, <= 2 l;alvo
22059000;Vermutes e vinhos aromatizados, outros;alvo
22060010;Sidra;alvo
22060090;Outras bebidas fermentadas;alvo
22071010;Álcool etílico não desnaturado >= 80% vol, água <= 1%;fora
22071090;Álcool etílico não desnaturado >= 80% vol, outros;fora
22072011;Álcool etílico desnaturado, água <= 1%;fora
22072019;Álcool etílico desnaturado, outros;fora
22072020;Aguardente desnaturada;fora
22082000;Aguardentes de vinho ou de bagaço de uvas;alvo
22083010;Uísques > 50% vol, recipientes >= 50 l;alvo
22083020;Uísques, embalagens <= 2 l;alvo
22083090;Uísques, outros;alvo
22084000;Rum e aguardentes de cana;alvo
22085000;Gim e genebra;alvo
22086000;Vodca;alvo
22087000;Licores;alvo
22089000;Outras bebidas espirituosas;alvo
```

`coletor/config.py`:
```python
"""Configuração do coletor: NCMs-alvo, token e limites."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigInvalida(Exception):
    """Configuração ausente ou com valor inválido."""


@dataclass(frozen=True)
class NcmAlvo:
    ncm: str
    descricao: str


@dataclass(frozen=True)
class Config:
    token: str
    ncms: tuple[NcmAlvo, ...]
    limite_consultas: int
    espera_maxima_min: int
    raiz: Path


def carregar_ncms(caminho: Path) -> tuple[NcmAlvo, ...]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo, delimiter=";"))
    ncms: list[NcmAlvo] = []
    for linha in linhas:
        if linha["status"].strip() != "alvo":
            continue
        ncm = linha["ncm"].strip()
        if len(ncm) != 8 or not ncm.isdigit():
            raise ConfigInvalida(f"NCM inválido em {caminho.name}: {ncm!r}")
        ncms.append(NcmAlvo(ncm, linha["descricao"].strip()))
    if not ncms:
        raise ConfigInvalida(f"nenhum NCM com status 'alvo' em {caminho.name}")
    return tuple(ncms)


def ler_arquivo_env(caminho: Path) -> dict[str, str]:
    if not caminho.exists():
        return {}
    valores: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip()
    return valores


def _ler_inteiro(ambiente: Mapping[str, str], nome: str, padrao: int, minimo: int, maximo: int) -> int:
    texto = ambiente.get(nome, "").strip()
    if not texto:
        return padrao
    try:
        valor = int(texto)
    except ValueError:
        raise ConfigInvalida(f"{nome} deve ser um número inteiro, recebido {texto!r}") from None
    if not minimo <= valor <= maximo:
        raise ConfigInvalida(f"{nome} deve estar entre {minimo} e {maximo}, recebido {valor}")
    return valor


def carregar_config(raiz: Path, ambiente: Mapping[str, str]) -> Config:
    token = ambiente.get("COSMOS_TOKEN", "").strip()
    if not token:
        raise ConfigInvalida("COSMOS_TOKEN não definido (variável de ambiente ou arquivo .env)")
    return Config(
        token=token,
        ncms=carregar_ncms(raiz / "ncms_alvo.csv"),
        limite_consultas=_ler_inteiro(ambiente, "LIMITE_CONSULTAS", 24, 1, 25),
        espera_maxima_min=_ler_inteiro(ambiente, "ESPERA_MAXIMA_MIN", 120, 0, 1440),
        raiz=raiz,
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add ncms_alvo.csv coletor/__init__.py coletor/config.py tests/test_config.py
git commit -m "feat: configuração do coletor (NCMs-alvo, token e limites)"
```

---

### Task 2: Tempo, gravação atômica e cota de 24 h

**Files:**
- Create: `coletor/tempo.py`, `coletor/arquivos.py`, `coletor/cota.py`
- Test: `tests/test_tempo_arquivos.py`, `tests/test_cota.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - `tempo.agora_utc() -> datetime`, `tempo.para_iso(momento: datetime) -> str`, `tempo.de_iso(texto: str) -> datetime`, `tempo.para_nome_arquivo(momento: datetime) -> str`
  - `arquivos.gravar_texto_atomico(caminho: Path, texto: str, encoding: str = "utf-8") -> None`, `arquivos.gravar_json_atomico(caminho: Path, dados: object) -> None`
  - `cota.JANELA: timedelta` (24 h), `cota.HISTORICO: timedelta` (48 h)
  - `cota.consultas_na_janela(consultas: Sequence[datetime], agora: datetime) -> int`
  - `cota.segundos_para_liberar(consultas: Sequence[datetime], agora: datetime, limite: int) -> float`
  - `cota.podar(consultas: Sequence[datetime], agora: datetime) -> list[datetime]`

- [ ] **Step 1: Escrever os testes**

`tests/test_tempo_arquivos.py`:
```python
import json
from datetime import datetime, timedelta, timezone

import pytest

from coletor import arquivos
from coletor.tempo import agora_utc, de_iso, para_iso, para_nome_arquivo


def test_iso_ida_e_volta_em_utc():
    momento = datetime(2026, 9, 16, 3, 17, 5, tzinfo=timezone(timedelta(hours=-3)))
    assert para_iso(momento) == "2026-09-16T06:17:05Z"
    assert de_iso("2026-09-16T06:17:05Z") == datetime(2026, 9, 16, 6, 17, 5, tzinfo=timezone.utc)


def test_nome_de_arquivo_compacto():
    assert para_nome_arquivo(datetime(2026, 9, 16, 6, 17, 5, tzinfo=timezone.utc)) == "20260916T061705Z"


def test_agora_utc_sem_microssegundos():
    agora = agora_utc()
    assert agora.tzinfo == timezone.utc and agora.microsecond == 0


def test_gravar_json_atomico_nao_deixa_temporario(tmp_path):
    caminho = tmp_path / "sub" / "dados.json"
    arquivos.gravar_json_atomico(caminho, {"produto": "CERVEJA ÁGUA"})
    assert json.loads(caminho.read_text(encoding="utf-8")) == {"produto": "CERVEJA ÁGUA"}
    assert list(caminho.parent.glob("*.tmp")) == []


def test_falha_na_troca_preserva_arquivo_original(tmp_path, monkeypatch):
    caminho = tmp_path / "estado.json"
    caminho.write_text("original", encoding="utf-8")

    def falhar(origem, destino):
        raise OSError("disco cheio")

    monkeypatch.setattr(arquivos.os, "replace", falhar)
    with pytest.raises(OSError):
        arquivos.gravar_texto_atomico(caminho, "novo")
    assert caminho.read_text(encoding="utf-8") == "original"


def test_gravar_texto_com_bom(tmp_path):
    caminho = tmp_path / "a.csv"
    arquivos.gravar_texto_atomico(caminho, "a;b\r\n", encoding="utf-8-sig")
    assert caminho.read_bytes() == b"\xef\xbb\xbfa;b\r\n"
```

`tests/test_cota.py`:
```python
from datetime import datetime, timedelta, timezone

from coletor.cota import consultas_na_janela, podar, segundos_para_liberar

AGORA = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)


def _ha(horas: float = 0, minutos: float = 0) -> datetime:
    return AGORA - timedelta(hours=horas, minutes=minutos)


def test_23_consultas_pode_consultar():
    assert segundos_para_liberar([_ha(1)] * 23, AGORA, 24) == 0.0


def test_24_consultas_nao_pode_consultar():
    assert segundos_para_liberar([_ha(1)] * 24, AGORA, 24) == 23 * 3600


def test_mais_antiga_libera_em_10_minutos():
    consultas = [_ha(23, 50)] + [_ha(1)] * 23
    assert segundos_para_liberar(consultas, AGORA, 24) == 600


def test_consultas_fora_da_janela_nao_contam():
    consultas = [_ha(24)] * 30 + [_ha(1)] * 23
    assert consultas_na_janela(consultas, AGORA) == 23
    assert segundos_para_liberar(consultas, AGORA, 24) == 0.0


def test_acima_do_limite_espera_liberar_o_excedente():
    consultas = [_ha(23, 50), _ha(23, 40)] + [_ha(1)] * 23
    assert segundos_para_liberar(consultas, AGORA, 24) == 1200


def test_podar_mantem_so_48_horas():
    assert podar([_ha(49), _ha(47), _ha(1)], AGORA) == [_ha(47), _ha(1)]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_tempo_arquivos.py tests/test_cota.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'coletor.tempo'` / `'coletor.cota'`

- [ ] **Step 3: Implementar**

`coletor/tempo.py`:
```python
"""Data/hora em UTC e seus formatos de texto."""

from datetime import datetime, timezone

_FORMATO_ISO = "%Y-%m-%dT%H:%M:%SZ"
_FORMATO_NOME = "%Y%m%dT%H%M%SZ"


def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def para_iso(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime(_FORMATO_ISO)


def de_iso(texto: str) -> datetime:
    return datetime.strptime(texto, _FORMATO_ISO).replace(tzinfo=timezone.utc)


def para_nome_arquivo(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime(_FORMATO_NOME)
```

`coletor/arquivos.py`:
```python
"""Gravação atômica: escreve em .tmp e troca pelo definitivo, nunca deixa arquivo pela metade."""

import json
import os
from pathlib import Path


def gravar_texto_atomico(caminho: Path, texto: str, encoding: str = "utf-8") -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    with temporario.open("w", encoding=encoding, newline="") as arquivo:
        arquivo.write(texto)
        arquivo.flush()
        os.fsync(arquivo.fileno())
    os.replace(temporario, caminho)


def gravar_json_atomico(caminho: Path, dados: object) -> None:
    gravar_texto_atomico(caminho, json.dumps(dados, ensure_ascii=False, indent=1))
```

`coletor/cota.py`:
```python
"""Janela móvel de 24 h: funciona tanto se a cota renovar à meia-noite quanto 24 h após cada uso."""

from datetime import datetime, timedelta
from typing import Sequence

JANELA = timedelta(hours=24)
HISTORICO = timedelta(hours=48)


def _na_janela(consultas: Sequence[datetime], agora: datetime) -> list[datetime]:
    return sorted(c for c in consultas if agora - c < JANELA)


def consultas_na_janela(consultas: Sequence[datetime], agora: datetime) -> int:
    return len(_na_janela(consultas, agora))


def segundos_para_liberar(consultas: Sequence[datetime], agora: datetime, limite: int) -> float:
    na_janela = _na_janela(consultas, agora)
    if len(na_janela) < limite:
        return 0.0
    libera_em = na_janela[len(na_janela) - limite] + JANELA
    return max(0.0, (libera_em - agora).total_seconds())


def podar(consultas: Sequence[datetime], agora: datetime) -> list[datetime]:
    return [c for c in consultas if agora - c < HISTORICO]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_tempo_arquivos.py tests/test_cota.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/tempo.py coletor/arquivos.py coletor/cota.py tests/test_tempo_arquivos.py tests/test_cota.py
git commit -m "feat: relógio UTC, gravação atômica e janela de cota de 24 h"
```

---

### Task 3: Estado da coleta (`dados/estado.json`)

**Files:**
- Create: `coletor/estado.py`
- Test: `tests/test_estado.py`

**Interfaces:**
- Consumes: `arquivos.gravar_json_atomico`, `cota.podar`, `tempo.para_iso`, `tempo.de_iso`
- Produces:
  - `VERSAO = 1`, `EstadoInvalido(Exception)`
  - `estado_vazio() -> dict` → `{"versao": 1, "consultas": [], "ncms": {}}`
  - `carregar(caminho: Path) -> dict`, `salvar(caminho: Path, estado: dict) -> None`
  - `consultas(estado: dict) -> list[datetime]`, `registrar_consulta(estado: dict, momento: datetime) -> None`, `podar_consultas(estado: dict, agora: datetime) -> None`
  - `info_ncm(estado: dict, ncm: str) -> dict | None`: chaves `ultima_pagina: int`, `total_paginas: int`, `total_produtos: int`, `total_lido_em: str | None`, `concluido_em: str | None`
  - `atualizar_ncm(estado: dict, ncm: str, pagina: int, total_paginas: int, total_produtos: int, lido_em: datetime) -> None`

- [ ] **Step 1: Escrever os testes**

`tests/test_estado.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest

from coletor import estado as est

AGORA = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)


def test_estado_inexistente_devolve_vazio(tmp_path):
    assert est.carregar(tmp_path / "estado.json") == {"versao": 1, "consultas": [], "ncms": {}}


def test_salvar_e_carregar_ida_e_volta(tmp_path):
    caminho = tmp_path / "dados" / "estado.json"
    estado = est.estado_vazio()
    est.registrar_consulta(estado, AGORA)
    est.atualizar_ncm(estado, "22030000", 1, 200, 5981, AGORA)
    est.salvar(caminho, estado)
    assert est.carregar(caminho) == estado


@pytest.mark.parametrize("conteudo", ["{", '{"versao": 99, "consultas": [], "ncms": {}}', "[]"])
def test_estado_corrompido_ou_versao_desconhecida(tmp_path, conteudo):
    caminho = tmp_path / "estado.json"
    caminho.write_text(conteudo, encoding="utf-8")
    with pytest.raises(est.EstadoInvalido):
        est.carregar(caminho)


def test_atualizar_ncm_em_andamento_e_depois_concluido():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 2, 40, AGORA)
    assert est.info_ncm(estado, "22030000") == {
        "ultima_pagina": 1, "total_paginas": 2, "total_produtos": 40,
        "total_lido_em": "2026-09-16T06:17:00Z", "concluido_em": None,
    }
    depois = AGORA + timedelta(days=1)
    est.atualizar_ncm(estado, "22030000", 2, 2, 41, depois)
    info = est.info_ncm(estado, "22030000")
    assert (info["ultima_pagina"], info["total_produtos"], info["concluido_em"]) == (2, 41, "2026-09-17T06:17:00Z")


def test_ncm_sem_produtos_conclui_na_pagina_1():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22042219", 1, 1, 0, AGORA)
    assert est.info_ncm(estado, "22042219")["concluido_em"] == "2026-09-16T06:17:00Z"


def test_info_ncm_ausente():
    assert est.info_ncm(est.estado_vazio(), "22030000") is None


def test_consultas_registradas_e_podadas():
    estado = est.estado_vazio()
    est.registrar_consulta(estado, AGORA - timedelta(hours=49))
    est.registrar_consulta(estado, AGORA - timedelta(hours=1))
    est.podar_consultas(estado, AGORA)
    assert est.consultas(estado) == [AGORA - timedelta(hours=1)]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_estado.py -v`
Expected: FAIL com `ImportError: cannot import name 'estado' from 'coletor'`

- [ ] **Step 3: Implementar**

`coletor/estado.py`:
```python
"""Progresso da coleta e histórico de consultas, persistidos em dados/estado.json."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from coletor.arquivos import gravar_json_atomico
from coletor.cota import podar
from coletor.tempo import de_iso, para_iso

VERSAO = 1


class EstadoInvalido(Exception):
    """estado.json ilegível ou de versão desconhecida (nunca é sobrescrito nesse caso)."""


def estado_vazio() -> dict:
    return {"versao": VERSAO, "consultas": [], "ncms": {}}


def carregar(caminho: Path) -> dict:
    if not caminho.exists():
        return estado_vazio()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise EstadoInvalido(f"{caminho.name} não é JSON válido") from erro
    if not isinstance(dados, dict) or dados.get("versao") != VERSAO:
        raise EstadoInvalido(f"{caminho.name} tem formato ou versão desconhecida")
    return dados


def salvar(caminho: Path, estado: dict) -> None:
    gravar_json_atomico(caminho, estado)


def consultas(estado: dict) -> list[datetime]:
    return [de_iso(texto) for texto in estado["consultas"]]


def registrar_consulta(estado: dict, momento: datetime) -> None:
    estado["consultas"].append(para_iso(momento))


def podar_consultas(estado: dict, agora: datetime) -> None:
    estado["consultas"] = [para_iso(momento) for momento in podar(consultas(estado), agora)]


def info_ncm(estado: dict, ncm: str) -> dict | None:
    return estado["ncms"].get(ncm)


def atualizar_ncm(estado: dict, ncm: str, pagina: int, total_paginas: int, total_produtos: int, lido_em: datetime) -> None:
    info = estado["ncms"].setdefault(
        ncm,
        {"ultima_pagina": 0, "total_paginas": 0, "total_produtos": 0, "total_lido_em": None, "concluido_em": None},
    )
    info["ultima_pagina"] = max(info["ultima_pagina"], pagina)
    info["total_paginas"] = total_paginas
    info["total_produtos"] = total_produtos
    info["total_lido_em"] = para_iso(lido_em)
    if info["concluido_em"] is None and info["ultima_pagina"] >= total_paginas:
        info["concluido_em"] = para_iso(lido_em)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_estado.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/estado.py tests/test_estado.py
git commit -m "feat: estado da coleta com progresso por NCM e histórico de consultas"
```

---

### Task 4: Bruto imutável (`dados/bruto/`) e ajudantes de teste

**Files:**
- Create: `coletor/bruto.py`, `tests/ajudantes.py`, `tests/conftest.py`
- Test: `tests/test_bruto.py`

**Interfaces:**
- Consumes: `arquivos.gravar_json_atomico`, `tempo.para_iso`, `tempo.para_nome_arquivo`
- Produces:
  - `bruto.gravar_pagina(raiz_bruto: Path, ncm: str, pagina: int, url: str, coletado_em: datetime, resposta: dict) -> Path`
  - `bruto.listar_paginas(raiz_bruto: Path) -> list[dict]`: documentos `{"coleta": {fonte, ncm, pagina, url, coletado_em}, "resposta": {...}}` em ordem (coletado_em, ncm, pagina, nome do arquivo)
  - `tests/ajudantes.py`: `INICIO`, `produto(...)`, `resposta(...)`, `documento(...)`, `Relogio`, `ApiFalsa`, `roteiro_paginas(...)`
  - `tests/conftest.py`: fixtures `relogio`, `config`

- [ ] **Step 1: Criar os ajudantes de teste e escrever os testes do bruto**

`tests/ajudantes.py`:
```python
"""Fábricas e dublês de teste. Estrutura modelada em uma página real da API (15/09/2026)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

INICIO = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)


def produto(gtin: int, descricao: str = "CERVEJA TESTE LATA 350ML", gtins_extra: tuple[int, ...] = (), **extra) -> dict:
    base = {
        "description": descricao,
        "gtin": gtin,
        "width": None, "height": None, "length": None, "net_weight": None, "gross_weight": None,
        "created_at": "2014-04-24T11:07:34.000-03:00",
        "updated_at": "2026-09-02T16:48:59.000-03:00",
        "release_date": None, "price": None, "avg_price": None, "max_price": 0.0, "min_price": 0.0,
        "gtins": [{"gtin": gtin, "commercial_unit": {"type_packaging": "Unidade", "quantity_packaging": 1, "ballast": None, "layer": None}}]
        + [{"gtin": g, "commercial_unit": {"type_packaging": "Caixa", "quantity_packaging": 12, "ballast": 15, "layer": 4}} for g in gtins_extra],
        "origin": "COSMOS",
        "barcode_image": f"https://cosmos.bluesoft.com.br/products/barcode/{gtin}.png",
        "brand": {"name": "MARCA TESTE", "picture": "/assets/brand.png"},
        "gpc": None,
        "ncm": {"code": "22030000", "description": "Cervejas de malte.", "full_description": "Bebidas - Cervejas de malte.", "ex": None},
        "category": None,
    }
    base.update(extra)
    return base


def resposta(ncm: str, pagina: int, total_paginas: int, produtos: list[dict], total_count: int | None = None) -> dict:
    return {
        "code": ncm, "description": "descrição", "full_description": "descrição completa", "ex": None,
        "products": list(produtos), "current_page": pagina, "per_page": 30,
        "total_pages": total_paginas,
        "total_count": total_count if total_count is not None else total_paginas * 2,
    }


def documento(ncm: str, pagina: int, produtos: list[dict], coletado_em: str = "2026-09-16T06:17:05Z", total_paginas: int = 1) -> dict:
    return {
        "coleta": {
            "fonte": f"ncm:{ncm}", "ncm": ncm, "pagina": pagina,
            "url": f"https://cosmos.bluesoft.com.br/api/ncms/{ncm}/products?page={pagina}",
            "coletado_em": coletado_em,
        },
        "resposta": resposta(ncm, pagina, total_paginas, produtos),
    }


class Relogio:
    """Relógio falso: cada leitura avança 1 s; dormir() avança o tempo pedido e registra."""

    def __init__(self, inicio: datetime = INICIO):
        self.atual = inicio
        self.dormidas: list[float] = []

    def __call__(self) -> datetime:
        valor = self.atual
        self.atual += timedelta(seconds=1)
        return valor

    def dormir(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.atual += timedelta(seconds=segundos)


class ApiFalsa:
    """Imita ClienteCosmos: chama antes_de_enviar e devolve (ou lança) o que o roteiro mandar."""

    def __init__(self, antes_de_enviar: Callable[[], None], roteiro: Callable[[str, int], object]):
        self._antes = antes_de_enviar
        self._roteiro = roteiro
        self.chamadas: list[tuple[str, int]] = []

    def url_pagina(self, ncm: str, pagina: int) -> str:
        return f"https://cosmos.bluesoft.com.br/api/ncms/{ncm}/products?page={pagina}"

    def buscar_pagina(self, ncm: str, pagina: int) -> dict:
        self._antes()
        self.chamadas.append((ncm, pagina))
        resultado = self._roteiro(ncm, pagina)
        if isinstance(resultado, BaseException):
            raise resultado
        return resultado


def roteiro_paginas(totais: dict[str, int]) -> Callable[[str, int], dict]:
    """2 produtos por página, GTINs únicos por (ncm, página, posição)."""

    def roteiro(ncm: str, pagina: int) -> dict:
        itens = [produto(int(f"789{ncm}{pagina:03d}{i}")) for i in (1, 2)]
        return resposta(ncm, pagina, totais[ncm], itens)

    return roteiro
```

`tests/conftest.py`:
```python
import pytest

from coletor.config import Config, NcmAlvo
from tests.ajudantes import Relogio


@pytest.fixture
def relogio() -> Relogio:
    return Relogio()


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(
        token="token-de-teste",
        ncms=(NcmAlvo("22030000", "Cervejas de malte"), NcmAlvo("22085000", "Gim e genebra")),
        limite_consultas=24,
        espera_maxima_min=120,
        raiz=tmp_path,
    )
```

`tests/test_bruto.py`:
```python
import json
from datetime import datetime, timezone

from coletor import bruto
from tests.ajudantes import produto, resposta

MOMENTO = datetime(2026, 9, 16, 6, 17, 5, tzinfo=timezone.utc)
URL = "https://cosmos.bluesoft.com.br/api/ncms/22030000/products?page=2"


def test_gravar_pagina_cria_arquivo_com_coleta_e_resposta(tmp_path):
    corpo = resposta("22030000", 2, 200, [produto(7896657720018)])
    caminho = bruto.gravar_pagina(tmp_path, "22030000", 2, URL, MOMENTO, corpo)
    assert caminho == tmp_path / "ncm_22030000" / "p0002_20260916T061705Z.json"
    assert json.loads(caminho.read_text(encoding="utf-8")) == {
        "coleta": {"fonte": "ncm:22030000", "ncm": "22030000", "pagina": 2, "url": URL, "coletado_em": "2026-09-16T06:17:05Z"},
        "resposta": corpo,
    }


def test_mesma_pagina_no_mesmo_segundo_nao_sobrescreve(tmp_path):
    primeiro = bruto.gravar_pagina(tmp_path, "22030000", 2, URL, MOMENTO, resposta("22030000", 2, 200, []))
    segundo = bruto.gravar_pagina(tmp_path, "22030000", 2, URL, MOMENTO, resposta("22030000", 2, 201, []))
    assert primeiro != segundo and segundo.name == "p0002_20260916T061705Z_2.json"
    assert len(list((tmp_path / "ncm_22030000").glob("*.json"))) == 2


def test_listar_paginas_em_ordem_cronologica_e_ignora_temporarios(tmp_path):
    depois = datetime(2026, 9, 17, 6, 17, 5, tzinfo=timezone.utc)
    bruto.gravar_pagina(tmp_path, "22085000", 1, URL, depois, resposta("22085000", 1, 1, []))
    bruto.gravar_pagina(tmp_path, "22030000", 1, URL, MOMENTO, resposta("22030000", 1, 1, []))
    (tmp_path / "ncm_22030000" / "p0009_x.json.tmp").write_text("{", encoding="utf-8")
    ordem = [(d["coleta"]["ncm"], d["coleta"]["coletado_em"]) for d in bruto.listar_paginas(tmp_path)]
    assert ordem == [("22030000", "2026-09-16T06:17:05Z"), ("22085000", "2026-09-17T06:17:05Z")]


def test_listar_paginas_sem_pasta(tmp_path):
    assert bruto.listar_paginas(tmp_path / "nao_existe") == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_bruto.py -v`
Expected: FAIL com `ImportError: cannot import name 'bruto' from 'coletor'`

- [ ] **Step 3: Implementar**

`coletor/bruto.py`:
```python
"""Respostas brutas da API: um arquivo por página baixada, nunca sobrescrito."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from coletor.arquivos import gravar_json_atomico
from coletor.tempo import para_iso, para_nome_arquivo


def gravar_pagina(raiz_bruto: Path, ncm: str, pagina: int, url: str, coletado_em: datetime, resposta: dict) -> Path:
    pasta = raiz_bruto / f"ncm_{ncm}"
    base = f"p{pagina:04d}_{para_nome_arquivo(coletado_em)}"
    caminho = pasta / f"{base}.json"
    sufixo = 2
    while caminho.exists():
        caminho = pasta / f"{base}_{sufixo}.json"
        sufixo += 1
    documento = {
        "coleta": {"fonte": f"ncm:{ncm}", "ncm": ncm, "pagina": pagina, "url": url, "coletado_em": para_iso(coletado_em)},
        "resposta": resposta,
    }
    gravar_json_atomico(caminho, documento)
    return caminho


def listar_paginas(raiz_bruto: Path) -> list[dict]:
    if not raiz_bruto.exists():
        return []
    itens = []
    for caminho in raiz_bruto.glob("ncm_*/p*.json"):
        documento = json.loads(caminho.read_text(encoding="utf-8"))
        coleta = documento["coleta"]
        itens.append(((coleta["coletado_em"], coleta["ncm"], coleta["pagina"], caminho.name), documento))
    return [documento for _, documento in sorted(itens, key=lambda item: item[0])]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_bruto.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/bruto.py tests/ajudantes.py tests/conftest.py tests/test_bruto.py
git commit -m "feat: gravação imutável das páginas brutas e ajudantes de teste"
```

---

### Task 5: Cliente da API do Cosmos

**Files:**
- Create: `coletor/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: nada do projeto
- Produces:
  - `BASE_URL = "https://cosmos.bluesoft.com.br/api"`, `USER_AGENT = "Cosmos-API-Request"`, `ESPERAS_S = (2, 4, 8)`
  - Exceções: `ErroApi(Exception)`, `CotaEsgotada(ErroApi)`, `TokenInvalido(ErroApi)`, `FalhaTemporaria(ErroApi)`, `RespostaInvalida(ErroApi)`
  - `transporte_urllib(pedido: urllib.request.Request, timeout: float) -> tuple[int, bytes]`
  - `ClienteCosmos(token: str, antes_de_enviar: Callable[[], None], transporte=transporte_urllib, dormir=time.sleep, timeout: float = 60.0)` com `url_pagina(ncm: str, pagina: int) -> str` e `buscar_pagina(ncm: str, pagina: int) -> dict`

- [ ] **Step 1: Escrever os testes**

`tests/test_api.py`:
```python
import io
import json
import urllib.error
import urllib.request

import pytest

from coletor import api

TOKEN = "token-secreto-123"


def _transporte(itens):
    fila = list(itens)
    pedidos = []

    def transporte(pedido, timeout):
        pedidos.append(pedido)
        item = fila.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    transporte.pedidos = pedidos
    return transporte


def _cliente(itens, ganchos=None):
    ganchos = ganchos if ganchos is not None else []
    dormidas = []
    transporte = _transporte(itens)
    cliente = api.ClienteCosmos(TOKEN, lambda: ganchos.append(1), transporte=transporte, dormir=dormidas.append)
    return cliente, transporte, ganchos, dormidas


def _ok(produtos=()):
    return 200, json.dumps({"products": list(produtos), "total_pages": 1, "total_count": 0}).encode("utf-8")


def test_sucesso_devolve_json_e_envia_cabecalhos():
    cliente, transporte, ganchos, _ = _cliente([_ok([{"gtin": 1}])])
    assert cliente.buscar_pagina("22030000", 3)["products"] == [{"gtin": 1}]
    pedido = transporte.pedidos[0]
    assert pedido.full_url == "https://cosmos.bluesoft.com.br/api/ncms/22030000/products?page=3"
    assert pedido.get_header("X-cosmos-token") == TOKEN
    assert pedido.get_header("User-agent") == "Cosmos-API-Request"
    assert ganchos == [1]


def test_5xx_tenta_de_novo_e_conta_cada_tentativa():
    cliente, _, ganchos, dormidas = _cliente([(500, b""), (502, b""), _ok()])
    cliente.buscar_pagina("22030000", 1)
    assert (len(ganchos), dormidas) == (3, [2, 4])


def test_5xx_persistente_vira_falha_temporaria():
    cliente, _, ganchos, dormidas = _cliente([(500, b"")] * 4)
    with pytest.raises(api.FalhaTemporaria):
        cliente.buscar_pagina("22030000", 1)
    assert (len(ganchos), dormidas) == (4, [2, 4, 8])


def test_erro_de_rede_persistente_vira_falha_temporaria():
    cliente, _, _, _ = _cliente([urllib.error.URLError("sem rede")] * 3 + [TimeoutError()])
    with pytest.raises(api.FalhaTemporaria):
        cliente.buscar_pagina("22030000", 1)


def test_429_vira_cota_esgotada_sem_nova_tentativa():
    cliente, _, ganchos, dormidas = _cliente([(429, b'{"message":"Limite de requests excedido"}')])
    with pytest.raises(api.CotaEsgotada):
        cliente.buscar_pagina("22030000", 1)
    assert (len(ganchos), dormidas) == (1, [])


@pytest.mark.parametrize("status", [401, 403])
def test_401_403_viram_token_invalido(status):
    cliente, _, _, _ = _cliente([(status, b"")])
    with pytest.raises(api.TokenInvalido):
        cliente.buscar_pagina("22030000", 1)


@pytest.mark.parametrize("item", [(200, b"{quebrado"), (200, b'{"sem_products": 1}'), (200, b"\xff"), (404, b"nao existe")])
def test_resposta_inesperada_vira_resposta_invalida(item):
    cliente, _, _, _ = _cliente([item])
    with pytest.raises(api.RespostaInvalida):
        cliente.buscar_pagina("22030000", 1)


def test_token_nunca_aparece_na_mensagem_de_erro():
    cliente, _, _, _ = _cliente([(429, f"token {TOKEN} excedeu".encode("utf-8"))])
    with pytest.raises(api.CotaEsgotada) as erro:
        cliente.buscar_pagina("22030000", 1)
    assert TOKEN not in str(erro.value)


def test_gancho_que_lanca_impede_o_envio():
    class Parar(Exception):
        pass

    def gancho():
        raise Parar()

    transporte = _transporte([_ok()])
    cliente = api.ClienteCosmos(TOKEN, gancho, transporte=transporte, dormir=lambda s: None)
    with pytest.raises(Parar):
        cliente.buscar_pagina("22030000", 1)
    assert transporte.pedidos == []


class _RespostaHttp:
    status = 200

    def __init__(self, corpo):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_transporte_urllib_devolve_status_e_corpo(monkeypatch):
    monkeypatch.setattr(api.urllib.request, "urlopen", lambda pedido, timeout: _RespostaHttp(b"{}"))
    assert api.transporte_urllib(urllib.request.Request("https://exemplo.test"), 1) == (200, b"{}")


def test_transporte_urllib_converte_http_error(monkeypatch):
    def urlopen(pedido, timeout):
        raise urllib.error.HTTPError(pedido.full_url, 429, "Too Many Requests", {}, io.BytesIO(b"limite"))

    monkeypatch.setattr(api.urllib.request, "urlopen", urlopen)
    assert api.transporte_urllib(urllib.request.Request("https://exemplo.test"), 1) == (429, b"limite")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_api.py -v`
Expected: FAIL com `ImportError: cannot import name 'api' from 'coletor'`

- [ ] **Step 3: Implementar**

`coletor/api.py`:
```python
"""Cliente da API do Bluesoft Cosmos: uma página por chamada, erros tipados, token nunca exposto."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Callable

BASE_URL = "https://cosmos.bluesoft.com.br/api"
USER_AGENT = "Cosmos-API-Request"
ESPERAS_S = (2, 4, 8)


class ErroApi(Exception):
    """Base dos erros da API."""


class CotaEsgotada(ErroApi):
    """HTTP 429."""


class TokenInvalido(ErroApi):
    """HTTP 401 ou 403."""


class FalhaTemporaria(ErroApi):
    """5xx ou erro de rede que persistiu após todas as tentativas."""


class RespostaInvalida(ErroApi):
    """Status inesperado ou corpo que não é a página esperada."""


def transporte_urllib(pedido: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            return resposta.status, resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read()


class ClienteCosmos:
    def __init__(
        self,
        token: str,
        antes_de_enviar: Callable[[], None],
        transporte: Callable[[urllib.request.Request, float], tuple[int, bytes]] = transporte_urllib,
        dormir: Callable[[float], None] = time.sleep,
        timeout: float = 60.0,
    ):
        self._token = token
        self._antes_de_enviar = antes_de_enviar
        self._transporte = transporte
        self._dormir = dormir
        self._timeout = timeout

    def url_pagina(self, ncm: str, pagina: int) -> str:
        return f"{BASE_URL}/ncms/{ncm}/products?page={pagina}"

    def buscar_pagina(self, ncm: str, pagina: int) -> dict:
        url = self.url_pagina(ncm, pagina)
        ultimo_problema = ""
        for tentativa in range(len(ESPERAS_S) + 1):
            if tentativa:
                self._dormir(ESPERAS_S[tentativa - 1])
            self._antes_de_enviar()
            pedido = urllib.request.Request(
                url,
                headers={"X-Cosmos-Token": self._token, "User-Agent": USER_AGENT, "Content-Type": "application/json"},
            )
            try:
                status, corpo = self._transporte(pedido, self._timeout)
            except OSError as erro:
                ultimo_problema = f"rede ({type(erro).__name__})"
                continue
            if status == 200:
                return self._interpretar(url, corpo)
            if status == 429:
                raise CotaEsgotada(f"HTTP 429: {self._trecho(corpo)}")
            if status in (401, 403):
                raise TokenInvalido(f"HTTP {status}: token recusado pela API")
            if status >= 500:
                ultimo_problema = f"HTTP {status}"
                continue
            raise RespostaInvalida(f"HTTP {status} em {url}: {self._trecho(corpo)}")
        raise FalhaTemporaria(f"{ultimo_problema} após {len(ESPERAS_S) + 1} tentativas em {url}")

    def _interpretar(self, url: str, corpo: bytes) -> dict:
        try:
            dados = json.loads(corpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RespostaInvalida(f"corpo não é JSON válido em {url}") from None
        if not isinstance(dados, dict) or not isinstance(dados.get("products"), list):
            raise RespostaInvalida(f"formato inesperado (sem 'products') em {url}")
        return dados

    def _trecho(self, corpo: bytes) -> str:
        return corpo.decode("utf-8", errors="replace")[:200].replace(self._token, "***")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_api.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/api.py tests/test_api.py
git commit -m "feat: cliente da API do Cosmos com novas tentativas e erros tipados"
```

---

### Task 6: Exportar `produtos.csv` e `gtins.csv`

**Files:**
- Create: `coletor/exportar.py`
- Test: `tests/test_exportar_produtos.py`

**Interfaces:**
- Consumes: `arquivos.gravar_texto_atomico`
- Produces:
  - `COLUNAS_CONTROLE: list[str]`, `COLUNAS_GTINS: list[str]`
  - `texto(valor: object) -> str`
  - `achatar_produto(produto: dict) -> dict[str, str]`
  - `registro_id(coleta: dict, posicao: int) -> str`
  - `linhas_produtos(paginas: Sequence[dict]) -> tuple[list[str], list[dict[str, str]]]`
  - `linhas_gtins(paginas: Sequence[dict]) -> list[dict[str, str]]`
  - `gravar_csv(caminho: Path, colunas: Sequence[str], linhas: Iterable[dict]) -> int`
  - `ler_csv(caminho: Path) -> list[dict[str, str]]`

- [ ] **Step 1: Escrever os testes**

`tests/test_exportar_produtos.py`:
```python
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
    assert colunas[:6] == exportar.COLUNAS_CONTROLE
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_exportar_produtos.py -v`
Expected: FAIL com `ImportError: cannot import name 'exportar' from 'coletor'`

- [ ] **Step 3: Implementar**

`coletor/exportar.py`:
```python
"""Geração dos CSVs a partir do bruto (fonte da verdade). Nenhuma deduplicação (D4)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from coletor.arquivos import gravar_texto_atomico

COLUNAS_CONTROLE = ["registro_id", "fonte", "ncm_consultado", "pagina", "posicao", "coletado_em"]
COLUNAS_GTINS = [
    "registro_id", "produto_gtin", "gtin", "e_o_proprio", "type_packaging", "quantity_packaging",
    "ballast", "layer", "fonte", "pagina", "coletado_em",
]


def texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (list, dict)):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)


def achatar_produto(produto: dict) -> dict[str, str]:
    linha: dict[str, str] = {}

    def visitar(objeto: dict, prefixo: str) -> None:
        for chave, valor in objeto.items():
            nome = f"{prefixo}{chave}"
            if not prefixo and chave == "gtins":
                linha["gtins_qtd"] = str(len(valor)) if isinstance(valor, list) else "0"
            elif isinstance(valor, dict):
                visitar(valor, f"{nome}_")
            else:
                linha[nome] = texto(valor)

    visitar(produto, "")
    return linha


def registro_id(coleta: dict, posicao: int) -> str:
    return f"{coleta['fonte']}|p{coleta['pagina']:04d}|{coleta['coletado_em']}|{posicao:02d}"


def _produtos(paginas: Sequence[dict]) -> Iterator[tuple[dict, int, dict]]:
    for documento in paginas:
        for posicao, produto in enumerate(documento["resposta"].get("products") or [], start=1):
            yield documento["coleta"], posicao, produto


def linhas_produtos(paginas: Sequence[dict]) -> tuple[list[str], list[dict[str, str]]]:
    colunas = list(COLUNAS_CONTROLE)
    vistas = set(colunas)
    linhas: list[dict[str, str]] = []
    for coleta, posicao, produto in _produtos(paginas):
        linha = {
            "registro_id": registro_id(coleta, posicao),
            "fonte": coleta["fonte"],
            "ncm_consultado": coleta["ncm"],
            "pagina": str(coleta["pagina"]),
            "posicao": str(posicao),
            "coletado_em": coleta["coletado_em"],
        }
        for nome, valor in achatar_produto(produto).items():
            linha[nome] = valor
            if nome not in vistas:
                vistas.add(nome)
                colunas.append(nome)
        linhas.append(linha)
    return [c for c in colunas if not _objeto_sempre_nulo(c, colunas, linhas)], linhas


def _objeto_sempre_nulo(coluna: str, colunas: list[str], linhas: list[dict[str, str]]) -> bool:
    # "brand" vazio + "brand_name" preenchido em outra linha: a coluna "brand" não carrega informação.
    if coluna in COLUNAS_CONTROLE or not any(c.startswith(f"{coluna}_") for c in colunas):
        return False
    return all(linha.get(coluna, "") == "" for linha in linhas)


def linhas_gtins(paginas: Sequence[dict]) -> list[dict[str, str]]:
    linhas: list[dict[str, str]] = []
    for coleta, posicao, produto in _produtos(paginas):
        produto_gtin = texto(produto.get("gtin"))
        for item in produto.get("gtins") or []:
            unidade = item.get("commercial_unit") or {}
            gtin = texto(item.get("gtin"))
            linhas.append({
                "registro_id": registro_id(coleta, posicao),
                "produto_gtin": produto_gtin,
                "gtin": gtin,
                "e_o_proprio": "sim" if gtin == produto_gtin else "não",
                "type_packaging": texto(unidade.get("type_packaging")),
                "quantity_packaging": texto(unidade.get("quantity_packaging")),
                "ballast": texto(unidade.get("ballast")),
                "layer": texto(unidade.get("layer")),
                "fonte": coleta["fonte"],
                "pagina": str(coleta["pagina"]),
                "coletado_em": coleta["coletado_em"],
            })
    return linhas


def gravar_csv(caminho: Path, colunas: Sequence[str], linhas: Iterable[dict]) -> int:
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=list(colunas), delimiter=";", restval="", extrasaction="ignore")
    escritor.writeheader()
    quantidade = 0
    for linha in linhas:
        escritor.writerow(linha)
        quantidade += 1
    gravar_texto_atomico(caminho, buffer.getvalue(), encoding="utf-8-sig")
    return quantidade


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_exportar_produtos.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/exportar.py tests/test_exportar_produtos.py
git commit -m "feat: exportação de produtos.csv e gtins.csv com todos os campos"
```

---

### Task 7: Exportar `conferencia_ncm.csv`, `execucoes.csv` e gerar todos os CSVs

**Files:**
- Modify: `coletor/exportar.py` (acrescentar ao final)
- Test: `tests/test_exportar_conferencia.py`

**Interfaces:**
- Consumes: `bruto.listar_paginas`, `estado.info_ncm`, `config.NcmAlvo`, e da Task 6 `texto`, `linhas_produtos`, `linhas_gtins`, `gravar_csv`, `ler_csv`, `COLUNAS_GTINS`
- Produces:
  - `COLUNAS_CONFERENCIA: list[str]`, `COLUNAS_EXECUCOES: list[str]`
  - `linhas_conferencia(ncms: Sequence[NcmAlvo], estado: dict, paginas: Sequence[dict]) -> list[dict[str, str]]`
  - `registrar_execucao(caminho: Path, registro: dict) -> None`
  - `gerar_csvs(raiz_bruto: Path, pasta_saida: Path, ncms: Sequence[NcmAlvo], estado: dict) -> dict[str, int]`: chaves `"produtos.csv"`, `"gtins.csv"`, `"conferencia_ncm.csv"`

- [ ] **Step 1: Escrever os testes**

`tests/test_exportar_conferencia.py`:
```python
from datetime import datetime, timezone

from coletor import bruto, exportar
from coletor import estado as est
from coletor.config import NcmAlvo
from tests.ajudantes import documento, produto, resposta

AGORA = datetime(2026, 9, 16, 6, 17, 0, tzinfo=timezone.utc)
CERVEJA = NcmAlvo("22030000", "Cervejas de malte")


def _conferencia(estado, paginas):
    return exportar.linhas_conferencia([CERVEJA], estado, paginas)[0]


def test_nao_iniciado():
    linha = _conferencia(est.estado_vazio(), [])
    assert (linha["status"], linha["total_api"], linha["diferenca"], linha["gtins_distintos"]) == ("não iniciado", "", "", "0")


def test_em_andamento():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 2, 4, AGORA)
    linha = _conferencia(estado, [documento("22030000", 1, [produto(1), produto(2)])])
    assert (linha["status"], linha["paginas_coletadas"], linha["total_paginas"], linha["diferenca"]) == ("em andamento", "1", "2", "2")


def test_concluido_conta_gtins_distintos_mesmo_com_pagina_repetida():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 1, 2, AGORA)
    paginas = [
        documento("22030000", 1, [produto(1), produto(2)]),
        documento("22030000", 1, [produto(1), produto(2)], coletado_em="2026-09-17T06:17:05Z"),
    ]
    linha = _conferencia(estado, paginas)
    assert (linha["status"], linha["linhas_baixadas"], linha["gtins_distintos"], linha["diferenca"]) == ("concluído", "4", "2", "0")


def test_concluido_com_falta():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 1, 3, AGORA)
    linha = _conferencia(estado, [documento("22030000", 1, [produto(1), produto(2)])])
    assert (linha["status"], linha["diferenca"]) == ("concluído com falta", "1")


def test_registrar_execucao_acrescenta_linhas(tmp_path):
    caminho = tmp_path / "execucoes.csv"
    exportar.registrar_execucao(caminho, {"inicio": "a", "motivo_parada": "limite", "consultas_feitas": 24})
    exportar.registrar_execucao(caminho, {"inicio": "b", "motivo_parada": "429"})
    linhas = exportar.ler_csv(caminho)
    assert [(l["inicio"], l["motivo_parada"], l["consultas_feitas"]) for l in linhas] == [("a", "limite", "24"), ("b", "429", "")]
    assert list(linhas[0].keys()) == exportar.COLUNAS_EXECUCOES


def test_gerar_csvs_escreve_os_tres_arquivos(tmp_path):
    raiz_bruto = tmp_path / "dados" / "bruto"
    bruto.gravar_pagina(raiz_bruto, "22030000", 1, "url", AGORA, resposta("22030000", 1, 1, [produto(1, gtins_extra=(9,))]))
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 1, 1, AGORA)
    contagens = exportar.gerar_csvs(raiz_bruto, tmp_path / "saida", [CERVEJA], estado)
    assert contagens == {"produtos.csv": 1, "gtins.csv": 2, "conferencia_ncm.csv": 1}
    assert exportar.ler_csv(tmp_path / "saida" / "conferencia_ncm.csv")[0]["status"] == "concluído"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_exportar_conferencia.py -v`
Expected: FAIL com `AttributeError: module 'coletor.exportar' has no attribute 'linhas_conferencia'`

- [ ] **Step 3: Implementar**

Em `coletor/exportar.py`, acrescentar aos imports:
```python
from coletor import bruto
from coletor.config import NcmAlvo
from coletor.estado import info_ncm
```

E acrescentar ao final do arquivo:
```python
COLUNAS_CONFERENCIA = [
    "ncm", "descricao", "total_api", "total_lido_em", "paginas_coletadas", "total_paginas",
    "linhas_baixadas", "gtins_distintos", "diferenca", "status",
]
COLUNAS_EXECUCOES = [
    "inicio", "fim", "consultas_feitas", "paginas_concluidas", "produtos_baixados",
    "motivo_parada", "alertas", "paginas_restantes", "dias_previstos",
]


def linhas_conferencia(ncms: Sequence[NcmAlvo], estado: dict, paginas: Sequence[dict]) -> list[dict[str, str]]:
    linhas: list[dict[str, str]] = []
    for alvo in ncms:
        documentos = [d for d in paginas if d["coleta"]["ncm"] == alvo.ncm]
        produtos = [p for d in documentos for p in d["resposta"].get("products") or []]
        gtins_distintos = len({texto(p.get("gtin")) for p in produtos})
        info = info_ncm(estado, alvo.ncm)
        linha = {
            "ncm": alvo.ncm,
            "descricao": alvo.descricao,
            "total_api": "",
            "total_lido_em": "",
            "paginas_coletadas": str(len({d["coleta"]["pagina"] for d in documentos})),
            "total_paginas": "",
            "linhas_baixadas": str(len(produtos)),
            "gtins_distintos": str(gtins_distintos),
            "diferenca": "",
            "status": "não iniciado",
        }
        if info is not None:
            diferenca = info["total_produtos"] - gtins_distintos
            if info["concluido_em"] is None:
                status = "em andamento"
            elif diferenca <= 0:
                status = "concluído"
            else:
                status = "concluído com falta"
            linha.update({
                "total_api": str(info["total_produtos"]),
                "total_lido_em": info["total_lido_em"] or "",
                "total_paginas": str(info["total_paginas"]),
                "diferenca": str(diferenca),
                "status": status,
            })
        linhas.append(linha)
    return linhas


def registrar_execucao(caminho: Path, registro: dict) -> None:
    linhas = ler_csv(caminho) + [{coluna: texto(registro.get(coluna)) for coluna in COLUNAS_EXECUCOES}]
    gravar_csv(caminho, COLUNAS_EXECUCOES, linhas)


def gerar_csvs(raiz_bruto: Path, pasta_saida: Path, ncms: Sequence[NcmAlvo], estado: dict) -> dict[str, int]:
    paginas = bruto.listar_paginas(raiz_bruto)
    colunas, produtos = linhas_produtos(paginas)
    return {
        "produtos.csv": gravar_csv(pasta_saida / "produtos.csv", colunas, produtos),
        "gtins.csv": gravar_csv(pasta_saida / "gtins.csv", COLUNAS_GTINS, linhas_gtins(paginas)),
        "conferencia_ncm.csv": gravar_csv(
            pasta_saida / "conferencia_ncm.csv", COLUNAS_CONFERENCIA, linhas_conferencia(ncms, estado, paginas)
        ),
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_exportar_produtos.py tests/test_exportar_conferencia.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/exportar.py tests/test_exportar_conferencia.py
git commit -m "feat: conferência por NCM, registro de execuções e geração dos CSVs"
```

---

### Task 8: Orquestração — ordem da coleta, cota e retomada

**Files:**
- Create: `coletor/principal.py`
- Test: `tests/test_principal_coleta.py`

**Interfaces:**
- Consumes: `Config`, `NcmAlvo`; `estado.*`; `bruto.gravar_pagina`; `exportar.gerar_csvs`, `exportar.registrar_execucao`; `cota.segundos_para_liberar`, `cota.consultas_na_janela`; exceções de `api`; `tempo.agora_utc`, `tempo.para_iso`
- Produces:
  - `LimiteAtingido(Exception)`, `Cancelado(Exception)`
  - `Caminhos(estado: Path, bruto: Path, saida: Path)` com `Caminhos.de(raiz: Path) -> Caminhos`
  - `proxima_pagina(ncms: Sequence[NcmAlvo], estado: dict) -> tuple[str, int] | None`
  - `calcular_progresso(ncms: Sequence[NcmAlvo], estado: dict, limite: int) -> dict[str, int]`: chaves `paginas_feitas`, `paginas_conhecidas`, `ncms_sem_contagem`, `paginas_restantes`, `dias_previstos`
  - `classificar_parada(erro: BaseException | None) -> tuple[str, int]`
  - `executar(config: Config, fabrica_cliente: Callable[[Callable[[], None]], Cliente], *, agora=agora_utc, dormir=time.sleep, saida=print) -> int`

- [ ] **Step 1: Escrever os testes**

`tests/test_principal_coleta.py`:
```python
from dataclasses import replace
from datetime import timedelta

from coletor import estado as est
from coletor import exportar, principal
from coletor.config import NcmAlvo
from tests.ajudantes import INICIO, ApiFalsa, Relogio, roteiro_paginas

NCMS = (NcmAlvo("22030000", "Cervejas"), NcmAlvo("22085000", "Gim"))


def _rodar(config, roteiro, relogio):
    apis = []

    def fabrica(antes_de_enviar):
        api = ApiFalsa(antes_de_enviar, roteiro)
        apis.append(api)
        return api

    saida = []
    codigo = principal.executar(config, fabrica, agora=relogio, dormir=relogio.dormir, saida=saida.append)
    return codigo, apis[0] if apis else None, saida


def _execucoes(config):
    return exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")


def test_proxima_pagina_prioriza_ncms_sem_contagem():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 1, 5, 150, INICIO)
    assert principal.proxima_pagina(NCMS, estado) == ("22085000", 1)
    est.atualizar_ncm(estado, "22085000", 1, 1, 10, INICIO)
    assert principal.proxima_pagina(NCMS, estado) == ("22030000", 2)
    est.atualizar_ncm(estado, "22030000", 5, 5, 150, INICIO)
    assert principal.proxima_pagina(NCMS, estado) is None


def test_primeira_execucao_pega_pagina_1_de_todos_e_depois_segue_em_ordem(config, relogio):
    codigo, api, _ = _rodar(config, roteiro_paginas({"22030000": 3, "22085000": 2}), relogio)
    assert api.chamadas == [("22030000", 1), ("22085000", 1), ("22030000", 2), ("22030000", 3), ("22085000", 2)]
    assert codigo == 0
    assert _execucoes(config)[-1]["motivo_parada"] == "concluido"


def test_para_no_limite_sem_chamar_a_api(config, relogio):
    config = replace(config, limite_consultas=3)
    codigo, api, _ = _rodar(config, roteiro_paginas({"22030000": 10, "22085000": 10}), relogio)
    assert (codigo, len(api.chamadas)) == (0, 3)
    registro = _execucoes(config)[-1]
    assert (registro["motivo_parada"], registro["consultas_feitas"]) == ("limite", "3")
    assert len(est.carregar(config.raiz / "dados" / "estado.json")["consultas"]) == 3


def test_retoma_da_pagina_seguinte_no_dia_seguinte(config):
    config = replace(config, limite_consultas=3)
    roteiro = roteiro_paginas({"22030000": 10, "22085000": 10})
    _rodar(config, roteiro, Relogio(INICIO))
    _, api, _ = _rodar(config, roteiro, Relogio(INICIO + timedelta(hours=25)))
    assert api.chamadas == [("22030000", 3), ("22030000", 4), ("22030000", 5)]
    assert len(_execucoes(config)) == 2


def _preparar_consultas(config, momentos):
    estado = est.estado_vazio()
    for momento in momentos:
        est.registrar_consulta(estado, momento)
    est.salvar(config.raiz / "dados" / "estado.json", estado)


def test_espera_quando_a_janela_libera_em_poucos_minutos(config, relogio):
    _preparar_consultas(config, [INICIO - timedelta(hours=23, minutes=50)] + [INICIO - timedelta(hours=1)] * 23)
    codigo, api, saida = _rodar(config, roteiro_paginas({"22030000": 10, "22085000": 10}), relogio)
    assert relogio.dormidas == [599.0]
    assert api.chamadas == [("22030000", 1)]
    assert codigo == 0 and _execucoes(config)[-1]["motivo_parada"] == "limite"
    assert any("Aguardando" in linha for linha in saida)


def test_nao_espera_quando_a_janela_demora(config, relogio):
    _preparar_consultas(config, [INICIO - timedelta(hours=1)] * 24)
    codigo, api, _ = _rodar(config, roteiro_paginas({"22030000": 10, "22085000": 10}), relogio)
    assert (codigo, api.chamadas, relogio.dormidas) == (0, [], [])


def test_calcular_progresso():
    estado = est.estado_vazio()
    est.atualizar_ncm(estado, "22030000", 5, 200, 5981, INICIO)
    assert principal.calcular_progresso(NCMS, estado, 24) == {
        "paginas_feitas": 5, "paginas_conhecidas": 200, "ncms_sem_contagem": 1,
        "paginas_restantes": 196, "dias_previstos": 9,
    }
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_principal_coleta.py -v`
Expected: FAIL com `ImportError: cannot import name 'principal' from 'coletor'`

- [ ] **Step 3: Implementar**

`coletor/principal.py`:
```python
"""Uma execução da coleta: laço de páginas dentro da cota e finalização garantida."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol, Sequence

from coletor import bruto, exportar
from coletor import estado as estado_mod
from coletor.api import CotaEsgotada, FalhaTemporaria, RespostaInvalida, TokenInvalido
from coletor.config import Config, NcmAlvo
from coletor.cota import consultas_na_janela, segundos_para_liberar
from coletor.tempo import agora_utc, para_iso


class LimiteAtingido(Exception):
    """A janela de 24 h está cheia e não libera dentro da espera máxima."""


class Cancelado(Exception):
    """A execução recebeu sinal de término."""


class Cliente(Protocol):
    def url_pagina(self, ncm: str, pagina: int) -> str: ...

    def buscar_pagina(self, ncm: str, pagina: int) -> dict: ...


FabricaCliente = Callable[[Callable[[], None]], Cliente]


@dataclass(frozen=True)
class Caminhos:
    estado: Path
    bruto: Path
    saida: Path

    @classmethod
    def de(cls, raiz: Path) -> "Caminhos":
        return cls(estado=raiz / "dados" / "estado.json", bruto=raiz / "dados" / "bruto", saida=raiz / "saida")


@dataclass
class Execucao:
    inicio: datetime
    consultas_feitas: int = 0
    paginas_concluidas: int = 0
    produtos_baixados: int = 0
    alertas: list[str] = field(default_factory=list)


def proxima_pagina(ncms: Sequence[NcmAlvo], estado: dict) -> tuple[str, int] | None:
    for alvo in ncms:
        if estado_mod.info_ncm(estado, alvo.ncm) is None:
            return alvo.ncm, 1
    for alvo in ncms:
        info = estado_mod.info_ncm(estado, alvo.ncm)
        if info["ultima_pagina"] < info["total_paginas"]:
            return alvo.ncm, info["ultima_pagina"] + 1
    return None


def calcular_progresso(ncms: Sequence[NcmAlvo], estado: dict, limite: int) -> dict[str, int]:
    feitas = conhecidas = sem_contagem = 0
    for alvo in ncms:
        info = estado_mod.info_ncm(estado, alvo.ncm)
        if info is None:
            sem_contagem += 1
            continue
        feitas += min(info["ultima_pagina"], info["total_paginas"])
        conhecidas += info["total_paginas"]
    restantes = (conhecidas - feitas) + sem_contagem
    return {
        "paginas_feitas": feitas,
        "paginas_conhecidas": conhecidas,
        "ncms_sem_contagem": sem_contagem,
        "paginas_restantes": restantes,
        "dias_previstos": math.ceil(restantes / limite) if restantes else 0,
    }


def classificar_parada(erro: BaseException | None) -> tuple[str, int]:
    if erro is None:
        return "concluido", 0
    if isinstance(erro, LimiteAtingido):
        return "limite", 0
    if isinstance(erro, CotaEsgotada):
        return "429", 0
    if isinstance(erro, TokenInvalido):
        return "erro: token", 1
    if isinstance(erro, FalhaTemporaria):
        return "erro: rede", 1
    if isinstance(erro, RespostaInvalida):
        return "erro: resposta", 1
    if isinstance(erro, (KeyboardInterrupt, Cancelado)):
        return "cancelado", 1
    return f"erro: {type(erro).__name__}", 1


def executar(
    config: Config,
    fabrica_cliente: FabricaCliente,
    *,
    agora: Callable[[], datetime] = agora_utc,
    dormir: Callable[[float], None] = time.sleep,
    saida: Callable[[str], None] = print,
) -> int:
    caminhos = Caminhos.de(config.raiz)
    execucao = Execucao(inicio=agora())
    estado: dict | None = None
    erro: BaseException | None = None
    try:
        estado = estado_mod.carregar(caminhos.estado)
        _coletar(config, fabrica_cliente, estado, execucao, caminhos, agora, dormir, saida)
    except (Exception, KeyboardInterrupt) as capturado:
        erro = capturado
    motivo, codigo = classificar_parada(erro)
    if erro is not None and codigo == 1:
        saida(f"Erro: {type(erro).__name__}: {str(erro)[:300]}")
    return _finalizar(config, estado, execucao, motivo, codigo, caminhos, agora, saida)


def _coletar(config, fabrica_cliente, estado, execucao, caminhos, agora, dormir, saida) -> None:
    def antes_de_enviar() -> None:
        momento = agora()
        espera = segundos_para_liberar(estado_mod.consultas(estado), momento, config.limite_consultas)
        if espera > 0:
            if espera > config.espera_maxima_min * 60:
                raise LimiteAtingido(f"janela de cota libera em {math.ceil(espera / 60)} min")
            saida(f"Aguardando {math.ceil(espera / 60)} min pela janela de cota...")
            dormir(espera)
            momento = agora()
        estado_mod.registrar_consulta(estado, momento)
        execucao.consultas_feitas += 1

    cliente = fabrica_cliente(antes_de_enviar)
    usadas = consultas_na_janela(estado_mod.consultas(estado), execucao.inicio)
    saida(f"[{para_iso(execucao.inicio)}] Início. Consultas nas últimas 24 h: {usadas}/{config.limite_consultas}")
    while (proxima := proxima_pagina(config.ncms, estado)) is not None:
        ncm, pagina = proxima
        resposta = cliente.buscar_pagina(ncm, pagina)
        coletado_em = agora()
        bruto.gravar_pagina(caminhos.bruto, ncm, pagina, cliente.url_pagina(ncm, pagina), coletado_em, resposta)
        produtos = resposta.get("products") or []
        total_paginas = int(resposta.get("total_pages") or 0)
        total_produtos = int(resposta.get("total_count") or 0)
        estado_mod.atualizar_ncm(estado, ncm, pagina, total_paginas, total_produtos, coletado_em)
        if not produtos and pagina < total_paginas:
            execucao.alertas.append(f"ncm:{ncm} p{pagina} vazia")
        estado_mod.salvar(caminhos.estado, estado)
        execucao.paginas_concluidas += 1
        execucao.produtos_baixados += len(produtos)
        saida(f"  ncm:{ncm} p{pagina}/{total_paginas} ({total_produtos} produtos no total) — {len(produtos)} itens")


def _finalizar(config, estado, execucao, motivo, codigo, caminhos, agora, saida) -> int:
    fim = agora()
    contagens: dict[str, int] = {}
    if estado is None:
        execucao.alertas.append("estado não carregado: estado e CSVs não foram alterados")
    else:
        try:
            estado_mod.podar_consultas(estado, fim)
            estado_mod.salvar(caminhos.estado, estado)
        except Exception as falha:
            execucao.alertas.append(f"falha ao salvar estado: {type(falha).__name__}")
            codigo = 1
        try:
            contagens = exportar.gerar_csvs(caminhos.bruto, caminhos.saida, config.ncms, estado)
        except Exception as falha:
            execucao.alertas.append(f"falha ao gerar CSVs: {type(falha).__name__}")
            codigo = 1
    progresso = calcular_progresso(config.ncms, estado or estado_mod.estado_vazio(), config.limite_consultas)
    try:
        exportar.registrar_execucao(caminhos.saida / "execucoes.csv", {
            "inicio": para_iso(execucao.inicio),
            "fim": para_iso(fim),
            "consultas_feitas": execucao.consultas_feitas,
            "paginas_concluidas": execucao.paginas_concluidas,
            "produtos_baixados": execucao.produtos_baixados,
            "motivo_parada": motivo,
            "alertas": " | ".join(execucao.alertas),
            "paginas_restantes": progresso["paginas_restantes"],
            "dias_previstos": progresso["dias_previstos"],
        })
    except Exception as falha:
        saida(f"Falha ao registrar a execução: {type(falha).__name__}")
        codigo = 1
    saida(f"Parada: {motivo} ({execucao.consultas_feitas} consultas nesta execução)")
    if contagens:
        saida("CSVs: " + ", ".join(f"{nome} ({linhas} linhas)" for nome, linhas in contagens.items()))
    saida(
        f"Progresso: {progresso['paginas_feitas']}/{progresso['paginas_conhecidas']} páginas conhecidas; "
        f"{progresso['ncms_sem_contagem']} NCMs sem contagem; previsão: ~{progresso['dias_previstos']} dias"
    )
    if execucao.alertas:
        saida("Alertas: " + " | ".join(execucao.alertas))
    return codigo
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_principal_coleta.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/principal.py tests/test_principal_coleta.py
git commit -m "feat: orquestração da coleta com ordem, cota de 24 h e retomada"
```

---

### Task 9: Finalização garantida em todos os motivos de parada

**Files:**
- Test: `tests/test_principal_finalizacao.py`
- Modify: `coletor/principal.py` somente se algum teste falhar (a implementação da Task 8 já cobre o comportamento; esta task o **prova** motivo a motivo)

**Interfaces:**
- Consumes: `principal.executar`, `principal.Cancelado`, exceções de `api`, `tests.ajudantes`
- Produces: nada novo

- [ ] **Step 1: Escrever os testes**

`tests/test_principal_finalizacao.py`:
```python
import pytest

from coletor import estado as est
from coletor import exportar, principal
from coletor.api import CotaEsgotada, FalhaTemporaria, RespostaInvalida, TokenInvalido
from tests.ajudantes import ApiFalsa, produto, resposta


def _rodar(config, roteiro, relogio):
    saida = []
    codigo = principal.executar(
        config, lambda antes: ApiFalsa(antes, roteiro), agora=relogio, dormir=relogio.dormir, saida=saida.append
    )
    return codigo, saida


def _falha_no_segundo_ncm(erro):
    def roteiro(ncm, pagina):
        if ncm == "22085000":
            return erro
        return resposta(ncm, pagina, 5, [produto(111), produto(222)])

    return roteiro


@pytest.mark.parametrize(
    ("erro", "motivo", "codigo_esperado"),
    [
        (CotaEsgotada("HTTP 429"), "429", 0),
        (TokenInvalido("HTTP 401"), "erro: token", 1),
        (FalhaTemporaria("HTTP 500"), "erro: rede", 1),
        (RespostaInvalida("formato"), "erro: resposta", 1),
        (principal.Cancelado("sinal 15"), "cancelado", 1),
        (KeyboardInterrupt(), "cancelado", 1),
        (ValueError("inesperado"), "erro: ValueError", 1),
    ],
)
def test_toda_parada_salva_estado_csvs_e_execucao(config, relogio, erro, motivo, codigo_esperado):
    codigo, saida = _rodar(config, _falha_no_segundo_ncm(erro), relogio)

    assert codigo == codigo_esperado
    estado = est.carregar(config.raiz / "dados" / "estado.json")
    assert est.info_ncm(estado, "22030000")["ultima_pagina"] == 1
    assert len(estado["consultas"]) == 2
    assert len(exportar.ler_csv(config.raiz / "saida" / "produtos.csv")) == 2
    assert len(exportar.ler_csv(config.raiz / "saida" / "conferencia_ncm.csv")) == 2
    assert exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["motivo_parada"] == motivo
    assert any(linha.startswith(f"Parada: {motivo}") for linha in saida)


def test_pagina_vazia_inesperada_gera_alerta(config, relogio):
    def roteiro(ncm, pagina):
        itens = [] if (ncm, pagina) == ("22030000", 1) else [produto(pagina)]
        return resposta(ncm, pagina, 2, itens)

    codigo, _ = _rodar(config, roteiro, relogio)
    assert codigo == 0
    assert "ncm:22030000 p1 vazia" in exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["alertas"]


def test_estado_corrompido_nao_e_sobrescrito(config, relogio):
    caminho = config.raiz / "dados" / "estado.json"
    caminho.parent.mkdir(parents=True)
    caminho.write_text("{", encoding="utf-8")

    codigo, _ = _rodar(config, _falha_no_segundo_ncm(ValueError()), relogio)

    assert codigo == 1
    assert caminho.read_text(encoding="utf-8") == "{"
    registro = exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]
    assert registro["motivo_parada"] == "erro: EstadoInvalido"
    assert "estado não carregado" in registro["alertas"]
    assert not (config.raiz / "saida" / "produtos.csv").exists()


def test_pagina_bruta_fica_gravada_mesmo_se_salvar_estado_falhar(config, relogio, monkeypatch):
    def falhar(caminho, estado):
        raise OSError("disco cheio")

    monkeypatch.setattr(principal.estado_mod, "salvar", falhar)
    codigo, _ = _rodar(config, _falha_no_segundo_ncm(ValueError()), relogio)

    assert codigo == 1
    assert len(list((config.raiz / "dados" / "bruto" / "ncm_22030000").glob("p0001_*.json"))) == 1
    assert not (config.raiz / "dados" / "estado.json").exists()
    assert "falha ao salvar estado" in exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["alertas"]


def test_falha_ao_gerar_csvs_vira_codigo_1_e_fica_registrada(config, relogio, monkeypatch):
    def falhar(*args):
        raise OSError("sem espaço")

    monkeypatch.setattr(principal.exportar, "gerar_csvs", falhar)
    codigo, _ = _rodar(config, _falha_no_segundo_ncm(CotaEsgotada("429")), relogio)

    assert codigo == 1
    assert "falha ao gerar CSVs" in exportar.ler_csv(config.raiz / "saida" / "execucoes.csv")[-1]["alertas"]


def test_falha_ao_registrar_execucao_vira_codigo_1(config, relogio, monkeypatch):
    def falhar(*args):
        raise OSError("sem espaço")

    monkeypatch.setattr(principal.exportar, "registrar_execucao", falhar)
    codigo, saida = _rodar(config, _falha_no_segundo_ncm(CotaEsgotada("429")), relogio)

    assert codigo == 1
    assert any("Falha ao registrar a execução" in linha for linha in saida)
```

- [ ] **Step 2: Rodar**

Run: `.venv/Scripts/python -m pytest tests/test_principal_finalizacao.py -v`
Expected: PASS (todos). Se algum falhar, é um defeito real da Task 8: use superpowers:systematic-debugging, corrija `coletor/principal.py` e rode de novo.

- [ ] **Step 3: Rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -v`
Expected: PASS (todos)

- [ ] **Step 4: Commit**

```bash
git add tests/test_principal_finalizacao.py
git commit -m "test: finalização garantida para cada motivo de parada"
```
(Se `coletor/principal.py` tiver sido corrigido, incluí-lo no `git add` e usar `fix:` na mensagem.)

---

### Task 10: Ponto de entrada `python -m coletor` e sinais

**Files:**
- Create: `coletor/__main__.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `config.carregar_config`, `config.ler_arquivo_env`, `config.ConfigInvalida`, `principal.executar`, `principal.Cancelado`, `api.ClienteCosmos`
- Produces:
  - `main(raiz: Path | None = None, ambiente: Mapping[str, str] | None = None, fabrica_cliente=None, instalar_sinais: bool = True) -> int`
  - `_ao_sinal(numero: int, quadro: object) -> None` (lança `Cancelado`)

- [ ] **Step 1: Escrever os testes**

`tests/test_main.py`:
```python
import pytest

from coletor import __main__ as entrada
from coletor import exportar
from coletor.principal import Cancelado
from tests.ajudantes import ApiFalsa, roteiro_paginas


def _raiz(tmp_path):
    (tmp_path / "ncms_alvo.csv").write_text("ncm;descricao;status\n22030000;Cerveja;alvo\n", encoding="utf-8")
    return tmp_path


def test_config_invalida_retorna_1_sem_criar_arquivos(tmp_path, capsys):
    codigo = entrada.main(raiz=_raiz(tmp_path), ambiente={}, instalar_sinais=False)
    assert codigo == 1
    assert "COSMOS_TOKEN" in capsys.readouterr().err
    assert not (tmp_path / "saida").exists()


def test_execucao_completa_com_api_falsa(tmp_path):
    fabrica = lambda antes: ApiFalsa(antes, roteiro_paginas({"22030000": 2}))
    codigo = entrada.main(raiz=_raiz(tmp_path), ambiente={"COSMOS_TOKEN": "tk"}, fabrica_cliente=fabrica, instalar_sinais=False)
    assert codigo == 0
    assert exportar.ler_csv(tmp_path / "saida" / "execucoes.csv")[-1]["motivo_parada"] == "concluido"


def test_le_token_do_arquivo_env_quando_ambiente_nao_e_passado(tmp_path, monkeypatch):
    raiz = _raiz(tmp_path)
    monkeypatch.delenv("COSMOS_TOKEN", raising=False)
    fabrica = lambda antes: ApiFalsa(antes, roteiro_paginas({"22030000": 1}))
    assert entrada.main(raiz=raiz, fabrica_cliente=fabrica, instalar_sinais=False) == 1
    (raiz / ".env").write_text("COSMOS_TOKEN=do-arquivo\n", encoding="utf-8")
    assert entrada.main(raiz=raiz, fabrica_cliente=fabrica, instalar_sinais=False) == 0


def test_sinal_vira_cancelado():
    with pytest.raises(Cancelado):
        entrada._ao_sinal(15, None)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_main.py -v`
Expected: FAIL com `ImportError: cannot import name '__main__' from 'coletor'` (ou `ModuleNotFoundError`)

- [ ] **Step 3: Implementar**

`coletor/__main__.py`:
```python
"""Entrada: python -m coletor (raiz = pasta atual)."""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path
from typing import Mapping

from coletor import principal
from coletor.api import ClienteCosmos
from coletor.config import ConfigInvalida, carregar_config, ler_arquivo_env


def _ao_sinal(numero: int, quadro: object) -> None:
    raise principal.Cancelado(f"sinal {numero}")


def main(
    raiz: Path | None = None,
    ambiente: Mapping[str, str] | None = None,
    fabrica_cliente: principal.FabricaCliente | None = None,
    instalar_sinais: bool = True,
) -> int:
    raiz = raiz if raiz is not None else Path.cwd()
    if ambiente is None:
        ambiente = {**ler_arquivo_env(raiz / ".env"), **os.environ}
    try:
        config = carregar_config(raiz, ambiente)
    except ConfigInvalida as erro:
        print(f"Configuração inválida: {erro}", file=sys.stderr)
        return 1
    if instalar_sinais:
        signal.signal(signal.SIGTERM, _ao_sinal)
    if fabrica_cliente is None:
        def fabrica_cliente(antes_de_enviar):
            return ClienteCosmos(config.token, antes_de_enviar)
    return principal.executar(config, fabrica_cliente)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_main.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add coletor/__main__.py tests/test_main.py
git commit -m "feat: ponto de entrada python -m coletor com tratamento de sinais"
```

---

### Task 11: Workflow do GitHub Actions e README

**Files:**
- Create: `.github/workflows/coleta.yml`, `README.md`
- Test: `tests/test_workflow.py`

**Interfaces:**
- Consumes: `python -m coletor` (Task 10), secret `COSMOS_TOKEN`
- Produces: workflow `coleta.yml` disparável por `workflow_dispatch`

- [ ] **Step 1: Confirmar as versões atuais das actions e registrar a referência**

Run:
```bash
gh api repos/actions/checkout/releases/latest --jq .tag_name
gh api repos/actions/setup-python/releases/latest --jq .tag_name
```
Usar a **major** retornada (ex.: `v4` → `actions/checkout@v4`) no Step 3. Registrar em `documentos/referencias.md` os dois acessos (`https://api.github.com/repos/actions/checkout/releases/latest` e `.../setup-python/releases/latest`), com data, "Claude", "gh api" e a versão encontrada.

- [ ] **Step 2: Escrever o teste do workflow**

`tests/test_workflow.py`:
```python
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "coleta.yml"


def test_workflow_so_por_disparo_sem_concorrencia_e_commit_sempre():
    conteudo = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in conteudo
    assert "schedule:" not in conteudo
    assert "cancel-in-progress: false" in conteudo
    assert "contents: write" in conteudo
    assert "timeout-minutes" not in conteudo
    assert "COSMOS_TOKEN: ${{ secrets.COSMOS_TOKEN }}" in conteudo
    assert "python -m coletor" in conteudo
    assert "if: always()" in conteudo
    assert "git add dados saida" in conteudo
```

Run: `.venv/Scripts/python -m pytest tests/test_workflow.py -v`
Expected: FAIL com `FileNotFoundError`

- [ ] **Step 3: Criar o workflow**

`.github/workflows/coleta.yml` (trocar `@v4`/`@v5` pelas majors confirmadas no Step 1):
```yaml
name: coleta-diaria

on:
  workflow_dispatch:

concurrency:
  group: coleta-cosmos
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  coletar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Coletar páginas do Cosmos
        env:
          COSMOS_TOKEN: ${{ secrets.COSMOS_TOKEN }}
          PYTHONUNBUFFERED: "1"
        run: python -m coletor

      - name: Salvar dados no repositório
        if: always()
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add dados saida
          if git diff --cached --quiet; then
            echo "Sem mudanças para salvar."
          else
            git commit -m "chore: coleta $(date -u +%Y-%m-%dT%H:%MZ)"
            git push
          fi
```

- [ ] **Step 4: Criar o README**

`README.md`:
````markdown
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
````

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_workflow.py tests/test_seguranca.py -v`
Expected: PASS (todos)

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/coleta.yml README.md tests/test_workflow.py documentos/referencias.md
git commit -m "feat: workflow de coleta disparado por workflow_dispatch e README"
```

---

### Task 12: Verificação, revisões, limpeza, publicação e primeira execução

**Files:**
- Modify: `documentos/plano-e-praticas.md` (seção 8), `documentos/referencias.md` (se houver acessos)
- Delete (com confirmação): `cosmos_bebidas.py`

**Interfaces:**
- Consumes: tudo
- Produces: repositório público no GitHub com secret configurado; instruções para o cron-job.org

- [ ] **Step 1: Suíte completa com cobertura (superpowers:verification-before-completion)**

Run: `.venv/Scripts/python -m pytest --cov=coletor --cov-report=term-missing`
Expected: todos PASS e `Required test coverage of 80% reached`. Se ficar abaixo de 80%, escrever testes para as linhas listadas em `Missing` antes de seguir.

- [ ] **Step 2: Revisões (superpowers:requesting-code-review)**

Pedir uma revisão de código (`ecc:python-reviewer` ou `ecc:code-reviewer`) e uma de segurança (`ecc:security-reviewer`) sobre `git diff` desde o primeiro commit. Foco da segurança: token (`api.py`, `__main__.py`, workflow), escrita de arquivos (`arquivos.py`, `bruto.py`), `.gitignore`. Corrigir CRITICAL e HIGH com TDD (um teste que falha → correção → passa), commitando cada correção como `fix: ...`.

- [ ] **Step 3: Remover o protótipo — CHECKPOINT com a Pilar**

Perguntar à Pilar: "Posso apagar `cosmos_bebidas.py`? O coletor novo o substitui e ele nunca foi commitado." Só com o "sim":
```bash
rm cosmos_bebidas.py
```

- [ ] **Step 4: Atualizar a documentação**

Em `documentos/plano-e-praticas.md`, substituir o conteúdo da seção "## 8. Estado atual dos artefatos" por:
```markdown
## 8. Estado atual dos artefatos

- `coletor/`: coletor da Fase 1 implementado conforme `documentos/specs/2026-09-15-fase1-coleta-design.md`
  e `documentos/planos/2026-09-15-fase1-coleta.md`, com testes (cobertura ≥ 80%).
- `documentos/exploracao/2026-09-15/`: dados de teste de 15/09/2026 (exploratórios, não usados pelo coletor).
- Protótipo `cosmos_bebidas.py`: removido.
- Prática: **não rodar `python -m coletor` localmente** enquanto a coleta diária estiver ativa (cota e estado compartilhados).
```

```bash
git add documentos/plano-e-praticas.md
git commit -m "docs: estado dos artefatos após a implementação da Fase 1"
```

- [ ] **Step 5: Publicar no GitHub — CHECKPOINT com a Pilar (ação externa e pública)**

Mostrar `git status --porcelain --untracked-files=all` e `git ls-files` à Pilar e confirmar o nome do repositório. Só com o "ok":
```bash
gh repo create raspagem-catalogo-bebidas --public --source . --remote origin --push
sed -n 's/^COSMOS_TOKEN=//p' .env | gh secret set COSMOS_TOKEN
gh secret list
```
Expected: `COSMOS_TOKEN` listado. O token **nunca** é impresso.

- [ ] **Step 6: Instruções do cron-job.org para a Pilar (ela configura)**

Entregar à Pilar, preenchendo `{usuario}`:
1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
   - Repository access: **Only select repositories** → `raspagem-catalogo-bebidas`.
   - Permissions: a permissão de repositório **Actions** com escrita. Conferir na documentação do endpoint de dispatch no dia e registrar o acesso em `referencias.md`.
   - Expiration: **≥ 120 dias**. Criar lembrete na agenda 1 semana antes de vencer.
2. cron-job.org → Create cronjob:
   - URL: `https://api.github.com/repos/{usuario}/raspagem-catalogo-bebidas/actions/workflows/coleta.yml/dispatches`
   - Schedule: diário, horário fixo fora da hora cheia (ex.: 03:17, fuso America/Sao_Paulo).
   - Advanced → Request method: **POST**; Headers: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: <versão da documentação no dia>`; Body: `{"ref":"main"}`.
   - Notifications: ativar aviso de falha.
3. **Não** usar o "test run" do cron-job.org antes do Step 7, porque ele dispara uma coleta real.

- [ ] **Step 7: Primeira execução real — CHECKPOINT com a Pilar, nunca antes de 16/09/2026 12:16 BRT**

Com o "ok" da Pilar e depois do horário acima, disparar pelo teste do cron-job.org (valida também o disparo) ou por:
```bash
gh workflow run coleta.yml --ref main
gh run watch
```
Expected no registro: 21 linhas `ncm:... p1/...` (uma por NCM), depois até 3 páginas seguintes, `Parada: limite (24 consultas nesta execução)` e o commit `chore: coleta ...` no repositório. Conferir `saida/conferencia_ncm.csv` (21 NCMs com `total_api`) e `saida/execucoes.csv` (previsão de dias) com a Pilar, e registrar a previsão de dias em `documentos/plano-e-praticas.md`.
