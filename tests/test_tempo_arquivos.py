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
