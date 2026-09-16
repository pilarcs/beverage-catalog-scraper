from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "coleta.yml"


def test_workflow_so_por_disparo_sem_concorrencia_e_commit_sempre():
    conteudo = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in conteudo
    assert "schedule:" not in conteudo
    assert "cancel-in-progress: false" in conteudo
    assert "contents: write" in conteudo
    assert "timeout-minutes" not in conteudo
    assert conteudo.count("COSMOS_TOKEN: ${{ secrets.PILAR_COSMOS_TOKEN }}") == 2
    assert "COLETOR_RESPONSAVEL: PILAR" in conteudo
    assert "python -m coletor" in conteudo
    assert "if: always()" in conteudo
    assert "git add dados saida" in conteudo
    assert "git pull --rebase" in conteudo
    assert "mkdir -p dados saida" in conteudo
    assert "grep -R -F" in conteudo
    assert "steps.varredura.outcome == 'success'" in conteudo
