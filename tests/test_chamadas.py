from __future__ import annotations

import json

import pytest
from openai import APIStatusError

from avalonops import Avalon

from .fake_gateway import REQUEST_ID_DO_FAKE, FakeGateway

MENSAGENS = [{"role": "user", "content": "oi"}]


def _novo(fake: FakeGateway, metadata: dict | None = None) -> Avalon:
    return Avalon(api_key="gov_teste", base_url=fake.url, metadata=metadata)


def test_metadata_do_construtor_vira_x_metadata(fake: FakeGateway) -> None:
    _novo(fake, {"_user": "fabio"}).chat.completions.create(model="@teste/gpt-4", messages=MENSAGENS)
    assert json.loads(fake.ultima()["headers"]["x-metadata"]) == {"_user": "fabio"}


def test_merge_por_chave_e_corpo_sem_metadata(fake: FakeGateway) -> None:
    _novo(fake, {"_user": "fabio", "time": "plataforma"}).chat.completions.create(
        model="@teste/gpt-4", messages=MENSAGENS, metadata={"_user": "lorena"}
    )
    ultima = fake.ultima()
    assert json.loads(ultima["headers"]["x-metadata"]) == {"_user": "lorena", "time": "plataforma"}
    assert "metadata" not in ultima["corpo"]
    assert ultima["corpo"]["model"] == "@teste/gpt-4"


def test_sem_metadata_o_header_nao_vai(fake: FakeGateway) -> None:
    _novo(fake).chat.completions.create(model="@teste/gpt-4", messages=MENSAGENS)
    assert "x-metadata" not in fake.ultima()["headers"]


def test_request_id_na_resposta_nao_stream(fake: FakeGateway) -> None:
    resposta = _novo(fake).chat.completions.create(model="@teste/gpt-4", messages=MENSAGENS)
    assert resposta.request_id == REQUEST_ID_DO_FAKE
    assert resposta.choices[0].message.content == "olá"


def test_request_id_fica_fora_do_model_dump(fake: FakeGateway) -> None:
    """F6: object.__setattr__ mantém o id fora de model_dump()/to_json() —
    paridade com o Node (Object.defineProperty não-enumerável)."""
    resposta = _novo(fake).chat.completions.create(model="@teste/gpt-4", messages=MENSAGENS)
    assert "request_id" not in resposta.model_dump()
    assert resposta.request_id == REQUEST_ID_DO_FAKE


def test_request_id_no_stream_e_chunks_fluem(fake: FakeGateway) -> None:
    stream = _novo(fake).chat.completions.create(model="@teste/gpt-4", messages=MENSAGENS, stream=True)
    texto = "".join(chunk.choices[0].delta.content or "" for chunk in stream)
    assert texto == "olá"
    assert stream.request_id == REQUEST_ID_DO_FAKE  # type: ignore[union-attr]


def test_embeddings_metadata_e_request_id(fake: FakeGateway) -> None:
    resposta = _novo(fake, {"_user": "fabio"}).embeddings.create(
        model="text-embedding-3-small", input="oi"
    )
    assert resposta.request_id == REQUEST_ID_DO_FAKE
    assert fake.ultima()["rota"] == "/v1/embeddings"
    assert json.loads(fake.ultima()["headers"]["x-metadata"]) == {"_user": "fabio"}


def test_metadata_com_acento_sobrevive_ascii_no_header(fake: FakeGateway) -> None:
    resposta = _novo(fake, {"_user": "João"}).chat.completions.create(
        model="@teste/gpt-4", messages=MENSAGENS
    )
    header = fake.ultima()["headers"]["x-metadata"]
    header.encode("ascii")  # não levanta UnicodeEncodeError
    assert json.loads(header)["_user"] == "João"
    assert resposta.choices[0].message.content == "olá"


def test_models_list_cru(fake: FakeGateway) -> None:
    ids = [m.id for m in _novo(fake).models.list()]
    assert ids == ["@teste/gpt-4"]


def test_403_chega_cru_como_erro_do_sdk_openai(fake: FakeGateway) -> None:
    with pytest.raises(APIStatusError) as capturado:
        _novo(fake).chat.completions.create(model="@nega/gpt-4", messages=MENSAGENS)
    assert capturado.value.status_code == 403
    # O corpo {erro:{codigo}} não é a forma OpenAI — basta que UMA superfície
    # do erro (body/mensagem) carregue o código intacto.
    superficie = json.dumps({"body": capturado.value.body, "mensagem": str(capturado.value)})
    assert "modelo_nao_permitido" in superficie
