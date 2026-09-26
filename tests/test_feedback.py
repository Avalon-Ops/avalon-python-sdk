import json

import pytest
from openai import APIStatusError

from avalonops import Avalon

from .fake_gateway import REQUEST_ID_DO_FAKE, REQUEST_ID_ERRO_500, UUID_INEXISTENTE, FakeGateway


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
    _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=-1, peso=0.5)
    assert fake.ultima()["corpo"] == {"request_id": REQUEST_ID_DO_FAKE, "valor": -1, "peso": 0.5}


def test_404_chega_cru(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=UUID_INEXISTENTE, valor=1)
    assert capturado.value.status_code == 404


def test_valor_fora_da_faixa_nao_e_validado_no_cliente(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=20)
    assert capturado.value.status_code == 400
    # A prova de que o SDK não validou: o fake RECEBEU valor 20.
    assert fake.ultima()["corpo"]["valor"] == 20


def test_valor_nao_inteiro_fake_recusa_com_400_valor_invalido(fake: FakeGateway) -> None:
    # Fidelidade a validacao.ts (núcleo): valor não-inteiro não é validado no
    # cliente, mas o fake precisa recusar como o gateway real recusaria.
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=0.5)
    assert capturado.value.status_code == 400
    superficie = json.dumps({"body": capturado.value.body, "mensagem": str(capturado.value)})
    assert "valor_invalido" in superficie


def test_peso_fora_de_0_1_fake_recusa_com_400_peso_invalido(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=1, peso=1.5)
    assert capturado.value.status_code == 400
    superficie = json.dumps({"body": capturado.value.body, "mensagem": str(capturado.value)})
    assert "peso_invalido" in superficie


def test_peso_zero_e_aceito(fake: FakeGateway) -> None:
    # soma de pesos zero é "sem amostra", não erro (validacao.ts).
    criado = _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=1, peso=0)
    assert fake.ultima()["corpo"] == {"request_id": REQUEST_ID_DO_FAKE, "valor": 1, "peso": 0}
    assert criado["peso"] == 0


def test_retry_desligado_no_feedback_500_chega_cru_e_contagem_e_um(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_ERRO_500, valor=1)
    assert capturado.value.status_code == 500
    assert fake.contagem_feedback() == 1


def test_metadata_presente_entra_no_corpo_campo_a_campo(fake: FakeGateway) -> None:
    _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=4, metadata={"_user": "ana"})
    assert fake.ultima()["corpo"] == {
        "request_id": REQUEST_ID_DO_FAKE,
        "valor": 4,
        "metadata": {"_user": "ana"},
    }


def test_sem_metadata_o_campo_nao_vai_no_corpo(fake: FakeGateway) -> None:
    _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=4)
    assert "metadata" not in fake.ultima()["corpo"]
