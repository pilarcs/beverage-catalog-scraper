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
