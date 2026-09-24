"""SDK oficial da AvalonOps — wrapper fino sobre o SDK da OpenAI.

Spec: 2026-09-24-sdks-avalon-design.md (RN-SDK-01..07). A classe Avalon
COMPÕE o client openai (nunca estende): chat/embeddings são embrulhados
(metadata → header x-metadata; x-avalon-request-id → request_id), models é
re-exposto cru, feedback fala com POST /v1/feedback pelo mesmo transporte.
Erros do gateway chegam crus (APIStatusError do SDK openai).
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

import httpx
from openai import OpenAI

CABECALHO_REQUEST_ID = "x-avalon-request-id"

__all__ = ["CABECALHO_REQUEST_ID", "Avalon", "raiz_para_v1"]


def raiz_para_v1(raiz: str) -> str:
    """A raiz do gateway (a MESMA env AVALON_BASE_URL do tutorial) vira a
    base /v1 — sem duplicar quando já termina em /v1 (RN-SDK-02). Nenhuma
    URL default: o produto é auto-hospedado."""
    sem_barra = raiz.rstrip("/")
    return sem_barra if sem_barra.endswith("/v1") else sem_barra + "/v1"


def _headers_com_metadata(
    base: Mapping[str, str],
    por_request: Mapping[str, str] | None,
    extra_headers: Mapping[str, str] | None,
) -> dict[str, str]:
    """Merge por chave: o por-request vence o do construtor chave a chave;
    objeto final vazio → header ausente (RN-SDK-03). httpx codifica headers
    em ASCII — ensure_ascii=True escapa acentos e CJK para \\uXXXX antes de
    a requisição sair; separators compactos deixam o header byte a byte
    igual ao do Node (JSON.stringify + escape manual)."""
    headers = dict(extra_headers or {})
    combinado: dict[str, str] = {**base, **dict(por_request or {})}
    if combinado:
        headers["x-metadata"] = json.dumps(combinado, ensure_ascii=True, separators=(",", ":"))
    return headers


def _anexar_request_id(resposta: Any, cabecalhos: httpx.Headers) -> Any:
    """object.__setattr__ como caminho único: mantém o id fora de
    model_dump()/to_json() — paridade com o Node, que o mantém fora do
    JSON.stringify (Object.defineProperty não-enumerável)."""
    request_id = cabecalhos.get(CABECALHO_REQUEST_ID)
    if request_id is not None:
        object.__setattr__(resposta, "request_id", request_id)
    return resposta


class _Completions:
    def __init__(self, cliente: OpenAI, metadata_base: Mapping[str, str]) -> None:
        self._cliente = cliente
        self._metadata_base = metadata_base

    def create(
        self,
        *,
        metadata: Mapping[str, str] | None = None,
        extra_headers: Mapping[str, str] | None = None,
        **params: Any,
    ) -> Any:
        headers = _headers_com_metadata(self._metadata_base, metadata, extra_headers)
        bruto = self._cliente.chat.completions.with_raw_response.create(
            extra_headers=headers, **params
        )
        return _anexar_request_id(bruto.parse(), bruto.headers)


class _Chat:
    def __init__(self, cliente: OpenAI, metadata_base: Mapping[str, str]) -> None:
        self.completions = _Completions(cliente, metadata_base)


class _Embeddings:
    def __init__(self, cliente: OpenAI, metadata_base: Mapping[str, str]) -> None:
        self._cliente = cliente
        self._metadata_base = metadata_base

    def create(
        self,
        *,
        metadata: Mapping[str, str] | None = None,
        extra_headers: Mapping[str, str] | None = None,
        **params: Any,
    ) -> Any:
        headers = _headers_com_metadata(self._metadata_base, metadata, extra_headers)
        bruto = self._cliente.embeddings.with_raw_response.create(extra_headers=headers, **params)
        return _anexar_request_id(bruto.parse(), bruto.headers)


class _Feedback:
    def __init__(self, cliente: OpenAI) -> None:
        self._cliente = cliente

    def create(self, *, request_id: str, valor: float, peso: float | None = None) -> Any:
        """Espelho campo a campo de POST /v1/feedback — a validação é do
        gateway (RN-SDK-05); 404/400 chegam crus como APIStatusError.
        max_retries=0: é um INSERT sem idempotência no gateway — o retry
        padrão do SDK openai gravaria feedback duas vezes."""
        corpo: dict[str, Any] = {"request_id": request_id, "valor": valor}
        if peso is not None:
            corpo["peso"] = peso
        resposta = self._cliente.post(
            "/feedback", body=corpo, cast_to=httpx.Response, options={"max_retries": 0}
        )
        return resposta.json()


class Avalon:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        chave = api_key if api_key is not None else os.environ.get("AVALON_API_KEY")
        if not chave:
            raise ValueError("api_key ausente: passe api_key= ou defina a env AVALON_API_KEY.")
        raiz = base_url if base_url is not None else os.environ.get("AVALON_BASE_URL")
        if not raiz:
            raise ValueError(
                "base_url ausente: passe base_url= ou defina a env AVALON_BASE_URL "
                "(a raiz do gateway, sem /v1)."
            )
        self._cliente = OpenAI(api_key=chave, base_url=raiz_para_v1(raiz))
        base: dict[str, str] = dict(metadata or {})
        self.chat = _Chat(self._cliente, base)
        self.embeddings = _Embeddings(self._cliente, base)
        self.models = self._cliente.models
        self.feedback = _Feedback(self._cliente)
