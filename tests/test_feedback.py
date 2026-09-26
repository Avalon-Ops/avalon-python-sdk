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


def test_valor_nao_inteiro_mensagem_especifica_como_no_nucleo(fake: FakeGateway) -> None:
    # Fix I6 da revisão final ("Logs idênticos à Portkey"): o núcleo passa
    # mensagemAoCliente ESPECÍFICA (a regra em si) para valor_invalido — não
    # mais a genérica de politicaDeForma sem 3º argumento.
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=0.5)
    assert capturado.value.status_code == 400
    body = capturado.value.body
    if isinstance(body, str):
        body = json.loads(body)
    assert body.get("erro", {}).get("codigo") == "valor_invalido"
    assert body.get("erro", {}).get("mensagem") == "valor deve ser um inteiro entre -10 e 10."


def test_valor_float_integral_e_aceito_mas_float_fracionario_e_recusado(fake: FakeGateway) -> None:
    # Fix M1 da revisão final: JSON manda 4.0 → o núcleo (JS) recebe o
    # número 4 e Number.isInteger(4) passa; o fake em Python distinguia
    # int/float na marra (isinstance(valor, int) rejeitava 4.0), recusando o
    # que o gateway real aceitaria. `valor.is_integer()` alinha os dois.
    criado = _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=4.0)
    assert criado["valor"] == 4.0

    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=4.5)
    assert capturado.value.status_code == 400


def test_peso_fora_de_0_1_fake_recusa_com_400_peso_invalido_mensagem_especifica(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=1, peso=1.5)
    assert capturado.value.status_code == 400
    body = capturado.value.body
    if isinstance(body, str):
        body = json.loads(body)
    assert body.get("erro", {}).get("codigo") == "peso_invalido"
    # Fix I6 da revisão final: mesmo racional do valor_invalido.
    assert body.get("erro", {}).get("mensagem") == "peso deve ser um número entre 0 e 1."


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


# Fix M2 da revisão final ("Logs idênticos à Portkey"): o núcleo valida
# `metadata` do feedback via validarMetadataDefault nas duas rotas (objeto
# de strings, até 128 caracteres por valor, 400 metadata_invalida com a
# frase genérica) — o fake em Python não validava nada, e a resposta 201
# não ecoava o campo (o núcleo ecoa).
def test_metadata_invalida_chega_cru_quando_nao_e_objeto_de_strings(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(
            request_id=REQUEST_ID_DO_FAKE, valor=1, metadata={"origem": 42}  # type: ignore[dict-item]
        )
    assert capturado.value.status_code == 400
    body = capturado.value.body
    if isinstance(body, str):
        body = json.loads(body)
    assert body.get("erro", {}).get("codigo") == "metadata_invalida"
    # metadata_invalida continua com a frase GENÉRICA — Fix I6 só mudou
    # valor_invalido/peso_invalido.
    assert body.get("erro", {}).get("mensagem") == "A requisição não está no formato aceito pela sua organização."


def test_metadata_invalida_chega_cru_quando_valor_excede_128_caracteres(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=1, metadata={"_user": "a" * 129})
    assert capturado.value.status_code == 400
    superficie = json.dumps({"body": capturado.value.body, "mensagem": str(capturado.value)})
    assert "metadata_invalida" in superficie


def test_resposta_201_ecoa_metadata(fake: FakeGateway) -> None:
    criado = _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=4, metadata={"_user": "ana"})
    assert criado["metadata"] == {"_user": "ana"}


# N3(b) da re-revisão final do Bloco A: o núcleo real SEMPRE devolve
# `metadata` na resposta 201 (objeto vazio quando o campo não veio no
# corpo) — o fake só ecoava quando `metadata` estava presente na requisição,
# omitindo a chave por completo quando ausente.
def test_resposta_201_sempre_tem_metadata_mesmo_quando_ausente_na_requisicao(fake: FakeGateway) -> None:
    criado = _novo(fake).feedback.create(request_id=REQUEST_ID_DO_FAKE, valor=4)
    assert "metadata" not in fake.ultima()["corpo"]
    assert criado["metadata"] == {}
