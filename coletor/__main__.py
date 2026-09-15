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
