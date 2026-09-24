import pytest
from openai import APIStatusError

from avalonops import Avalon

from .fake_gateway import REQUEST_ID_DO_FAKE, UUID_INEXISTENTE, FakeGateway


def _novo(fake: FakeGateway) -> Avalon:
    return Avalon(api_key="gov_teste", base_url=fake.url)


def test_envia_o_corpo_exato_sem_peso_e_devolve_o_201(fake: FakeGateway) -> None:
    criado = _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=1)
    ultima = fake.ultima()
    assert ultima["metodo"] == "POST"
    assert ultima["rota"] == "/v1/feedback"
    assert ultima["headers"]["authorization"] == "Bearer gov_teste"
    assert ultima["corpo"] == {"request_id": REQUEST_ID_DO_FAKE, "valor": 1}
    assert criado["logId"] == REQUEST_ID_DO_FAKE


def test_peso_presente_entra_no_corpo(fake: FakeGateway) -> None:
    _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=-0.5, peso=2)
    assert fake.ultima()["corpo"] == {"request_id": REQUEST_ID_DO_FAKE, "valor": -0.5, "peso": 2}


def test_404_chega_cru(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=UUID_INEXISTENTE, valor=1)
    assert capturado.value.status_code == 404


def test_valor_fora_da_faixa_nao_e_validado_no_cliente(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=2)
    assert capturado.value.status_code == 400
    # A prova de que o SDK não validou: o fake RECEBEU valor 2.
    assert fake.ultima()["corpo"]["valor"] == 2
