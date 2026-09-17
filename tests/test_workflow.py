from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "coleta.yml"


def test_workflow_so_por_disparo_sem_concorrencia_e_commit_sempre():
    conteudo = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in conteudo
    assert "schedule:" not in conteudo
    assert "cancel-in-progress: false" in conteudo
    assert "contents: write" in conteudo
    assert "timeout-minutes" not in conteudo
    assert "cred: [PILAR]" in conteudo
    assert "max-parallel: 1" in conteudo
    assert "ref: ${{ github.ref_name }}" in conteudo
    assert "COSMOS_TOKEN: ${{ secrets[format('{0}_COSMOS_TOKEN', matrix.cred)] }}" in conteudo
    assert "COLETOR_RESPONSAVEL: ${{ matrix.cred }}" in conteudo
    assert "secrets.PILAR_COSMOS_TOKEN" not in conteudo
    assert "python -m coletor" in conteudo
    assert "if: always()" in conteudo
    assert "git add dados saida" in conteudo
    assert "git pull --rebase" in conteudo
    assert "mkdir -p dados saida" in conteudo
    assert "grep -R -F" in conteudo
    assert "steps.varredura.outcome == 'success'" in conteudo
    assert "python -m coletor --reconciliar --anterior" in conteudo
    assert "git reset --hard origin/main" in conteudo
    assert "actions/upload-artifact@v7" in conteudo
    assert "if: ${{ failure() && steps.varredura.outcome == 'success' }}" in conteudo
    assert "if: failure()" not in conteudo
    assert "for tentativa in 1 2 3 4 5" in conteudo
