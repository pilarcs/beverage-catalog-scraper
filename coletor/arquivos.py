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
