import pytest

from avalonops import Avalon, raiz_para_v1

from .fake_gateway import FakeGateway


def _limpar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AVALON_API_KEY", raising=False)
    monkeypatch.delenv("AVALON_BASE_URL", raising=False)


def test_sem_api_key_falha_nomeando_a_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpar(monkeypatch)
    with pytest.raises(ValueError, match="AVALON_API_KEY"):
        Avalon()


def test_sem_base_url_falha_ensinando_que_a_base_e_a_raiz(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpar(monkeypatch)
    with pytest.raises(ValueError, match=r"AVALON_BASE_URL.*sem /v1"):
        Avalon(api_key="gov_x")


def test_as_envs_bastam(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVALON_API_KEY", "gov_env")
    monkeypatch.setenv("AVALON_BASE_URL", "http://127.0.0.1:9")
    Avalon()  # não levanta


def test_raiz_para_v1_anexa_sem_duplicar() -> None:
    assert raiz_para_v1("https://gw.acme.br") == "https://gw.acme.br/v1"
    assert raiz_para_v1("https://gw.acme.br/") == "https://gw.acme.br/v1"
    assert raiz_para_v1("https://gw.acme.br/v1") == "https://gw.acme.br/v1"


def test_construtor_vence_env_mesmo_com_env_invalida(
    monkeypatch: pytest.MonkeyPatch, fake: FakeGateway
) -> None:
    """F8/RN-SDK-02: envs INVÁLIDAS (porta morta) não atrapalham — o
    construtor aponta pro fake e a chamada completa prova que ele venceu."""
    monkeypatch.setenv("AVALON_API_KEY", "gov_env_invalida")
    monkeypatch.setenv("AVALON_BASE_URL", "http://127.0.0.1:9")
    cliente = Avalon(api_key="gov_teste", base_url=fake.url)
    resposta = cliente.chat.completions.create(
        model="@teste/gpt-4", messages=[{"role": "user", "content": "oi"}]
    )
    assert resposta.choices[0].message.content == "olá"
