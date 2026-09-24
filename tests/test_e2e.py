"""RN-SDK-06: fumaça contra gateway REAL, só quando as envs existem — o CI
público nunca depende de segredo. models.list não gasta tokens."""
import os

import pytest

from avalonops import Avalon

_BASE = os.environ.get("AVALON_E2E_BASE_URL")
_CHAVE = os.environ.get("AVALON_E2E_API_KEY")


@pytest.mark.skipif(not _BASE or not _CHAVE, reason="AVALON_E2E_BASE_URL/AVALON_E2E_API_KEY ausentes")
def test_models_list_no_gateway_real() -> None:
    client = Avalon(api_key=_CHAVE, base_url=_BASE)
    pagina = client.models.list()
    assert len(pagina.data) >= 0
