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
        responsavel="PILAR",
        ncms=(NcmAlvo("22030000", "Cervejas de malte"), NcmAlvo("22085000", "Gim e genebra")),
        limite_consultas=24,
        espera_maxima_min=120,
        raiz=tmp_path,
    )
