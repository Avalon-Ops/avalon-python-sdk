from collections.abc import Iterator

import pytest

from .fake_gateway import FakeGateway


@pytest.fixture()
def fake() -> Iterator[FakeGateway]:
    servidor = FakeGateway()
    yield servidor
    servidor.parar()
