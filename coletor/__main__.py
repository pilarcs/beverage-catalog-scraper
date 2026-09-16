"""Entrada: python -m coletor (raiz = pasta atual)."""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path
from typing import Mapping, Sequence

from coletor import principal
from coletor import reconciliar as reconciliar_mod
from coletor.api import ClienteCosmos
from coletor.config import ConfigInvalida, carregar_config, ler_arquivo_env
from coletor.estado import EstadoInvalido


def _ao_sinal(numero: int, quadro: object) -> None:
    raise principal.Cancelado(f"sinal {numero}")


def _analisar_argv(argv: Sequence[str]) -> tuple[bool, Path | None] | None:
    """Devolve (reconciliar?, anterior) ou None se algum argumento for inválido."""
    reconciliar_flag = False
    anterior: Path | None = None
    indice = 0
    while indice < len(argv):
        arg = argv[indice]
        if arg == "--reconciliar":
            reconciliar_flag = True
            indice += 1
        elif arg == "--anterior":
            if indice + 1 >= len(argv):
                return None
            anterior = Path(argv[indice + 1])
            indice += 2
        else:
            return None
    if anterior is not None and not reconciliar_flag:
        return None
    return reconciliar_flag, anterior


def _reconciliar(raiz: Path, anterior: Path | None) -> int:
    try:
        contagens = reconciliar_mod.reconciliar(raiz, anterior)
    except (EstadoInvalido, ConfigInvalida, OSError) as erro:
        print(f"Falha na reconciliação: {erro}", file=sys.stderr)
        return 1
    print(
        "Reconciliado: produtos.csv ({} linhas), gtins.csv ({}), conferencia_ncm.csv ({}), "
        "execucoes.csv ({}), consultas unidas: {}".format(
            contagens["produtos.csv"],
            contagens["gtins.csv"],
            contagens["conferencia_ncm.csv"],
            contagens["execucoes"],
            contagens["consultas_unidas"],
        )
    )
    return 0


def main(
    raiz: Path | None = None,
    ambiente: Mapping[str, str] | None = None,
    fabrica_cliente: principal.FabricaCliente | None = None,
    instalar_sinais: bool = True,
    argv: Sequence[str] | None = None,
) -> int:
    raiz = raiz if raiz is not None else Path.cwd()
    argv = sys.argv[1:] if argv is None else argv
    analisado = _analisar_argv(argv)
    if analisado is None:
        print(f"Argumento inválido: {' '.join(argv)}", file=sys.stderr)
        return 2
    usar_reconciliar, anterior = analisado
    if usar_reconciliar:
        return _reconciliar(raiz, anterior)
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
